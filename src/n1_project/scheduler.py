from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def local_now(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))


def current_slot(now: datetime, times: list[str], window_minutes: int = 5) -> str | None:
    """Return the matching HH:MM slot if now is close enough to it."""

    current_minutes = now.hour * 60 + now.minute
    for raw_time in times:
        hour_text, minute_text = raw_time.split(":", 1)
        target_minutes = int(hour_text) * 60 + int(minute_text)
        if 0 <= current_minutes - target_minutes < window_minutes:
            return raw_time
    return None
