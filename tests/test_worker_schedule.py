from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from n1_project.config import Settings
from n1_project.worker import due_article_slot


def test_due_article_slot_returns_stable_slot_key(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "DZEN_DAILY_ARTICLES_ENABLED": "true",
            "DZEN_DAILY_ARTICLE_TIMES": "13:00,19:00",
        },
        project_root=tmp_path,
    )
    now = datetime(2026, 7, 3, 13, 2, tzinfo=ZoneInfo("Europe/Moscow"))

    assert due_article_slot(settings, now=now) == "2026-07-03 13:00"


def test_due_article_slot_disabled(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {"DZEN_DAILY_ARTICLES_ENABLED": "false", "DZEN_DAILY_ARTICLE_TIMES": "13:00"},
        project_root=tmp_path,
    )
    now = datetime(2026, 7, 3, 13, 2, tzinfo=ZoneInfo("Europe/Moscow"))

    assert due_article_slot(settings, now=now) is None
