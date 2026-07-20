import ssl
from pathlib import Path

import pytest

from n1_project.publishers.max import MaxPublisher
from n1_project.publishers.telegram import DzenBridgePublisher, TelegramPublisher
from n1_project.publishers.vk import VkPublisher


@pytest.mark.asyncio
async def test_telegram_dry_run_payload() -> None:
    publisher = TelegramPublisher("token", "-100", 4096, dry_run=True)

    result = await publisher.publish_text("Привет")

    assert result.ok is True
    assert result.destination_id == "dry-run"
    assert result.payload == {"chat_id": "-100", "text": "Привет", "disable_web_page_preview": False}


@pytest.mark.asyncio
async def test_dzen_dry_run_payload_can_use_html_parse_mode() -> None:
    publisher = DzenBridgePublisher("token", "-100", 4096, dry_run=True, parse_mode="HTML")

    result = await publisher.publish_text("Title.\n\n<b>Key point</b>\n\nBody")

    assert result.ok is True
    assert result.payload == {
        "chat_id": "-100",
        "text": "Title.\n\n<b>Key point</b>\n\nBody",
        "disable_web_page_preview": False,
        "parse_mode": "HTML",
    }


@pytest.mark.asyncio
async def test_dzen_photo_dry_run_payload_uses_caption_limit_and_html() -> None:
    publisher = DzenBridgePublisher("token", "-100", 4096, dry_run=True, parse_mode="HTML", caption_max_chars=1024)

    result = await publisher.publish_photo("https://images.pexels.com/photo.jpg", "Title.\n\n<b>Что случилось</b>")

    assert result.ok is True
    assert result.payload == {
        "chat_id": "-100",
        "photo": "https://images.pexels.com/photo.jpg",
        "caption": "Title.\n\n<b>Что случилось</b>",
        "parse_mode": "HTML",
    }


@pytest.mark.asyncio
async def test_vk_dry_run_converts_owner_id() -> None:
    publisher = VkPublisher("token", "123", 16350, dry_run=True)

    result = await publisher.publish_text("Привет")

    assert result.ok is True
    assert result.payload
    assert result.payload["owner_id"] == "-123"
    assert "access_token" not in result.payload


@pytest.mark.asyncio
async def test_max_dry_run_payload() -> None:
    publisher = MaxPublisher("token", "123", "https://platform-api2.max.ru", 4000, ca_bundle="/tmp/ca.pem", dry_run=True)

    result = await publisher.publish_text("hello")

    assert result.ok is True
    assert result.destination_id == "dry-run"
    assert result.payload == {"text": "hello"}


def test_bundled_max_ca_bundle_loads() -> None:
    bundle = Path(__file__).resolve().parents[1] / "certs" / "russian_trusted_ca_bundle.pem"

    assert bundle.exists()
    ssl.create_default_context(cafile=str(bundle))
