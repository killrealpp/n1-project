from pathlib import Path

from n1_project.config import Settings, read_dotenv


def test_read_dotenv_and_settings(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "APP_ENV=test",
                "DB_PATH=data/test.sqlite3",
                "SOURCE_FETCH_MODE=public-preview",
                "WORKER_POLL_SECONDS=60",
                "WORKER_BATCH_LIMIT=7",
                "TRANSLATION_MAX_ATTEMPTS=3",
                "TELEGRAM_BOT_TOKEN=token",
                "TELEGRAM_TARGET_CHAT_ID=-1001",
                "TELEGRAM_SOURCE_PUBLIC_NAME=num1_ch",
                "VK_TOKEN=vk",
                "VK_ID=123",
                "MAX_CA_BUNDLE=certs/max.pem",
                "ADMIN_TELEGRAM_CHAT_ID=-100admin",
                "ADMIN_NOTIFICATIONS_ENABLED=true",
                "ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS=11",
                "DZEN_DAILY_ARTICLES_ENABLED=true",
                "DZEN_DAILY_ARTICLE_TIMES=10:00,18:00",
                "DZEN_ARTICLE_MIN_POSTS=9",
                "DZEN_ARTICLE_CANDIDATE_LIMIT=10",
                "DZEN_ARTICLE_REVIEW_ENABLED=true",
                "DZEN_ARTICLE_REVIEW_MAX_ATTEMPTS=4",
                "DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3",
                "DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true",
                "TRANSLATION_PROVIDER=openrouter",
                "OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash",
                "SOCIAL_POST_MAX_LINES=2",
                "SOCIAL_POST_TARGET_MAX_CHARS=500",
                "PUBLISH_ORDER=vk, telegram",
            ]
        ),
        encoding="utf-8",
    )

    raw = read_dotenv(env_path)
    settings = Settings.from_mapping(raw, project_root=tmp_path)

    assert settings.app_env == "test"
    assert settings.db_path == tmp_path / "data" / "test.sqlite3"
    assert settings.source_fetch_mode == "public-preview"
    assert settings.worker_poll_seconds == 60
    assert settings.worker_batch_limit == 7
    assert settings.translation_max_attempts == 3
    assert settings.telegram_source_public_name == "num1_ch"
    assert settings.dzen_daily_articles_enabled is True
    assert settings.dzen_daily_article_times == ["10:00", "18:00"]
    assert settings.dzen_article_min_posts == 9
    assert settings.dzen_article_candidate_limit == 10
    assert settings.admin_telegram_chat_id == "-100admin"
    assert settings.admin_notifications_enabled is True
    assert settings.admin_callback_poll_timeout_seconds == 11
    assert settings.dzen_article_review_enabled is True
    assert settings.dzen_article_review_max_attempts == 4
    assert settings.dzen_article_review_timeout_hours == 3
    assert settings.dzen_article_auto_publish_weekends is True
    assert settings.translation_provider == "openrouter"
    assert settings.openrouter_translation_model == "deepseek/deepseek-v4-flash"
    assert settings.max_ca_bundle == str(tmp_path / "certs" / "max.pem")
    assert settings.social_post_max_lines == 2
    assert settings.social_post_target_max_chars == 500
    assert settings.publish_order == ["vk", "telegram"]


def test_openrouter_is_default_llm_path(tmp_path: Path) -> None:
    settings = Settings.from_mapping({}, project_root=tmp_path)

    assert settings.llm_provider == "openrouter"
    assert settings.translation_provider == "openrouter"
    assert settings.article_llm_provider == "openrouter"
    assert settings.openrouter_translation_model == "deepseek/deepseek-v4-flash"
    assert settings.openrouter_article_model == "openai/gpt-5.3-chat"
    assert settings.translation_max_attempts == 5
    assert settings.admin_callback_poll_timeout_seconds == 25
