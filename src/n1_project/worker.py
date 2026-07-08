from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from n1_project.admin import ARTICLE_ACCEPT_PREFIX, ARTICLE_REJECT_PREFIX, AdminNotifier
from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import ArticleRecord, QueuedMessage, SourcePost
from n1_project.formatters import prepare_social_post_text
from n1_project.health import run_health_check
from n1_project.llm import TextModel, article_user_prompt, build_text_model, translation_user_prompt
from n1_project.publishers import build_publishers
from n1_project.scheduler import current_slot, local_now
from n1_project.telegram_public_preview import fetch_public_preview_posts
from n1_project.telegram_source import TelegramSource
from n1_project.validators import (
    format_dzen_article_text,
    source_has_translatable_english,
    translation_issues,
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


def should_notify_translation_failure(attempts_before_failure: int, max_attempts: int) -> bool:
    return attempts_before_failure == 0 or attempts_before_failure + 1 >= max_attempts


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
            translated = prepare_social_post_text(
                await translate_source_text(model, message.source_text),
                max_lines=settings.social_post_max_lines,
                target_max_chars=settings.social_post_target_max_chars,
            )
            issues = [] if dry_run else translation_issues(message.source_text, translated)
            if issues:
                raise ValueError(translation_validation_error(issues, translated))
            if dry_run:
                logging.info("dry-run translation row=%s chars=%s", message.id, len(translated))
                print(json.dumps({"row": message.id, "translated_text": translated}, ensure_ascii=False))
            else:
                db.mark_translated(message.id, translated)
                logging.info("translated row=%s chars=%s", message.id, len(translated))
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
        translated = prepare_social_post_text(
            await translate_source_text(model, message.source_text),
            max_lines=settings.social_post_max_lines,
            target_max_chars=settings.social_post_target_max_chars,
        )
        issues = [] if dry_run else translation_issues(message.source_text, translated)
        if issues:
            raise ValueError(translation_validation_error(issues, translated))
        if not dry_run:
            db.mark_translated(message.id, translated)
        print(
            json.dumps(
                {
                    "row": message.id,
                    "ok": True,
                    "status": "dry_run" if dry_run else "translated",
                    "saved": not dry_run,
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


async def draft_dzen_article_with_validation(
    model: TextModel,
    posts: list[str],
    settings: Settings,
    *,
    review_note: str | None = None,
    article_date_label: str | None = None,
    max_attempts: int = 3,
) -> tuple[str, list[str]]:
    note = review_note
    article = ""
    issues: list[str] = []
    for attempt in range(1, max_attempts + 1):
        article = await model.write_dzen_article(
            posts,
            min_chars=settings.dzen_article_target_min_chars,
            max_chars=settings.dzen_article_target_max_chars,
            review_note=note,
            article_date_label=article_date_label,
        )
        article = format_dzen_article_text(article, article_date_label=article_date_label)
        issues = validate_dzen_bridge_article(
            article,
            min_chars=settings.dzen_article_target_min_chars,
            max_chars=settings.dzen_article_target_max_chars,
        )
        if not issues:
            return article, []
        note = (
            "The previous draft failed validation and must be rewritten.\n"
            f"Validation issues: {'; '.join(issues)}.\n"
            "Return a new article where the first sentence is a short Dzen title under 140 characters, "
            "contains no links, and ends as its own sentence before the opening paragraph. "
            "Keep the article within the requested character limits and preserve only source-grounded facts."
        )
        if review_note:
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


async def publish_approved_dzen_article(
    db: QueueDatabase,
    settings: Settings,
    admin: AdminNotifier,
    article: ArticleRecord,
    dry_run: bool,
) -> None:
    publisher = build_publishers(settings, dry_run=dry_run).get("dzen")
    if not publisher:
        error = "DZEN_TELEGRAM_BRIDGE_CHAT_ID or Telegram bot token is not configured"
        db.update_article_status(article.id, "failed_publish", error=error)
        await notify_admin(admin, "Dzen publish not configured", error)
        raise ValueError(error)

    result = await publisher.publish_text(article.text)
    if dry_run:
        print(json.dumps({"platform": "dzen", "ok": result.ok, "article": article.text}, ensure_ascii=False))
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
    logging.info("Dzen article published article_id=%s destination=%s", article.id, result.destination_id)


def dzen_article_candidate_messages(db: QueueDatabase, settings: Settings) -> list[QueuedMessage]:
    limit = max(1, settings.dzen_article_candidate_limit)
    newest_messages = db.translated_posts_for_article(limit=limit, newest_first=True)
    return list(reversed(newest_messages))


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
) -> int:
    publisher = build_publishers(settings, dry_run=dry_run).get("dzen")
    if not publisher:
        raise ValueError("DZEN_TELEGRAM_BRIDGE_CHAT_ID or Telegram bot token is not configured")
    result = await publisher.publish_text(article)
    if dry_run:
        print(json.dumps({"platform": "dzen", "ok": result.ok, "article": article}, ensure_ascii=False))
        return 0
    article_id = db.record_article(
        text=article,
        status="published" if result.ok else "failed_publish",
        destination_id=result.destination_id,
        error=result.error,
        message_ids=message_ids if result.ok else [],
        slot_key=slot_key,
    )
    if not result.ok:
        await notify_admin(admin, "Dzen article publish failed", result.error or "unknown publish error")
        raise RuntimeError(f"Dzen publish failed: {result.error}")
    logging.info("Dzen article published article_id=%s destination=%s", article_id, result.destination_id)
    return article_id


async def generate_dzen_article(
    db: QueueDatabase,
    settings: Settings,
    model: TextModel,
    admin: AdminNotifier,
    dry_run: bool,
    force: bool = False,
    slot_key: str | None = None,
) -> None:
    if slot_key and not dry_run and db.article_slot_status(slot_key) in {"published", "pending_review"}:
        logging.info("skip Dzen article: slot already handled %s status=%s", slot_key, db.article_slot_status(slot_key))
        return
    messages = dzen_article_candidate_messages(db, settings)
    if not messages:
        logging.info("no translated posts available for Dzen article")
        return
    if len(messages) < settings.dzen_article_min_posts and not force:
        logging.info(
            "skip Dzen article: %s posts available, minimum is %s",
            len(messages),
            settings.dzen_article_min_posts,
        )
        return
    posts = [message.translated_text or "" for message in messages]
    message_ids = [message.id for message in messages]
    date_label = dzen_article_date_label(settings, slot_key=slot_key)
    article, issues = await draft_dzen_article_with_validation(
        model,
        posts,
        settings,
        article_date_label=date_label,
    )
    if issues and not dry_run:
        article_id = db.record_article(
            text=article,
            status="failed_validation",
            error="; ".join(issues),
            message_ids=[],
            slot_key=slot_key,
        )
        await notify_admin(
            admin,
            "Dzen article validation failed",
            f"article_id={article_id}\nissues={'; '.join(issues)}",
        )
        raise ValueError(f"Dzen article validation failed article_id={article_id}: {'; '.join(issues)}")
    if issues:
        logging.warning("dry-run Dzen article validation issues: %s", "; ".join(issues))

    if dry_run:
        print(json.dumps({"platform": "dzen", "ok": True, "article": article}, ensure_ascii=False))
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
            message_ids=message_ids,
            slot_key=slot_key,
            review_attempts=attempt,
        )
        result = await admin.send_article_review(
            article_id=article_id,
            article_text=article,
            attempt=attempt,
            slot_key=slot_key,
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
        message_ids=message_ids,
        dry_run=dry_run,
        slot_key=slot_key,
    )
    if settings.dzen_article_review_enabled and should_auto_publish_dzen_article(settings):
        await notify_admin(
            admin,
            "Dzen article auto-published",
            f"article_id={article_id}\nslot={slot_key or 'manual'}\nsource_candidates={len(message_ids)}",
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

    posts = [message.translated_text or "" for message in messages]
    review_note = (
        "Previous draft was rejected by the editor. Generate a meaningfully different and stronger version. "
        "Improve the title/card, keep every fact source-grounded, avoid repeating the rejected wording, "
        "and make the Russian prose more human and direct."
    )
    new_text, issues = await draft_dzen_article_with_validation(
        model,
        posts,
        settings,
        review_note=review_note,
        article_date_label=dzen_article_date_label(settings, slot_key=article.slot_key),
    )
    if issues:
        db.update_article_status(article.id, "failed_validation", error="; ".join(issues))
        if callback_id:
            await admin.answer_callback(callback_id, "Новый вариант не прошел валидацию.")
        await notify_admin(admin, "Regenerated Dzen article validation failed", "; ".join(issues))
        return

    attempt = article.review_attempts + 1
    db.record_article(
        text=new_text,
        status="pending_review",
        message_ids=[message.id for message in messages],
        slot_key=article.slot_key,
        review_attempts=attempt,
        review_chat_id=chat_id,
        review_message_id=message_id,
    )
    await admin.edit_message_text(chat_id, message_id, f"Dzen-статья #{article_id} отклонена. Генерирую вариант #{attempt}.")
    result = await admin.send_article_review(
        article_id=article.id,
        article_text=new_text,
        attempt=attempt,
        slot_key=article.slot_key,
    )
    if result.ok and result.destination_id:
        db.update_article_review_message(article.id, admin.chat_id, result.destination_id)
    if callback_id:
        await admin.answer_callback(callback_id, "Отклонено. Новый вариант отправлен.")


def print_status(db: QueueDatabase, settings: Settings) -> None:
    data = {
        "db_path": str(settings.db_path),
        "source_fetch_mode": settings.source_fetch_mode,
        "publish_order": settings.publish_order,
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
                "attempts": message.attempts,
                "last_error": message.last_error,
                "source_text": message.source_text,
                "translated_text": message.translated_text,
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


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
    print(
        json.dumps(
            {
                "row": row_id,
                "ok": True,
                "status": "translated",
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
    posts = [message.translated_text or "" for message in messages]
    if not posts:
        raise ValueError("No translated posts available for article prompt preview")
    print(
        json.dumps(
            {
                "post_count": len(posts),
                "prompt": article_user_prompt(
                    posts,
                    min_chars=settings.dzen_article_target_min_chars,
                    max_chars=settings.dzen_article_target_max_chars,
                    article_date_label=dzen_article_date_label(settings),
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

    scheduled_slot_key = due_article_slot(settings)
    if scheduled_slot_key:
        logging.info("Dzen article slot due: %s", scheduled_slot_key)
    if article or scheduled_slot_key:
        manual_slot_key = None if scheduled_slot_key else f"manual-{int(time.time())}" if not dry_run else None
        await generate_dzen_article(
            db,
            settings,
            model,
            admin,
            dry_run=dry_run,
            force=force_article,
            slot_key=scheduled_slot_key or manual_slot_key,
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
    parser.add_argument("--list-failed-translations", action="store_true", help="Print failed translation rows and exit")
    parser.add_argument("--reset-failed", action="store_true", help="Move failed translation/publish rows back to retryable states")
    parser.add_argument("--doctor", action="store_true", help="Check env and provider readiness")
    parser.add_argument("--print-translation-prompt", action="store_true", help="Print the translation prompt without calling an LLM")
    parser.add_argument("--print-article-prompt", action="store_true", help="Print the Dzen article prompt without calling an LLM")
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
        translated = prepare_social_post_text(
            await translate_source_text(model, args.source_text),
            max_lines=settings.social_post_max_lines,
            target_max_chars=settings.social_post_target_max_chars,
        )
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
            skip_publish=effective_skip_publish,
            skip_translate=args.ingest_only,
        )


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
