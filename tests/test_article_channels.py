from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from n1_project.article_channels import (
    classify_text_topic,
    configured_article_channels,
    daily_article_schedule,
    due_article_slots,
    filter_messages_for_channel,
    stable_publish_time,
)
from n1_project.config import Settings
from n1_project.domain import QueuedMessage


def test_stable_publish_time_is_inside_window_and_repeatable() -> None:
    day = datetime(2026, 7, 10).date()

    first = stable_publish_time(
        day=day,
        channel_key="energy",
        window_index=0,
        window="09:20-10:20",
        randomize=True,
    )
    second = stable_publish_time(
        day=day,
        channel_key="energy",
        window_index=0,
        window="09:20-10:20",
        randomize=True,
    )

    assert first == second
    assert "09:20" <= first < "10:20"


def test_daily_article_schedule_creates_one_slot_per_channel(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "DZEN_ARTICLE_CHANNELS": "russia,energy,tech",
            "DZEN_ARTICLE_RANDOMIZE_TIMES": "false",
        },
        project_root=tmp_path,
    )

    slots = daily_article_schedule(settings, datetime(2026, 7, 10).date())

    assert len(slots) == 3
    assert [slot.slot_key for slot in slots] == [
        "2026-07-10 russia:daily",
        "2026-07-10 energy:daily",
        "2026-07-10 tech:daily",
    ]
    assert [slot.publish_time for slot in slots] == ["10:30", "14:30", "18:30"]


def test_configured_article_channels_use_channel_bot_tokens(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "main-token",
            "DZEN_ARTICLE_CHANNELS": "russia,energy,tech",
            "DZEN_ENERGY_TELEGRAM_BOT_TOKEN": "energy-token",
            "DZEN_TECH_TELEGRAM_BOT_TOKEN": "tech-token",
        },
        project_root=tmp_path,
    )

    channels = {channel.key: channel for channel in configured_article_channels(settings)}

    assert channels["russia"].bot_token == "main-token"
    assert channels["energy"].bot_token == "energy-token"
    assert channels["tech"].bot_token == "tech-token"


def test_due_article_slots_matches_randomized_time(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {
            "DZEN_DAILY_ARTICLES_ENABLED": "true",
            "DZEN_ARTICLE_CHANNELS": "energy",
            "DZEN_ARTICLE_WINDOWS": "energy=09:20-10:20",
            "DZEN_ARTICLE_RANDOMIZE_TIMES": "false",
        },
        project_root=tmp_path,
    )

    due = due_article_slots(settings, datetime(2026, 7, 10, 9, 22, tzinfo=ZoneInfo("Europe/Moscow")))

    assert len(due) == 1
    assert due[0].slot_key == "2026-07-10 energy:daily"


def test_filter_messages_for_channel_keeps_matching_topic() -> None:
    messages = [
        QueuedMessage(1, "@src", "1", "Brent is higher", "Нефть Brent растет", "published", 0, None),
        QueuedMessage(2, "@src", "2", "BTC ETF inflows rise", "Приток в BTC ETF растет", "published", 0, None),
        QueuedMessage(3, "@src", "3", "IMOEX is lower", "Индекс Мосбиржи IMOEX снижается", "published", 0, None),
    ]

    assert [message.id for message in filter_messages_for_channel(messages, "energy")] == [1]
    assert [message.id for message in filter_messages_for_channel(messages, "tech")] == [2]
    assert [message.id for message in filter_messages_for_channel(messages, "russia")] == [3]


def test_classify_text_topic_picks_one_channel() -> None:
    assert classify_text_topic("Brent oil and natural gas prices moved higher") == "energy"
    assert classify_text_topic("AI chips and BTC inflows are back in focus") == "tech"
    assert classify_text_topic("Russian ruble and MOEX shares are weaker") == "russia"


def test_saved_topic_overrides_keyword_matches() -> None:
    messages = [
        QueuedMessage(
            1,
            "@src",
            "1",
            "Brent oil is higher",
            "Brent grows",
            "published",
            0,
            None,
            topic="tech",
        ),
    ]

    assert filter_messages_for_channel(messages, "energy") == []
    assert [message.id for message in filter_messages_for_channel(messages, "tech")] == [1]
