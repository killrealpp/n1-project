from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePost:
    source_channel_id: str
    source_message_id: str
    text: str
    date_iso: str | None = None


@dataclass(frozen=True)
class QueuedMessage:
    id: int
    source_channel_id: str
    source_message_id: str
    source_text: str
    translated_text: str | None
    status: str
    attempts: int
    last_error: str | None


@dataclass(frozen=True)
class PublishResult:
    platform: str
    ok: bool
    destination_id: str | None = None
    error: str | None = None
    payload: dict[str, object] | None = None


@dataclass(frozen=True)
class ArticleRecord:
    id: int
    slot_key: str | None
    text: str
    status: str
    destination_id: str | None
    error: str | None
    review_attempts: int
    review_chat_id: str | None
    review_message_id: str | None
    created_at: str
    updated_at: str
