from n1_project.formatters import normalize_social_post, prepare_social_post_text


def test_normalize_social_post_trims_without_changing_structure() -> None:
    text = "  BTC grew by 5%  \n\n  - CryptoQuant  "

    assert normalize_social_post(text, max_lines=1) == "BTC grew by 5%\n\n- CryptoQuant"


def test_normalize_social_post_does_not_compact_long_list() -> None:
    text = "\n".join(
        [
            "Weekly flows:",
            "- stocks",
            "- bonds",
            "- money market funds",
            "- LSEG",
        ]
    )

    assert normalize_social_post(text, max_lines=2) == text


def test_prepare_social_post_does_not_truncate_editorial_target() -> None:
    text = "A" * 20

    assert prepare_social_post_text(text, max_lines=3, target_max_chars=5) == text
