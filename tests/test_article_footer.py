from pathlib import Path

from n1_project.article_footer import (
    append_dzen_article_footer,
    dzen_article_footer_text,
    footer_applies,
)
from n1_project.config import Settings


def footer_settings(tmp_path: Path) -> Settings:
    return Settings.from_mapping(
        {
            "DZEN_ARTICLE_FOOTER_ENABLED": "true",
            "DZEN_ARTICLE_FOOTER_POLICY": "evening",
            "DZEN_ARTICLE_FOOTER_ROTATE": "true",
            "DZEN_ARTICLE_FOOTER_TELEGRAM_URL": "https://t.me/bazar",
            "DZEN_ARTICLE_FOOTER_VK_URL": "https://vk.com/bazar",
            "DZEN_ARTICLE_FOOTER_MAX_URL": "https://max.ru/bazar",
        },
        project_root=tmp_path,
    )


def test_footer_applies_only_to_evening_slots(tmp_path: Path) -> None:
    settings = footer_settings(tmp_path)

    assert footer_applies(settings, "2026-07-10 tech:evening") is True
    assert footer_applies(settings, "2026-07-10 tech:morning") is False
    assert footer_applies(settings, None) is False


def test_footer_text_contains_links_and_allowed_html(tmp_path: Path) -> None:
    settings = footer_settings(tmp_path)

    footer = dzen_article_footer_text(settings, "2026-07-10 energy:evening")

    assert "<b>" in footer
    assert "https://t.me/bazar" in footer
    assert "https://vk.com/bazar" in footer
    assert "https://max.ru/bazar" in footer


def test_footer_is_not_added_when_links_are_missing(tmp_path: Path) -> None:
    settings = Settings.from_mapping(
        {"DZEN_ARTICLE_FOOTER_ENABLED": "true", "DZEN_ARTICLE_FOOTER_POLICY": "evening"},
        project_root=tmp_path,
    )

    assert dzen_article_footer_text(settings, "2026-07-10 energy:evening") == ""


def test_append_footer_keeps_article_when_not_due(tmp_path: Path) -> None:
    settings = footer_settings(tmp_path)
    article = "Заголовок.\n\nТекст статьи."

    assert append_dzen_article_footer(article, settings, "2026-07-10 energy:morning") == article
    assert "https://t.me/bazar" in append_dzen_article_footer(article, settings, "2026-07-10 energy:evening")
