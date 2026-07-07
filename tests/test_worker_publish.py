import pytest

from n1_project.config import Settings
from n1_project.db import QueueDatabase
from n1_project.domain import PublishResult, SourcePost
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


class FakePublisher:
    def __init__(self, platform: str, calls: list[str]):
        self.platform = platform
        self.calls = calls

    async def publish_text(self, text: str) -> PublishResult:
        self.calls.append(self.platform)
        return PublishResult(self.platform, True, destination_id=f"{self.platform}-id")


@pytest.mark.asyncio
async def test_publish_pending_resumes_after_already_published_platform(tmp_path, monkeypatch) -> None:
    settings = Settings.from_mapping({"PUBLISH_ORDER": "vk,max,telegram"}, project_root=tmp_path)
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    row_id, _ = db.upsert_source_post(SourcePost("@num1_ch", "1", "Hello"))
    db.mark_translated(row_id, "hello")
    db.mark_failed(row_id, "failed_retry", "previous MAX error")
    db.record_publish_result(row_id, "vk", "published", destination_id="vk-id")
    calls: list[str] = []

    monkeypatch.setattr(
        "n1_project.worker.build_publishers",
        lambda settings, dry_run=False: {
            "vk": FakePublisher("vk", calls),
            "max": FakePublisher("max", calls),
            "telegram": FakePublisher("telegram", calls),
        },
    )

    await publish_pending(db, settings, dry_run=False, limit=1)

    assert calls == ["max", "telegram"]
    assert db.status_counts() == {"published": 1}
    assert db.publish_status_counts() == {
        "max:published": 1,
        "telegram:published": 1,
        "vk:published": 1,
    }
