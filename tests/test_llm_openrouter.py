import json

import httpx
import pytest

from n1_project.llm import (
    OPENROUTER_CHAT_COMPLETIONS_URL,
    OpenRouterError,
    openrouter_chat_completion,
)

PAYLOAD = {"model": "openai/gpt-5.6-terra", "messages": [{"role": "user", "content": "hi"}]}


def response(status_code: int, *, body: str = "", headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        text=body,
        headers=headers or {},
        request=httpx.Request("POST", OPENROUTER_CHAT_COMPLETIONS_URL),
    )


def ok_response(content: str = "готовый текст") -> httpx.Response:
    payload = {"choices": [{"message": {"content": content}}]}
    return response(200, body=json.dumps(payload, ensure_ascii=False))


def install_fake_transport(monkeypatch, outcomes: list) -> dict:
    """Serve queued responses/exceptions and record calls and sleeps."""
    state: dict = {"calls": 0, "sleeps": []}
    queue = list(outcomes)

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info) -> bool:
            return False

        async def post(self, url, json=None, headers=None):
            state["calls"] += 1
            outcome = queue.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr("n1_project.llm.httpx.AsyncClient", FakeAsyncClient)

    async def fake_sleep(delay: float) -> None:
        state["sleeps"].append(delay)

    state["sleep"] = fake_sleep
    return state


async def test_rate_limit_is_retried_and_retry_after_is_honoured(monkeypatch) -> None:
    state = install_fake_transport(
        monkeypatch,
        [response(429, body="rate limited", headers={"Retry-After": "5"}), ok_response()],
    )

    result = await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert result == "готовый текст"
    assert state["calls"] == 2
    assert state["sleeps"] == [5.0]


async def test_server_errors_back_off_exponentially(monkeypatch) -> None:
    state = install_fake_transport(
        monkeypatch,
        [response(500, body="boom"), response(502, body="bad gateway"), ok_response()],
    )

    result = await openrouter_chat_completion(PAYLOAD, "key", retry_base_seconds=2.0, sleep=state["sleep"])

    assert result == "готовый текст"
    assert state["sleeps"] == [2.0, 4.0]


async def test_transport_errors_are_retried(monkeypatch) -> None:
    state = install_fake_transport(
        monkeypatch,
        [httpx.ConnectError("connection refused"), ok_response()],
    )

    assert await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"]) == "готовый текст"
    assert state["calls"] == 2


async def test_missing_model_fails_immediately_with_a_readable_reason(monkeypatch) -> None:
    body = '{"error":{"message":"No endpoints found for openai/gpt-5.3-chat","code":404}}'
    state = install_fake_transport(monkeypatch, [response(404, body=body)])

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert excinfo.value.status_code == 404
    assert "модель не найдена в каталоге OpenRouter" in str(excinfo.value)
    # The response body is what actually explains the failure, so it must survive.
    assert "No endpoints found for openai/gpt-5.3-chat" in str(excinfo.value)
    assert state["calls"] == 1
    assert state["sleeps"] == []


async def test_payment_required_fails_immediately(monkeypatch) -> None:
    state = install_fake_transport(monkeypatch, [response(402, body='{"error":"insufficient credits"}')])

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert "нет оплаты на счете OpenRouter" in str(excinfo.value)
    assert state["calls"] == 1


async def test_invalid_key_fails_immediately(monkeypatch) -> None:
    state = install_fake_transport(monkeypatch, [response(401, body="unauthorized")])

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert "неверный OPENROUTER_API_KEY" in str(excinfo.value)
    assert state["calls"] == 1


async def test_retries_are_bounded_by_max_attempts(monkeypatch) -> None:
    state = install_fake_transport(monkeypatch, [response(503, body="unavailable")] * 3)

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", max_attempts=3, sleep=state["sleep"])

    assert excinfo.value.status_code == 503
    assert state["calls"] == 3
    assert len(state["sleeps"]) == 2


async def test_error_payload_returned_with_status_200_is_not_silently_accepted(monkeypatch) -> None:
    body = json.dumps({"error": {"message": "model is overloaded"}}, ensure_ascii=False)
    state = install_fake_transport(monkeypatch, [response(200, body=body)])

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert "model is overloaded" in str(excinfo.value)


async def test_long_response_bodies_are_truncated(monkeypatch) -> None:
    state = install_fake_transport(monkeypatch, [response(400, body="x" * 5000)])

    with pytest.raises(OpenRouterError) as excinfo:
        await openrouter_chat_completion(PAYLOAD, "key", sleep=state["sleep"])

    assert len(excinfo.value.body or "") <= 503
