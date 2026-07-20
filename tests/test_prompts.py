from n1_project.llm import article_user_prompt, translation_user_prompt
from n1_project.story_plan import StoryPlan


def test_translation_prompt_requests_strict_literal_translation() -> None:
    prompt = translation_user_prompt("BTC is up 5% - CryptoQuant")

    assert "Preserve every line break" in prompt
    assert "Do not add or remove hashtags" in prompt
    assert "If the source starts with an emoji or flag" in prompt
    assert "Translate each source line exactly once" in prompt
    assert "Do not add blank lines" in prompt
    assert "return the source text unchanged" in prompt
    assert "Never return `None`" in prompt
    assert "Do not invent sources" in prompt
    assert "Return only the translated post text" in prompt
    assert "limit up" in prompt
    assert "верхняя планка" in prompt
    assert "шортовые позиции" in prompt
    assert "лонговые позиции" in prompt


def test_article_prompt_requests_theme_grouping() -> None:
    prompt = article_user_prompt(["BTC is higher", "RGBI is below 112"], 650, 950)

    assert "от 650 до 950 символов" in prompt
    assert "Пиши на русском языке" in prompt
    assert "не обязательным чек-листом" in prompt
    assert "Выбери один доказуемый сюжет" in prompt
    assert "Один пост = одна доказуемая мысль" in prompt
    assert "Не давай инвестиционных советов" in prompt
    assert "Telegram/Dzen" in prompt
    assert "подпись к посту с картинкой" in prompt
    assert "Не используй одинаковые видимые метки" in prompt
    assert "Желательная структура" not in prompt
    assert "доказательство через causal_chain" in prompt
    assert "теряют монетизацию" in prompt
    assert "Проверка перед выдачей" in prompt


def test_article_prompt_requests_human_dzen_style() -> None:
    prompt = article_user_prompt(["Brent is above $80 - EIA"], 650, 950)

    assert "редактор рыночного Telegram-канала" in prompt
    assert "как Bloomberg, Reuters, РБК" in prompt
    assert "формируется противоречивая картина" in prompt
    assert "Не начинай заголовок" in prompt
    assert "Что произошло..." not in prompt
    assert "Почему это важно..." not in prompt
    assert "на фоне неопределенности" in prompt
    assert "Средняя длина - 10-18 слов" in prompt
    assert "быстрый понятный пост" in prompt


def test_article_prompt_accepts_review_note() -> None:
    prompt = article_user_prompt(["BTC is higher"], 2500, 3900, review_note="Предыдущий черновик отклонен.")

    assert "Заметка редактора для этой правки" in prompt
    assert "Предыдущий черновик отклонен." in prompt


def test_article_prompt_accepts_article_date() -> None:
    prompt = article_user_prompt(["BTC is higher"], 650, 950, article_date_label="6 июля 2026 года")

    assert "Контекст даты публикации: 6 июля 2026 года" in prompt
    assert "Первая строка - заголовок" in prompt
    assert "Упоминай дату только если это помогает тексту" in prompt


def test_article_prompt_includes_story_plan_contract() -> None:
    plan = StoryPlan(
        thesis="На российском рынке капитала появляется больше поводов для оживления.",
        selected_message_ids=(3, 4, 5),
        mode="cluster",
        connection="Ставка, IPO и приватизация НСПК связаны через рынок капитала.",
        causal_chain=(
            "Более низкая ставка удешевляет деньги.",
            "На этом фоне компании получают больше пространства для размещений и сделок.",
        ),
        why_it_matters="Инвестор смотрит не только на ставку, но и на новые сделки.",
        what_changes_view="Картину изменят решение ЦБ и спрос на IPO.",
        image_query="russian stock exchange investors",
        confidence=0.86,
    )

    prompt = article_user_prompt(
        ["ЦБ может снизить ставку", "Банк России видит интерес к IPO", "Совкомбанк готов к НСПК"],
        650,
        950,
        story_plan=plan,
    )

    assert "Редакторский план, которому нужно следовать" in prompt
    assert "selected_message_ids: 3, 4, 5" in prompt
    assert "На российском рынке капитала" in prompt
    assert "Используй только источники, выбранные в редакторском плане" in prompt
    assert "russian stock exchange investors" in prompt
