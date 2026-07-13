from datetime import datetime

import pytest

from n1_project.admin import AdminNotifier
from n1_project.article_channels import configured_article_channels
from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import PublishResult, SourcePost
from n1_project.llm import TextModel
from n1_project.worker import (
    approve_article_from_cli,
    dzen_article_candidate_messages,
    dzen_article_date_label,
    dzen_publisher_for_channel,
    generate_dzen_article,
    manual_article_channels,
    print_articles,
    process_timed_out_article_reviews,
    should_auto_publish_dzen_article,
)


class ArticleModel(TextModel):
    async def translate_post(self, source_text: str) -> str:
        raise NotImplementedError

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        return (
            "Рынок получил несколько важных сигналов к вечеру.\n\n"
            "Нефть, валюта и банки остались в центре внимания. "
            "Источник сохранил короткий формат новостей, поэтому выводы здесь осторожные.\n\n"
            "Первый блок фиксирует движение в энергетике. Второй блок показывает банковскую повестку.\n\n"
            "Итог дня простой: инвесторам стоит следить за новыми фактами, а не за громкими версиями."
        )


class RetryArticleModel(TextModel):
    def __init__(self) -> None:
        self.calls = 0

    async def translate_post(self, source_text: str) -> str:
        raise NotImplementedError

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        self.calls += 1
        if self.calls == 1:
            return (
                "Это слишком длинный заголовок, который специально превышает лимит Дзена и должен заставить "
                "воркер попросить модель переписать первый sentence перед публикацией черновика.\n\n"
                "Короткий текст."
            )
        assert review_note is not None
        return (
            "Короткий рыночный заголовок.\n\n"
            "Второй вариант уже соблюдает лимит заголовка и сохраняет факты без лишней драматизации."
        )


class FakeDzenPublisher:
    platform = "dzen"

    def __init__(self) -> None:
        self.published_texts: list[str] = []

    async def publish_text(self, text: str) -> PublishResult:
        self.published_texts.append(text)
        return PublishResult("dzen", True, destination_id="dzen-message")


def test_dzen_article_candidate_messages_backfills_topics(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "DZEN_ARTICLE_CHANNELS": "russia,energy,tech",
            "DZEN_ARTICLE_CANDIDATE_LIMIT": "10",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    oil_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Brent oil is higher"))
    btc_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "2", "BTC ETF inflows rise"))
    db.mark_translated(oil_id, "Brent grows")
    db.mark_translated(btc_id, "BTC ETF inflows rise")
    energy = next(channel for channel in configured_article_channels(settings) if channel.key == "energy")

    messages = dzen_article_candidate_messages(db, settings, energy)

    assert [message.id for message in messages] == [oil_id]
    assert db.message_by_id(oil_id).topic == "energy"
    assert db.message_by_id(btc_id).topic == "tech"


def test_manual_article_channels_can_select_one_or_all(tmp_path) -> None:
    settings = Settings.from_mapping(
        {"DZEN_ARTICLE_CHANNELS": "russia,energy,tech"},
        project_root=tmp_path,
    )

    assert [channel.key for channel in manual_article_channels(settings, "tech")] == ["tech"]
    assert [channel.key for channel in manual_article_channels(settings, "all")] == ["russia", "energy", "tech"]


def test_print_articles_outputs_recent_preview(tmp_path, capsys) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    db.record_article("Title.\n\nBody text.", "published", destination_id="77", slot_key="manual-tech-1")

    print_articles(db, limit=1)

    output = capsys.readouterr().out
    assert '"slot_key": "manual-tech-1"' in output
    assert '"text_preview": "Title. Body text."' in output


@pytest.mark.asyncio
async def test_dzen_publisher_for_channel_uses_channel_bot_token(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "main-token",
            "DZEN_ARTICLE_CHANNELS": "energy",
            "DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID": "-100energy",
            "DZEN_ENERGY_TELEGRAM_BOT_TOKEN": "energy-token",
        },
        project_root=tmp_path,
    )
    energy = configured_article_channels(settings)[0]

    publisher = dzen_publisher_for_channel(settings, energy, dry_run=True)
    result = await publisher.publish_text("Тест")

    assert result.ok is True
    assert result.payload["chat_id"] == "-100energy"
    assert publisher.bot_token == "energy-token"


@pytest.mark.asyncio
async def test_generate_dzen_article_publishes_directly_when_review_disabled(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Нефть растет")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 18:00",
    )

    article = db.article_for_slot("2026-07-06 18:00")
    assert article is not None
    assert article.status == "published"
    assert article.review_message_id is None
    assert len(fake_publisher.published_texts) == 1


@pytest.mark.asyncio
async def test_generate_dzen_article_appends_footer_for_daily_slot(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1200",
            "DZEN_ARTICLE_FOOTER_TELEGRAM_URL": "https://t.me/bazar",
            "DZEN_ARTICLE_FOOTER_VK_URL": "https://vk.com/bazar",
            "DZEN_ARTICLE_FOOTER_MAX_URL": "https://max.ru/bazar",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Нефть растет")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 russia:daily",
    )

    assert "https://t.me/bazar" in fake_publisher.published_texts[0]
    assert "https://vk.com/bazar" in fake_publisher.published_texts[0]
    assert "https://max.ru/bazar" in fake_publisher.published_texts[0]


@pytest.mark.asyncio
async def test_generate_dzen_article_skips_already_published_slot(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    db.record_article(
        "Existing title.\n\nExisting body.",
        "published",
        destination_id="dzen-message",
        slot_key="2026-07-06 russia:daily",
    )
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Нефть растет")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 russia:daily",
    )

    assert fake_publisher.published_texts == []
    assert db.article_for_slot("2026-07-06 russia:daily").text == "Existing title.\n\nExisting body."


@pytest.mark.asyncio
async def test_generate_dzen_article_sends_pending_review(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "ADMIN_TELEGRAM_CHAT_ID": "-100admin",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
            "DZEN_ARTICLE_REVIEW_ENABLED": "true",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Нефть растет")

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "-100admin", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 18:00",
    )

    article = db.article_for_slot("2026-07-06 18:00")
    assert article is not None
    assert article.status == "pending_review"
    assert article.review_attempts == 1
    assert article.review_message_id == "dry-run"
    assert db.translated_posts_for_article() == []


@pytest.mark.asyncio
async def test_generate_dzen_article_retries_invalid_title(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "ADMIN_TELEGRAM_CHAT_ID": "-100admin",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
            "DZEN_ARTICLE_REVIEW_ENABLED": "true",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Нефть растет")
    model = RetryArticleModel()

    await generate_dzen_article(
        db,
        settings,
        model,
        AdminNotifier("token", "-100admin", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 18:00",
    )

    article = db.article_for_slot("2026-07-06 18:00")
    assert article is not None
    assert article.status == "pending_review"
    assert article.text.startswith("Короткий рыночный заголовок.")
    assert model.calls == 2
def test_dzen_article_auto_publish_weekends(tmp_path) -> None:
    settings = Settings.from_mapping(
        {"DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS": "true"},
        project_root=tmp_path,
    )

    assert should_auto_publish_dzen_article(settings, datetime(2026, 7, 11, 18, 0)) is True
    assert should_auto_publish_dzen_article(settings, datetime(2026, 7, 6, 18, 0)) is False

    disabled = Settings.from_mapping(
        {"DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS": "false"},
        project_root=tmp_path,
    )
    assert should_auto_publish_dzen_article(disabled, datetime(2026, 7, 11, 18, 0)) is False


def test_dzen_article_date_label_uses_slot_date(tmp_path) -> None:
    settings = Settings.from_mapping({}, project_root=tmp_path)

    assert dzen_article_date_label(settings, slot_key="2026-07-06 18:00") == "6 июля 2026 года"


@pytest.mark.asyncio
async def test_generate_dzen_article_auto_publishes_on_weekend(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "ADMIN_TELEGRAM_CHAT_ID": "123456789",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
            "DZEN_ARTICLE_REVIEW_ENABLED": "true",
            "DZEN_ARTICLE_CANDIDATE_LIMIT": "10",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "РќРµС„С‚СЊ СЂР°СЃС‚РµС‚")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.should_auto_publish_dzen_article", lambda settings: True)
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-11 18:00",
    )

    article = db.article_for_slot("2026-07-11 18:00")
    assert article is not None
    assert article.status == "published"
    assert article.destination_id == "dzen-message"
    assert article.review_message_id is None
    assert len(fake_publisher.published_texts) == 1
    assert db.translated_posts_for_article() == []


@pytest.mark.asyncio
async def test_approve_article_from_cli_publishes_pending_review(tmp_path, monkeypatch, capsys) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    article_id = db.record_article("Market title.\n\nBody text.", "pending_review", review_attempts=1)
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await approve_article_from_cli(
        db,
        settings,
        AdminNotifier("token", "123456789", dry_run=True),
        article_id,
        dry_run=False,
    )

    output = capsys.readouterr().out
    article = db.article_by_id(article_id)
    assert '"ok": true' in output
    assert article is not None
    assert article.status == "published"
    assert article.destination_id == "dzen-message"
    assert fake_publisher.published_texts == ["Market title.\n\nBody text."]


@pytest.mark.asyncio
async def test_process_timed_out_article_reviews_rejects_old_pending_review(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "ADMIN_TELEGRAM_CHAT_ID": "123456789",
            "DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS": "3",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    article_id = db.record_article(
        "article text",
        "pending_review",
        slot_key="2026-07-06 18:00",
        review_attempts=1,
        review_chat_id="123456789",
        review_message_id="13",
    )
    with db.connect() as conn:
        conn.execute(
            "UPDATE articles SET updated_at = datetime('now', '-4 hours') WHERE id = ?",
            (article_id,),
        )

    await process_timed_out_article_reviews(
        db,
        settings,
        AdminNotifier("token", "123456789", dry_run=True),
    )

    article = db.article_by_id(article_id)
    assert article is not None
    assert article.status == "rejected_timeout"
    assert article.error == "review timed out after 3 hours"


def test_dzen_article_date_label_uses_slot_date(tmp_path) -> None:
    settings = Settings.from_mapping({}, project_root=tmp_path)

    assert dzen_article_date_label(settings, slot_key="2026-07-06 18:00") == "6 июля 2026 года"
