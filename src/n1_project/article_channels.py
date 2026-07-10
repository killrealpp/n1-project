from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from n1_project.domain import QueuedMessage
from n1_project.scheduler import local_now

if TYPE_CHECKING:
    from n1_project.config import Settings


DEFAULT_CHANNEL_WINDOWS = {
    "russia": ["09:00-10:00", "14:00-15:00", "18:30-19:30"],
    "energy": ["09:20-10:20", "14:25-15:25", "19:15-20:15"],
    "tech": ["09:40-10:40", "14:50-15:50", "20:00-21:00"],
}
DEFAULT_CHANNEL_NAMES = {
    "russia": "BAZAR RUSSIA",
    "energy": "BAZAR ENERGY",
    "tech": "BAZAR TECH",
}
DEFAULT_TOPIC_HINTS = {
    "russia": (
        "российский рынок, рубль, ЦБ, IPO, дивиденды, buyback, облигации, "
        "российские компании, банки, ипотека и экономика для людей"
    ),
    "energy": (
        "нефть, газ, СПГ, бензин, металлы, сырьевые прогнозы, Ормуз, "
        "энергетика и геополитические риски, влияющие на цены"
    ),
    "tech": (
        "криптовалюты, BTC, ETH, DeFi, стейблкоины, ИИ, чипы, "
        "технологические компании и глобальные технорынки"
    ),
}
SLOT_LABELS = ("morning", "afternoon", "evening")
TOPIC_PRIORITY = ("tech", "energy", "russia")


@dataclass(frozen=True)
class ArticleChannel:
    key: str
    name: str
    bridge_chat_id: str
    bot_token: str
    windows: tuple[str, ...]
    topic_hint: str


@dataclass(frozen=True)
class ArticleDueSlot:
    channel: ArticleChannel
    window_index: int
    window: str
    publish_time: str
    slot_key: str

    @property
    def slot_label(self) -> str:
        if self.window_index < len(SLOT_LABELS):
            return SLOT_LABELS[self.window_index]
        return f"slot{self.window_index + 1}"


def configured_article_channels(settings: Settings) -> list[ArticleChannel]:
    channels: list[ArticleChannel] = []
    for key in settings.dzen_article_channels or ["russia"]:
        normalized = key.strip().lower()
        if not normalized:
            continue
        windows = settings.dzen_article_windows.get(normalized) or DEFAULT_CHANNEL_WINDOWS.get(normalized)
        if not windows and settings.dzen_daily_article_times:
            windows = [f"{item}-{item}" for item in settings.dzen_daily_article_times]
        if not windows:
            windows = DEFAULT_CHANNEL_WINDOWS["russia"]
        channels.append(
            ArticleChannel(
                key=normalized,
                name=DEFAULT_CHANNEL_NAMES.get(normalized, normalized.upper()),
                bridge_chat_id=settings.dzen_article_bridge_chat_ids.get(normalized, ""),
                bot_token=settings.dzen_article_bot_tokens.get(normalized, settings.telegram_bot_token),
                windows=tuple(windows),
                topic_hint=DEFAULT_TOPIC_HINTS.get(normalized, "рыночные новости и экономические сигналы"),
            )
        )
    return channels


def default_article_channel(settings: Settings) -> ArticleChannel:
    channels = configured_article_channels(settings)
    return channels[0] if channels else ArticleChannel(
        key="russia",
        name="BAZAR RUSSIA",
        bridge_chat_id=settings.dzen_telegram_bridge_chat_id,
        bot_token=settings.dzen_article_bot_tokens.get("russia", settings.telegram_bot_token),
        windows=tuple(DEFAULT_CHANNEL_WINDOWS["russia"]),
        topic_hint=DEFAULT_TOPIC_HINTS["russia"],
    )


def article_channel_from_slot(settings: Settings, slot_key: str | None) -> ArticleChannel:
    if slot_key:
        parts = slot_key.split()
        if len(parts) >= 2 and ":" in parts[1]:
            key = parts[1].split(":", 1)[0].lower()
            for channel in configured_article_channels(settings):
                if channel.key == key:
                    return channel
    return default_article_channel(settings)


def parse_hhmm(value: str) -> int:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"invalid time: {value}")
    return hour * 60 + minute


def format_hhmm(total_minutes: int) -> str:
    total_minutes %= 24 * 60
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def parse_window(window: str) -> tuple[int, int]:
    if "-" not in window:
        minute = parse_hhmm(window)
        return minute, minute
    start_text, end_text = window.split("-", 1)
    start = parse_hhmm(start_text.strip())
    end = parse_hhmm(end_text.strip())
    if end < start:
        raise ValueError(f"article window crosses midnight or is invalid: {window}")
    return start, end


def stable_publish_time(
    *,
    day: date,
    channel_key: str,
    window_index: int,
    window: str,
    randomize: bool,
) -> str:
    start, end = parse_window(window)
    if not randomize or start == end:
        return format_hhmm(start)
    span = max(1, end - start)
    seed = f"{day.isoformat()}|{channel_key}|{window_index}|{window}".encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    offset = int.from_bytes(digest[:8], "big") % span
    return format_hhmm(start + offset)


def daily_article_schedule(settings: Settings, current_date: date) -> list[ArticleDueSlot]:
    slots: list[ArticleDueSlot] = []
    for channel in configured_article_channels(settings):
        for index, window in enumerate(channel.windows):
            publish_time = stable_publish_time(
                day=current_date,
                channel_key=channel.key,
                window_index=index,
                window=window,
                randomize=settings.dzen_article_randomize_times,
            )
            label = SLOT_LABELS[index] if index < len(SLOT_LABELS) else f"slot{index + 1}"
            slots.append(
                ArticleDueSlot(
                    channel=channel,
                    window_index=index,
                    window=window,
                    publish_time=publish_time,
                    slot_key=f"{current_date.isoformat()} {channel.key}:{label}",
                )
            )
    return slots


def due_article_slots(settings: Settings, now: datetime | None = None) -> list[ArticleDueSlot]:
    if not settings.dzen_daily_articles_enabled:
        return []
    current = now or local_now(settings.app_timezone)
    current_minutes = current.hour * 60 + current.minute
    due: list[ArticleDueSlot] = []
    for slot in daily_article_schedule(settings, current.date()):
        target_minutes = parse_hhmm(slot.publish_time)
        if 0 <= current_minutes - target_minutes < settings.dzen_article_slot_window_minutes:
            due.append(slot)
    return due


TOKEN_RULES: dict[str, tuple[str, ...]] = {
    "russia": (
        "🇷🇺",
        "russia",
        "russian",
        "ruble",
        "rouble",
        "cbr",
        "key rate",
        "moscow exchange",
        "dividend",
        "dividends",
        "imoex",
        "rgbi",
        "moex",
        "мосбирж",
        "московск",
        "банк россии",
        "цбр",
        "цб",
        "ключев",
        "рубл",
        "ipo",
        "нспк",
        "совкомбанк",
        "северсталь",
        "втб",
        "сбер",
        "softline",
        "дивиден",
        "buyback",
        "обратн",
        "акци",
        "облигац",
        "минфин",
        "ипотек",
        "ваканс",
        "зарплат",
        "интерфакс",
        "риа",
        "тасс",
        "известия",
        "ведомости",
    ),
    "energy": (
        "🛢",
        "нефт",
        "oil",
        "crude",
        "gas",
        "natural gas",
        "fuel",
        "gasoline",
        "diesel",
        "energy",
        "tanker",
        "tankers",
        "brent",
        "wti",
        "urals",
        "спг",
        "lng",
        "газ",
        "бензин",
        "топлив",
        "eia",
        "spr",
        "opec",
        "опек",
        "ормуз",
        "hormuz",
        "катар",
        "танкер",
        "алюмин",
        "goldman",
        "morgan stanley",
        "металл",
        "золото",
        "медь",
        "уголь",
        "санкц",
        "иран",
        "ближн",
    ),
    "tech": (
        "✴",
        "ai",
        "chip",
        "chips",
        "semiconductor",
        "semiconductors",
        "crypto",
        "stablecoin",
        "stablecoins",
        "blockchain",
        "token",
        "tokens",
        "btc",
        "eth",
        "bitcoin",
        "ethereum",
        "битко",
        "эфир",
        "крипт",
        "стейбл",
        "defi",
        "tvl",
        "on-chain",
        "ончейн",
        "cryptoquant",
        "glassnode",
        "bitwise",
        "sosovalue",
        "usdt",
        "usdc",
        "solana",
        "bonk",
        "zcash",
        "openai",
        "anthropic",
        "nvidia",
        "nvda",
        "samsung",
        "hynix",
        "palantir",
        "spacex",
        "gpt",
        "ии",
        "нейросет",
        "чип",
        "полупровод",
        "технолог",
        "it-сектор",
    ),
}


def topic_score(text: str, channel_key: str) -> int:
    normalized = " " + text.lower() + " "
    score = 0
    for token in TOKEN_RULES.get(channel_key, ()):
        if len(token) <= 3 and token.isascii():
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", normalized):
                score += 1
            continue
        if token in normalized:
            score += 1
    return score


def message_text(message: QueuedMessage) -> str:
    return "\n".join(part for part in (message.translated_text, message.source_text) if part)


def classify_text_topic(text: str) -> str | None:
    scores = {channel_key: topic_score(text, channel_key) for channel_key in TOKEN_RULES}
    best_score = max(scores.values(), default=0)
    if best_score <= 0:
        return None
    for channel_key in TOPIC_PRIORITY:
        if scores.get(channel_key) == best_score:
            return channel_key
    return max(scores, key=scores.get)


def classify_message_topic(message: QueuedMessage) -> str | None:
    if message.topic in TOKEN_RULES:
        return message.topic
    return classify_text_topic(message_text(message))


def message_matches_channel(message: QueuedMessage, channel_key: str) -> bool:
    if channel_key not in TOKEN_RULES:
        return True
    if message.topic in TOKEN_RULES:
        return message.topic == channel_key
    return topic_score(message_text(message), channel_key) > 0


def filter_messages_for_channel(messages: list[QueuedMessage], channel_key: str) -> list[QueuedMessage]:
    return [message for message in messages if message_matches_channel(message, channel_key)]


def article_channel_review_note(channel: ArticleChannel, review_note: str | None = None) -> str:
    channel_note = (
        f"Канал статьи: {channel.name}. "
        f"Тематика канала: {channel.topic_hint}. "
        "Выбирай только посты, которые подходят этой тематике. "
        "Если среди кандидатов есть чужие темы, не используй их в статье."
    )
    if review_note:
        return channel_note + "\n\n" + review_note
    return channel_note
