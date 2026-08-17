import logging

import pytest
import httpx

from n1_project.admin import ARTICLE_ACCEPT_PREFIX, ARTICLE_REJECT_PREFIX, AdminNotifier, repair_mojibake


@pytest.mark.asyncio
async def test_admin_review_dry_run_payload() -> None:
    admin = AdminNotifier("token", "-100admin", dry_run=True)

    result = await admin.send_article_review(
        article_id=42,
        article_text="Заголовок статьи.\n\nТекст статьи.",
        attempt=2,
        slot_key="2026-07-06 18:00",
    )

    assert result.ok is True
    assert result.payload
    assert result.payload["chat_id"] == "-100admin"
    assert "Черновик Dzen-статьи #42" in result.payload["text"]
    keyboard = result.payload["reply_markup"]["inline_keyboard"]
    assert keyboard[0][0]["callback_data"] == f"{ARTICLE_ACCEPT_PREFIX}42"
    assert keyboard[0][1]["callback_data"] == f"{ARTICLE_REJECT_PREFIX}42"


def test_repair_mojibake() -> None:
    assert repair_mojibake("РџСЂРёРЅСЏС‚Рѕ. РћС‚РїСЂР°РІР»РµРЅРѕ РІ Dzen.") == "Принято. Отправлено в Dzen."
    assert repair_mojibake("Принято. Отправлено в Dzen.") == "Принято. Отправлено в Dzen."

@pytest.mark.asyncio
async def test_get_callback_updates_timeout_returns_empty_list(monkeypatch, caplog) -> None:
    class TimeoutClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectTimeout("connect timed out")

    monkeypatch.setattr(httpx, "AsyncClient", TimeoutClient)
    admin = AdminNotifier("token", "-100admin")
    caplog.set_level(logging.DEBUG)

    updates = await admin.get_callback_updates(offset=123)

    assert updates == []
    assert "admin getUpdates failed" in caplog.text
    # httpx timeouts stringify to nothing, so the type has to carry the meaning.
    assert "ConnectTimeout" in caplog.text
    assert admin.update_backoff_seconds == 2.0


@pytest.mark.asyncio
async def test_get_callback_updates_uses_long_poll_timeout(monkeypatch) -> None:
    calls = {}

    class Response:
        def json(self):
            return {"ok": True, "result": []}

    class CaptureClient:
        def __init__(self, *args, **kwargs):
            calls["client_timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            calls["payload"] = json
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", CaptureClient)
    admin = AdminNotifier("token", "-100admin")

    updates = await admin.get_callback_updates(offset=123, timeout_seconds=25)

    assert updates == []
    assert calls["client_timeout"] == 35.0
    assert calls["payload"]["timeout"] == 25
    assert calls["payload"]["offset"] == 123


class FakeUpdatesClient:
    """Serve queued getUpdates payloads to AdminNotifier."""

    queue: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        payload = FakeUpdatesClient.queue.pop(0)

        class Response:
            def json(self_inner):
                return payload

        return Response()


@pytest.mark.asyncio
async def test_repeated_gateway_errors_back_off_exponentially(monkeypatch) -> None:
    FakeUpdatesClient.queue = [{"ok": False, "error_code": 502, "description": "Bad Gateway"}] * 4
    monkeypatch.setattr(httpx, "AsyncClient", FakeUpdatesClient)
    admin = AdminNotifier("token", "-100admin")

    delays = []
    for _ in range(4):
        assert await admin.get_callback_updates(offset=None) == []
        delays.append(admin.update_backoff_seconds)

    assert delays == [2.0, 4.0, 8.0, 16.0]


@pytest.mark.asyncio
async def test_rate_limit_uses_retry_after_from_telegram(monkeypatch) -> None:
    FakeUpdatesClient.queue = [
        {
            "ok": False,
            "error_code": 429,
            "description": "Too Many Requests: retry after 5",
            "parameters": {"retry_after": 5},
        }
    ]
    monkeypatch.setattr(httpx, "AsyncClient", FakeUpdatesClient)
    admin = AdminNotifier("token", "-100admin")

    await admin.get_callback_updates(offset=None)

    assert admin.update_backoff_seconds == 5.0


@pytest.mark.asyncio
async def test_a_burst_of_gateway_errors_stays_out_of_the_warning_log(monkeypatch, caplog) -> None:
    FakeUpdatesClient.queue = [{"ok": False, "error_code": 502, "description": "Bad Gateway"}] * 3
    monkeypatch.setattr(httpx, "AsyncClient", FakeUpdatesClient)
    admin = AdminNotifier("token", "-100admin", sustained_failure_seconds=300.0)
    caplog.set_level(logging.WARNING)

    for _ in range(3):
        await admin.get_callback_updates(offset=None)

    assert caplog.text == ""


@pytest.mark.asyncio
async def test_a_sustained_outage_is_warned_about(monkeypatch, caplog) -> None:
    FakeUpdatesClient.queue = [{"ok": False, "error_code": 502, "description": "Bad Gateway"}] * 2
    monkeypatch.setattr(httpx, "AsyncClient", FakeUpdatesClient)
    admin = AdminNotifier("token", "-100admin", sustained_failure_seconds=0.0)
    caplog.set_level(logging.WARNING)

    await admin.get_callback_updates(offset=None)

    assert "admin getUpdates failing for" in caplog.text
    assert "error_code=502" in caplog.text


@pytest.mark.asyncio
async def test_a_successful_poll_clears_the_backoff(monkeypatch) -> None:
    FakeUpdatesClient.queue = [
        {"ok": False, "error_code": 502, "description": "Bad Gateway"},
        {"ok": True, "result": [{"update_id": 1}]},
    ]
    monkeypatch.setattr(httpx, "AsyncClient", FakeUpdatesClient)
    admin = AdminNotifier("token", "-100admin")

    await admin.get_callback_updates(offset=None)
    assert admin.update_backoff_seconds == 2.0

    assert await admin.get_callback_updates(offset=None) == [{"update_id": 1}]
    assert admin.update_backoff_seconds == 0.0
