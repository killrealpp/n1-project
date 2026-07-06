from __future__ import annotations

import httpx

from n1_project.domain import PublishResult
from n1_project.publishers.base import Publisher
from n1_project.validators import ensure_max_chars


class MaxPublisher(Publisher):
    platform = "max"

    def __init__(
        self,
        access_token: str,
        chat_id: str,
        api_base_url: str,
        max_chars: int,
        dry_run: bool = False,
    ):
        self.access_token = access_token
        self.chat_id = chat_id
        self.api_base_url = api_base_url.rstrip("/")
        self.max_chars = max_chars
        self.dry_run = dry_run

    async def publish_text(self, text: str) -> PublishResult:
        if not self.access_token or not self.chat_id:
            return PublishResult(self.platform, False, error="missing MAX_ACCESS_TOKEN or MAX_CHAT_ID")
        ensure_max_chars(text, self.max_chars, self.platform)
        payload = {"text": text}
        if self.dry_run:
            return PublishResult(self.platform, True, destination_id="dry-run", payload=payload)

        url = f"{self.api_base_url}/messages"
        params = {"chat_id": self.chat_id}
        headers = {"Authorization": self.access_token}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, headers=headers, json=payload)
            data = response.json()
        destination_id = self._extract_message_id(data)
        if response.is_success:
            return PublishResult(self.platform, True, destination_id=destination_id or "accepted")
        return PublishResult(self.platform, False, error=str(data))

    @staticmethod
    def _extract_message_id(data: dict[str, object]) -> str | None:
        for key in ("message_id", "id", "mid"):
            value = data.get(key)
            if value:
                return str(value)
        message = data.get("message")
        if isinstance(message, dict):
            for key in ("message_id", "id", "mid"):
                value = message.get(key)
                if value:
                    return str(value)
        return None
