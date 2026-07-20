from __future__ import annotations

from n1_project.config import Settings
from n1_project.publishers.base import Publisher
from n1_project.publishers.max import MaxPublisher
from n1_project.publishers.telegram import DzenBridgePublisher, TelegramPublisher
from n1_project.publishers.vk import VkPublisher


def build_publishers(settings: Settings, dry_run: bool = False) -> dict[str, Publisher]:
    publishers: dict[str, Publisher] = {
        "telegram": TelegramPublisher(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_target_chat_id,
            max_chars=settings.telegram_max_text_chars,
            dry_run=dry_run,
            caption_max_chars=settings.telegram_photo_caption_max_chars,
        ),
        "vk": VkPublisher(
            token=settings.vk_token,
            vk_id=settings.vk_id,
            max_chars=settings.vk_max_text_chars,
            dry_run=dry_run,
        ),
        "max": MaxPublisher(
            access_token=settings.max_access_token,
            chat_id=settings.max_chat_id,
            api_base_url=settings.max_api_base_url,
            max_chars=settings.max_max_text_chars,
            ca_bundle=settings.max_ca_bundle,
            dry_run=dry_run,
        ),
    }
    if settings.dzen_telegram_bridge_chat_id:
        publishers["dzen"] = DzenBridgePublisher(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.dzen_telegram_bridge_chat_id,
            max_chars=settings.dzen_post_max_text_chars,
            dry_run=dry_run,
            parse_mode=settings.dzen_article_parse_mode or None,
            caption_max_chars=settings.telegram_photo_caption_max_chars,
        )
    return publishers
