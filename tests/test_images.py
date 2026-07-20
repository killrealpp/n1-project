import pytest

from n1_project.images import PexelsImageProvider, build_pexels_photo_query


def test_build_pexels_photo_query_picks_market_theme() -> None:
    assert build_pexels_photo_query(["Brent oil rises as OPEC meets"], topic="markets") == "oil refinery energy market"
    assert build_pexels_photo_query(["BTC ETF inflows rise"], topic="markets") == "cryptocurrency bitcoin market"
    assert build_pexels_photo_query(["Nvidia and AI chip demand grows"], topic="markets") == "semiconductor chip technology"
    assert build_pexels_photo_query(["MOEX and ruble are under pressure"], topic="markets") == "stock market trading board"


@pytest.mark.asyncio
async def test_pexels_provider_dry_run_returns_deterministic_photo() -> None:
    provider = PexelsImageProvider(api_key="", dry_run=True)

    image = await provider.search_photo("financial market chart")

    assert image is not None
    assert image.query == "financial market chart"
    assert image.url.startswith("https://images.pexels.com/photos/dry-run/")
    assert image.credit == "Фото: Pexels"
