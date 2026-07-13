from n1_project.llm import article_user_prompt, translation_user_prompt


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


def test_article_prompt_requests_theme_grouping() -> None:
    prompt = article_user_prompt(["BTC is higher", "RGBI is below 112"], 1600, 2800)

    assert "от 1600 до 2800 символов" in prompt
    assert "Пиши на русском языке" in prompt
    assert "не обязательным чек-листом" in prompt
    assert "складываются в понятную тему" in prompt
    assert "4-8 связанных постов" in prompt
    assert "Не давай инвестиционных советов" in prompt
    assert "Dzen" in prompt or "Дзена" in prompt
    assert "Первый абзац должен работать как описание карточки Дзена" in prompt
    assert "Тело статьи обязано прямо ответить" in prompt
    assert "Не превращай статью в список новостей" in prompt
    assert "Не раздувай один короткий сигнал" in prompt
    assert "Держи подлежащее, сказуемое и дополнение рядом" in prompt
    assert "Проверка перед выдачей" in prompt


def test_article_prompt_requests_human_dzen_style() -> None:
    prompt = article_user_prompt(["Brent is above $80 - EIA"], 2500, 3900)

    assert "опытный финансовый журналист" in prompt
    assert "как Bloomberg, Reuters, РБК" in prompt
    assert "формируется противоречивая картина" in prompt
    assert "Не начинай заголовок" in prompt
    assert "Что произошло..." not in prompt
    assert "Почему это важно..." not in prompt
    assert "По данным" in prompt
    assert "Средняя длина - 10-18 слов" in prompt
    assert "рынок остается чувствительным" in prompt


def test_article_prompt_accepts_review_note() -> None:
    prompt = article_user_prompt(["BTC is higher"], 2500, 3900, review_note="Предыдущий черновик отклонен.")

    assert "Заметка редактора для этой правки" in prompt
    assert "Предыдущий черновик отклонен." in prompt


def test_article_prompt_accepts_article_date() -> None:
    prompt = article_user_prompt(["BTC is higher"], 2500, 3900, article_date_label="6 июля 2026 года")

    assert "Контекст даты статьи: 6 июля 2026 года" in prompt
    assert "Первая строка - заголовок Дзена" in prompt
    assert "не делай сухую отдельную строку `Сводка за ...`" in prompt
