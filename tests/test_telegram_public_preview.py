from n1_project.telegram_public_preview import clean_telegram_html_text, parse_public_preview_posts


def test_clean_telegram_html_text() -> None:
    raw = 'Weekly flows:<br/>- Inflows into <a href="https://example.com">global equities</a><br/>— LSEG data'

    assert clean_telegram_html_text(raw) == "Weekly flows:\n- Inflows into global equities\n— LSEG data"


def test_parse_public_preview_posts() -> None:
    page = """
    <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="num1_ch/123">
      <div class="tgme_widget_message_text js-message_text" dir="auto">BTC is up 5%<br/>— CryptoQuant</div>
    </div>
    """

    posts = parse_public_preview_posts("num1_ch", page)

    assert len(posts) == 1
    assert posts[0].source_channel_id == "@num1_ch"
    assert posts[0].source_message_id == "123"
    assert posts[0].text == "BTC is up 5%\n— CryptoQuant"
