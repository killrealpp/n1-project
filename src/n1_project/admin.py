from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from n1_project.domain import PublishResult
from n1_project.validators import ensure_max_chars


ARTICLE_ACCEPT_PREFIX = "dzen_accept:"
ARTICLE_REJECT_PREFIX = "dzen_reject:"

ADMIN_UPDATE_BACKOFF_BASE_SECONDS = 2.0
ADMIN_UPDATE_MAX_BACKOFF_SECONDS = 60.0
ADMIN_UPDATE_SUSTAINED_FAILURE_SECONDS = 300.0


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
        sustained_failure_seconds: float = ADMIN_UPDATE_SUSTAINED_FAILURE_SECONDS,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.max_chars = max_chars
        self.dry_run = dry_run
        self.sustained_failure_seconds = sustained_failure_seconds
        self._consecutive_update_failures = 0
        self._first_update_failure_at: float | None = None
        self._last_sustained_warning_at: float | None = None
        self._retry_after_seconds = 0.0

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

    @property
    def update_backoff_seconds(self) -> float:
        """How long the caller should wait before polling getUpdates again."""
        if self._consecutive_update_failures <= 0:
            return 0.0
        if self._retry_after_seconds > 0:
            return min(self._retry_after_seconds, ADMIN_UPDATE_MAX_BACKOFF_SECONDS)
        delay = ADMIN_UPDATE_BACKOFF_BASE_SECONDS * (2 ** (self._consecutive_update_failures - 1))
        return min(delay, ADMIN_UPDATE_MAX_BACKOFF_SECONDS)

    def _record_update_success(self) -> None:
        self._consecutive_update_failures = 0
        self._first_update_failure_at = None
        self._last_sustained_warning_at = None
        self._retry_after_seconds = 0.0

    def _record_update_failure(self, description: str, *, retry_after: float = 0.0) -> None:
        """Count one polling failure and log it at a level that matches its weight.

        Telegram returns short bursts of 502 all day. Logging each one as a
        warning buries real problems, so a burst stays at debug level and only
        an outage lasting past sustained_failure_seconds is warned about, once
        per interval.
        """
        now = time.monotonic()
        self._consecutive_update_failures += 1
        self._retry_after_seconds = max(0.0, retry_after)
        if self._first_update_failure_at is None:
            self._first_update_failure_at = now

        failing_for = now - self._first_update_failure_at
        delay = self.update_backoff_seconds
        if failing_for >= self.sustained_failure_seconds and (
            self._last_sustained_warning_at is None
            or now - self._last_sustained_warning_at >= self.sustained_failure_seconds
        ):
            self._last_sustained_warning_at = now
            logging.warning(
                "admin getUpdates failing for %.0f min (%s consecutive, retry in %.1fs): %s",
                failing_for / 60,
                self._consecutive_update_failures,
                delay,
                description,
            )
            return
        logging.debug(
            "admin getUpdates failed (%s consecutive, retry in %.1fs): %s",
            self._consecutive_update_failures,
            delay,
            description,
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
            # httpx timeouts stringify to an empty message, so log the type too.
            self._record_update_failure(f"{type(exc).__name__}: {exc!r}")
            return []
        if not data.get("ok"):
            parameters = data.get("parameters") or {}
            try:
                retry_after = float(parameters.get("retry_after") or 0)
            except (TypeError, ValueError):
                retry_after = 0.0
            self._record_update_failure(
                f"error_code={data.get('error_code')} description={data.get('description')!r}",
                retry_after=retry_after,
            )
            return []
        self._record_update_success()
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
