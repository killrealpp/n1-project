from __future__ import annotations

import httpx

from n1_project.domain import PublishResult
from n1_project.publishers.base import Publisher
from n1_project.validators import ensure_max_chars


class TelegramPublisher(Publisher):
    platform = "telegram"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        max_chars: int,
        dry_run: bool = False,
        parse_mode: str | None = None,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.max_chars = max_chars
        self.dry_run = dry_run
        self.parse_mode = parse_mode

    async def publish_text(self, text: str) -> PublishResult:
        if not self.bot_token or not self.chat_id:
            return PublishResult(self.platform, False, error="missing Telegram bot token or chat id")
        ensure_max_chars(text, self.max_chars, self.platform)
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": False}
        if self.parse_mode:
            payload["parse_mode"] = self.parse_mode
        if self.dry_run:
            return PublishResult(self.platform, True, destination_id="dry-run", payload=payload)

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
        if data.get("ok") and data.get("result", {}).get("message_id"):
            return PublishResult(self.platform, True, destination_id=str(data["result"]["message_id"]))
        return PublishResult(self.platform, False, error=str(data))


class DzenBridgePublisher(TelegramPublisher):
    platform = "dzen"
