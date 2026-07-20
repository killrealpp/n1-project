from __future__ import annotations

import httpx

from n1_project.article_channels import configured_article_channels, daily_article_schedule
from n1_project.config import Settings
from n1_project.scheduler import local_now


def mtproto_missing_settings(settings: Settings) -> list[str]:
    missing = []
    if not settings.telegram_source_channel_id:
        missing.append("TELEGRAM_SOURCE_CHANNEL_ID")
    if not settings.telegram_api_id:
        missing.append("TELEGRAM_API_ID")
    if not settings.telegram_api_hash:
        missing.append("TELEGRAM_API_HASH")
    if not settings.telegram_mtproto_session_string:
        missing.append("TELEGRAM_MTPROTO_SESSION_STRING")
    return missing


def mtproto_session_format(settings: Settings) -> dict[str, object]:
    value = settings.telegram_mtproto_session_string
    if not value:
        return {"ok": False, "error": "empty", "length": 0}
    try:
        from telethon.sessions import StringSession

        StringSession(value)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "length": len(value)}
    return {"ok": True, "error": None, "length": len(value)}


def settings_health(settings: Settings) -> dict[str, object]:
    mtproto_missing = mtproto_missing_settings(settings)
    mtproto_session = mtproto_session_format(settings)
    ollama_required = settings.translation_provider == "ollama" or settings.article_llm_provider == "ollama"
    article_channels = configured_article_channels(settings)
    today = local_now(settings.app_timezone).date()
    return {
        "source_fetch_mode": settings.source_fetch_mode,
        "translation_max_attempts": settings.translation_max_attempts,
        "telegram_target_ready": bool(settings.telegram_bot_token and settings.telegram_target_chat_id),
        "telegram_mtproto_ready": not mtproto_missing and bool(mtproto_session["ok"]),
        "telegram_mtproto_missing": mtproto_missing,
        "telegram_mtproto_session": mtproto_session,
        "telegram_public_preview_ready": bool(settings.telegram_source_public_name),
        "vk_ready": bool(settings.vk_token and settings.vk_id),
        "max_ready": bool(settings.max_access_token and settings.max_chat_id),
        "max_ca_bundle": settings.max_ca_bundle or None,
        "max_ca_bundle_configured": bool(settings.max_ca_bundle),
        "admin_notifications_ready": bool(
            settings.admin_notifications_enabled
            and settings.telegram_bot_token
            and settings.admin_telegram_chat_id
        ),
        "admin_callback_poll_timeout_seconds": settings.admin_callback_poll_timeout_seconds,
        "dzen_bridge_ready": bool(settings.telegram_bot_token and settings.dzen_telegram_bridge_chat_id),
        "dzen_article_review_enabled": settings.dzen_article_review_enabled,
        "dzen_article_review_ready": bool(
            settings.dzen_article_review_enabled
            and settings.telegram_bot_token
            and settings.admin_telegram_chat_id
        ),
        "llm_provider": settings.llm_provider,
        "translation_provider": settings.translation_provider,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_translation_model": settings.ollama_translation_model,
        "ollama_required": ollama_required,
        "article_llm_provider": settings.article_llm_provider,
        "openrouter_ready": bool(settings.openrouter_api_key),
        "openrouter_translation_model": settings.openrouter_translation_model,
        "openrouter_article_model": settings.openrouter_article_model,
        "publish_order": settings.publish_order,
        "dzen_daily_articles_enabled": settings.dzen_daily_articles_enabled,
        "dzen_article_times": settings.dzen_daily_article_times,
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
            for channel in article_channels
        ],
        "dzen_article_bridge_channels_ready": sum(1 for channel in article_channels if channel.bridge_chat_id),
        "dzen_article_publish_channels_ready": sum(
            1 for channel in article_channels if channel.bridge_chat_id and channel.bot_token
        ),
        "dzen_article_channel_specific_bots_ready": sum(
            1 for channel in article_channels if channel.key in settings.dzen_article_bot_tokens
        ),
        "dzen_article_randomize_times": settings.dzen_article_randomize_times,
        "dzen_article_slot_window_minutes": settings.dzen_article_slot_window_minutes,
        "dzen_article_parse_mode": settings.dzen_article_parse_mode,
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
            "per_page": settings.pexels_photo_per_page,
        },
        "telegram_photo_caption_max_chars": settings.telegram_photo_caption_max_chars,
        "dzen_article_schedule_today": [
            {
                "channel": slot.channel.key,
                "slot_key": slot.slot_key,
                "window": slot.window,
                "publish_time": slot.publish_time,
            }
            for slot in daily_article_schedule(settings, today)
        ],
        "dzen_article_min_posts": settings.dzen_article_min_posts,
        "dzen_article_candidate_limit": settings.dzen_article_candidate_limit,
        "dzen_article_review_timeout_hours": settings.dzen_article_review_timeout_hours,
        "dzen_article_auto_publish_weekends": settings.dzen_article_auto_publish_weekends,
    }


async def ollama_health(settings: Settings) -> dict[str, object]:
    url = f"{settings.ollama_base_url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc), "models": []}

    models = []
    for item in data.get("models", []):
        name = item.get("name")
        if name:
            models.append(str(name))
    return {
        "ok": True,
        "url": url,
        "models": models,
        "translation_model_available": settings.ollama_translation_model in models,
        "article_model_available": settings.ollama_article_model in models,
    }


async def run_health_check(settings: Settings) -> dict[str, object]:
    ollama_required = settings.translation_provider == "ollama" or settings.article_llm_provider == "ollama"
    return {
        "settings": settings_health(settings),
        "ollama": await ollama_health(settings)
        if ollama_required
        else {
            "ok": None,
            "skipped": True,
            "reason": "Ollama is not required when translation and article providers are external.",
            "models": [],
            "url": settings.ollama_base_url,
            "translation_model_available": None,
            "article_model_available": None,
        },
    }
