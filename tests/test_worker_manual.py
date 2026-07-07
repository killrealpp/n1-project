from pathlib import Path

import pytest

from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import SourcePost
from n1_project.llm import TextModel
from n1_project.worker import exception_report, set_translation_from_cli, translate_one_row


class FakeTextModel(TextModel):
    async def translate_post(self, source_text: str) -> str:
        return (
            "\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
            "\u0412\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
            "\u0422\u0440\u0435\u0442\u044c\u044f \u0441\u0442\u0440\u043e\u043a\u0430"
        )

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        raise NotImplementedError


def test_exception_report_includes_traceback_details() -> None:
    def raise_error() -> None:
        raise RuntimeError("boom")

    try:
        raise_error()
    except RuntimeError as exc:
        report = exception_report(exc)

    assert "type=RuntimeError" in report
    assert "error=boom" in report
    assert "raise_error" in report


def test_set_translation_from_cli_preserves_lines(tmp_path: Path, capsys) -> None:
    settings = Settings.from_mapping(
        {
            "SOCIAL_POST_MAX_LINES": "2",
            "SOCIAL_POST_TARGET_MAX_CHARS": "700",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Hello\nWorld\nAgain"))

    set_translation_from_cli(
        db,
        settings,
        row_id,
        "\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0412\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0422\u0440\u0435\u0442\u044c\u044f \u0441\u0442\u0440\u043e\u043a\u0430",
    )

    message = db.message_by_id(row_id)
    assert message is not None
    assert message.status == "translated"
    assert message.translated_text == (
        "\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0412\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0422\u0440\u0435\u0442\u044c\u044f \u0441\u0442\u0440\u043e\u043a\u0430"
    )
    assert '"status": "translated"' in capsys.readouterr().out


def test_set_translation_from_cli_rejects_invalid_manual_text(tmp_path: Path, capsys) -> None:
    settings = Settings.from_mapping(project_root=tmp_path, env={})
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "\U0001f1f7\U0001f1fa Hello"))

    set_translation_from_cli(db, settings, row_id, "\u041f\u0440\u0438\u0432\u0435\u0442 #tag")

    output = capsys.readouterr().out
    assert '"ok": false' in output
    assert "leading emoji sequence changed" in output
    assert db.message_by_id(row_id).status == "received"


@pytest.mark.asyncio
async def test_translate_one_row_saves_model_output_without_compacting(tmp_path: Path, capsys) -> None:
    settings = Settings.from_mapping(
        {
            "SOCIAL_POST_MAX_LINES": "2",
            "SOCIAL_POST_TARGET_MAX_CHARS": "700",
        },
        project_root=tmp_path,
    )
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Hello\nWorld\nAgain"))

    await translate_one_row(db, settings, FakeTextModel(), row_id, dry_run=False)

    message = db.message_by_id(row_id)
    assert message is not None
    assert message.status == "translated"
    assert (
        message.translated_text
        == "\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0412\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0422\u0440\u0435\u0442\u044c\u044f \u0441\u0442\u0440\u043e\u043a\u0430"
    )
    output = capsys.readouterr().out
    assert '"ok": true' in output
    assert '"saved": true' in output


@pytest.mark.asyncio
async def test_translate_one_row_requires_force_for_existing_translation(tmp_path: Path, capsys) -> None:
    settings = Settings.from_mapping(project_root=tmp_path, env={})
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Hello\nWorld\nAgain"))
    db.mark_translated(row_id, "\u0421\u0442\u0430\u0440\u044b\u0439 \u043f\u0435\u0440\u0435\u0432\u043e\u0434")

    await translate_one_row(db, settings, FakeTextModel(), row_id, dry_run=False)

    assert "row is not translatable" in capsys.readouterr().out
    assert db.message_by_id(row_id).translated_text == "\u0421\u0442\u0430\u0440\u044b\u0439 \u043f\u0435\u0440\u0435\u0432\u043e\u0434"

    await translate_one_row(db, settings, FakeTextModel(), row_id, dry_run=False, force=True)

    assert db.message_by_id(row_id).translated_text == (
        "\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0412\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430\n"
        "\u0422\u0440\u0435\u0442\u044c\u044f \u0441\u0442\u0440\u043e\u043a\u0430"
    )
