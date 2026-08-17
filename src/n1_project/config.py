from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None or value.strip() == "":
        return default
    return int(value.strip())


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value.strip() == "":
        return default
    return float(value.strip())


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def parse_key_value_csv(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    result: dict[str, str] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item or "=" not in item:
            continue
        key, item_value = item.split("=", 1)
        key = key.strip().lower()
        item_value = item_value.strip()
        if key and item_value:
            result[key] = item_value
    return result


def parse_channel_windows(value: str | None) -> dict[str, list[str]]:
    if not value:
        return {}
    result: dict[str, list[str]] = {}
    for raw_item in value.split(";"):
        item = raw_item.strip()
        if not item or "=" not in item:
            continue
        key, windows_text = item.split("=", 1)
        windows = [window.strip() for window in windows_text.split("|") if window.strip()]
        if key.strip() and windows:
            result[key.strip().lower()] = windows
    return result


def resolve_optional_path(value: str | None, root: Path) -> str:
    if value is None or value.strip() == "":
        return ""
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        path = root / path
    return str(path)


def default_existing_path(root: Path, relative_path: str) -> str:
    path = root / relative_path
    return str(path) if path.exists() else ""


def resolve_max_ca_bundle(value: str | None, root: Path) -> str:
    configured = resolve_optional_path(value, root)
    if configured:
        return configured
    return default_existing_path(root, "certs/russian_trusted_ca_bundle.pem")


@dataclass(frozen=True)
class Settings:
    project_root: Path
    app_env: str
    app_timezone: str
    log_level: str
    db_path: Path
    source_fetch_mode: str
    worker_poll_seconds: int
    worker_batch_limit: int
    translation_max_attempts: int
    dead_queue_alert_enabled: bool
    dead_queue_alert_interval_hours: int

    telegram_bot_token: str
    telegram_target_chat_id: str
    telegram_source_channel_id: str
    telegram_source_public_name: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_mtproto_session_string: str

    vk_token: str
    vk_id: str

    max_access_token: str
    max_chat_id: str
    max_api_base_url: str
    max_ca_bundle: str

    admin_telegram_chat_id: str
    admin_notifications_enabled: bool
    admin_callback_poll_timeout_seconds: int

    dzen_telegram_bridge_chat_id: str
    dzen_article_channels: list[str]
    dzen_article_bridge_chat_ids: dict[str, str]
    dzen_article_bot_tokens: dict[str, str]
    dzen_article_windows: dict[str, list[str]]
    dzen_article_randomize_times: bool
    dzen_article_slot_window_minutes: int
    dzen_article_slot_retry_until_end_of_day: bool
    dzen_article_slot_max_attempts: int
    dzen_article_parse_mode: str
    dzen_article_footer_enabled: bool
    dzen_article_footer_policy: str
    dzen_article_footer_rotate: bool
    dzen_article_footer_telegram_url: str
    dzen_article_footer_vk_url: str
    dzen_article_footer_max_url: str
    dzen_daily_articles_enabled: bool
    dzen_daily_article_times: list[str]
    dzen_article_min_posts: int
    dzen_article_candidate_limit: int
    dzen_article_review_enabled: bool
    dzen_article_review_max_attempts: int
    dzen_article_review_timeout_hours: int
    dzen_article_auto_publish_weekends: bool
    dzen_article_image_enabled: bool
    dzen_article_image_required: bool
    dzen_article_image_credit_enabled: bool
    telegram_photo_caption_max_chars: int

    pexels_api_key: str
    pexels_api_base_url: str
    pexels_photo_orientation: str
    pexels_photo_size: str
    pexels_photo_per_page: int

    llm_provider: str
    translation_provider: str
    ollama_base_url: str
    ollama_translation_model: str
    ollama_article_model: str
    article_llm_provider: str
    openrouter_api_key: str
    openrouter_translation_model: str
    openrouter_article_model: str
    openrouter_max_attempts: int
    openrouter_retry_base_seconds: float

    telegram_max_text_chars: int
    vk_max_text_chars: int
    max_max_text_chars: int
    dzen_post_max_text_chars: int
    dzen_article_target_min_chars: int
    dzen_article_target_max_chars: int
    social_post_max_lines: int
    social_post_target_max_chars: int
    publish_order: list[str]
    publish_min_seconds_between_posts: int

    @classmethod
    def from_mapping(cls, env: Mapping[str, str], project_root: Path | None = None) -> "Settings":
        root = project_root or Path.cwd()
        db_path_raw = env.get("DB_PATH", "data/n1_project.sqlite3")
        db_path = Path(db_path_raw)
        if not db_path.is_absolute():
            db_path = root / db_path

        dzen_article_channels = parse_csv(env.get("DZEN_ARTICLE_CHANNELS", "markets"))
        if not dzen_article_channels:
            dzen_article_channels = ["russia"]
        dzen_bridge_chat_id = env.get("DZEN_TELEGRAM_BRIDGE_CHAT_ID", "")
        dzen_article_bridge_chat_ids = parse_key_value_csv(env.get("DZEN_ARTICLE_BRIDGE_CHAT_IDS"))
        for key, env_key in (
            ("russia", "DZEN_RUSSIA_TELEGRAM_BRIDGE_CHAT_ID"),
            ("energy", "DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID"),
            ("tech", "DZEN_TECH_TELEGRAM_BRIDGE_CHAT_ID"),
        ):
            if env.get(env_key):
                dzen_article_bridge_chat_ids[key] = str(env[env_key])
        if dzen_bridge_chat_id and "russia" not in dzen_article_bridge_chat_ids:
            dzen_article_bridge_chat_ids["russia"] = dzen_bridge_chat_id
        if dzen_bridge_chat_id and len(dzen_article_channels) == 1:
            dzen_article_bridge_chat_ids.setdefault(dzen_article_channels[0], dzen_bridge_chat_id)
        dzen_article_bot_tokens = parse_key_value_csv(env.get("DZEN_ARTICLE_BOT_TOKENS"))
        for key, env_key in (
            ("russia", "DZEN_RUSSIA_TELEGRAM_BOT_TOKEN"),
            ("energy", "DZEN_ENERGY_TELEGRAM_BOT_TOKEN"),
            ("tech", "DZEN_TECH_TELEGRAM_BOT_TOKEN"),
        ):
            if env.get(env_key):
                dzen_article_bot_tokens[key] = str(env[env_key])

        dzen_article_image_enabled = parse_bool(env.get("DZEN_ARTICLE_IMAGE_ENABLED"), False)

        return cls(
            project_root=root,
            app_env=env.get("APP_ENV", "development"),
            app_timezone=env.get("APP_TIMEZONE", "Europe/Moscow"),
            log_level=env.get("LOG_LEVEL", "info"),
            db_path=db_path,
            source_fetch_mode=env.get("SOURCE_FETCH_MODE", "mtproto").lower(),
            worker_poll_seconds=parse_int(env.get("WORKER_POLL_SECONDS"), 300),
            worker_batch_limit=parse_int(env.get("WORKER_BATCH_LIMIT"), 10),
            translation_max_attempts=parse_int(env.get("TRANSLATION_MAX_ATTEMPTS"), 5),
            dead_queue_alert_enabled=parse_bool(env.get("DEAD_QUEUE_ALERT_ENABLED"), True),
            dead_queue_alert_interval_hours=parse_int(env.get("DEAD_QUEUE_ALERT_INTERVAL_HOURS"), 24),
            telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_target_chat_id=env.get("TELEGRAM_TARGET_CHAT_ID", ""),
            telegram_source_channel_id=env.get("TELEGRAM_SOURCE_CHANNEL_ID", ""),
            telegram_source_public_name=env.get("TELEGRAM_SOURCE_PUBLIC_NAME", ""),
            telegram_api_id=parse_int(env.get("TELEGRAM_API_ID")),
            telegram_api_hash=env.get("TELEGRAM_API_HASH", ""),
            telegram_mtproto_session_string=env.get("TELEGRAM_MTPROTO_SESSION_STRING", ""),
            vk_token=env.get("VK_TOKEN", env.get("VK_ACCESS_TOKEN", "")),
            vk_id=env.get("VK_ID", env.get("VK_OWNER_ID", "")),
            max_access_token=env.get("MAX_ACCESS_TOKEN", ""),
            max_chat_id=env.get("MAX_CHAT_ID", ""),
            max_api_base_url=env.get("MAX_API_BASE_URL", "https://platform-api2.max.ru").rstrip("/"),
            max_ca_bundle=resolve_max_ca_bundle(env.get("MAX_CA_BUNDLE"), root),
            admin_telegram_chat_id=env.get("ADMIN_TELEGRAM_CHAT_ID", env.get("TELEGRAM_TARGET_CHAT_ID", "")),
            admin_notifications_enabled=parse_bool(env.get("ADMIN_NOTIFICATIONS_ENABLED"), True),
            admin_callback_poll_timeout_seconds=parse_int(env.get("ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS"), 25),
            dzen_telegram_bridge_chat_id=dzen_bridge_chat_id,
            dzen_article_channels=dzen_article_channels,
            dzen_article_bridge_chat_ids=dzen_article_bridge_chat_ids,
            dzen_article_bot_tokens=dzen_article_bot_tokens,
            dzen_article_windows=parse_channel_windows(env.get("DZEN_ARTICLE_WINDOWS")),
            dzen_article_randomize_times=parse_bool(env.get("DZEN_ARTICLE_RANDOMIZE_TIMES"), True),
            dzen_article_slot_window_minutes=parse_int(env.get("DZEN_ARTICLE_SLOT_WINDOW_MINUTES"), 5),
            dzen_article_slot_retry_until_end_of_day=parse_bool(
                env.get("DZEN_ARTICLE_SLOT_RETRY_UNTIL_END_OF_DAY"), True
            ),
            dzen_article_slot_max_attempts=parse_int(env.get("DZEN_ARTICLE_SLOT_MAX_ATTEMPTS"), 6),
            dzen_article_parse_mode=env.get("DZEN_ARTICLE_PARSE_MODE", "HTML").strip(),
            dzen_article_footer_enabled=parse_bool(env.get("DZEN_ARTICLE_FOOTER_ENABLED"), True),
            dzen_article_footer_policy=env.get("DZEN_ARTICLE_FOOTER_POLICY", "always").strip().lower(),
            dzen_article_footer_rotate=parse_bool(env.get("DZEN_ARTICLE_FOOTER_ROTATE"), True),
            dzen_article_footer_telegram_url=env.get("DZEN_ARTICLE_FOOTER_TELEGRAM_URL", "").strip(),
            dzen_article_footer_vk_url=env.get("DZEN_ARTICLE_FOOTER_VK_URL", "").strip(),
            dzen_article_footer_max_url=env.get("DZEN_ARTICLE_FOOTER_MAX_URL", "").strip(),
            dzen_daily_articles_enabled=parse_bool(env.get("DZEN_DAILY_ARTICLES_ENABLED")),
            dzen_daily_article_times=parse_csv(env.get("DZEN_DAILY_ARTICLE_TIMES")),
            dzen_article_min_posts=parse_int(env.get("DZEN_ARTICLE_MIN_POSTS"), 1),
            dzen_article_candidate_limit=parse_int(env.get("DZEN_ARTICLE_CANDIDATE_LIMIT"), 10),
            dzen_article_review_enabled=parse_bool(env.get("DZEN_ARTICLE_REVIEW_ENABLED"), False),
            dzen_article_review_max_attempts=parse_int(env.get("DZEN_ARTICLE_REVIEW_MAX_ATTEMPTS"), 5),
            dzen_article_review_timeout_hours=parse_int(env.get("DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS"), 3),
            dzen_article_auto_publish_weekends=parse_bool(env.get("DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS"), True),
            dzen_article_image_enabled=dzen_article_image_enabled,
            dzen_article_image_required=parse_bool(env.get("DZEN_ARTICLE_IMAGE_REQUIRED"), dzen_article_image_enabled),
            dzen_article_image_credit_enabled=parse_bool(env.get("DZEN_ARTICLE_IMAGE_CREDIT_ENABLED"), False),
            telegram_photo_caption_max_chars=parse_int(env.get("TELEGRAM_PHOTO_CAPTION_MAX_CHARS"), 1024),
            pexels_api_key=env.get("PEXELS_API_KEY", "").strip(),
            pexels_api_base_url=env.get("PEXELS_API_BASE_URL", "https://api.pexels.com").rstrip("/"),
            pexels_photo_orientation=env.get("PEXELS_PHOTO_ORIENTATION", "landscape").strip().lower(),
            pexels_photo_size=env.get("PEXELS_PHOTO_SIZE", "large").strip().lower(),
            pexels_photo_per_page=parse_int(env.get("PEXELS_PHOTO_PER_PAGE"), 12),
            llm_provider=env.get("LLM_PROVIDER", "openrouter").lower(),
            translation_provider=env.get("TRANSLATION_PROVIDER", env.get("LLM_PROVIDER", "openrouter")).lower(),
            ollama_base_url=env.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            ollama_translation_model=env.get("OLLAMA_TRANSLATION_MODEL", "llama3.1:8b"),
            ollama_article_model=env.get("OLLAMA_ARTICLE_MODEL", "llama3.1:8b"),
            article_llm_provider=env.get("ARTICLE_LLM_PROVIDER", env.get("LLM_PROVIDER", "openrouter")).lower(),
            openrouter_api_key=env.get("OPENROUTER_API_KEY", ""),
            openrouter_translation_model=env.get(
                "OPENROUTER_TRANSLATION_MODEL",
                env.get("OPENROUTER_ARTICLE_MODEL", "deepseek/deepseek-v4-flash"),
            ),
            openrouter_article_model=env.get("OPENROUTER_ARTICLE_MODEL", "openai/gpt-5.6-terra"),
            openrouter_max_attempts=parse_int(env.get("OPENROUTER_MAX_ATTEMPTS"), 4),
            openrouter_retry_base_seconds=parse_float(env.get("OPENROUTER_RETRY_BASE_SECONDS"), 2.0),
            telegram_max_text_chars=parse_int(env.get("TELEGRAM_MAX_TEXT_CHARS"), 4096),
            vk_max_text_chars=parse_int(env.get("VK_MAX_TEXT_CHARS"), 16350),
            max_max_text_chars=parse_int(env.get("MAX_MAX_TEXT_CHARS"), 4000),
            dzen_post_max_text_chars=parse_int(env.get("DZEN_POST_MAX_TEXT_CHARS"), 4096),
            dzen_article_target_min_chars=parse_int(env.get("DZEN_ARTICLE_TARGET_MIN_CHARS"), 650),
            dzen_article_target_max_chars=parse_int(env.get("DZEN_ARTICLE_TARGET_MAX_CHARS"), 950),
            social_post_max_lines=parse_int(env.get("SOCIAL_POST_MAX_LINES"), 3),
            social_post_target_max_chars=parse_int(env.get("SOCIAL_POST_TARGET_MAX_CHARS"), 700),
            publish_order=parse_csv(env.get("PUBLISH_ORDER", "vk,telegram")),
            publish_min_seconds_between_posts=parse_int(env.get("PUBLISH_MIN_SECONDS_BETWEEN_POSTS"), 180),
        )

    @classmethod
    def load(cls, env_path: Path | str = ".env", project_root: Path | None = None) -> "Settings":
        root = project_root or Path.cwd()
        path = Path(env_path)
        if not path.is_absolute():
            path = root / path
        return cls.from_mapping(read_dotenv(path), project_root=root)

    def require_for_telegram_target(self) -> None:
        if not self.telegram_bot_token or not self.telegram_target_chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_TARGET_CHAT_ID are required")

    def require_for_telegram_source(self) -> None:
        missing = []
        if not self.telegram_source_channel_id:
            missing.append("TELEGRAM_SOURCE_CHANNEL_ID")
        if not self.telegram_api_id:
            missing.append("TELEGRAM_API_ID")
        if not self.telegram_api_hash:
            missing.append("TELEGRAM_API_HASH")
        if not self.telegram_mtproto_session_string:
            missing.append("TELEGRAM_MTPROTO_SESSION_STRING")
        if missing:
            raise ValueError("Missing Telegram source settings: " + ", ".join(missing))
