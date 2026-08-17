from pathlib import Path

from n1_project.config import Settings
from n1_project.health import openrouter_models_health, run_health_check, settings_health


def fake_catalog(*model_ids: str):
    async def fetch() -> list[str]:
        return list(model_ids)

    return fetch


def test_settings_health_flags(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_TARGET_CHAT_ID": "-100",
            "TELEGRAM_SOURCE_PUBLIC_NAME": "num1_ch",
            "VK_TOKEN": "vk",
            "VK_ID": "123",
            "MAX_CA_BUNDLE": "certs/max.pem",
            "ADMIN_TELEGRAM_CHAT_ID": "-300",
            "ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS": "17",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-200",
            "DZEN_ARTICLE_REVIEW_ENABLED": "true",
            "DZEN_ARTICLE_CHANNELS": "russia,energy,tech",
            "DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID": "-201",
            "DZEN_ENERGY_TELEGRAM_BOT_TOKEN": "energy-token",
            "DZEN_TECH_TELEGRAM_BRIDGE_CHAT_ID": "-202",
            "DZEN_TECH_TELEGRAM_BOT_TOKEN": "tech-token",
            "DZEN_DAILY_ARTICLES_ENABLED": "true",
            "DZEN_ARTICLE_FOOTER_TELEGRAM_URL": "https://t.me/bazar",
            "DZEN_ARTICLE_FOOTER_VK_URL": "https://vk.com/bazar",
            "DZEN_ARTICLE_FOOTER_MAX_URL": "https://max.ru/bazar",
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
    assert health["max_ca_bundle_configured"] is True
    assert health["max_ca_bundle"] == str(tmp_path / "certs" / "max.pem")
    assert health["admin_notifications_ready"] is True
    assert health["admin_callback_poll_timeout_seconds"] == 17
    assert health["dzen_bridge_ready"] is True
    assert health["dzen_article_review_ready"] is True
    assert health["dzen_daily_articles_enabled"] is True
    assert health["dzen_article_bridge_channels_ready"] == 3
    assert health["dzen_article_publish_channels_ready"] == 3
    assert health["dzen_article_channel_specific_bots_ready"] == 2
    assert [item["key"] for item in health["dzen_article_channels"]] == ["russia", "energy", "tech"]
    assert [item["bot_configured"] for item in health["dzen_article_channels"]] == [True, True, True]
    assert [item["bot_source"] for item in health["dzen_article_channels"]] == ["default", "channel", "channel"]
    assert len(health["dzen_article_schedule_today"]) == 3
    assert health["dzen_article_parse_mode"] == "HTML"
    assert health["dzen_article_footer"]["enabled"] is True
    assert health["dzen_article_footer"]["policy"] == "always"
    assert health["dzen_article_footer"]["links_configured"] == {
        "telegram": True,
        "vk": True,
        "max": True,
    }
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
            "OPENROUTER_ARTICLE_MODEL": "openai/gpt-5.6-terra",
        },
        project_root=tmp_path,
    )

    health = await run_health_check(
        settings,
        openrouter_fetch=fake_catalog("deepseek/deepseek-v4-flash", "openai/gpt-5.6-terra"),
    )

    assert health["settings"]["translation_provider"] == "openrouter"
    assert health["settings"]["openrouter_ready"] is True
    assert health["ollama"]["skipped"] is True
    assert health["openrouter"]["status"] == "green"


async def test_openrouter_health_flags_missing_article_model(tmp_path: Path) -> None:
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

    health = await openrouter_models_health(
        settings,
        fetch=fake_catalog("deepseek/deepseek-v4-flash", "openai/gpt-5.2-chat", "openai/gpt-5.6-terra"),
    )

    assert health["ok"] is False
    assert health["status"] == "red"
    assert health["problems"] == ["модель openai/gpt-5.3-chat отсутствует в каталоге OpenRouter"]
    assert health["models"]["OPENROUTER_TRANSLATION_MODEL"]["present"] is True
    assert health["models"]["OPENROUTER_ARTICLE_MODEL"]["present"] is False


async def test_openrouter_health_accepts_model_variant_suffix(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TRANSLATION_PROVIDER": "openrouter",
            "ARTICLE_LLM_PROVIDER": "openrouter",
            "OPENROUTER_ARTICLE_MODEL": "openai/gpt-5.6-terra:online",
            "OPENROUTER_TRANSLATION_MODEL": "deepseek/deepseek-v4-flash",
        },
        project_root=tmp_path,
    )

    health = await openrouter_models_health(
        settings,
        fetch=fake_catalog("deepseek/deepseek-v4-flash", "openai/gpt-5.6-terra"),
    )

    assert health["ok"] is True
    assert health["problems"] == []


async def test_openrouter_health_does_not_fail_doctor_when_catalog_is_unreachable(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TRANSLATION_PROVIDER": "openrouter",
            "ARTICLE_LLM_PROVIDER": "openrouter",
            "OPENROUTER_ARTICLE_MODEL": "openai/gpt-5.6-terra",
            "OPENROUTER_TRANSLATION_MODEL": "deepseek/deepseek-v4-flash",
        },
        project_root=tmp_path,
    )

    async def broken_fetch() -> list[str]:
        raise RuntimeError("connection refused")

    health = await openrouter_models_health(settings, fetch=broken_fetch)

    assert health["ok"] is None
    assert health["status"] == "unknown"
    assert health["problems"] == []
    assert "connection refused" in str(health["error"])


async def test_openrouter_health_is_skipped_for_local_providers(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TRANSLATION_PROVIDER": "ollama",
            "ARTICLE_LLM_PROVIDER": "ollama",
        },
        project_root=tmp_path,
    )

    health = await openrouter_models_health(settings, fetch=fake_catalog())

    assert health["status"] == "skipped"
    assert health["skipped"] is True


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
