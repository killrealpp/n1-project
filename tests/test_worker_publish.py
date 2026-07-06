import pytest

from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import SourcePost
from n1_project.worker import publish_pending


@pytest.mark.asyncio
async def test_publish_pending_reports_unpublishable_row(tmp_path, capsys) -> None:
    settings = Settings.from_mapping({"PUBLISH_ORDER": "telegram"}, project_root=tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Hello"))

    await publish_pending(db, settings, dry_run=True, limit=1, message_id=row_id)

    output = capsys.readouterr().out
    assert '"ok": false' in output
    assert "row is not publishable" in output
