from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus

import httpx


@dataclass(frozen=True)
class ArticleImage:
    url: str
    query: str
    source_url: str | None = None
    photographer: str | None = None
    photographer_url: str | None = None

    @property
    def credit(self) -> str | None:
        if self.photographer:
            return f"Фото: {self.photographer} / Pexels"
        return "Фото: Pexels"


TOPIC_QUERIES = {
    "russia": "stock market trading board",
    "energy": "oil refinery energy market",
    "tech": "semiconductor chip technology",
    "markets": "financial market chart",
}

KEYWORD_QUERIES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        (
            "brent",
            "wti",
            "opec",
            "oil",
            "lng",
            "gas",
            "нефт",
            "опек",
            "газ",
            "спг",
            "топлив",
            "бензин",
            "танкер",
        ),
        "oil refinery energy market",
    ),
    (
        (
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "stablecoin",
            "битко",
            "эфир",
            "крипт",
            "стейбл",
        ),
        "cryptocurrency bitcoin market",
    ),
    (
        (
            "nvidia",
            "nvda",
            "apple",
            "meta",
            "openai",
            "ai",
            "chip",
            "semiconductor",
            "ии",
            "чип",
            "полупровод",
            "нейросет",
            "технолог",
        ),
        "semiconductor chip technology",
    ),
    (
        (
            "moex",
            "imoex",
            "ruble",
            "cbr",
            "дивиден",
            "облигац",
            "мосбирж",
            "рубл",
            "цб",
            "ставк",
            "банк",
            "акци",
        ),
        "stock market trading board",
    ),
)


def build_pexels_photo_query(texts: Iterable[str], topic: str | None = None) -> str:
    normalized = "\n".join(texts).lower()
    for tokens, query in KEYWORD_QUERIES:
        if any(token in normalized for token in tokens):
            return query
    if topic:
        return TOPIC_QUERIES.get(topic, TOPIC_QUERIES["markets"])
    return TOPIC_QUERIES["markets"]


class PexelsImageProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.pexels.com",
        orientation: str = "landscape",
        size: str = "large",
        per_page: int = 12,
        timeout: float = 20.0,
        dry_run: bool = False,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.orientation = orientation
        self.size = size
        self.per_page = max(1, min(per_page, 80))
        self.timeout = timeout
        self.dry_run = dry_run

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self.dry_run)

    async def search_photo(self, query: str) -> ArticleImage | None:
        if not self.configured:
            return None
        if self.dry_run:
            slug = quote_plus(query)
            return ArticleImage(
                url=f"https://images.pexels.com/photos/dry-run/{slug}.jpg",
                query=query,
                source_url=f"https://www.pexels.com/search/{slug}/",
            )

        params: dict[str, object] = {
            "query": query,
            "orientation": self.orientation,
            "size": self.size,
            "per_page": self.per_page,
        }
        headers = {"Authorization": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/search", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        for photo in data.get("photos") or []:
            src = photo.get("src") if isinstance(photo, dict) else None
            if not isinstance(src, dict):
                continue
            url = str(src.get("large") or src.get("original") or src.get("medium") or "").strip()
            if not url:
                continue
            return ArticleImage(
                url=url,
                query=query,
                source_url=str(photo.get("url") or "") or None,
                photographer=str(photo.get("photographer") or "") or None,
                photographer_url=str(photo.get("photographer_url") or "") or None,
            )
        return None
