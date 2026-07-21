import json
from datetime import datetime

import pytest

from n1_project.admin import AdminNotifier
from n1_project.article_channels import configured_article_channels
from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import PublishResult, QueuedMessage, SourcePost
from n1_project.images import ArticleImage
from n1_project.llm import TextModel
from n1_project.story_plan import StoryPlan
from n1_project.worker import (
    approve_article_from_cli,
    dzen_article_candidate_messages,
    dzen_article_date_label,
    dzen_publisher_for_channel,
    generate_dzen_article,
    manual_article_channels,
    print_articles,
    process_timed_out_article_reviews,
    publish_generated_dzen_article,
    select_dzen_article_image,
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
        story_plan=None,
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
        story_plan=None,
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


class OverLimitArticleModel(TextModel):
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
        story_plan=None,
    ) -> str:
        self.calls += 1
        return (
            "Market title.\n\n"
            "First paragraph keeps the useful context and should survive trimming. "
            "It explains why the selected market signal matters for readers.\n\n"
            "Second paragraph adds another grounded detail from the source pool. "
            "It is still relevant and can remain if space allows.\n\n"
            "Third paragraph is useful but less important than the opening. "
            "This paragraph may be removed when the Telegram bridge limit is tight.\n\n"
            "Final paragraph is the least important part of this generated draft. "
            "It should disappear before the footer links are touched."
        )


class AlwaysInvalidArticleModel(TextModel):
    async def translate_post(self, source_text: str) -> str:
        raise NotImplementedError

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        story_plan=None,
    ) -> str:
        return ("A" * 141) + ".\n\nBody text."


class SelectiveArticleModel(ArticleModel):
    def __init__(self) -> None:
        self.received_posts: list[str] = []

    async def plan_dzen_story(
        self,
        candidates,
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        channel_note: str | None = None,
    ) -> str:
        selected_ids = [candidates[0].message_id, candidates[2].message_id]
        return json.dumps(
            {
                "thesis": "Снижение ставки и IPO усиливают тему рынка капитала.",
                "selected_message_ids": selected_ids,
                "mode": "cluster",
                "connection": "Ставка влияет на стоимость денег, а IPO показывает спрос на новые сделки.",
                "causal_chain": [
                    "Более низкая ставка делает деньги дешевле.",
                    "На этом фоне компаниям проще тестировать интерес инвесторов к размещениям.",
                ],
                "why_it_matters": "Для инвесторов это смещает внимание к новым корпоративным сделкам.",
                "what_changes_view": "Картину изменят решение ЦБ и фактический спрос на IPO.",
                "image_query": "russian stock exchange investors",
                "confidence": 0.82,
            },
            ensure_ascii=False,
        )

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        story_plan=None,
    ) -> str:
        self.received_posts = posts
        return (
            "Ставка и IPO возвращают внимание к рынку капитала.\n\n"
            "В выбранных источниках ставка связана со стоимостью денег, а IPO показывает спрос на новые сделки.\n\n"
            "Для инвесторов это важно как переход от ожидания ставки к конкретным корпоративным историям.\n\n"
            "Картину изменят решение ЦБ и фактический спрос на размещения."
        )


class FakeDzenPublisher:
    platform = "dzen"

    def __init__(self) -> None:
        self.published_texts: list[str] = []
        self.published_photos: list[tuple[str, str]] = []

    async def publish_text(self, text: str) -> PublishResult:
        self.published_texts.append(text)
        return PublishResult("dzen", True, destination_id="dzen-message")

    async def publish_photo(self, photo_url: str, caption: str) -> PublishResult:
        self.published_photos.append((photo_url, caption))
        return PublishResult("dzen", True, destination_id="dzen-photo-message")


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
async def test_generate_dzen_article_links_only_selected_story_messages(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
            "DZEN_ARTICLE_CANDIDATE_LIMIT": "10",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    first_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "The central bank may cut rates"))
    second_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "2", "Oil inventories rose"))
    third_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "3", "The market expects more IPOs"))
    db.mark_translated(first_id, "ЦБ может снизить ставку")
    db.mark_translated(second_id, "Запасы нефти выросли")
    db.mark_translated(third_id, "Рынок ждет новых IPO")
    fake_publisher = FakeDzenPublisher()
    model = SelectiveArticleModel()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        model,
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-20 markets:morning",
    )

    article = db.article_for_slot("2026-07-20 markets:morning")
    assert article is not None
    assert article.status == "published"
    assert model.received_posts == ["ЦБ может снизить ставку", "Рынок ждет новых IPO"]
    assert [message.id for message in db.messages_for_article(article.id)] == [first_id, third_id]
    assert [message.id for message in db.translated_posts_for_article()] == [second_id]
    assert article.selected_message_ids_json == f"[{first_id}, {third_id}]"
    assert article.plan_json is not None
    assert "russian stock exchange investors" in article.plan_json


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
async def test_generate_dzen_article_trims_over_limit_body_before_footer(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "440",
            "DZEN_ARTICLE_FOOTER_TELEGRAM_URL": "https://t.me/bazar",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Oil is higher")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})
    model = OverLimitArticleModel()

    await generate_dzen_article(
        db,
        settings,
        model,
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 russia:daily",
    )

    article = db.article_for_slot("2026-07-06 russia:daily")
    assert article is not None
    assert article.status == "published"
    assert len(fake_publisher.published_texts[0]) <= settings.dzen_article_target_max_chars
    assert "https://t.me/bazar" in fake_publisher.published_texts[0]
    assert "Final paragraph" not in fake_publisher.published_texts[0]
    assert model.calls == 1


@pytest.mark.asyncio
async def test_generate_dzen_article_records_validation_failure_without_raising(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "1",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "1000",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Oil is higher"))
    db.mark_translated(row_id, "Oil is higher")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        AlwaysInvalidArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 russia:daily",
    )

    article = db.article_for_slot("2026-07-06 russia:daily")
    assert article is not None
    assert article.status == "failed_validation"
    assert "title too long" in (article.error or "")
    assert fake_publisher.published_texts == []


@pytest.mark.asyncio
async def test_generate_dzen_article_publishes_pexels_photo_caption(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "950",
            "DZEN_ARTICLE_IMAGE_ENABLED": "true",
            "DZEN_ARTICLE_IMAGE_CREDIT_ENABLED": "true",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "BTC ETF inflows rise"))
    db.mark_translated(row_id, "Приток в BTC ETF растет")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    async def fake_select_image(*args, **kwargs):
        return ArticleImage(
            url="https://images.pexels.com/photos/btc.jpg",
            query="cryptocurrency bitcoin market",
            photographer="Jane Doe",
        )

    monkeypatch.setattr("n1_project.worker.select_dzen_article_image", fake_select_image)

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 markets:morning",
    )

    article = db.article_for_slot("2026-07-06 markets:morning")
    assert article is not None
    assert article.status == "published"
    assert article.destination_id == "dzen-photo-message"
    assert article.image_url == "https://images.pexels.com/photos/btc.jpg"
    assert article.image_query == "cryptocurrency bitcoin market"
    assert fake_publisher.published_texts == []
    assert fake_publisher.published_photos[0][0] == "https://images.pexels.com/photos/btc.jpg"
    assert "Фото: Jane Doe / Pexels" in fake_publisher.published_photos[0][1]


@pytest.mark.asyncio
async def test_publish_generated_dzen_article_rejects_overlong_photo_caption(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_IMAGE_ENABLED": "true",
            "TELEGRAM_PHOTO_CAPTION_MAX_CHARS": "1024",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})
    image = ArticleImage(url="https://images.pexels.com/photos/market.jpg", query="financial market chart")

    await publish_generated_dzen_article(
        db,
        settings,
        AdminNotifier("token", "123456789", dry_run=True),
        "A" * 1025,
        message_ids=[1],
        dry_run=False,
        slot_key="2026-07-06 markets:morning",
        image=image,
    )

    article = db.article_for_slot("2026-07-06 markets:morning")
    assert article is not None
    assert article.status == "failed_validation"
    assert article.image_url == "https://images.pexels.com/photos/market.jpg"
    assert "Dzen photo caption too long: 1025 chars; max is 1024" in (article.error or "")
    assert fake_publisher.published_texts == []
    assert fake_publisher.published_photos == []


@pytest.mark.asyncio
async def test_generate_dzen_article_requires_image_when_visual_posts_are_enabled(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "DZEN_TELEGRAM_BRIDGE_CHAT_ID": "-100dzen",
            "DZEN_ARTICLE_TARGET_MIN_CHARS": "50",
            "DZEN_ARTICLE_TARGET_MAX_CHARS": "950",
            "DZEN_ARTICLE_IMAGE_ENABLED": "true",
        },
        project_root=tmp_path,
    )
    assert settings.dzen_article_image_required is True
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "BTC ETF inflows rise"))
    db.mark_translated(row_id, "Приток в BTC ETF растет")
    fake_publisher = FakeDzenPublisher()
    monkeypatch.setattr("n1_project.worker.build_publishers", lambda settings, dry_run=False: {"dzen": fake_publisher})

    await generate_dzen_article(
        db,
        settings,
        ArticleModel(),
        AdminNotifier("token", "123456789", dry_run=True),
        dry_run=False,
        force=True,
        slot_key="2026-07-06 markets:morning",
    )

    article = db.article_for_slot("2026-07-06 markets:morning")
    assert article is not None
    assert article.status == "failed_image"
    assert "Pexels image lookup returned no usable photo" in (article.error or "")
    assert fake_publisher.published_texts == []
    assert fake_publisher.published_photos == []


@pytest.mark.asyncio
async def test_select_dzen_article_image_uses_story_plan_query(tmp_path) -> None:
    settings = Settings.from_mapping(
        {
            "DZEN_ARTICLE_IMAGE_ENABLED": "true",
        },
        project_root=tmp_path,
    )
    channel = configured_article_channels(settings)[0]
    message = QueuedMessage(
        1,
        "@num1_ch",
        "1",
        "Brent oil is higher",
        "Нефть растет",
        "translated",
        0,
        None,
        topic="energy",
    )
    plan = StoryPlan(
        thesis="Рынок капитала оживает.",
        selected_message_ids=(1,),
        mode="single",
        connection="Один факт.",
        causal_chain=("Факт.", "Значение."),
        why_it_matters="Значение.",
        what_changes_view="Что изменит картину.",
        image_query="russian stock exchange investors",
        confidence=0.7,
    )

    image = await select_dzen_article_image(
        settings,
        article="Рынок капитала оживает.\n\nТекст.",
        messages=[message],
        channel=channel,
        story_plan=plan,
        dry_run=True,
    )

    assert image is not None
    assert image.query == "russian stock exchange investors"
    assert "oil" not in image.query


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
