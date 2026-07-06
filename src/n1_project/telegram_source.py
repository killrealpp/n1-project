from __future__ import annotations

from n1_project.config import Settings
from n1_project.domain import SourcePost


class TelegramSource:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_latest(self, limit: int = 1) -> list[SourcePost]:
        self.settings.require_for_telegram_source()
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise RuntimeError("telethon is not installed; run `python -m pip install -e .`") from exc

        posts: list[SourcePost] = []
        async with TelegramClient(
            StringSession(self.settings.telegram_mtproto_session_string),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        ) as client:
            async for message in client.iter_messages(self.settings.telegram_source_channel_id, limit=limit):
                text = message.message or ""
                if not text.strip():
                    continue
                posts.append(
                    SourcePost(
                        source_channel_id=str(self.settings.telegram_source_channel_id),
                        source_message_id=str(message.id),
                        text=text.strip(),
                        date_iso=message.date.isoformat() if message.date else None,
                    )
                )
        posts.reverse()
        return posts
