import ssl
from pathlib import Path

import pytest

from n1_project.publishers.max import MaxPublisher
from n1_project.publishers.telegram import TelegramPublisher
from n1_project.publishers.vk import VkPublisher


@pytest.mark.asyncio
async def test_telegram_dry_run_payload() -> None:
    publisher = TelegramPublisher("token", "-100", 4096, dry_run=True)

    result = await publisher.publish_text("Привет")

    assert result.ok is True
    assert result.destination_id == "dry-run"
    assert result.payload == {"chat_id": "-100", "text": "Привет", "disable_web_page_preview": False}


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
