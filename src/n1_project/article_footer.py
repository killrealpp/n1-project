from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from n1_project.validators import sanitize_article_html

if TYPE_CHECKING:
    from n1_project.config import Settings


FOOTER_VARIANTS = (
    {
        "title": "Где ещё следить",
        "telegram": "Оперативные новости и короткие разборы — в Telegram:",
        "vk": "Дополнительные публикации и обсуждения — во ВКонтакте:",
        "max": "Главная сводка дня — в MAX:",
    },
    {
        "title": "Больше материалов",
        "telegram": "Самые быстрые обновления выходят в Telegram:",
        "vk": "Для обсуждений и дополнительных заметок есть ВКонтакте:",
        "max": "Короткую сводку дня можно читать в MAX:",
    },
    {
        "title": "Куда перейти дальше",
        "telegram": "Telegram — для быстрых рыночных сигналов:",
        "vk": "ВКонтакте — для обсуждений и дополнительных материалов:",
        "max": "MAX — для главных новостей дня коротко:",
    },
)


def footer_links(settings: Settings) -> dict[str, str]:
    links = {
        "telegram": settings.dzen_article_footer_telegram_url,
        "vk": settings.dzen_article_footer_vk_url,
        "max": settings.dzen_article_footer_max_url,
    }
    return {key: value for key, value in links.items() if value}


def footer_applies(settings: Settings, slot_key: str | None) -> bool:
    if not settings.dzen_article_footer_enabled:
        return False
    if not footer_links(settings):
        return False
    policy = settings.dzen_article_footer_policy
    if policy in {"none", "off", "never", "false"}:
        return False
    if policy in {"all", "always", "every"}:
        return True
    if policy in {"evening", "once_per_day", "once-per-day"}:
        return bool(slot_key and ":evening" in slot_key)
    return False


def footer_variant_index(settings: Settings, slot_key: str | None) -> int:
    if not settings.dzen_article_footer_rotate:
        return 0
    seed = (slot_key or "manual").encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    return int.from_bytes(digest[:4], "big") % len(FOOTER_VARIANTS)


def dzen_article_footer_text(settings: Settings, slot_key: str | None) -> str:
    if not footer_applies(settings, slot_key):
        return ""
    links = footer_links(settings)
    variant = FOOTER_VARIANTS[footer_variant_index(settings, slot_key)]
    blocks = [f"<b>{variant['title']}</b>"]
    for key in ("telegram", "vk", "max"):
        url = links.get(key)
        if not url:
            continue
        blocks.append(f"{variant[key]}\n{url}")
    return sanitize_article_html("\n\n".join(blocks))


def dzen_article_footer_reserve_chars(settings: Settings, slot_key: str | None) -> int:
    footer = dzen_article_footer_text(settings, slot_key)
    return len(footer) + 2 if footer else 0


def append_dzen_article_footer(article: str, settings: Settings, slot_key: str | None) -> str:
    footer = dzen_article_footer_text(settings, slot_key)
    if not footer:
        return article
    return article.rstrip() + "\n\n" + footer
