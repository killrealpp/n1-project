from n1_project.validators import (
    ensure_title_is_sentence,
    format_dzen_article_text,
    leftover_english_issue,
    normalize_vk_owner_id,
    preservation_issues,
    source_has_translatable_english,
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


def test_translation_issues_allow_calendar_date_reordering() -> None:
    source = (
        "\U0001f4c5\U0001f5d3 CALENDAR FOR TODAY - 2026.07.09\n\n"
        "\U0001f1e8\U0001f1f3 China - CPI consumer inflation (June) - 04:30 MSK\n"
        "\U0001f1ea\U0001f1fa ECB minutes from the last meeting - 14:30 MSK\n"
        "\U0001f1fa\U0001f1f8 US - Initial jobless claims - 15:30 MSK\n"
        "\U0001f1fa\U0001f1f8 US - Existing home sales (June) - 17:00 MSK\n"
        "\U0001f6e2\ufe0f US natural gas - EIA inventories - 17:30 MSK\n\n"
        "\U0001f1f7\U0001f1fa Dividend cutoff: $PLZL\n\n"
        "\U0001f1f7\U0001f1fa $MGKL MGKL - Investor Day\n\n"
        "\U0001f1f7\U0001f1fa Trading in settlement futures on ETF iShares MSCI South Korea ETF "
        "will start on the Moscow Exchange derivatives market"
    )
    output = (
        "\U0001f4c5\U0001f5d3 \u041a\u0410\u041b\u0415\u041d\u0414\u0410\u0420\u042c "
        "\u041d\u0410 \u0421\u0415\u0413\u041e\u0414\u041d\u042f - 09.07.2026\n\n"
        "\U0001f1e8\U0001f1f3 \u041a\u0438\u0442\u0430\u0439 - "
        "\u041f\u043e\u0442\u0440\u0435\u0431\u0438\u0442\u0435\u043b\u044c\u0441\u043a\u0430\u044f "
        "\u0438\u043d\u0444\u043b\u044f\u0446\u0438\u044f CPI (\u0438\u044e\u043d\u044c) - 04:30 \u041c\u0421\u041a\n"
        "\U0001f1ea\U0001f1fa \u041f\u0440\u043e\u0442\u043e\u043a\u043e\u043b "
        "\u0415\u0426\u0411 \u0441 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0435\u0433\u043e "
        "\u0437\u0430\u0441\u0435\u0434\u0430\u043d\u0438\u044f - 14:30 \u041c\u0421\u041a\n"
        "\U0001f1fa\U0001f1f8 \u0421\u0428\u0410 - \u041f\u0435\u0440\u0432\u0438\u0447\u043d\u044b\u0435 "
        "\u0437\u0430\u044f\u0432\u043a\u0438 \u043d\u0430 \u043f\u043e\u0441\u043e\u0431\u0438\u0435 "
        "\u043f\u043e \u0431\u0435\u0437\u0440\u0430\u0431\u043e\u0442\u0438\u0446\u0435 - 15:30 \u041c\u0421\u041a\n"
        "\U0001f1fa\U0001f1f8 \u0421\u0428\u0410 - \u041f\u0440\u043e\u0434\u0430\u0436\u0438 "
        "\u0436\u0438\u043b\u044c\u044f \u043d\u0430 \u0432\u0442\u043e\u0440\u0438\u0447\u043d\u043e\u043c "
        "\u0440\u044b\u043d\u043a\u0435 (\u0438\u044e\u043d\u044c) - 17:00 \u041c\u0421\u041a\n"
        "\U0001f6e2\ufe0f \u041f\u0440\u0438\u0440\u043e\u0434\u043d\u044b\u0439 \u0433\u0430\u0437 "
        "\u0421\u0428\u0410 - \u0417\u0430\u043f\u0430\u0441\u044b \u043f\u043e "
        "\u0434\u0430\u043d\u043d\u044b\u043c EIA - 17:30 \u041c\u0421\u041a\n\n"
        "\U0001f1f7\U0001f1fa \u0414\u0430\u0442\u0430 \u043e\u0442\u0441\u0435\u0447\u043a\u0438 "
        "\u043f\u043e \u0434\u0438\u0432\u0438\u0434\u0435\u043d\u0434\u0430\u043c: $PLZL\n\n"
        "\U0001f1f7\U0001f1fa $MGKL MGKL - \u0414\u0435\u043d\u044c \u0438\u043d\u0432\u0435\u0441\u0442\u043e\u0440\u0430\n\n"
        "\U0001f1f7\U0001f1fa \u041d\u0430\u0447\u043d\u0443\u0442\u0441\u044f \u0442\u043e\u0440\u0433\u0438 "
        "\u0440\u0430\u0441\u0447\u0435\u0442\u043d\u044b\u043c\u0438 \u0444\u044c\u044e\u0447\u0435\u0440\u0441\u0430\u043c\u0438 "
        "\u043d\u0430 iShares MSCI South Korea ETF \u043d\u0430 \u0441\u0440\u043e\u0447\u043d\u043e\u043c "
        "\u0440\u044b\u043d\u043a\u0435 \u041c\u043e\u0441\u043a\u043e\u0432\u0441\u043a\u043e\u0439 "
        "\u0431\u0438\u0440\u0436\u0438"
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_removed_thousands_separator() -> None:
    source = "Net income rose to 6,400 million rubles - IF"
    output = "\u0427\u0438\u0441\u0442\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c \u0432\u044b\u0440\u043e\u0441\u043b\u0430 \u0434\u043e 6400 \u043c\u043b\u043d \u0440\u0443\u0431\u043b\u0435\u0439 - IF"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_space_thousands_separator() -> None:
    source = "Revenue reached 8,000 million rubles - IF"
    output = "\u0412\u044b\u0440\u0443\u0447\u043a\u0430 \u0434\u043e\u0441\u0442\u0438\u0433\u043b\u0430 8 000 \u043c\u043b\u043d \u0440\u0443\u0431\u043b\u0435\u0439 - IF"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_multiplier_suffix_translation() -> None:
    source = "Trading volume grew 1.5x - IF"
    output = "\u041e\u0431\u044a\u0435\u043c \u0442\u043e\u0440\u0433\u043e\u0432 \u0432\u044b\u0440\u043e\u0441 \u0432 1,5 \u0440\u0430\u0437\u0430 - IF"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_h1_period_translation() -> None:
    source = (
        "DOM RF: mortgage issuance in H1 2026 rose 48% YoY\n"
        "VTB: mortgage issuance in Russia in H1 2026 grew 1.5x"
    )
    output = (
        "\u0414\u041e\u041c.\u0420\u0424: \u0432\u044b\u0434\u0430\u0447\u0430 \u0438\u043f\u043e\u0442\u0435\u043a\u0438 "
        "\u0432 1 \u043f\u043e\u043b\u0443\u0433\u043e\u0434\u0438\u0438 2026 \u0433\u043e\u0434\u0430 "
        "\u0432\u044b\u0440\u043e\u0441\u043b\u0430 \u043d\u0430 48% \u0433/\u0433\n"
        "\u0412\u0422\u0411: \u0432\u044b\u0434\u0430\u0447\u0430 \u0438\u043f\u043e\u0442\u0435\u043a\u0438 "
        "\u0432 \u0420\u043e\u0441\u0441\u0438\u0438 \u0432 1 \u043f\u043e\u043b\u0443\u0433\u043e\u0434\u0438\u0438 "
        "2026 \u0433\u043e\u0434\u0430 \u0432\u044b\u0440\u043e\u0441\u043b\u0430 \u0432 1,5 \u0440\u0430\u0437\u0430"
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_h1_as_roman_half_year_translation() -> None:
    source = "Russia doubled coal exports to Brazil in H1 2026 - PRIME"
    output = (
        "\u0420\u043e\u0441\u0441\u0438\u044f \u0443\u0434\u0432\u043e\u0438\u043b\u0430 "
        "\u044d\u043a\u0441\u043f\u043e\u0440\u0442 \u0443\u0433\u043b\u044f \u0432 "
        "\u0411\u0440\u0430\u0437\u0438\u043b\u0438\u044e \u0432 I "
        "\u043f\u043e\u043b\u0443\u0433\u043e\u0434\u0438\u0438 2026 \u2014 PRIME"
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_q2_period_word_translation() -> None:
    source = (
        "Samsung reported preliminary results showing operating profit rose 19x YoY in Q2 2026. "
        "Revenue grew 2.2x.\n"
        "Q2 profit exceeded combined earnings over the past three years.\n"
        "The driver remains the same - AI."
    )
    output = (
        "Samsung \u0441\u043e\u043e\u0431\u0449\u0438\u043b\u0430 \u043e "
        "\u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 "
        "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430\u0445: "
        "\u043e\u043f\u0435\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u0430\u044f "
        "\u043f\u0440\u0438\u0431\u044b\u043b\u044c \u0432\u044b\u0440\u043e\u0441\u043b\u0430 "
        "\u0432 19 \u0440\u0430\u0437 \u0433/\u0433 \u0432\u043e "
        "\u0432\u0442\u043e\u0440\u043e\u043c \u043a\u0432\u0430\u0440\u0442\u0430\u043b\u0435 "
        "2026 \u0433\u043e\u0434\u0430. \u0412\u044b\u0440\u0443\u0447\u043a\u0430 "
        "\u0432\u044b\u0440\u043e\u0441\u043b\u0430 \u0432 2,2 \u0440\u0430\u0437\u0430.\n"
        "\u041f\u0440\u0438\u0431\u044b\u043b\u044c \u0437\u0430 \u0432\u0442\u043e\u0440\u043e\u0439 "
        "\u043a\u0432\u0430\u0440\u0442\u0430\u043b \u043f\u0440\u0435\u0432\u044b\u0441\u0438\u043b\u0430 "
        "\u0441\u043e\u0432\u043e\u043a\u0443\u043f\u043d\u0443\u044e \u043f\u0440\u0438\u0431\u044b\u043b\u044c "
        "\u0437\u0430 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0442\u0440\u0438 "
        "\u0433\u043e\u0434\u0430.\n"
        "\u0414\u0440\u0430\u0439\u0432\u0435\u0440 \u043e\u0441\u0442\u0430\u0435\u0442\u0441\u044f "
        "\u0442\u0435\u043c \u0436\u0435 - AI."
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_english_ordinal_suffix_translation() -> None:
    source = "Trump asked Walmart to cut prices for the 250th anniversary of the United States"
    output = "Трамп попросил Walmart снизить цены к 250-летию США"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_attached_magnitude_suffix_translation() -> None:
    source = "BonkDAO hacked for $20M, but BONK = -6%"
    output = "BonkDAO взломали на $20 млн, но BONK = -6%"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_model_hyphen_in_translation() -> None:
    source = (
        "\u26a0\ufe0f\U0001f1fa\U0001f1f8\U0001f1ee\U0001f1f1\U0001f1f9\U0001f1f7 "
        "Netanyahu does not want Trump to sell F35 to Erdogan, calls Erdogan Kim Jong Un.\n\n"
        "Trump wants to sell F35 to Erdogan, calls Erdogan a great leader.\n\n"
        "Netanyahu hates Erdogan. Erdogan hates Netanyahu."
    )
    output = (
        "\u26a0\ufe0f\U0001f1fa\U0001f1f8\U0001f1ee\U0001f1f1\U0001f1f9\U0001f1f7 "
        "\u041d\u0435\u0442\u0430\u043d\u044c\u044f\u0445\u0443 \u043d\u0435 \u0445\u043e\u0447\u0435\u0442, "
        "\u0447\u0442\u043e\u0431\u044b \u0422\u0440\u0430\u043c\u043f \u043f\u0440\u043e\u0434\u0430\u0432\u0430\u043b "
        "F-35 \u042d\u0440\u0434\u043e\u0433\u0430\u043d\u0443, \u043d\u0430\u0437\u044b\u0432\u0430\u0435\u0442 "
        "\u042d\u0440\u0434\u043e\u0433\u0430\u043d\u0430 \u041a\u0438\u043c \u0427\u0435\u043d \u042b\u043d\u043e\u043c.\n\n"
        "\u0422\u0440\u0430\u043c\u043f \u0445\u043e\u0447\u0435\u0442 \u043f\u0440\u043e\u0434\u0430\u0442\u044c "
        "F-35 \u042d\u0440\u0434\u043e\u0433\u0430\u043d\u0443, \u043d\u0430\u0437\u044b\u0432\u0430\u0435\u0442 "
        "\u042d\u0440\u0434\u043e\u0433\u0430\u043d\u0430 \u0432\u0435\u043b\u0438\u043a\u0438\u043c \u043b\u0438\u0434\u0435\u0440\u043e\u043c.\n\n"
        "\u041d\u0435\u0442\u0430\u043d\u044c\u044f\u0445\u0443 \u043d\u0435\u043d\u0430\u0432\u0438\u0434\u0438\u0442 "
        "\u042d\u0440\u0434\u043e\u0433\u0430\u043d\u0430. \u042d\u0440\u0434\u043e\u0433\u0430\u043d "
        "\u043d\u0435\u043d\u0430\u0432\u0438\u0434\u0438\u0442 \u041d\u0435\u0442\u0430\u043d\u044c\u044f\u0445\u0443."
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_l1_as_first_level_translation() -> None:
    source = (
        "\u2734\ufe0f BNB Chain is building a new L1 blockchain for agentic trading\n\n"
        "Sub-50ms transaction confirmations, no public mempool to reduce front-running risk\n\n"
        "Testnet launch is planned for late 2026, mainnet for 2027"
    )
    output = (
        "\u2734\ufe0f BNB Chain \u0441\u0442\u0440\u043e\u0438\u0442 \u043d\u043e\u0432\u044b\u0439 "
        "\u0431\u043b\u043e\u043a\u0447\u0435\u0439\u043d \u043f\u0435\u0440\u0432\u043e\u0433\u043e "
        "\u0443\u0440\u043e\u0432\u043d\u044f \u0434\u043b\u044f \u0430\u0433\u0435\u043d\u0442\u043d\u043e\u0439 "
        "\u0442\u043e\u0440\u0433\u043e\u0432\u043b\u0438\n\n"
        "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 "
        "\u0442\u0440\u0430\u043d\u0437\u0430\u043a\u0446\u0438\u0439 \u043c\u0435\u043d\u0435\u0435 "
        "\u0447\u0435\u043c \u0437\u0430 50 \u043c\u0438\u043b\u043b\u0438\u0441\u0435\u043a\u0443\u043d\u0434, "
        "\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u043f\u0443\u0431\u043b\u0438\u0447\u043d\u043e\u0433\u043e "
        "mempool \u0434\u043b\u044f \u0441\u043d\u0438\u0436\u0435\u043d\u0438\u044f \u0440\u0438\u0441\u043a\u0430 "
        "\u0444\u0440\u043e\u043d\u0442\u0440\u0430\u043d\u043d\u0438\u043d\u0433\u0430\n\n"
        "\u0417\u0430\u043f\u0443\u0441\u043a \u0442\u0435\u0441\u0442\u043d\u0435\u0442\u0430 "
        "\u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d \u043d\u0430 "
        "\u043a\u043e\u043d\u0435\u0446 2026 \u0433\u043e\u0434\u0430, \u043c\u0435\u0439\u043d\u043d\u0435\u0442\u0430 "
        "\u2014 \u043d\u0430 2027 \u0433\u043e\u0434"
    )

    assert translation_issues(source, output) == []


def test_translation_issues_allow_layer_one_as_first_level_translation() -> None:
    source = "BNB Chain is building a new Layer-1 blockchain"
    output = "BNB Chain \u0441\u0442\u0440\u043e\u0438\u0442 \u043d\u043e\u0432\u044b\u0439 \u0431\u043b\u043e\u043a\u0447\u0435\u0439\u043d \u043f\u0435\u0440\u0432\u043e\u0433\u043e \u0443\u0440\u043e\u0432\u043d\u044f"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_ticker_only_output_without_cyrillic() -> None:
    source = "💱 USDCNY = 6.79\nUSDRUB = 80.2"
    output = "💱 USDCNY = 6.79\nUSDRUB = 80.2"

    assert translation_issues(source, output) == []


def test_translation_issues_allow_pref_ticker_suffix_without_cyrillic() -> None:
    source = "\U0001f1f7\U0001f1fa KZOS -10% | KZOSp +10%"
    output = "\U0001f1f7\U0001f1fa KZOS -10% | KZOSp +10%"

    assert source_has_translatable_english(source) is False
    assert translation_issues(source, output) == []


def test_translation_issues_allow_double_pref_ticker_suffix_without_cyrillic() -> None:
    source = "\U0001f4c8\U0001f1f7\U0001f1fa KZOS = +12% KZOSpp = +20%"
    output = "\U0001f4c8\U0001f1f7\U0001f1fa KZOS = +12% KZOSpp = +20%"

    assert source_has_translatable_english(source) is False
    assert translation_issues(source, output) == []


def test_translation_issues_reject_untranslated_all_caps_news() -> None:
    source = "VTB NET PROFIT UNDER IFRS FELL 2.5X YEAR-ON-YEAR"
    output = "VTB NET PROFIT UNDER IFRS FELL 2.5X YEAR-ON-YEAR"

    assert "output has no Cyrillic text" in translation_issues(source, output)


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


def test_format_dzen_article_text_separates_title_and_body() -> None:
    text = (
        "Ипотека снова ускорилась. Сводка за 6 июля 2026 года: "
        "DOM RF сообщил о росте выдач, а ВТБ отметил увеличение в 1,5 раза."
    )

    formatted = format_dzen_article_text(text, article_date_label="6 июля 2026 года")

    assert formatted == (
        "Ипотека снова ускорилась.\n\n"
        "Сводка за 6 июля 2026 года: DOM RF сообщил о росте выдач, а ВТБ отметил увеличение в 1,5 раза."
    )


def test_format_dzen_article_text_does_not_add_missing_date_summary() -> None:
    text = "Крипторынок получил новый сигнал. Bitcoin вырос, а Ethereum сохранил обороты."

    formatted = format_dzen_article_text(text, article_date_label="6 июля 2026 года")

    assert formatted == (
        "Крипторынок получил новый сигнал.\n\n"
        "Bitcoin вырос, а Ethereum сохранил обороты."
    )


def test_format_dzen_article_text_preserves_bold_section_blocks() -> None:
    text = "Market title.\n\n<b>What changed</b>\nBody with RGBI > 114 and spread < 2%."

    formatted = format_dzen_article_text(text)

    assert formatted == "Market title.\n\n<b>What changed</b>\n\nBody with RGBI &gt; 114 and spread &lt; 2%."
    assert validate_dzen_bridge_article(formatted, min_chars=1, max_chars=500) == []


def test_validate_dzen_article_rejects_bold_title_and_unbalanced_tags() -> None:
    text = "<b>Market title.</b>\n\nBody <b>without close."

    issues = validate_dzen_bridge_article(text, min_chars=1, max_chars=500)

    assert "title contains bold HTML" in issues
    assert "unbalanced <b> tags" in issues


def test_leftover_english_allows_short_attributions_in_russian_text() -> None:
    output = "\u0411\u0438\u0442\u043a\u043e\u0438\u043d \u0432\u044b\u0440\u043e\u0441 \u043d\u0430 5% - CryptoQuant."

    assert leftover_english_issue(output) is None


def test_leftover_english_detects_untranslated_output() -> None:
    assert leftover_english_issue("Bitcoin is higher today") == "output has no Cyrillic text"


def test_source_has_translatable_english_ignores_hashtag_only_signal() -> None:
    assert source_has_translatable_english("\U0001f1f7\U0001f1fa\U0001f4c9 #188") is False
    assert source_has_translatable_english("VTB NET PROFIT UNDER IFRS FELL 2.5X") is True
