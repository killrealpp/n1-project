from pathlib import Path

from n1_project.config import Settings
from n1_project.health import run_health_check, settings_health


def test_settings_health_flags(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_TARGET_CHAT_ID": "-100",
            "TELEGRAM_SOURCE_PUBLIC_NAME": "num1_ch",
            "VK_TOKEN": "vk",
            "VK_ID": "123",
            "ADMIN_TELEGRAM_CHAT_ID": "-300",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-200",
            "DZEN_DAILY_ARTICLES_ENABLED": "true",
        },
        project_root=tmp_path,
    )

    health = settings_health(settings)

    assert health["telegram_target_ready"] is True
    assert health["telegram_public_preview_ready"] is True
    assert health["telegram_mtproto_ready"] is False
    assert health["telegram_mtproto_session"]["ok"] is False
    assert health["telegram_mtproto_missing"] == [
        "TELEGRAM_SOURCE_CHANNEL_ID",
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_MTPROTO_SESSION_STRING",
    ]
    assert health["vk_ready"] is True
    assert health["max_ready"] is False
    assert health["admin_notifications_ready"] is True
    assert health["dzen_bridge_ready"] is True
    assert health["dzen_article_review_ready"] is True
    assert health["dzen_daily_articles_enabled"] is True
    assert health["dzen_article_candidate_limit"] == 10
    assert health["dzen_article_review_timeout_hours"] == 3
    assert health["dzen_article_auto_publish_weekends"] is True


async def test_run_health_skips_ollama_when_external_providers_are_used(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TRANSLATION_PROVIDER": "openrouter",
            "ARTICLE_LLM_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "key",
            "OPENROUTER_TRANSLATION_MODEL": "deepseek/deepseek-v4-flash",
            "OPENROUTER_ARTICLE_MODEL": "openai/gpt-5.3-chat",
        },
        project_root=tmp_path,
    )

    health = await run_health_check(settings)

    assert health["settings"]["translation_provider"] == "openrouter"
    assert health["settings"]["openrouter_ready"] is True
    assert health["ollama"]["skipped"] is True


def test_settings_health_reports_only_missing_mtproto_session(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_SOURCE_CHANNEL_ID": "@num1_ch",
            "TELEGRAM_API_ID": "123456",
            "TELEGRAM_API_HASH": "a" * 32,
        },
        project_root=tmp_path,
    )

    health = settings_health(settings)

    assert health["telegram_mtproto_ready"] is False
    assert health["telegram_mtproto_missing"] == ["TELEGRAM_MTPROTO_SESSION_STRING"]


def test_settings_health_rejects_invalid_mtproto_session_string(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_SOURCE_CHANNEL_ID": "@num1_ch",
            "TELEGRAM_API_ID": "123456",
            "TELEGRAM_API_HASH": "a" * 32,
            "TELEGRAM_MTPROTO_SESSION_STRING": "not-a-valid-session",
        },
        project_root=tmp_path,
    )

    health = settings_health(settings)

    assert health["telegram_mtproto_ready"] is False
    assert health["telegram_mtproto_missing"] == []
    assert health["telegram_mtproto_session"]["ok"] is False
