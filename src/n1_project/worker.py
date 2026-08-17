from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import traceback
from collections import Counter
from contextlib import suppress
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from n1_project.admin import ARTICLE_ACCEPT_PREFIX, ARTICLE_REJECT_PREFIX, AdminNotifier
from n1_project.article_footer import append_dzen_article_footer, dzen_article_footer_reserve_chars
from n1_project.article_channels import (
    ArticleChannel,
    ArticleDueSlot,
    article_channel_from_slot,
    article_channel_review_note,
    classify_message_topic,
    classify_text_topic,
    configured_article_channels,
    daily_article_schedule,
    default_article_channel,
    due_article_slots,
    filter_messages_for_channel,
)
from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import ArticleRecord, QueuedMessage, SourcePost
from n1_project.formatters import prepare_social_post_text
from n1_project.health import run_health_check
from n1_project.images import ArticleImage, PexelsImageProvider, build_pexels_photo_query
from n1_project.llm import TextModel, article_user_prompt, build_text_model, translation_user_prompt
from n1_project.publishers import build_publishers
from n1_project.publishers.telegram import DzenBridgePublisher
from n1_project.scheduler import current_slot, local_now
from n1_project.story_plan import (
    StoryPlan,
    StoryPlanParseError,
    caption_editorial_issues,
    fallback_story_plan,
    parse_story_plan_json,
    selected_messages_for_plan,
    story_candidates_from_messages,
    story_plan_issues,
    story_plan_to_json,
)
from n1_project.telegram_public_preview import fetch_public_preview_posts
from n1_project.telegram_source import TelegramSource
from n1_project.validators import (
    format_dzen_article_text,
    source_has_translatable_english,
    translation_issues,
    trim_dzen_article_to_max_chars,
    validate_dzen_bridge_article,
)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


async def ingest_manual_text(db: QueueDatabase, settings: Settings, text: str, message_id: str | None) -> None:
    source_id = settings.telegram_source_channel_id or "manual"
    source_message_id = message_id or f"manual-{int(time.time())}"
    row_id, inserted = db.upsert_source_post(
        SourcePost(source_channel_id=str(source_id), source_message_id=str(source_message_id), text=text)
    )
    logging.info("manual source message %s as row %s", "inserted" if inserted else "already exists", row_id)


async def ingest_latest(db: QueueDatabase, settings: Settings, limit: int) -> None:
    source = TelegramSource(settings)
    posts = await source.fetch_latest(limit=limit)
    for post in posts:
        row_id, inserted = db.upsert_source_post(post)
        logging.info(
            "source message %s row=%s tg_message_id=%s",
            "inserted" if inserted else "already exists",
            row_id,
            post.source_message_id,
        )
    if not posts:
        logging.info("no text posts found in latest %s source messages", limit)


async def ingest_public_preview(db: QueueDatabase, settings: Settings, limit: int) -> None:
    channel_name = settings.telegram_source_public_name
    if not channel_name:
        raise ValueError("TELEGRAM_SOURCE_PUBLIC_NAME is required for --fetch-public-preview")
    posts = await fetch_public_preview_posts(channel_name, limit=limit)
    for post in posts:
        row_id, inserted = db.upsert_source_post(post)
        logging.info(
            "public preview message %s row=%s tg_message_id=%s",
            "inserted" if inserted else "already exists",
            row_id,
            post.source_message_id,
        )
    if not posts:
        logging.info("no text posts found in public preview for @%s", channel_name)


async def translate_source_text(model: TextModel, source_text: str) -> str:
    if not source_has_translatable_english(source_text):
        return source_text
    return await model.translate_post(source_text)


def prepare_translated_social_text(settings: Settings, text: str) -> str:
    return prepare_social_post_text(
        text,
        max_lines=settings.social_post_max_lines,
        target_max_chars=settings.social_post_target_max_chars,
    )


async def translate_with_single_repair(
    model: TextModel,
    settings: Settings,
    source_text: str,
    *,
    dry_run: bool,
) -> tuple[str, list[str]]:
    translated = prepare_translated_social_text(settings, await translate_source_text(model, source_text))
    issues = [] if dry_run else translation_issues(source_text, translated)
    if not issues or dry_run or not source_has_translatable_english(source_text):
        return translated, issues

    repaired = prepare_translated_social_text(
        settings,
        await model.repair_translation(source_text, translated, issues),
    )
    repaired_issues = translation_issues(source_text, repaired)
    if not repaired_issues:
        logging.info("translation repair succeeded after issues=%s", "; ".join(issues))
        return repaired, []
    return repaired, repaired_issues


def should_notify_translation_failure(attempts_before_failure: int, max_attempts: int) -> bool:
    return attempts_before_failure == 0 or attempts_before_failure + 1 >= max_attempts


def translated_message_topic(message: QueuedMessage, translated_text: str | None = None) -> str | None:
    text = "\n".join(
        part
        for part in (
            translated_text if translated_text is not None else message.translated_text,
            message.source_text,
        )
        if part
    )
    return classify_text_topic(text)


def save_recomputed_message_topic(
    db: QueueDatabase,
    message: QueuedMessage,
    translated_text: str | None = None,
) -> str | None:
    topic = translated_message_topic(message, translated_text=translated_text)
    if topic != message.topic:
        db.set_message_topic(message.id, topic)
    return topic


def ensure_message_topic(db: QueueDatabase, message: QueuedMessage) -> QueuedMessage:
    topic = classify_message_topic(message)
    if topic != message.topic:
        db.set_message_topic(message.id, topic)
        return replace(message, topic=topic)
    return message


async def translate_pending(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    dry_run: bool,
    limit: int,
    admin: AdminNotifier | None = None,
) -> None:
    for message in db.messages_for_translation(limit=limit, max_attempts=settings.translation_max_attempts):
        try:
            translated, issues = await translate_with_single_repair(
                model,
                settings,
                message.source_text,
                dry_run=dry_run,
            )
            if issues:
                raise ValueError(translation_validation_error(issues, translated))
            if dry_run:
                logging.info("dry-run translation row=%s chars=%s", message.id, len(translated))
                print(json.dumps({"row": message.id, "translated_text": translated}, ensure_ascii=False))
            else:
                db.mark_translated(message.id, translated)
                topic = save_recomputed_message_topic(db, message, translated)
                logging.info("translated row=%s chars=%s topic=%s", message.id, len(translated), topic or "unknown")
        except Exception as exc:
            if not dry_run:
                db.mark_failed(message.id, "failed_translation", str(exc))
            logging.exception("translation failed row=%s", message.id)
            if admin:
                if should_notify_translation_failure(message.attempts, settings.translation_max_attempts):
                    await notify_admin(
                        admin,
                        "Translation failed",
                        (
                            f"row={message.id}\n"
                            f"attempt={message.attempts + 1}/{settings.translation_max_attempts}\n"
                            f"error={exc}"
                        ),
                    )


async def translate_one_row(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    row_id: int,
    dry_run: bool,
    force: bool = False,
) -> None:
    message = db.message_by_id(row_id)
    if message is None:
        print(json.dumps({"row": row_id, "ok": False, "error": "row not found"}, ensure_ascii=False, sort_keys=True))
        return
    if not force and message.status not in {"received", "failed_translation"}:
        print(
            json.dumps(
                {
                    "row": row_id,
                    "ok": False,
                    "error": "row is not translatable; status must be received or failed_translation",
                    "status": message.status,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    try:
        translated, issues = await translate_with_single_repair(
            model,
            settings,
            message.source_text,
            dry_run=dry_run,
        )
        if issues:
            raise ValueError(translation_validation_error(issues, translated))
        if not dry_run:
            db.mark_translated(message.id, translated)
            topic = save_recomputed_message_topic(db, message, translated)
        else:
            topic = translated_message_topic(message, translated)
        print(
            json.dumps(
                {
                    "row": message.id,
                    "ok": True,
                    "status": "dry_run" if dry_run else "translated",
                    "saved": not dry_run,
                    "topic": topic,
                    "translated_text": translated,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    except Exception as exc:
        if not dry_run:
            db.mark_failed(message.id, "failed_translation", str(exc))
        logging.exception("translation failed row=%s", message.id)
        print(json.dumps({"row": message.id, "ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))


async def publish_pending(
    db: QueueDatabase,
    settings: Settings,
    dry_run: bool,
    limit: int,
    message_id: int | None = None,
    admin: AdminNotifier | None = None,
) -> None:
    publishers = build_publishers(settings, dry_run=dry_run)
    order = settings.publish_order
    messages = db.messages_for_publishing(limit=limit, message_id=message_id)
    if message_id is not None and not messages:
        print(
            json.dumps(
                {
                    "row": message_id,
                    "ok": False,
                    "error": "row is not publishable; it must exist, have translated_text, and be translated or failed_retry",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    for message in messages:
        text = message.translated_text or ""
        all_ok = True
        already_published = db.successful_publish_platforms(message.id)
        for platform in order:
            if platform in already_published:
                logging.info("publish skip row=%s platform=%s already published", message.id, platform)
                if dry_run:
                    print(
                        json.dumps(
                            {
                                "row": message.id,
                                "platform": platform,
                                "ok": True,
                                "destination_id": "already-published",
                                "skipped": True,
                            },
                            ensure_ascii=False,
                        )
                    )
                continue
            publisher = publishers.get(platform)
            if not publisher:
                error = f"publisher not configured: {platform}"
                all_ok = False
                if not dry_run:
                    db.mark_failed(message.id, "failed_retry", error)
                logging.error("%s row=%s", error, message.id)
                if admin:
                    await notify_admin(admin, "Publisher not configured", f"row={message.id}\nplatform={platform}")
                break
            try:
                result = await publisher.publish_text(text)
            except Exception as exc:
                result = publisher_result_error(platform, exc)
            if dry_run:
                print(
                    json.dumps(
                        {
                            "row": message.id,
                            "platform": platform,
                            "ok": result.ok,
                            "destination_id": result.destination_id,
                            "error": result.error,
                            "payload": result.payload,
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                db.record_publish_result(
                    message_id=message.id,
                    platform=platform,
                    status="published" if result.ok else "failed",
                    destination_id=result.destination_id,
                    error=result.error,
                    payload=result.payload,
                )
            if not result.ok:
                all_ok = False
                if not dry_run:
                    db.mark_failed(message.id, "failed_retry", result.error or "unknown publish error")
                logging.error("publish failed row=%s platform=%s error=%s", message.id, platform, result.error)
                if admin:
                    await notify_admin(
                        admin,
                        "Publish failed",
                        f"row={message.id}\nplatform={platform}\nerror={result.error or 'unknown publish error'}",
                    )
                break
            logging.info("publish ok row=%s platform=%s destination=%s", message.id, platform, result.destination_id)
        if all_ok and not dry_run:
            db.mark_published(message.id)


async def publish_text_once(settings: Settings, text: str, dry_run: bool) -> None:
    publishers = build_publishers(settings, dry_run=dry_run)
    for platform in settings.publish_order:
        publisher = publishers.get(platform)
        if not publisher:
            print(json.dumps({"platform": platform, "ok": False, "error": "publisher not configured"}, ensure_ascii=False))
            break
        result = await publisher.publish_text(text)
        print(
            json.dumps(
                {
                    "platform": platform,
                    "ok": result.ok,
                    "destination_id": result.destination_id,
                    "error": result.error,
                    "payload": result.payload,
                },
                ensure_ascii=False,
            )
        )
        if not result.ok:
            break


async def ingest_from_mode(db: QueueDatabase, settings: Settings, mode: str, limit: int) -> None:
    if mode == "none":
        return
    if mode == "mtproto":
        await ingest_latest(db, settings, limit)
        return
    if mode == "public-preview":
        await ingest_public_preview(db, settings, limit)
        return
    raise ValueError(f"Unknown source mode: {mode}")


def publisher_result_error(platform: str, exc: Exception):
    from n1_project.domain import PublishResult

    return PublishResult(platform=platform, ok=False, error=str(exc))


def translation_validation_error(issues: list[str], translated: str) -> str:
    output = translated.replace("\r\n", "\n").replace("\r", "\n")
    output = output.replace("\n", "\\n")
    if len(output) > 500:
        output = output[:497] + "..."
    return f"{'; '.join(issues)} | output={output}"


def exception_report(exc: Exception, *, max_chars: int = 3000) -> str:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
    if len(trace) > max_chars:
        trace = "[trimmed]\n" + trace[-max_chars:]
    return f"type={type(exc).__name__}\nerror={exc}\n\n{trace}"


RU_MONTH_NAMES = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def dzen_article_date_label(settings: Settings, slot_key: str | None = None, now: datetime | None = None) -> str:
    current = now or local_now(settings.app_timezone)
    if slot_key:
        try:
            current = datetime.strptime(slot_key.split()[0], "%Y-%m-%d")
        except (IndexError, ValueError):
            logging.warning("could not parse Dzen article slot date: %s", slot_key)
    return f"{current.day} {RU_MONTH_NAMES[current.month]} {current.year} года"


RU_MONTH_NAMES = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def dzen_article_date_label(settings: Settings, slot_key: str | None = None, now: datetime | None = None) -> str:
    current = now or local_now(settings.app_timezone)
    if slot_key:
        try:
            current = datetime.strptime(slot_key.split()[0], "%Y-%m-%d")
        except (IndexError, ValueError):
            logging.warning("could not parse Dzen article slot date: %s", slot_key)
    return f"{current.day} {RU_MONTH_NAMES[current.month]} {current.year} года"


def dzen_article_effective_max_chars(settings: Settings) -> int:
    if settings.dzen_article_image_enabled:
        return min(settings.dzen_article_target_max_chars, settings.telegram_photo_caption_max_chars)
    return settings.dzen_article_target_max_chars


async def plan_dzen_story_with_validation(
    model: TextModel,
    messages: list[QueuedMessage],
    settings: Settings,
    *,
    review_note: str | None = None,
    article_date_label: str | None = None,
    article_channel: ArticleChannel | None = None,
    max_attempts: int = 2,
) -> tuple[StoryPlan, list[str]]:
    candidates = story_candidates_from_messages(messages)
    if not candidates:
        raise ValueError("no story candidates available")

    note = article_channel_review_note(article_channel, review_note) if article_channel else review_note
    channel_note = article_channel.topic_hint if article_channel else None
    effective_max_chars = dzen_article_effective_max_chars(settings)
    effective_min_chars = min(settings.dzen_article_target_min_chars, effective_max_chars)
    issues: list[str] = []

    for attempt in range(1, max_attempts + 1):
        try:
            raw_plan = await model.plan_dzen_story(
                candidates,
                min_chars=effective_min_chars,
                max_chars=effective_max_chars,
                review_note=note,
                article_date_label=article_date_label,
                channel_note=channel_note,
            )
            return parse_story_plan_json(raw_plan, candidates), []
        except (StoryPlanParseError, NotImplementedError, ValueError) as exc:
            issues = [str(exc)]
            logging.warning("Dzen story plan validation failed attempt=%s issues=%s", attempt, "; ".join(issues))
            note = (
                "Предыдущий story plan не прошел редакторскую проверку.\n"
                f"Проблемы: {'; '.join(issues)}.\n"
                "Верни новый JSON-план. Если cluster нельзя доказать, выбери mode=\"single\"."
            )
            if article_channel:
                note = article_channel_review_note(article_channel, note)

    fallback = fallback_story_plan(candidates)
    fallback_issues = story_plan_issues(fallback, candidates)
    if fallback_issues:
        return fallback, fallback_issues
    logging.warning("Dzen story plan fell back to single message id=%s", fallback.selected_message_ids[0])
    return fallback, []


async def draft_dzen_article_with_validation(
    model: TextModel,
    posts: list[str],
    settings: Settings,
    *,
    review_note: str | None = None,
    article_date_label: str | None = None,
    article_channel: ArticleChannel | None = None,
    story_plan: StoryPlan | None = None,
    slot_key: str | None = None,
    max_attempts: int = 3,
) -> tuple[str, list[str]]:
    note = article_channel_review_note(article_channel, review_note) if article_channel else review_note
    article = ""
    issues: list[str] = []
    effective_max_chars = dzen_article_effective_max_chars(settings)
    effective_min_chars = min(settings.dzen_article_target_min_chars, effective_max_chars)
    footer_reserve = dzen_article_footer_reserve_chars(settings, slot_key)
    body_max_chars = max(1, effective_max_chars - footer_reserve)
    draft_min_chars = min(max(500, effective_min_chars - footer_reserve), body_max_chars)
    draft_max_chars = body_max_chars
    for attempt in range(1, max_attempts + 1):
        article = await model.write_dzen_article(
            posts,
            min_chars=draft_min_chars,
            max_chars=draft_max_chars,
            review_note=note,
            article_date_label=article_date_label,
            story_plan=story_plan,
        )
        article_body = format_dzen_article_text(article, article_date_label=article_date_label)
        article = append_dzen_article_footer(article_body, settings, slot_key)
        issues = validate_dzen_bridge_article(
            article,
            min_chars=effective_min_chars,
            max_chars=effective_max_chars,
        )
        if story_plan:
            issues.extend(caption_editorial_issues(article, story_plan))
        if issues and len(article) > effective_max_chars:
            trimmed_body = trim_dzen_article_to_max_chars(article_body, body_max_chars)
            if trimmed_body != article_body:
                article = append_dzen_article_footer(trimmed_body, settings, slot_key)
                issues = validate_dzen_bridge_article(
                    article,
                    min_chars=effective_min_chars,
                    max_chars=effective_max_chars,
                )
                if story_plan:
                    issues.extend(caption_editorial_issues(article, story_plan))
                if not issues:
                    logging.info("Dzen article draft trimmed to fit max_chars=%s", effective_max_chars)
                    return article, []
        if not issues:
            return article, []
        note = (
            "Предыдущий caption не прошел валидацию и должен быть переписан.\n"
            f"Проблемы проверки: {'; '.join(issues)}.\n"
            "Верни новый caption, где первое предложение - короткий заголовок до 140 символов, "
            "без ссылок, без вопросительного знака и без переобещания. "
            "Не используй видимые шаблонные метки `Что случилось`, `Почему важно`, `Что смотреть`. "
            "Уложись в заданный диапазон длины, докажи тезис через выбранные источники и сохраняй только факты из исходных постов."
        )
        if article_channel:
            note = article_channel_review_note(article_channel, note)
        elif review_note:
            note = review_note + "\n\n" + note
        logging.warning("Dzen article draft validation failed attempt=%s issues=%s", attempt, "; ".join(issues))
    return article, issues


def build_admin_notifier(settings: Settings, dry_run: bool = False) -> AdminNotifier:
    return AdminNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.admin_telegram_chat_id,
        enabled=settings.admin_notifications_enabled,
        max_chars=settings.telegram_max_text_chars,
        dry_run=dry_run,
    )


async def notify_admin(admin: AdminNotifier, title: str, body: str, *, level: str = "error") -> None:
    if not admin.configured:
        return
    try:
        result = await admin.notify(title, body, level=level)
        if not result.ok:
            logging.warning("admin notification failed: %s", result.error)
    except Exception:
        logging.exception("admin notification failed")


def dzen_publisher_for_channel(settings: Settings, channel: ArticleChannel, dry_run: bool = False):
    channel_specific_token = settings.dzen_article_bot_tokens.get(channel.key)
    if channel.bridge_chat_id and (
        channel_specific_token or channel.bridge_chat_id != settings.dzen_telegram_bridge_chat_id
    ):
        return DzenBridgePublisher(
            bot_token=channel.bot_token,
            chat_id=channel.bridge_chat_id,
            max_chars=settings.dzen_post_max_text_chars,
            dry_run=dry_run,
            parse_mode=settings.dzen_article_parse_mode or None,
            caption_max_chars=settings.telegram_photo_caption_max_chars,
        )
    publisher = build_publishers(settings, dry_run=dry_run).get("dzen")
    if publisher:
        return publisher
    return None


async def publish_dzen_article_payload(publisher, article: str, image: ArticleImage | None):
    if image and hasattr(publisher, "publish_photo"):
        logging.info(
            "Dzen article publish payload method=photo chars=%s caption_max=%s image_query=%s",
            len(article),
            getattr(publisher, "caption_max_chars", "unknown"),
            image.query,
        )
        return await publisher.publish_photo(image.url, article)
    if image:
        logging.warning(
            "Dzen publisher does not support photo payloads; falling back to text chars=%s image_query=%s",
            len(article),
            image.query,
        )
    logging.info("Dzen article publish payload method=text chars=%s image_available=%s", len(article), bool(image))
    return await publisher.publish_text(article)


def dzen_photo_caption_error(article: str, settings: Settings, image: ArticleImage | None) -> str | None:
    if not image:
        return None
    length = len(article)
    if length <= settings.telegram_photo_caption_max_chars:
        return None
    return f"Dzen photo caption too long: {length} chars; max is {settings.telegram_photo_caption_max_chars}"


async def publish_approved_dzen_article(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    article: ArticleRecord,
    dry_run: bool,
) -> None:
    channel = article_channel_from_slot(settings, article.slot_key)
    publisher = dzen_publisher_for_channel(settings, channel, dry_run=dry_run)
    if not publisher:
        error = f"Dzen bridge is not configured for {channel.key}"
        db.update_article_status(article.id, "failed_publish", error=error)
        await notify_admin(admin, "Dzen publish not configured", error)
        raise ValueError(error)

    image = None
    if article.image_url:
        image = ArticleImage(
            url=article.image_url,
            query=article.image_query or "",
        )
    caption_error = dzen_photo_caption_error(article.text, settings, image)
    if caption_error:
        db.update_article_status(article.id, "failed_validation", error=caption_error)
        await notify_admin(admin, "Dzen article caption too long", f"article_id={article.id}\n{caption_error}")
        logging.error(
            "Dzen article caption too long article_id=%s channel=%s chars=%s max=%s image_query=%s",
            article.id,
            channel.key,
            len(article.text),
            settings.telegram_photo_caption_max_chars,
            image.query if image else None,
        )
        raise ValueError(caption_error)
    result = await publish_dzen_article_payload(publisher, article.text, image)
    if dry_run:
        print(
            json.dumps(
                {
                    "platform": "dzen",
                    "ok": result.ok,
                    "article": article.text,
                    "image_url": article.image_url,
                    "image_query": article.image_query,
                },
                ensure_ascii=False,
            )
        )
        return
    db.update_article_status(
        article.id,
        "published" if result.ok else "failed_publish",
        destination_id=result.destination_id,
        error=result.error,
    )
    if not result.ok:
        await notify_admin(admin, "Dzen article publish failed", result.error or "unknown publish error")
        raise RuntimeError(f"Dzen publish failed: {result.error}")
    logging.info(
        "Dzen article published article_id=%s channel=%s destination=%s",
        article.id,
        channel.key,
        result.destination_id,
    )


def dzen_article_candidate_messages(
    db: QueueDatabase,
    settings: Settings,
    article_channel: ArticleChannel | None = None,
) -> list[QueuedMessage]:
    limit = max(1, settings.dzen_article_candidate_limit)
    newest_messages = db.translated_posts_for_article(limit=limit, newest_first=True)
    messages = [ensure_message_topic(db, message) for message in reversed(newest_messages)]
    if article_channel and len(configured_article_channels(settings)) > 1:
        messages = filter_messages_for_channel(messages, article_channel.key)
    return messages


def dominant_article_topic(messages: list[QueuedMessage], article: str, channel: ArticleChannel) -> str | None:
    topics = [classify_message_topic(message) for message in messages]
    counts = Counter(topic for topic in topics if topic)
    if counts:
        return str(counts.most_common(1)[0][0])
    detected = classify_text_topic(article)
    if detected:
        return detected
    return channel.key if channel.key in {"markets", "russia", "energy", "tech"} else None


async def select_dzen_article_image(
    settings: Settings,
    *,
    article: str,
    messages: list[QueuedMessage],
    channel: ArticleChannel,
    story_plan: StoryPlan | None = None,
    dry_run: bool,
) -> ArticleImage | None:
    if not settings.dzen_article_image_enabled:
        logging.info("Dzen image selection skipped channel=%s reason=disabled", channel.key)
        return None
    provider = PexelsImageProvider(
        api_key=settings.pexels_api_key,
        base_url=settings.pexels_api_base_url,
        orientation=settings.pexels_photo_orientation,
        size=settings.pexels_photo_size,
        per_page=settings.pexels_photo_per_page,
        dry_run=dry_run,
    )
    if not provider.configured:
        logging.warning("Dzen image publishing enabled, but PEXELS_API_KEY is empty")
        return None
    query = story_plan.image_query.strip() if story_plan and story_plan.image_query.strip() else ""
    query_source = "story_plan" if query else "fallback"
    if not query:
        topic = dominant_article_topic(messages, article, channel)
        query = build_pexels_photo_query(
            [article, *(message.translated_text or message.source_text for message in messages)],
            topic=topic,
        )
    logging.info(
        "Dzen image lookup channel=%s query=%s source=%s dry_run=%s",
        channel.key,
        query,
        query_source,
        dry_run,
    )
    try:
        image = await provider.search_photo(query)
    except Exception as exc:
        logging.warning("Pexels image lookup failed query=%s error=%s", query, exc)
        return None
    if not image:
        logging.warning("Pexels image lookup returned no photos query=%s", query)
        return None
    logging.info("Dzen image selected channel=%s query=%s source_url=%s", channel.key, image.query, image.source_url)
    return image


def append_image_credit_if_fits(article: str, settings: Settings, image: ArticleImage | None) -> str:
    if not image or not settings.dzen_article_image_credit_enabled or not image.credit:
        return article
    candidate = article.rstrip() + "\n\n" + image.credit
    max_chars = min(settings.dzen_article_target_max_chars, settings.telegram_photo_caption_max_chars)
    if len(candidate) <= max_chars:
        return candidate
    return article


def should_auto_publish_dzen_article(settings: Settings, now: datetime | None = None) -> bool:
    current = now or local_now(settings.app_timezone)
    return settings.dzen_article_auto_publish_weekends and current.weekday() >= 5


async def publish_generated_dzen_article(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    article: str,
    message_ids: list[int],
    dry_run: bool,
    slot_key: str | None,
    article_channel: ArticleChannel | None = None,
    image: ArticleImage | None = None,
    story_plan: StoryPlan | None = None,
) -> int:
    channel = article_channel or article_channel_from_slot(settings, slot_key)
    publisher = dzen_publisher_for_channel(settings, channel, dry_run=dry_run)
    if not publisher:
        raise ValueError(f"Dzen bridge is not configured for {channel.key}")
    caption_error = dzen_photo_caption_error(article, settings, image)
    if caption_error:
        if dry_run:
            raise ValueError(caption_error)
        article_id = db.record_article(
            text=article,
            status="failed_validation",
            error=caption_error,
            message_ids=[],
            selected_message_ids=list(story_plan.selected_message_ids) if story_plan else message_ids,
            slot_key=slot_key,
            image_url=image.url if image else None,
            image_query=image.query if image else None,
            image_credit=image.credit if image else None,
            plan_json=story_plan_to_json(story_plan) if story_plan else None,
        )
        await notify_admin(admin, "Dzen article caption too long", f"article_id={article_id}\nchannel={channel.key}\n{caption_error}")
        logging.error(
            "Dzen article caption too long article_id=%s channel=%s chars=%s max=%s image_query=%s",
            article_id,
            channel.key,
            len(article),
            settings.telegram_photo_caption_max_chars,
            image.query if image else None,
        )
        return article_id
    result = await publish_dzen_article_payload(publisher, article, image)
    if dry_run:
        print(
            json.dumps(
                {
                    "platform": "dzen",
                    "channel": channel.key,
                    "ok": result.ok,
                    "article": article,
                    "story_plan": story_plan_to_json(story_plan) if story_plan else None,
                    "selected_message_ids": list(story_plan.selected_message_ids) if story_plan else message_ids,
                    "image_url": image.url if image else None,
                    "image_query": image.query if image else None,
                },
                ensure_ascii=False,
            )
        )
        return 0
    article_id = db.record_article(
        text=article,
        status="published" if result.ok else "failed_publish",
        destination_id=result.destination_id,
        error=result.error,
        message_ids=message_ids if result.ok else [],
        selected_message_ids=list(story_plan.selected_message_ids) if story_plan else message_ids,
        slot_key=slot_key,
        image_url=image.url if image else None,
        image_query=image.query if image else None,
        image_credit=image.credit if image else None,
        plan_json=story_plan_to_json(story_plan) if story_plan else None,
    )
    if not result.ok:
        await notify_admin(admin, "Dzen article publish failed", result.error or "unknown publish error")
        raise RuntimeError(f"Dzen publish failed: {result.error}")
    logging.info(
        "Dzen article published article_id=%s channel=%s destination=%s",
        article_id,
        channel.key,
        result.destination_id,
    )
    return article_id


async def generate_dzen_article(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    dry_run: bool,
    force: bool = False,
    slot_key: str | None = None,
    article_channel: ArticleChannel | None = None,
) -> None:
    channel = article_channel or article_channel_from_slot(settings, slot_key)
    if slot_key and not dry_run and db.article_slot_status(slot_key) in {"published", "pending_review"}:
        logging.info("skip Dzen article: slot already handled %s status=%s", slot_key, db.article_slot_status(slot_key))
        return
    messages = dzen_article_candidate_messages(db, settings, channel)
    if not messages:
        logging.info("no translated posts available for Dzen article channel=%s", channel.key)
        return
    if len(messages) < settings.dzen_article_min_posts and not force:
        logging.info(
            "skip Dzen article channel=%s: %s posts available, minimum is %s",
            channel.key,
            len(messages),
            settings.dzen_article_min_posts,
        )
        return
    date_label = dzen_article_date_label(settings, slot_key=slot_key)
    story_plan, plan_issues = await plan_dzen_story_with_validation(
        model,
        messages,
        settings,
        article_date_label=date_label,
        article_channel=channel,
    )
    selected_messages = selected_messages_for_plan(messages, story_plan)
    selected_message_ids = [message.id for message in selected_messages]
    plan_json = story_plan_to_json(story_plan)
    if plan_issues and not dry_run:
        article_id = db.record_article(
            text="",
            status="failed_validation",
            error="; ".join(plan_issues),
            message_ids=[],
            selected_message_ids=selected_message_ids,
            slot_key=slot_key,
            plan_json=plan_json,
            increment_generation_attempt=True,
        )
        await notify_admin(
            admin,
            "Dzen story plan validation failed",
            f"article_id={article_id}\nchannel={channel.key}\nissues={'; '.join(plan_issues)}",
        )
        return
    if plan_issues:
        logging.warning("dry-run Dzen story plan validation issues: %s", "; ".join(plan_issues))
    if not selected_messages:
        logging.warning("Dzen story plan selected no usable source messages channel=%s", channel.key)
        return

    posts = [message.translated_text or "" for message in selected_messages]
    article, issues = await draft_dzen_article_with_validation(
        model,
        posts,
        settings,
        article_date_label=date_label,
        article_channel=channel,
        story_plan=story_plan,
        slot_key=slot_key,
    )
    if issues and not dry_run:
        article_id = db.record_article(
            text=article,
            status="failed_validation",
            error="; ".join(issues),
            message_ids=[],
            selected_message_ids=selected_message_ids,
            slot_key=slot_key,
            plan_json=plan_json,
            increment_generation_attempt=True,
        )
        await notify_admin(
            admin,
            "Dzen article validation failed",
            f"article_id={article_id}\nchannel={channel.key}\nissues={'; '.join(issues)}",
        )
        logging.error(
            "Dzen article validation failed article_id=%s channel=%s issues=%s",
            article_id,
            channel.key,
            "; ".join(issues),
        )
        return
    if issues:
        logging.warning("dry-run Dzen article validation issues: %s", "; ".join(issues))

    image = await select_dzen_article_image(
        settings,
        article=article,
        messages=selected_messages,
        channel=channel,
        story_plan=story_plan,
        dry_run=dry_run,
    )
    if settings.dzen_article_image_required and not image and not dry_run:
        article_id = db.record_article(
            text=article,
            status="failed_image",
            error="Pexels image lookup returned no usable photo",
            message_ids=[],
            selected_message_ids=selected_message_ids,
            slot_key=slot_key,
            plan_json=plan_json,
            increment_generation_attempt=True,
        )
        await notify_admin(
            admin,
            "Dzen article image failed",
            f"article_id={article_id}\nchannel={channel.key}\nslot={slot_key or 'manual'}",
        )
        return
    article = append_image_credit_if_fits(article, settings, image)

    if dry_run:
        print(
            json.dumps(
                {
                    "platform": "dzen",
                    "channel": channel.key,
                    "ok": True,
                    "article": article,
                    "story_plan": plan_json,
                    "selected_message_ids": selected_message_ids,
                    "image_url": image.url if image else None,
                    "image_query": image.query if image else None,
                },
                ensure_ascii=False,
            )
        )
        return

    if settings.dzen_article_review_enabled and not should_auto_publish_dzen_article(settings):
        if not admin.configured:
            raise ValueError("Dzen article review is enabled but ADMIN_TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN is missing")
        existing = db.article_for_slot(slot_key) if slot_key else None
        attempt = (existing.review_attempts if existing else 0) + 1
        if attempt > settings.dzen_article_review_max_attempts:
            raise ValueError(f"Dzen article review exceeded max attempts: {settings.dzen_article_review_max_attempts}")
        article_id = db.record_article(
            text=article,
            status="pending_review",
            message_ids=selected_message_ids,
            selected_message_ids=selected_message_ids,
            slot_key=slot_key,
            review_attempts=attempt,
            image_url=image.url if image else None,
            image_query=image.query if image else None,
            image_credit=image.credit if image else None,
            plan_json=plan_json,
        )
        result = await admin.send_article_review(
            article_id=article_id,
            article_text=article,
            attempt=attempt,
            slot_key=f"{channel.name} / {slot_key or 'manual'}",
        )
        if not result.ok:
            db.update_article_status(article_id, "failed_review_notify", error=result.error)
            raise RuntimeError(f"Could not send article review message: {result.error}")
        if result.destination_id:
            db.update_article_review_message(article_id, admin.chat_id, result.destination_id)
        logging.info("Dzen article queued for review article_id=%s attempt=%s", article_id, attempt)
        return

    article_id = await publish_generated_dzen_article(
        db,
        settings,
        admin,
        article,
        message_ids=selected_message_ids,
        dry_run=dry_run,
        slot_key=slot_key,
        article_channel=channel,
        image=image,
        story_plan=story_plan,
    )
    if settings.dzen_article_review_enabled and should_auto_publish_dzen_article(settings):
        await notify_admin(
            admin,
            "Dzen article auto-published",
            (
                f"article_id={article_id}\nchannel={channel.key}\nslot={slot_key or 'manual'}\n"
                f"source_candidates={len(messages)}\nselected_messages={len(selected_message_ids)}"
            ),
            level="info",
        )


async def process_timed_out_article_reviews(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
) -> None:
    hours = settings.dzen_article_review_timeout_hours
    if hours <= 0:
        return
    for article in db.pending_review_articles_older_than(hours):
        reason = f"review timed out after {hours} hours"
        db.update_article_status(article.id, "rejected_timeout", error=reason)
        if admin.configured and article.review_chat_id and article.review_message_id:
            await admin.edit_message_text(
                article.review_chat_id,
                article.review_message_id,
                f"Dzen article #{article.id} rejected automatically: no response within {hours} hours.",
            )
        await notify_admin(
            admin,
            "Dzen article review timed out",
            f"article_id={article.id}\nslot={article.slot_key or 'manual'}\n{reason}",
            level="warning",
        )


async def process_admin_callbacks(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    dry_run: bool,
    update_timeout_seconds: int = 0,
) -> None:
    if not admin.configured:
        return
    offset_raw = db.get_state("admin_telegram_update_offset")
    offset = int(offset_raw) if offset_raw else None
    updates = await admin.get_callback_updates(offset, timeout_seconds=update_timeout_seconds)
    for update in updates:
        update_id = int(update.get("update_id", 0))
        try:
            callback = update.get("callback_query") or {}
            data = str(callback.get("data") or "")
            callback_id = str(callback.get("id") or "")
            message = callback.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = str(chat.get("id") or "")
            message_id = str(message.get("message_id") or "")
            if admin.chat_id and chat_id != str(admin.chat_id):
                if callback_id:
                    await admin.answer_callback(callback_id, "Эта кнопка не из админского чата.")
                continue
            if data.startswith(ARTICLE_ACCEPT_PREFIX):
                article_id = int(data.removeprefix(ARTICLE_ACCEPT_PREFIX))
                await handle_article_accept(db, settings, admin, article_id, chat_id, message_id, callback_id, dry_run)
            elif data.startswith(ARTICLE_REJECT_PREFIX):
                article_id = int(data.removeprefix(ARTICLE_REJECT_PREFIX))
                await handle_article_reject(db, settings, model, admin, article_id, chat_id, message_id, callback_id)
        except Exception as exc:
            logging.exception("admin callback failed update_id=%s", update_id)
            await notify_admin(admin, "Admin callback failed", f"update_id={update_id}\nerror={exc}")
        finally:
            db.set_state("admin_telegram_update_offset", str(update_id + 1))


async def poll_admin_callbacks_forever(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    dry_run: bool,
) -> None:
    if not admin.configured:
        logging.info("admin callback long-poll disabled: admin notifications are not configured")
        return
    timeout_seconds = max(1, settings.admin_callback_poll_timeout_seconds)
    logging.info("starting admin callback long-poll timeout_seconds=%s", timeout_seconds)
    while True:
        try:
            await process_admin_callbacks(
                db,
                settings,
                model,
                admin,
                dry_run=dry_run,
                update_timeout_seconds=timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logging.exception("admin callback long-poll failed")
            await notify_admin(admin, "Admin callback polling failed", exception_report(exc))
            await asyncio.sleep(2)


async def handle_article_accept(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    article_id: int,
    chat_id: str,
    message_id: str,
    callback_id: str,
    dry_run: bool,
) -> None:
    article = db.article_by_id(article_id)
    if article is None:
        if callback_id:
            await admin.answer_callback(callback_id, "Статья не найдена.")
        return
    if article.status != "pending_review":
        if callback_id:
            await admin.answer_callback(callback_id, f"Статус статьи: {article.status}")
        return
    await publish_approved_dzen_article(db, settings, admin, article, dry_run=dry_run)
    if callback_id:
        await admin.answer_callback(callback_id, "Принято. Отправлено в Dzen.")
    await admin.edit_message_text(chat_id, message_id, f"Dzen-статья #{article_id} принята и отправлена.")


async def handle_article_reject(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    article_id: int,
    chat_id: str,
    message_id: str,
    callback_id: str,
) -> None:
    article = db.article_by_id(article_id)
    if article is None:
        if callback_id:
            await admin.answer_callback(callback_id, "Статья не найдена.")
        return
    if article.status != "pending_review":
        if callback_id:
            await admin.answer_callback(callback_id, f"Статус статьи: {article.status}")
        return
    if article.review_attempts >= settings.dzen_article_review_max_attempts:
        db.update_article_status(article.id, "rejected", error="review max attempts reached")
        if callback_id:
            await admin.answer_callback(callback_id, "Лимит вариантов исчерпан.")
        await admin.edit_message_text(chat_id, message_id, f"Dzen-статья #{article_id} отклонена. Лимит вариантов исчерпан.")
        return

    messages = db.messages_for_article(article.id, limit=50)
    if not messages:
        error = "No source messages linked to rejected article"
        db.update_article_status(article.id, "failed_regeneration", error=error)
        if callback_id:
            await admin.answer_callback(callback_id, "Нет исходных постов для нового варианта.")
        await notify_admin(admin, "Dzen article regeneration failed", f"article_id={article.id}\n{error}")
        return

    review_note = (
        "Предыдущий черновик отклонен редактором. Сделай заметно другой и более сильный вариант. "
        "Улучши заголовок и первый экран, сохраняй каждый факт привязанным к источникам, "
        "не повторяй формулировки отклоненного текста и сделай русский стиль живее и прямее."
    )
    channel = article_channel_from_slot(settings, article.slot_key)
    date_label = dzen_article_date_label(settings, slot_key=article.slot_key)
    story_plan, plan_issues = await plan_dzen_story_with_validation(
        model,
        messages,
        settings,
        review_note=review_note,
        article_date_label=date_label,
        article_channel=channel,
    )
    selected_messages = selected_messages_for_plan(messages, story_plan)
    selected_message_ids = [message.id for message in selected_messages]
    plan_json = story_plan_to_json(story_plan)
    if plan_issues or not selected_messages:
        issue_text = "; ".join(plan_issues or ["story plan selected no usable source messages"])
        db.update_article_status(article.id, "failed_validation", error=issue_text)
        if callback_id:
            await admin.answer_callback(callback_id, "Новый story plan не прошел проверку.")
        await notify_admin(admin, "Regenerated Dzen story plan failed", issue_text)
        return

    posts = [message.translated_text or "" for message in selected_messages]
    new_text, issues = await draft_dzen_article_with_validation(
        model,
        posts,
        settings,
        review_note=review_note,
        article_date_label=date_label,
        article_channel=channel,
        story_plan=story_plan,
        slot_key=article.slot_key,
    )
    if issues:
        db.update_article_status(article.id, "failed_validation", error="; ".join(issues))
        if callback_id:
            await admin.answer_callback(callback_id, "Новый вариант не прошел валидацию.")
        await notify_admin(admin, "Regenerated Dzen article validation failed", "; ".join(issues))
        return

    image = await select_dzen_article_image(
        settings,
        article=new_text,
        messages=selected_messages,
        channel=channel,
        story_plan=story_plan,
        dry_run=False,
    )
    if settings.dzen_article_image_required and not image:
        db.update_article_status(article.id, "failed_image", error="Pexels image lookup returned no usable photo")
        if callback_id:
            await admin.answer_callback(callback_id, "Не удалось подобрать картинку Pexels.")
        await notify_admin(admin, "Regenerated Dzen article image failed", f"article_id={article.id}")
        return
    new_text = append_image_credit_if_fits(new_text, settings, image)

    attempt = article.review_attempts + 1
    db.record_article(
        text=new_text,
        status="pending_review",
        message_ids=selected_message_ids,
        selected_message_ids=selected_message_ids,
        slot_key=article.slot_key,
        review_attempts=attempt,
        review_chat_id=chat_id,
        review_message_id=message_id,
        image_url=image.url if image else None,
        image_query=image.query if image else None,
        image_credit=image.credit if image else None,
        plan_json=plan_json,
    )
    await admin.edit_message_text(chat_id, message_id, f"Dzen-статья #{article_id} отклонена. Генерирую вариант #{attempt}.")
    result = await admin.send_article_review(
        article_id=article.id,
        article_text=new_text,
        attempt=attempt,
        slot_key=f"{channel.name} / {article.slot_key or 'manual'}",
    )
    if result.ok and result.destination_id:
        db.update_article_review_message(article.id, admin.chat_id, result.destination_id)
    if callback_id:
        await admin.answer_callback(callback_id, "Отклонено. Новый вариант отправлен.")


def print_status(db: QueueDatabase, settings: Settings) -> None:
    today = local_now(settings.app_timezone).date()
    data = {
        "db_path": str(settings.db_path),
        "source_fetch_mode": settings.source_fetch_mode,
        "publish_order": settings.publish_order,
        "dzen_article_review_enabled": settings.dzen_article_review_enabled,
        "dzen_article_footer": {
            "enabled": settings.dzen_article_footer_enabled,
            "policy": settings.dzen_article_footer_policy,
            "rotate": settings.dzen_article_footer_rotate,
            "links_configured": {
                "telegram": bool(settings.dzen_article_footer_telegram_url),
                "vk": bool(settings.dzen_article_footer_vk_url),
                "max": bool(settings.dzen_article_footer_max_url),
            },
        },
        "dzen_article_image": {
            "enabled": settings.dzen_article_image_enabled,
            "required": settings.dzen_article_image_required,
            "pexels_ready": bool(settings.pexels_api_key),
            "orientation": settings.pexels_photo_orientation,
            "size": settings.pexels_photo_size,
        },
        "dzen_article_effective_max_chars": dzen_article_effective_max_chars(settings),
        "dzen_article_channels": [
            {
                "key": channel.key,
                "name": channel.name,
                "bridge_configured": bool(channel.bridge_chat_id),
                "bot_configured": bool(channel.bot_token),
                "bot_source": "channel"
                if channel.key in settings.dzen_article_bot_tokens
                else "default"
                if channel.bot_token
                else None,
                "windows": list(channel.windows),
            }
            for channel in configured_article_channels(settings)
        ],
        "dzen_article_schedule_today": [
            {
                "channel": slot.channel.key,
                "slot_key": slot.slot_key,
                "window": slot.window,
                "publish_time": slot.publish_time,
            }
            for slot in daily_article_schedule(settings, today)
        ],
        "message_status": db.status_counts(),
        "publish_status": db.publish_status_counts(),
        "article_status": db.article_status_counts(),
    }
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def print_messages(db: QueueDatabase, limit: int) -> None:
    rows = []
    for message in db.recent_messages(limit=limit):
        rows.append(
            {
                "id": message.id,
                "source_channel_id": message.source_channel_id,
                "source_message_id": message.source_message_id,
                "status": message.status,
                "topic": message.topic,
                "attempts": message.attempts,
                "last_error": message.last_error,
                "source_text": message.source_text,
                "translated_text": message.translated_text,
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def print_failed_translations(db: QueueDatabase, limit: int) -> None:
    rows = []
    for message in db.failed_translation_messages(limit=limit):
        rows.append(
            {
                "id": message.id,
                "source_channel_id": message.source_channel_id,
                "source_message_id": message.source_message_id,
                "status": message.status,
                "topic": message.topic,
                "attempts": message.attempts,
                "last_error": message.last_error,
                "source_text": message.source_text,
                "translated_text": message.translated_text,
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def print_articles(db: QueueDatabase, limit: int) -> None:
    rows = []
    for article in db.recent_articles(limit=limit):
        text_preview = " ".join(article.text.split())
        rows.append(
            {
                "id": article.id,
                "slot_key": article.slot_key,
                "status": article.status,
                "destination_id": article.destination_id,
                "error": article.error,
                "review_attempts": article.review_attempts,
                "generation_attempts": article.generation_attempts,
                "created_at": article.created_at,
                "updated_at": article.updated_at,
                "image_configured": bool(article.image_url),
                "image_query": article.image_query,
                "selected_message_ids": article.selected_message_ids_json,
                "plan_json": article.plan_json,
                "text_preview": text_preview[:500],
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def manual_article_channels(settings: Settings, channel_key: str | None) -> list[ArticleChannel]:
    channels = configured_article_channels(settings)
    if not channel_key:
        return [default_article_channel(settings)]
    normalized = channel_key.strip().lower()
    if normalized == "all":
        return channels
    for channel in channels:
        if channel.key == normalized:
            return [channel]
    available = ", ".join(channel.key for channel in channels)
    raise ValueError(f"Unknown article channel: {channel_key}. Available: {available}, all")


def set_translation_from_cli(db: QueueDatabase, settings: Settings, row_id: int, text: str, force: bool = False) -> None:
    prepared = prepare_social_post_text(
        text,
        max_lines=settings.social_post_max_lines,
        target_max_chars=settings.social_post_target_max_chars,
    )
    message = db.message_by_id(row_id)
    if message is None:
        print(json.dumps({"row": row_id, "ok": False, "error": "row not found"}, ensure_ascii=False, sort_keys=True))
        return
    issues = [] if force else translation_issues(message.source_text, prepared)
    if issues:
        print(
            json.dumps(
                {
                    "row": row_id,
                    "ok": False,
                    "error": "; ".join(issues),
                    "translated_text": prepared,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    db.set_manual_translation(row_id, prepared)
    topic = save_recomputed_message_topic(db, message, prepared)
    print(
        json.dumps(
            {
                "row": row_id,
                "ok": True,
                "status": "translated",
                "topic": topic,
                "translated_text": prepared,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


async def print_translation_prompt_preview(settings: Settings, source_text: str | None, from_public_preview: bool, limit: int) -> None:
    items: list[dict[str, str | None]] = []
    if source_text:
        items.append({"source_message_id": "manual", "text": source_text})
    elif from_public_preview:
        posts = await fetch_public_preview_posts(settings.telegram_source_public_name, limit=limit)
        items.extend({"source_message_id": post.source_message_id, "text": post.text} for post in posts)
    else:
        raise ValueError("--print-translation-prompt requires --source-text or --fetch-public-preview")

    for item in items:
        print(
            json.dumps(
                {
                    "source_message_id": item["source_message_id"],
                    "prompt": translation_user_prompt(str(item["text"])),
                },
                ensure_ascii=False,
            )
        )


def print_article_prompt_preview(db: QueueDatabase, settings: Settings, limit: int) -> None:
    messages = list(reversed(db.translated_posts_for_article(limit=limit, newest_first=True)))
    candidates = story_candidates_from_messages(messages)
    if not candidates:
        raise ValueError("No translated posts available for article prompt preview")
    story_plan = fallback_story_plan(candidates)
    selected_messages = selected_messages_for_plan(messages, story_plan)
    posts = [message.translated_text or "" for message in selected_messages]
    print(
        json.dumps(
            {
                "post_count": len(posts),
                "story_plan": story_plan_to_json(story_plan),
                "prompt": article_user_prompt(
                    posts,
                    min_chars=min(settings.dzen_article_target_min_chars, dzen_article_effective_max_chars(settings)),
                    max_chars=dzen_article_effective_max_chars(settings),
                    article_date_label=dzen_article_date_label(settings),
                    story_plan=story_plan,
                ),
            },
            ensure_ascii=False,
        )
    )


async def approve_article_from_cli(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    article_id: int,
    dry_run: bool,
) -> None:
    article = db.article_by_id(article_id)
    if article is None:
        print(json.dumps({"article_id": article_id, "ok": False, "error": "article not found"}, ensure_ascii=False))
        return
    if article.status != "pending_review":
        print(
            json.dumps(
                {
                    "article_id": article_id,
                    "ok": False,
                    "error": "article is not pending_review",
                    "status": article.status,
                },
                ensure_ascii=False,
            )
        )
        return
    await publish_approved_dzen_article(db, settings, admin, article, dry_run=dry_run)
    print(
        json.dumps(
            {
                "article_id": article_id,
                "ok": True,
                "status": "dry_run" if dry_run else "published",
            },
            ensure_ascii=False,
        )
    )


def due_article_slot(settings: Settings, now: datetime | None = None) -> str | None:
    if not settings.dzen_daily_articles_enabled:
        return None
    current = now or local_now(settings.app_timezone)
    slot = current_slot(current, settings.dzen_daily_article_times)
    if not slot:
        return None
    return f"{current.date().isoformat()} {slot}"


FINISHED_ARTICLE_SLOT_STATUSES = frozenset({"published", "pending_review"})


def article_slot_is_open(db: QueueDatabase, settings: Settings, slot: ArticleDueSlot) -> bool:
    """Report whether a due slot still needs an article today.

    A slot closes once it is published or waiting for admin review, and also
    once it has burned its attempt budget, so a persistent failure cannot keep
    calling the article model every poll until midnight.
    """
    status, attempts = db.article_slot_state(slot.slot_key)
    if status in FINISHED_ARTICLE_SLOT_STATUSES:
        return False
    max_attempts = settings.dzen_article_slot_max_attempts
    if max_attempts > 0 and attempts >= max_attempts:
        return False
    return True


async def handle_article_slot_failure(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    slot: ArticleDueSlot,
    exc: Exception,
    *,
    dry_run: bool,
) -> None:
    """Record one failed article slot without killing the rest of the pass."""
    logging.exception(
        "Dzen article slot failed channel=%s slot=%s",
        slot.channel.key,
        slot.slot_key,
    )
    summary = f"{type(exc).__name__}: {exc}".strip()
    article_id: int | None = None
    attempts = 0
    if not dry_run:
        article_id = db.record_article(
            text="",
            status="failed_generation",
            error=summary[:1000],
            message_ids=[],
            selected_message_ids=[],
            slot_key=slot.slot_key,
            increment_generation_attempt=True,
        )
        _, attempts = db.article_slot_state(slot.slot_key)
    remaining = max(0, settings.dzen_article_slot_max_attempts - attempts)
    await notify_admin(
        admin,
        "Dzen article slot failed",
        f"slot={slot.slot_key}\n"
        f"channel={slot.channel.key}\n"
        f"article_id={article_id}\n"
        f"attempt={attempts} of {settings.dzen_article_slot_max_attempts} (remaining={remaining})\n"
        f"{summary}\n\n"
        f"{exception_report(exc)}",
    )


async def run_processing_pass(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    *,
    source_mode: str,
    dry_run: bool,
    limit: int,
    article: bool,
    force_article: bool,
    article_channel: str | None,
    skip_publish: bool,
    skip_translate: bool,
    process_callbacks: bool = True,
) -> None:
    if process_callbacks:
        await process_admin_callbacks(db, settings, model, admin, dry_run=dry_run)
    await process_timed_out_article_reviews(db, settings, admin)
    await ingest_from_mode(db, settings, source_mode, limit)
    if skip_translate:
        return
    await translate_pending(db, settings, model, dry_run=dry_run, limit=limit, admin=admin)
    if not skip_publish:
        await publish_pending(db, settings, dry_run=dry_run, limit=limit, admin=admin)

    scheduled_slots = due_article_slots(
        settings,
        slot_is_open=lambda slot: article_slot_is_open(db, settings, slot),
    )
    for scheduled_slot in scheduled_slots:
        logging.info(
            "Dzen article slot due: channel=%s slot=%s time=%s window=%s",
            scheduled_slot.channel.key,
            scheduled_slot.slot_key,
            scheduled_slot.publish_time,
            scheduled_slot.window,
        )
        try:
            await generate_dzen_article(
                db,
                settings,
                model,
                admin,
                dry_run=dry_run,
                force=force_article,
                slot_key=scheduled_slot.slot_key,
                article_channel=scheduled_slot.channel,
            )
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            await handle_article_slot_failure(db, settings, admin, scheduled_slot, exc, dry_run=dry_run)

    if article and not scheduled_slots:
        for manual_channel in manual_article_channels(settings, article_channel):
            manual_slot_key = f"manual-{manual_channel.key}-{int(time.time())}" if not dry_run else None
            await generate_dzen_article(
                db,
                settings,
                model,
                admin,
                dry_run=dry_run,
                force=force_article,
                slot_key=manual_slot_key,
                article_channel=manual_channel,
            )


async def amain() -> None:
    configure_output_encoding()
    parser = argparse.ArgumentParser(description="N1 publishing worker")
    parser.add_argument("--env", default=".env", help="Path to .env")
    parser.add_argument("--once", action="store_true", help="Run one pass and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously until interrupted")
    parser.add_argument("--dry-run", action="store_true", help="Do not call external publish APIs or the configured LLM")
    parser.add_argument("--source-text", help="Manually enqueue one source text")
    parser.add_argument("--source-message-id", help="Manual source message id for --source-text")
    parser.add_argument("--fetch-latest", action="store_true", help="Fetch latest Telegram source posts via MTProto")
    parser.add_argument("--fetch-public-preview", action="store_true", help="Fetch latest public Telegram preview posts")
    parser.add_argument(
        "--source-mode",
        choices=["mtproto", "public-preview", "none"],
        help="Source mode for --loop or a single explicit pass",
    )
    parser.add_argument("--limit", type=int, help="Processing limit")
    parser.add_argument("--row-id", type=int, help="Queue row id for row-specific commands")
    parser.add_argument("--translate-row", type=int, help="Translate one queued row and mark it translated")
    parser.add_argument("--force-translate", action="store_true", help="Allow --translate-row to overwrite an existing translation")
    parser.add_argument("--set-translation", help="Set translated text for --row-id and mark it translated")
    parser.add_argument("--translation-file", help="Read translated text for --row-id from a UTF-8 file")
    parser.add_argument("--publish-row", type=int, help="Publish one translated queue row")
    parser.add_argument("--skip-publish", action="store_true", help="Ingest/translate but do not publish")
    parser.add_argument("--ingest-only", action="store_true", help="Only ingest source rows; do not translate or publish")
    parser.add_argument("--article", action="store_true", help="Generate and send one Dzen bridge article")
    parser.add_argument("--force-article", action="store_true", help="Generate Dzen article even below DZEN_ARTICLE_MIN_POSTS")
    parser.add_argument("--approve-article", type=int, help="Publish a pending Dzen article by id")
    parser.add_argument("--status", action="store_true", help="Print queue status and exit")
    parser.add_argument("--list-messages", action="store_true", help="Print recent queued messages and exit")
    parser.add_argument("--list-articles", action="store_true", help="Print recent Dzen articles and exit")
    parser.add_argument("--list-failed-translations", action="store_true", help="Print failed translation rows and exit")
    parser.add_argument("--reset-failed", action="store_true", help="Move failed translation/publish rows back to retryable states")
    parser.add_argument("--doctor", action="store_true", help="Check env and provider readiness")
    parser.add_argument("--print-translation-prompt", action="store_true", help="Print the translation prompt without calling an LLM")
    parser.add_argument("--print-article-prompt", action="store_true", help="Print the Dzen article prompt without calling an LLM")
    parser.add_argument("--article-channel", help="Manual article channel key for --article, or all")
    args = parser.parse_args()

    settings = Settings.load(Path(args.env))
    configure_logging(settings.log_level)

    if args.doctor:
        print(json.dumps(await run_health_check(settings), ensure_ascii=False, indent=2, sort_keys=True))
        return

    if args.print_translation_prompt:
        await print_translation_prompt_preview(
            settings,
            source_text=args.source_text,
            from_public_preview=args.fetch_public_preview,
            limit=args.limit if args.limit is not None else settings.worker_batch_limit,
        )
        return

    model = build_text_model(settings, dry_run=args.dry_run)
    admin = build_admin_notifier(settings, dry_run=args.dry_run)

    if args.dry_run and args.source_text:
        translated = prepare_translated_social_text(settings, await translate_source_text(model, args.source_text))
        print(json.dumps({"translated_text": translated}, ensure_ascii=False))
        await publish_text_once(settings, translated, dry_run=True)
        if args.article:
            article_date_label = dzen_article_date_label(settings)
            article = await model.write_dzen_article(
                [translated],
                min_chars=settings.dzen_article_target_min_chars,
                max_chars=settings.dzen_article_target_max_chars,
                article_date_label=article_date_label,
            )
            article = format_dzen_article_text(article, article_date_label=article_date_label)
            print(json.dumps({"article": article}, ensure_ascii=False))
        return

    db = QueueDatabase(settings.db_path)
    db.initialize()

    if args.status:
        print_status(db, settings)
        return

    if args.list_messages:
        print_messages(db, limit=args.limit if args.limit is not None else 10)
        return

    if args.list_articles:
        print_articles(db, limit=args.limit if args.limit is not None else 10)
        return

    if args.list_failed_translations:
        print_failed_translations(db, limit=args.limit if args.limit is not None else 20)
        return

    if args.translate_row is not None:
        await translate_one_row(db, settings, model, args.translate_row, dry_run=args.dry_run, force=args.force_translate)
        return

    if args.set_translation or args.translation_file:
        if args.row_id is None:
            raise ValueError("--row-id is required with --set-translation or --translation-file")
        text = args.set_translation
        if args.translation_file:
            text = Path(args.translation_file).read_text(encoding="utf-8")
        if text is None:
            raise ValueError("No translation text provided")
        set_translation_from_cli(db, settings, args.row_id, text, force=args.force_translate)
        return

    if args.publish_row is not None:
        await publish_pending(
            db,
            settings,
            dry_run=args.dry_run,
            limit=1,
            message_id=args.publish_row,
            admin=admin,
        )
        return

    if args.print_article_prompt:
        print_article_prompt_preview(
            db,
            settings,
            limit=args.limit if args.limit is not None else settings.dzen_article_candidate_limit,
        )
        return

    if args.approve_article is not None:
        await approve_article_from_cli(db, settings, admin, args.approve_article, dry_run=args.dry_run)
        return

    if args.reset_failed:
        reset_translation = db.reset_failed_translations()
        reset_publish = db.reset_failed_publishing()
        print(
            json.dumps(
                {
                    "reset_failed_translation": reset_translation,
                    "reset_failed_publishing": reset_publish,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    if args.source_text:
        await ingest_manual_text(db, settings, args.source_text, args.source_message_id)

    if args.fetch_latest:
        source_mode = "mtproto"
    elif args.fetch_public_preview:
        source_mode = "public-preview"
    elif args.source_mode:
        source_mode = args.source_mode
    else:
        source_mode = settings.source_fetch_mode if args.loop else "none"

    article_only = (
        args.article
        and not args.loop
        and not args.fetch_latest
        and not args.fetch_public_preview
        and not args.source_text
        and source_mode == "none"
    )
    effective_skip_publish = args.skip_publish or article_only

    if args.loop:
        logging.info("starting worker loop source_mode=%s poll_seconds=%s", source_mode, settings.worker_poll_seconds)
        callback_task = asyncio.create_task(
            poll_admin_callbacks_forever(db, settings, model, admin, dry_run=args.dry_run)
        )
        try:
            while True:
                try:
                    await run_processing_pass(
                        db,
                        settings,
                        model,
                        admin,
                        source_mode=source_mode,
                        dry_run=args.dry_run,
                        limit=args.limit if args.limit is not None else settings.worker_batch_limit,
                        article=args.article,
                        force_article=args.force_article,
                        article_channel=args.article_channel,
                        skip_publish=args.skip_publish,
                        skip_translate=args.ingest_only,
                        process_callbacks=False,
                    )
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    logging.exception("worker pass failed")
                    await notify_admin(admin, "Worker pass failed", exception_report(exc))
                await asyncio.sleep(settings.worker_poll_seconds)
        finally:
            callback_task.cancel()
            with suppress(asyncio.CancelledError):
                await callback_task
    else:
        await run_processing_pass(
            db,
            settings,
            model,
            admin,
            source_mode=source_mode,
            dry_run=args.dry_run,
            limit=args.limit if args.limit is not None else settings.worker_batch_limit,
            article=args.article,
            force_article=args.force_article,
            article_channel=args.article_channel,
            skip_publish=effective_skip_publish,
            skip_translate=args.ingest_only,
        )


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
