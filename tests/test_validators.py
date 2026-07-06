from n1_project.validators import (
    ensure_title_is_sentence,
    leftover_english_issue,
    normalize_vk_owner_id,
    preservation_issues,
    structure_issues,
    translation_issues,
    unexpected_addition_issues,
    validate_dzen_bridge_article,
)


def test_normalize_vk_owner_id() -> None:
    assert normalize_vk_owner_id("240021174") == "-240021174"
    assert normalize_vk_owner_id("-240021174") == "-240021174"
    assert normalize_vk_owner_id("@name") == "@name"


def test_preservation_issues_detects_missing_url_number_and_hashtag() -> None:
    source = "BTC is up 12% today: https://example.com #BTC"
    output = "BTC grew today."

    issues = preservation_issues(source, output)

    assert any("missing urls" in issue for issue in issues)
    assert any("missing numbers" in issue for issue in issues)
    assert any("missing hashtags" in issue for issue in issues)


def test_unexpected_addition_issues_detects_hallucinated_details() -> None:
    source = "\U0001f1f7\U0001f1fa Sovcombank has announced its readiness to participate in the privatization of NSPK"
    output = (
        "\U0001f6a8 \u0421\u043e\u0432\u043a\u043e\u043c\u0431\u0430\u043d\u043a "
        "\u0433\u043e\u0442\u043e\u0432 \u043a\u0443\u043f\u0438\u0442\u044c 50%+1 "
        "\u0430\u043a\u0446\u0438\u044e \u041d\u0421\u041f\u041a. "
        "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: LSEG #\u041d\u0421\u041f\u041a"
    )

    issues = unexpected_addition_issues(source, output)

    assert any("added numbers" in issue for issue in issues)
    assert any("added hashtags" in issue for issue in issues)
    assert any("added emojis" in issue for issue in issues)
    assert any("added source attributions" in issue for issue in issues)


def test_translation_issues_include_unexpected_additions() -> None:
    source = "Qatar is increasing LNG shipments through the Strait of Hormuz - BBG"
    output = "\u041a\u0430\u0442\u0430\u0440 \u043d\u0430\u0440\u0430\u0449\u0438\u0432\u0430\u0435\u0442 LNG \u043d\u0430 25% - BBG #LNG"

    issues = translation_issues(source, output)

    assert any("added numbers" in issue for issue in issues)
    assert any("added hashtags" in issue for issue in issues)


def test_translation_issues_allow_number_before_terminal_period() -> None:
    source = "June 2026 was the weakest month for aluminum since 2008."
    output = "\u0418\u044e\u043d\u044c 2026 \u0433\u043e\u0434\u0430 \u0441\u0442\u0430\u043b \u0441\u0430\u043c\u044b\u043c \u0441\u043b\u0430\u0431\u044b\u043c \u043c\u0435\u0441\u044f\u0446\u0435\u043c \u0434\u043b\u044f \u0430\u043b\u044e\u043c\u0438\u043d\u0438\u044f \u0441 2008 \u0433\u043e\u0434\u0430."

    assert translation_issues(source, output) == []


def test_translation_issues_allow_removed_thousands_separator() -> None:
    source = "Net income rose to 6,400 million rubles - IF"
    output = "\u0427\u0438\u0441\u0442\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c \u0432\u044b\u0440\u043e\u0441\u043b\u0430 \u0434\u043e 6400 \u043c\u043b\u043d \u0440\u0443\u0431\u043b\u0435\u0439 - IF"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_space_thousands_separator() -> None:
    source = "Revenue reached 8,000 million rubles - IF"
    output = "\u0412\u044b\u0440\u0443\u0447\u043a\u0430 \u0434\u043e\u0441\u0442\u0438\u0433\u043b\u0430 8 000 \u043c\u043b\u043d \u0440\u0443\u0431\u043b\u0435\u0439 - IF"

    assert translation_issues(source, output) == []


def test_structure_issues_detect_line_count_and_leading_emoji_changes() -> None:
    source = "\U0001f6e2\ufe0f Qatar\n- BBG"
    output = "Qatar \U0001f6e2\ufe0f - BBG"

    issues = structure_issues(source, output)

    assert any("line count changed" in issue for issue in issues)
    assert "leading emoji sequence changed" in issues


def test_dzen_article_title_limit() -> None:
    long_title = "\u0410" * 141 + ".\n\n\u0422\u0435\u043a\u0441\u0442"
    issues = validate_dzen_bridge_article(long_title, min_chars=1, max_chars=1000)

    assert any("title too long" in issue for issue in issues)


def test_ensure_title_is_sentence_adds_period_to_short_title_line() -> None:
    text = "\u041a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a\n\n\u041f\u0435\u0440\u0432\u044b\u0439 \u0430\u0431\u0437\u0430\u0446 \u0441\u0442\u0430\u0442\u044c\u0438 \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0435\u0442 \u043c\u044b\u0441\u043b\u044c."

    normalized = ensure_title_is_sentence(text)

    assert normalized.startswith("\u041a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a.\n\n")
    assert validate_dzen_bridge_article(normalized, min_chars=1, max_chars=500) == []


def test_leftover_english_allows_short_attributions_in_russian_text() -> None:
    output = "\u0411\u0438\u0442\u043a\u043e\u0438\u043d \u0432\u044b\u0440\u043e\u0441 \u043d\u0430 5% - CryptoQuant."

    assert leftover_english_issue(output) is None


def test_leftover_english_detects_untranslated_output() -> None:
    assert leftover_english_issue("Bitcoin is higher today") == "output has no Cyrillic text"
