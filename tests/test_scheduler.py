from datetime import datetime
from zoneinfo import ZoneInfo

from n1_project.scheduler import current_slot


def test_current_slot_matches_within_window() -> None:
    now = datetime(2026, 7, 3, 13, 3, tzinfo=ZoneInfo("Europe/Moscow"))

    assert current_slot(now, ["13:00", "19:00"]) == "13:00"


def test_current_slot_does_not_match_before_or_after_window() -> None:
    before = datetime(2026, 7, 3, 12, 59, tzinfo=ZoneInfo("Europe/Moscow"))
    after = datetime(2026, 7, 3, 13, 6, tzinfo=ZoneInfo("Europe/Moscow"))

    assert current_slot(before, ["13:00"]) is None
    assert current_slot(after, ["13:00"]) is None
