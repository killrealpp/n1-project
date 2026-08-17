from pathlib import Path

from n1_project.admin import AdminNotifier
from n1_project.article_channels import ArticleDueSlot, configured_article_channels
from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.llm import TextModel
from n1_project.worker import (
    article_slot_is_open,
    handle_article_slot_failure,
    run_processing_pass,
)


def slot_settings(tmp_path: Path, **overrides: str) -> Settings:
    values = {
        "DZEN_DAILY_ARTICLES_ENABLED": "true",
        "DZEN_ARTICLE_CHANNELS": "russia,energy",
        "DZEN_ARTICLE_SLOT_MAX_ATTEMPTS": "6",
    }
    values.update(overrides)
    return Settings.from_mapping(values, project_root=tmp_path)


def make_slot(settings: Settings, channel_key: str, slot_key: str) -> ArticleDueSlot:
    channel = next(item for item in configured_article_channels(settings) if item.key == channel_key)
    return ArticleDueSlot(
        channel=channel,
        window_index=0,
        window="11:30-12:00",
        publish_time="11:40",
        slot_key=slot_key,
    )


class UnusedModel(TextModel):
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
        raise NotImplementedError


def test_article_slot_is_open_for_an_untouched_slot(tmp_path: Path) -> None:
    settings = slot_settings(tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()

    assert article_slot_is_open(db, settings, make_slot(settings, "russia", "2026-08-17 russia:morning")) is True


def test_article_slot_closes_after_publishing(tmp_path: Path) -> None:
    settings = slot_settings(tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    db.record_article("Заголовок.\n\nТекст.", "published", slot_key="2026-08-17 russia:morning")

    assert article_slot_is_open(db, settings, make_slot(settings, "russia", "2026-08-17 russia:morning")) is False


def test_article_slot_stays_open_while_the_attempt_budget_lasts(tmp_path: Path) -> None:
    settings = slot_settings(tmp_path, DZEN_ARTICLE_SLOT_MAX_ATTEMPTS="3")
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    slot = make_slot(settings, "russia", "2026-08-17 russia:morning")

    # A budget of three allows exactly three attempts, then the slot closes.
    for _ in range(3):
        assert article_slot_is_open(db, settings, slot) is True
        db.record_article(
            "",
            "failed_generation",
            error="boom",
            slot_key=slot.slot_key,
            increment_generation_attempt=True,
        )

    assert db.article_slot_state(slot.slot_key) == ("failed_generation", 3)
    assert article_slot_is_open(db, settings, slot) is False


async def test_handle_article_slot_failure_records_a_visible_row(tmp_path: Path) -> None:
    settings = slot_settings(tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    admin = AdminNotifier("token", "-100", dry_run=True)
    slot = make_slot(settings, "energy", "2026-08-17 energy:morning")

    await handle_article_slot_failure(
        db,
        settings,
        admin,
        slot,
        RuntimeError("Client error '404 Not Found'"),
        dry_run=False,
    )

    article = db.article_for_slot(slot.slot_key)
    assert article is not None
    assert article.status == "failed_generation"
    assert article.generation_attempts == 1
    assert "404 Not Found" in (article.error or "")


async def test_handle_article_slot_failure_keeps_dry_runs_out_of_the_database(tmp_path: Path) -> None:
    settings = slot_settings(tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    admin = AdminNotifier("token", "-100", dry_run=True)
    slot = make_slot(settings, "energy", "2026-08-17 energy:morning")

    await handle_article_slot_failure(db, settings, admin, slot, RuntimeError("boom"), dry_run=True)

    assert db.article_for_slot(slot.slot_key) is None


async def test_one_failing_slot_does_not_stop_the_other_slots_or_the_pass(tmp_path: Path, monkeypatch) -> None:
    settings = slot_settings(tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    admin = AdminNotifier("token", "-100", dry_run=True)
    russia = make_slot(settings, "russia", "2026-08-17 russia:morning")
    energy = make_slot(settings, "energy", "2026-08-17 energy:morning")
    attempted: list[str] = []

    async def failing_generate(db_arg, settings_arg, model_arg, admin_arg, **kwargs) -> None:
        slot_key = kwargs["slot_key"]
        attempted.append(slot_key)
        if slot_key == russia.slot_key:
            raise RuntimeError("Client error '404 Not Found'")

    monkeypatch.setattr("n1_project.worker.due_article_slots", lambda *a, **kw: [russia, energy])
    monkeypatch.setattr("n1_project.worker.generate_dzen_article", failing_generate)

    await run_processing_pass(
        db,
        settings,
        UnusedModel(),
        admin,
        source_mode="none",
        dry_run=False,
        limit=5,
        article=False,
        force_article=False,
        article_channel=None,
        skip_publish=True,
        skip_translate=False,
        process_callbacks=False,
    )

    # The second slot still ran, and the failure landed in the database.
    assert attempted == [russia.slot_key, energy.slot_key]
    assert db.article_slot_state(russia.slot_key) == ("failed_generation", 1)
    assert db.article_slot_state(energy.slot_key) == (None, 0)
