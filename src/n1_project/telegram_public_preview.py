from __future__ import annotations

import html
import re

import httpx

from n1_project.domain import SourcePost


MESSAGE_RE = re.compile(
    r'<div class="tgme_widget_message[^"]*"[^>]*data-post="(?P<post>[^"]+)"[\s\S]*?'
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(?P<text>[\s\S]*?)</div>',
    re.IGNORECASE,
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t]+")


def clean_telegram_html_text(raw_html: str) -> str:
    text = BR_RE.sub("\n", raw_html)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    lines = [SPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def parse_public_preview_posts(channel_name: str, page_html: str) -> list[SourcePost]:
    posts: list[SourcePost] = []
    for match in MESSAGE_RE.finditer(page_html):
        post_ref = html.unescape(match.group("post"))
        if "/" not in post_ref:
            continue
        post_channel, post_id = post_ref.rsplit("/", 1)
        text = clean_telegram_html_text(match.group("text"))
        if not text:
            continue
        posts.append(
            SourcePost(
                source_channel_id=f"@{post_channel or channel_name}",
                source_message_id=post_id,
                text=text,
            )
        )
    return posts


async def fetch_public_preview_posts(channel_name: str, limit: int = 20) -> list[SourcePost]:
    normalized = channel_name.strip().lstrip("@")
    if not normalized:
        raise ValueError("Telegram public channel name is empty")
    url = f"https://t.me/s/{normalized}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    posts = parse_public_preview_posts(normalized, response.text)
    return posts[-limit:]
