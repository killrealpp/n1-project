from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from n1_project.article_channels import configured_article_channels
from n1_project.config import Settings
from n1_project.worker import dzen_publisher_for_channel


TEST_ARTICLES = {
    "energy": """Тестовый формат BAZAR ENERGY: нефть, газ и сырье без большого шума.

Это тестовая статья для оценки стиля. Она не описывает реальные новости дня и не является инвестиционной рекомендацией.

<b>Зачем нужен этот канал</b>

У энергетических новостей есть одна проблема: они быстро превращаются в набор громких слов. Нефть, газ, танкеры, санкции, запасы, OPEC, металл. Все звучит важно, но читатель ждет не шума, а простой связи: что изменилось и как это может повлиять на цены.

BAZAR ENERGY должен работать как спокойный фильтр. Если в ленте появляется сигнал по нефти, важно отделить движение цены от причины. Спрос, предложение, логистика, запасы и политика дают совсем разные выводы.

<b>Как это может звучать</b>

Нефть растет не просто потому, что рынок нервничает. Чаще всего за движением стоит конкретное ожидание: поставки могут стать дороже, запасы могут снизиться, а маршруты танкеров могут стать рискованнее. Такую связь нужно объяснять коротко и без больших слов.

Газ и LNG лучше подавать через вопрос доступности. Если топливо идет другим маршрутом или становится дороже, это влияет не только на компанию, но и на инфляцию, бюджеты и промышленность.

<b>Тон</b>

Хороший текст не должен пугать читателя. Он может быть живым, но должен оставаться трезвым. Не нужно писать, что рынок обязательно взорвется или развернется. Лучше сказать: сейчас важно смотреть, подтвердятся ли риски поставок и спроса.

Так канал будет полезным: он не просто повторяет новости, а помогает понять, где реальный фактор цены, а где только фон.""",
    "tech": """Тестовый формат BAZAR TECH: крипта, AI и чипы без хайпа.

Это тестовая статья для оценки стиля. Она не описывает реальные новости дня и не является инвестиционной рекомендацией.

<b>Что должен делать tech-канал</b>

Технологические новости легко превращаются в поток громких заголовков. BTC вырос, ETF получил приток, новая модель AI вышла, чипы снова в дефиците, компания дала сильный прогноз. Каждая новость может казаться отдельной, но читателю нужно понять, какая из них меняет ожидания.

BAZAR TECH должен писать живо, но без продажи хайпа. Особенно в крипте и искусственном интеллекте, где один яркий заголовок быстро начинает звучать как обещание прибыли.

<b>Как говорить про крипту</b>

Если в источниках есть данные по BTC, ETH, стейблкоинам или DeFi, статья не должна смотреть только на цену. Важные вопросы другие: откуда идет ликвидность, что делают крупные игроки, есть ли притоки в продукты и как меняется регулирование.

Рост интереса к активу еще не означает устойчивый тренд. Но он показывает, где сейчас собираются деньги и внимание. Это проще и честнее, чем делать прогноз из одного движения.

<b>Как говорить про AI и чипы</b>

В сюжетах про AI важно разделять продуктовый шум и инфраструктуру. Модели, дата-центры, чипы, память и энергия связаны между собой. Если одна часть цепочки становится дороже или дефицитнее, это влияет на весь сектор.

Текст не должен доказывать, что будущее уже наступило. Лучше показать спокойную картину: технологии растут, но рынок смотрит на деньги, вычислительные мощности и ограничения.

Сильный финал для BAZAR TECH не обещает чуда. Он говорит, куда идут капитал, вычисления и пользовательское внимание. Именно там чаще всего начинается следующий большой рыночный сюжет.""",
}


def assert_text_is_not_corrupted(text: str) -> None:
    cyrillic_count = sum(1 for char in text if "\u0400" <= char <= "\u04ff")
    if cyrillic_count < 100:
        raise ValueError("test article text does not contain enough Cyrillic characters")
    if "????" in text:
        raise ValueError("test article text already contains replacement question marks")


async def send_test_articles(channels: list[str], dry_run: bool) -> list[dict[str, object]]:
    settings = Settings.load(Path(".env"))
    configured = {channel.key: channel for channel in configured_article_channels(settings)}
    results: list[dict[str, object]] = []
    for key in channels:
        if key not in TEST_ARTICLES:
            raise ValueError(f"no test article for channel: {key}")
        channel = configured.get(key)
        if channel is None:
            raise ValueError(f"channel is not configured: {key}")
        text = TEST_ARTICLES[key]
        assert_text_is_not_corrupted(text)
        publisher = dzen_publisher_for_channel(settings, channel, dry_run=dry_run)
        if publisher is None:
            raise ValueError(f"publisher is not configured for channel: {key}")
        result = await publisher.publish_text(text)
        results.append(
            {
                "channel": key,
                "bot_source": "channel" if key in settings.dzen_article_bot_tokens else "default",
                "ok": result.ok,
                "destination_id": result.destination_id,
                "error": result.error[:300] if result.error else None,
                "chars": len(text),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels", nargs="+", default=["energy", "tech"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    results = asyncio.run(send_test_articles(args.channels, dry_run=args.dry_run))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not all(item["ok"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
