from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from n1_project.domain import PublishResult
from n1_project.validators import ensure_max_chars


ARTICLE_ACCEPT_PREFIX = "dzen_accept:"
ARTICLE_REJECT_PREFIX = "dzen_reject:"


def repair_mojibake(text: str) -> str:
    try:
        return text.encode("cp1251").decode("utf-8")
    except UnicodeError:
        return text


class AdminNotifier:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        enabled: bool = True,
        max_chars: int = 4096,
        dry_run: bool = False,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.max_chars = max_chars
        self.dry_run = dry_run

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.bot_token and self.chat_id)

    async def notify(self, title: str, body: str, *, level: str = "info") -> PublishResult:
        if not self.configured:
            return PublishResult("admin", False, error="admin notifications are not configured")
        text = f"[{level.upper()}] {title}\n\n{body}".strip()
        if len(text) > self.max_chars:
            text = text[: self.max_chars - 80].rstrip() + "\n\n[trimmed]"
        return await self._send_message(text)

    async def send_article_review(
        self,
        *,
        article_id: int,
        article_text: str,
        attempt: int,
        slot_key: str | None,
    ) -> PublishResult:
        if not self.configured:
            return PublishResult("admin", False, error="admin review chat is not configured")

        header = (
            f"Черновик Dzen-статьи #{article_id}\n"
            f"Попытка: {attempt}\n"
            f"Слот: {slot_key or 'manual'}\n\n"
        )
        text = header + article_text
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Принять и отправить в Dzen", "callback_data": f"{ARTICLE_ACCEPT_PREFIX}{article_id}"},
                    {"text": "Отклонить и сгенерировать заново", "callback_data": f"{ARTICLE_REJECT_PREFIX}{article_id}"},
                ]
            ]
        }
        if len(text) <= self.max_chars:
            return await self._send_message(text, reply_markup=reply_markup)

        await self._send_message(header + "Текст статьи не поместился в одно review-сообщение. Отправляю текст ниже.")
        for chunk in self._chunks(article_text, self.max_chars):
            await self._send_message(chunk)
        return await self._send_message(
            f"Действие для Dzen-статьи #{article_id}, попытка {attempt}:",
            reply_markup=reply_markup,
        )

    async def get_callback_updates(self, offset: int | None, timeout_seconds: int = 0) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        if self.dry_run:
            return []
        timeout_seconds = max(0, timeout_seconds)
        payload: dict[str, object] = {"timeout": timeout_seconds, "allowed_updates": ["callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        try:
            async with httpx.AsyncClient(timeout=max(30.0, timeout_seconds + 10.0)) as client:
                response = await client.post(url, json=payload)
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logging.warning("admin getUpdates request failed: %s", exc)
            return []
        if not data.get("ok"):
            logging.warning("admin getUpdates failed: %s", data)
            return []
        return list(data.get("result") or [])

    async def answer_callback(self, callback_query_id: str, text: str) -> None:
        if not self.configured or self.dry_run:
            return
        text = repair_mojibake(text)
        payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": False}
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json=payload)

    async def edit_message_text(self, chat_id: str, message_id: str, text: str) -> None:
        if not self.configured or self.dry_run:
            return
        text = repair_mojibake(text)
        if len(text) > self.max_chars:
            text = text[: self.max_chars - 80].rstrip() + "\n\n[trimmed]"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json=payload)

    async def _send_message(self, text: str, reply_markup: dict[str, object] | None = None) -> PublishResult:
        text = repair_mojibake(text)
        ensure_max_chars(text, self.max_chars, "admin")
        payload: dict[str, object] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if self.dry_run:
            return PublishResult("admin", True, destination_id="dry-run", payload=payload)

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
        if data.get("ok") and data.get("result", {}).get("message_id"):
            return PublishResult("admin", True, destination_id=str(data["result"]["message_id"]), payload=payload)
        return PublishResult("admin", False, error=json.dumps(data, ensure_ascii=False), payload=payload)

    @staticmethod
    def _chunks(text: str, max_chars: int) -> list[str]:
        chunks: list[str] = []
        remaining = text
        while remaining:
            chunks.append(remaining[:max_chars])
            remaining = remaining[max_chars:]
        return chunks
