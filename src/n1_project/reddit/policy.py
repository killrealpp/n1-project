"""Policy constants for the planned Reddit profile publishing stream."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class RedditSlotWindow:
    """A possible publication window, not an obligation to publish."""

    start_msk: str
    end_msk: str
    topic_hint: str


STARTING_DAILY_POST_LIMIT: Final[int] = 6
HARD_DAILY_POST_LIMIT: Final[int] = 12
MIN_MINUTES_BETWEEN_REDDIT_POSTS: Final[int] = 75

DEFAULT_POST_WINDOWS_MSK: Final[tuple[RedditSlotWindow, ...]] = (
    RedditSlotWindow("09:10", "10:20", "markets"),
    RedditSlotWindow("11:30", "12:50", "energy"),
    RedditSlotWindow("14:00", "15:20", "crypto"),
    RedditSlotWindow("16:30", "17:50", "russia"),
    RedditSlotWindow("19:00", "20:20", "ai"),
    RedditSlotWindow("21:30", "22:50", "geopolitics"),
)

RESERVE_POST_WINDOWS_MSK: Final[tuple[RedditSlotWindow, ...]] = (
    RedditSlotWindow("10:25", "11:20", "markets"),
    RedditSlotWindow("13:00", "13:55", "crypto"),
    RedditSlotWindow("15:30", "16:20", "energy"),
    RedditSlotWindow("18:00", "18:50", "chips"),
    RedditSlotWindow("20:35", "21:25", "russia"),
    RedditSlotWindow("22:55", "23:40", "markets"),
)

ALLOWED_HASHTAGS: Final[tuple[str, ...]] = (
    "#ai",
    "#bitcoin",
    "#chips",
    "#crypto",
    "#energy",
    "#geopolitics",
    "#markets",
    "#oil",
    "#rates",
    "#russia",
)

TOPIC_HASHTAGS: Final[dict[str, tuple[str, ...]]] = {
    "markets": ("#markets",),
    "russia": ("#markets", "#russia"),
    "energy": ("#energy", "#oil", "#markets"),
    "crypto": ("#crypto", "#bitcoin", "#markets"),
    "ai": ("#ai", "#markets"),
    "chips": ("#chips", "#ai", "#markets"),
    "geopolitics": ("#geopolitics", "#markets"),
    "rates": ("#rates", "#markets"),
}

TOPIC_DAILY_CAPS: Final[dict[str, int]] = {
    "markets": 3,
    "russia": 3,
    "energy": 2,
    "crypto": 2,
    "ai": 2,
    "chips": 2,
    "geopolitics": 2,
    "rates": 2,
}


def hashtags_for_topic(topic: str) -> tuple[str, ...]:
    return TOPIC_HASHTAGS.get(topic.lower(), ("#markets",))


def stable_publish_time(date_key: str, window: RedditSlotWindow, salt: str = "reddit") -> str:
    """Pick a stable per-day minute inside a window.

    The result changes across dates, but stays stable for restarts on the same
    date so the scheduler can remain idempotent.
    """

    start = minutes_from_hhmm(window.start_msk)
    end = minutes_from_hhmm(window.end_msk)
    if end < start:
        raise ValueError(f"Reddit window ends before it starts: {window.start_msk}-{window.end_msk}")
    digest = hashlib.sha256(f"{salt}|{date_key}|{window.topic_hint}|{window.start_msk}-{window.end_msk}".encode()).digest()
    minute = start + int.from_bytes(digest[:4], "big") % (end - start + 1)
    return hhmm_from_minutes(minute)


def minutes_from_hhmm(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid HH:MM value: {value}")
    hour, minute = (int(part) for part in parts)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Invalid HH:MM value: {value}")
    return hour * 60 + minute


def hhmm_from_minutes(value: int) -> str:
    if not 0 <= value < 24 * 60:
        raise ValueError(f"Invalid minute of day: {value}")
    return f"{value // 60:02d}:{value % 60:02d}"
