from n1_project.llm import article_user_prompt, translation_user_prompt


def test_translation_prompt_requests_strict_literal_translation() -> None:
    prompt = translation_user_prompt("BTC is up 5% - CryptoQuant")

    assert "Preserve every line break" in prompt
    assert "Do not add or remove hashtags" in prompt
    assert "If the source starts with an emoji or flag" in prompt
    assert "Translate each source line exactly once" in prompt
    assert "Do not add blank lines" in prompt
    assert "Do not invent sources" in prompt
    assert "Return only the translated post text" in prompt


def test_article_prompt_requests_theme_grouping() -> None:
    prompt = article_user_prompt(["BTC is higher", "RGBI is below 112"], 2500, 3900)

    assert "Group related items by theme" in prompt
    assert "markets, macro, companies, crypto" in prompt
    assert "between 2500 and 3900 characters" in prompt
    assert "Dzen generates the card description from early text" in prompt
    assert "Do not give investment advice" in prompt
    assert "Make the title concrete" in prompt
    assert "Make the title worth opening" in prompt
    assert "candidate pool, not as a mandatory checklist" in prompt
    assert "clear semantic cluster" in prompt
    assert "Сводка за день" in prompt
    assert "Standalone date-summary line" in prompt
    assert "Do not merge the title, date summary, and body into one paragraph" in prompt
    assert "body must directly pay off every hook" in prompt
    assert "do not inflate one short signal into a long article" in prompt
    assert "dependency-grammar-friendly sentence structure" in prompt
    assert "Keep the subject, verb, and object close" in prompt
    assert "Final quality gate" in prompt


def test_article_prompt_accepts_review_note() -> None:
    prompt = article_user_prompt(["BTC is higher"], 2500, 3900, review_note="Previous draft was rejected.")

    assert "Editor note for this revision" in prompt
    assert "Previous draft was rejected." in prompt


def test_article_prompt_accepts_article_date() -> None:
    prompt = article_user_prompt(["BTC is higher"], 2500, 3900, article_date_label="6 июля 2026 года")

    assert "Сводка за 6 июля 2026 года" in prompt
    assert "There is one blank line after the title" in prompt
    assert "The date-summary line is standalone" in prompt
