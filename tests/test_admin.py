import pytest

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
