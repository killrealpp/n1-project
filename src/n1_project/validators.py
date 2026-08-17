from __future__ import annotations

import html
import re

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
AROUND_CLOCK_RE = re.compile(r"(?<!\d)24\s*/\s*7(?!\d)")
NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"(?:\d{1,3}(?:[,\.\u00a0\u202f ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?:%|x|st|nd|rd|th|bps?|pps?|pts?|msecs?|ms|secs?|trln|bln|mln|bn|mn|[kmbt])?"
    r"(?!\w)",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"(?<![\d.])"
    r"(?:"
    r"(?P<ymd_year>\d{4})[./-](?P<ymd_month>\d{1,2})[./-](?P<ymd_day>\d{1,2})"
    r"|"
    r"(?P<dmy_day>\d{1,2})[./-](?P<dmy_month>\d{1,2})[./-](?P<dmy_year>\d{4})"
    r")"
    r"(?![\d.])"
)
PERIOD_NUMBER_RE = re.compile(r"\b[HQ]([1-4])\b", re.IGNORECASE)
RU_COMPACT_PERIOD_RE = re.compile(r"(?<!\w)([1-4])\s*[\u041f\u043f\u041a\u043a](?!\w)")
ALNUM_MODEL_NUMBER_RE = re.compile(r"\b[A-ZА-Я]{1,8}-?(\d{1,4})(?:[A-ZА-Яa-zа-я])?\b")
LAYER_NUMBER_RE = re.compile(r"\b(?:L|Layer)[-\s]?([1-4])\b", re.IGNORECASE)
RU_PERIOD_WORD_PATTERNS = {
    "1": (
        r"\bперв(?:ый|ого|ому|ым|ом|ая|ой|ую|ое|ом)\s+(?:квартал|квартале|квартала|кварталу|кварталом|полугодие|полугодии|полугодия|полугодию|полугодием)\b",
    ),
    "2": (
        r"\bвтор(?:ой|ого|ому|ым|ом|ая|ую|ое|ом)\s+(?:квартал|квартале|квартала|кварталу|кварталом|полугодие|полугодии|полугодия|полугодию|полугодием)\b",
    ),
    "3": (
        r"\bтрет(?:ий|ьего|ьему|ьим|ьем|ья|ью|ье|ьем)\s+(?:квартал|квартале|квартала|кварталу|кварталом)\b",
    ),
    "4": (
        r"\bчетверт(?:ый|ого|ому|ым|ом|ая|ую|ое|ом)\s+(?:квартал|квартале|квартала|кварталу|кварталом)\b",
    ),
}
EN_PERIOD_WORD_PATTERNS = {
    "1": (r"\bfirst\s+(?:half|quarter)\b",),
    "2": (r"\bsecond\s+(?:half|quarter)\b",),
    "3": (r"\bthird\s+quarter\b",),
    "4": (r"\bfourth\s+quarter\b",),
}
RU_LEVEL_WORD_PATTERNS = {
    "1": (
        r"\bперв(?:ый|ого|ому|ым|ом|ая|ой|ую|ое|ом)\s+уров(?:ень|ня|ню|нем|не)\b",
    ),
    "2": (
        r"\bвтор(?:ой|ого|ому|ым|ом|ая|ую|ое|ом)\s+уров(?:ень|ня|ню|нем|не)\b",
    ),
    "3": (
        r"\bтрет(?:ий|ьего|ьему|ьим|ьем|ья|ью|ье|ьем)\s+уров(?:ень|ня|ню|нем|не)\b",
    ),
    "4": (
        r"\bчетверт(?:ый|ого|ому|ым|ом|ая|ую|ое|ом)\s+уров(?:ень|ня|ню|нем|не)\b",
    ),
}
ROMAN_PERIOD_PATTERNS = {
    "1": (
        r"\bI\s+(?:квартал|квартале|квартала|кварталу|кварталом|полугодие|полугодии|полугодия|полугодию|полугодием)\b",
    ),
    "2": (
        r"\bII\s+(?:квартал|квартале|квартала|кварталу|кварталом|полугодие|полугодии|полугодия|полугодию|полугодием)\b",
    ),
    "3": (
        r"\bIII\s+(?:квартал|квартале|квартала|кварталу|кварталом)\b",
    ),
    "4": (
        r"\bIV\s+(?:квартал|квартале|квартала|кварталу|кварталом)\b",
    ),
}
HASHTAG_RE = re.compile(r"#[\w_]+", re.UNICODE)
LATIN_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
CYRILLIC_WORD_RE = re.compile(r"\b[\u0400-\u04FF]{4,}\b")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
# Below this count no output is ever reported as untranslated: real posts
# listing companies routinely reach eleven or twelve latin words.
LEFTOVER_ENGLISH_MIN_WORDS = 12
# A translation that is still half latin is suspicious; below that it is not.
LEFTOVER_ENGLISH_MIN_SHARE = 0.5
# A real translation drops the latin share well under the source's. Staying
# this close to the source means the English was never converted.
LEFTOVER_ENGLISH_SOURCE_SHARE_FACTOR = 0.85
BOLD_BLOCK_RE = re.compile(r"^\s*<b>[^<]{1,120}</b>\s*$", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
EMOJI_RE = re.compile(r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]")
LEADING_EMOJI_RE = re.compile(r"^\s*((?:[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]\ufe0f?\s*)+)")
GENERIC_ARTICLE_TITLE_RE = re.compile(
    r"^\s*(?:почему|что\s+произошло|что\s+теперь\s+будет|что\s+означает)\b",
    re.IGNORECASE,
)
SOURCE_LIMIT_UP_RE = re.compile(r"\blimit[-\s]?up\b|\bupper\s+price\s+limit\b", re.IGNORECASE)
OUTPUT_LIMIT_UP_GOOD_RE = re.compile(r"\b(?:верхн\w*\s+планк\w*|планк\w*\s+роста)\b", re.IGNORECASE)
OUTPUT_LIMIT_UP_BAD_RE = re.compile(r"\bлимит\s+ввер\w*|\bлимит\s+роста\b|\bпредохранител\w*", re.IGNORECASE)
SOURCE_TRADING_HALT_RE = re.compile(
    r"\b(?:"
    r"circuit\s+breakers?"
    r"|volatility\s+(?:halt|auction)s?"
    r"|trading\s+halts?"
    r"|halt(?:ed|s|ing)?\s+trading"
    r")\b",
    re.IGNORECASE,
)
HALT_WORD_RE = re.compile(r"\bhalt(?:ed|s|ing)?\b", re.IGNORECASE)
TRADING_CONTEXT_RE = re.compile(
    r"\b(?:trading|trade|trades|shares?|stock|stocks|equities|securities|exchange|bourse"
    r"|nasdaq|nyse|moex|listing|ticker)\b",
    re.IGNORECASE,
)
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+|\n+")
OUTPUT_TRADING_HALT_GOOD_RE = re.compile(
    r"\b(?:торг\w*\s+приостанов\w*|приостанов\w*\s+торг\w*|волатильностн\w*\s+пауз\w*|остановк\w*\s+торг\w*|дискретн\w*\s+аукцион\w*)\b",
    re.IGNORECASE,
)
OUTPUT_TRADING_HALT_BAD_RE = re.compile(r"\bпредохранител\w*", re.IGNORECASE)
SOURCE_SHORT_POSITION_RE = re.compile(r"\b(?:short\s+positions?|shorts)\b", re.IGNORECASE)
SOURCE_LONG_POSITION_RE = re.compile(r"\b(?:long\s+positions?|longs)\b", re.IGNORECASE)
OUTPUT_SHORT_POSITION_BAD_RE = re.compile(r"\bкоротк\w*\s+позици\w*", re.IGNORECASE)
OUTPUT_LONG_POSITION_BAD_RE = re.compile(r"\bдлинн\w*\s+позици\w*", re.IGNORECASE)
OUTPUT_SHORT_POSITION_GOOD_RE = re.compile(r"\b(?:шортов\w*\s+позици\w*|шорт\w*)\b", re.IGNORECASE)
OUTPUT_LONG_POSITION_GOOD_RE = re.compile(r"\b(?:лонгов\w*\s+позици\w*|лонг\w*)\b", re.IGNORECASE)
KNOWN_ATTRIBUTIONS = {
    "AUTOSTAT",
    "BBG",
    "BITWISE",
    "BOFA",
    "CPCA",
    "CRYPTOQUANT",
    "IF",
    "LSEG",
    "RTRS",
    "TASS",
}
CURRENCY_CODES = {
    "AUD",
    "BRL",
    "CAD",
    "CHF",
    "CNY",
    "EUR",
    "GBP",
    "HKD",
    "JPY",
    "RUB",
    "USD",
}
MARKET_SYMBOL_WORDS = {
    "CAC",
    "DAX",
    "DJIA",
    "FTSE",
    "HSI",
    "IMOEX",
    "MOEX",
    "NASDAQ",
    "NDX",
    "NIKKEI",
    "RTS",
    "RTSI",
    "SSEC",
    "SPX",
}


def normalize_vk_owner_id(vk_id: str) -> str:
    value = vk_id.strip()
    if not value:
        return value
    try:
        number = int(value)
    except ValueError:
        return value
    if number > 0:
        return str(-number)
    return str(number)


def ensure_max_chars(text: str, max_chars: int, label: str) -> None:
    length = len(text)
    if length > max_chars:
        raise ValueError(f"{label} text is {length} chars; max is {max_chars}")


def extract_urls(text: str) -> set[str]:
    return set(URL_RE.findall(text))


def canonical_date_token(match: re.Match[str]) -> str | None:
    if match.group("ymd_year"):
        year = int(match.group("ymd_year"))
        month = int(match.group("ymd_month"))
        day = int(match.group("ymd_day"))
    else:
        year = int(match.group("dmy_year"))
        month = int(match.group("dmy_month"))
        day = int(match.group("dmy_day"))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"date:{year:04d}-{month:02d}-{day:02d}"


def extract_date_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in DATE_RE.finditer(text):
        token = canonical_date_token(match)
        if token:
            tokens.add(token)
    return tokens


def mask_date_tokens(text: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        return " " if canonical_date_token(match) else match.group(0)

    return DATE_RE.sub(replacement, text)


def extract_numbers(text: str) -> set[str]:
    numbers = extract_date_tokens(text)
    number_text = mask_date_tokens(text)
    if AROUND_CLOCK_RE.search(number_text):
        numbers.add("24/7")
        number_text = AROUND_CLOCK_RE.sub(" ", number_text)
    if "круглосуточ" in text.lower():
        numbers.add("24/7")
    numbers.update(NUMBER_RE.findall(number_text))
    numbers.update(PERIOD_NUMBER_RE.findall(number_text))
    numbers.update(RU_COMPACT_PERIOD_RE.findall(number_text))
    numbers.update(ALNUM_MODEL_NUMBER_RE.findall(number_text))
    numbers.update(LAYER_NUMBER_RE.findall(number_text))
    normalized = text.lower()
    for value, patterns in RU_PERIOD_WORD_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            numbers.add(value)
    # English periods must be extracted too, otherwise "in the first half of the year"
    # translated as "в первом полугодии" looks like an invented number.
    for value, patterns in EN_PERIOD_WORD_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            numbers.add(value)
    for value, patterns in RU_LEVEL_WORD_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            numbers.add(value)
    for value, patterns in ROMAN_PERIOD_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            numbers.add(value)
    return numbers


def normalize_number_token(value: str) -> str:
    token = value.strip()
    suffix = ""
    if token.endswith("%"):
        token = token[:-1]
        suffix = "%"
    else:
        lower_token = token.lower()
        for removable_suffix in (
            "bps",
            "bp",
            "pps",
            "pp",
            "pts",
            "pt",
            "msecs",
            "msec",
            "ms",
            "secs",
            "sec",
            "trln",
            "bln",
            "mln",
            "bn",
            "mn",
            "st",
            "nd",
            "rd",
            "th",
            "x",
            "k",
            "m",
            "b",
            "t",
        ):
            if lower_token.endswith(removable_suffix):
                token = token[: -len(removable_suffix)]
                break

    token = token.replace("\u00a0", " ").replace("\u202f", " ")
    token = re.sub(r"(?<=\d)\s+(?=\d{3}(?:\D|$))", "", token)

    has_comma = "," in token
    has_dot = "." in token
    if has_comma and has_dot:
        if token.rfind(".") > token.rfind(","):
            token = token.replace(",", "")
        else:
            token = token.replace(".", "").replace(",", ".")
    elif has_comma:
        parts = token.split(",")
        if len(parts) > 1 and all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            token = "".join(parts)
        else:
            token = token.replace(",", ".")
    elif has_dot:
        parts = token.split(".")
        if len(parts) > 1 and all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            token = "".join(parts)

    return token + suffix


def is_grouped_number(parts: list[str]) -> bool:
    if not parts or not all(part.isdigit() for part in parts):
        return False
    if len(parts[0]) > 1 and parts[0].startswith("0"):
        return False
    if len(parts[0]) > 3:
        return len(parts) == 1
    return all(len(part) == 3 for part in parts[1:])


def number_token_readings(value: str) -> set[str]:
    """Return every plausible normalized reading of one extracted number token.

    A space separates thousands and also separates words, so the Russian
    "47 000 203-мм" is either the single number 47000203 or the number 47000
    followed by 203. Accepting both readings keeps a correct translation of
    "47,000 203mm shells" from being reported as one missing and one added
    number. Only tokens spanning three or more space-separated groups are
    ambiguous; "5 000" stays strict.
    """
    readings = {normalize_number_token(value)}
    parts = re.split(r"[   ]", value)
    if len(parts) < 3:
        return readings
    for index in range(1, len(parts)):
        head, tail = parts[:index], parts[index:]
        if is_grouped_number(head) and is_grouped_number(tail):
            readings.add(normalize_number_token(" ".join(head)))
            readings.add(normalize_number_token(" ".join(tail)))
    return readings


def number_keys(values: set[str]) -> set[str]:
    keys: set[str] = set()
    for value in values:
        keys.update(number_token_readings(value))
    return keys


def extract_hashtags(text: str) -> set[str]:
    return set(HASHTAG_RE.findall(text))


def extract_emojis(text: str) -> set[str]:
    return set(EMOJI_RE.findall(text))


def extract_known_attributions(text: str) -> set[str]:
    upper = text.upper()
    return {item for item in KNOWN_ATTRIBUTIONS if re.search(rf"\b{re.escape(item)}\b", upper)}


def non_empty_line_count(text: str) -> int:
    return sum(1 for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def leading_emojis(text: str) -> str:
    match = LEADING_EMOJI_RE.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", "", match.group(1))


def preservation_issues(source_text: str, output_text: str) -> list[str]:
    issues: list[str] = []
    for label, extractor in (
        ("url", extract_urls),
        ("hashtag", extract_hashtags),
        ("emoji", extract_emojis),
    ):
        missing = sorted(extractor(source_text) - extractor(output_text))
        if missing:
            issues.append(f"missing {label}s: {', '.join(missing)}")

    source_numbers = extract_numbers(source_text)
    output_number_keys = number_keys(extract_numbers(output_text))
    missing_numbers = sorted(
        value for value in source_numbers if not number_token_readings(value) & output_number_keys
    )
    if missing_numbers:
        issues.append(f"missing numbers: {', '.join(missing_numbers)}")
    return issues


def structure_issues(source_text: str, output_text: str) -> list[str]:
    issues: list[str] = []
    source_lines = non_empty_line_count(source_text)
    output_lines = non_empty_line_count(output_text)
    if source_lines != output_lines:
        issues.append(f"line count changed: source has {source_lines}, output has {output_lines}")

    source_prefix = leading_emojis(source_text)
    if source_prefix and leading_emojis(output_text) != source_prefix:
        issues.append("leading emoji sequence changed")
    return issues


def unexpected_addition_issues(source_text: str, output_text: str) -> list[str]:
    issues: list[str] = []
    for label, extractor in (
        ("url", extract_urls),
        ("hashtag", extract_hashtags),
        ("emoji", extract_emojis),
    ):
        added = sorted(extractor(output_text) - extractor(source_text))
        if added:
            issues.append(f"added {label}s: {', '.join(added)}")

    source_number_keys = number_keys(extract_numbers(source_text))
    output_numbers = extract_numbers(output_text)
    added_numbers = sorted(
        value for value in output_numbers if not number_token_readings(value) & source_number_keys
    )
    if added_numbers:
        issues.append(f"added numbers: {', '.join(added_numbers)}")

    added_attributions = sorted(extract_known_attributions(output_text) - extract_known_attributions(source_text))
    if added_attributions:
        issues.append(f"added source attributions: {', '.join(added_attributions)}")
    return issues


def first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    match = re.search(r"(?<=[.!?])\s+", stripped)
    if not match:
        return stripped.splitlines()[0].strip()
    return stripped[: match.start()].strip()


def ensure_title_is_sentence(text: str) -> str:
    lines = text.strip().splitlines()
    for index, line in enumerate(lines):
        title = line.strip()
        if not title:
            continue
        if len(title) <= 140 and not re.search(r"[.!?]\s*$", title):
            lines[index] = line.rstrip() + "."
        break
    return "\n".join(lines)


def split_first_sentence(text: str) -> tuple[str, str]:
    stripped = text.strip()
    if not stripped:
        return "", ""
    match = re.search(r"(?<=[.!?])\s+", stripped)
    if match:
        return stripped[: match.start()].strip(), stripped[match.end() :].strip()
    lines = stripped.splitlines()
    title = lines[0].strip()
    rest = "\n".join(lines[1:]).strip()
    return title, rest


def normalize_article_paragraphs(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if BOLD_BLOCK_RE.fullmatch(line):
            if current:
                blocks.append(" ".join(current))
                current = []
            blocks.append(line)
            continue
        if line:
            current.append(line)
            continue
        if current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return "\n\n".join(blocks)


def sanitize_article_html(text: str) -> str:
    open_marker = "\uE000B_OPEN\uE000"
    close_marker = "\uE000B_CLOSE\uE000"
    protected = re.sub(r"<\s*b\s*>", open_marker, text, flags=re.IGNORECASE)
    protected = re.sub(r"<\s*/\s*b\s*>", close_marker, protected, flags=re.IGNORECASE)
    escaped = html.escape(protected, quote=False)
    return escaped.replace(open_marker, "<b>").replace(close_marker, "</b>")


def format_dzen_article_text(text: str, article_date_label: str | None = None) -> str:
    article = ensure_title_is_sentence(text)
    title, rest = split_first_sentence(article)
    if not title:
        return ""

    rest = normalize_article_paragraphs(rest)
    blocks = [title]
    if rest:
        blocks.append(rest)
    return sanitize_article_html("\n\n".join(blocks))


def trim_dzen_article_to_max_chars(text: str, max_chars: int) -> str:
    article = text.strip()
    if max_chars <= 0 or len(article) <= max_chars:
        return article

    title, rest = split_first_sentence(article)
    if not title:
        return article[:max_chars].rstrip()

    blocks = [block.strip() for block in rest.split("\n\n") if block.strip()]
    while blocks and len("\n\n".join([title, *blocks])) > max_chars:
        last = blocks[-1]
        sentences = SENTENCE_SPLIT_RE.split(last)
        if len(sentences) > 1:
            shortened = " ".join(sentences[:-1]).strip()
            if shortened:
                blocks[-1] = shortened
            else:
                blocks.pop()
        else:
            blocks.pop()
        while blocks and BOLD_BLOCK_RE.fullmatch(blocks[-1]):
            blocks.pop()

    if blocks:
        candidate = "\n\n".join([title, *blocks]).strip()
        if len(candidate) <= max_chars:
            return candidate

    if len(title) <= max_chars:
        return title
    return title[:max_chars].rstrip()


def article_html_issues(text: str) -> list[str]:
    issues: list[str] = []
    for match in HTML_TAG_RE.finditer(text):
        if match.group(1).lower() != "b":
            issues.append(f"unsupported HTML tag: {match.group(0)}")
    if text.lower().count("<b>") != text.lower().count("</b>"):
        issues.append("unbalanced <b> tags")
    title = first_sentence(text)
    if "<b>" in title.lower() or "</b>" in title.lower():
        issues.append("title contains bold HTML")
    return issues


def validate_dzen_bridge_article(text: str, min_chars: int, max_chars: int) -> list[str]:
    issues: list[str] = []
    length = len(text)
    title = first_sentence(text)
    if length < min_chars:
        issues.append(f"article too short: {length} chars; min is {min_chars}")
    if length > max_chars:
        issues.append(f"article too long: {length} chars; max is {max_chars}")
    if len(title) > 140:
        issues.append(f"title too long: {len(title)} chars; max is 140")
    if extract_urls(title):
        issues.append("title contains a link")
    if GENERIC_ARTICLE_TITLE_RE.search(title):
        issues.append("title starts with a generic question template")
    issues.extend(article_html_issues(text))
    return issues


def leftover_english_issue(output_text: str) -> str | None:
    latin_words = LATIN_WORD_RE.findall(output_text)
    has_cyrillic = bool(CYRILLIC_RE.search(output_text))
    if has_cyrillic and len(latin_words) > 12:
        return f"many latin words remain: {len(latin_words)}"
    if not has_cyrillic and latin_words:
        return "output has no Cyrillic text"
    return None


def is_market_symbol_word(word: str) -> bool:
    if word.upper() in MARKET_SYMBOL_WORDS:
        return True
    if re.fullmatch(r"[A-Z]{2,5}[Pp]{1,2}", word):
        return True
    if not word.isupper():
        return False
    if word in KNOWN_ATTRIBUTIONS:
        return True
    if len(word) <= 5:
        return True
    if len(word) == 6 and word[:3] in CURRENCY_CODES and word[3:] in CURRENCY_CODES:
        return True
    if len(word) == 7 and word[:4] in {"USDC", "USDT"} and word[4:] in CURRENCY_CODES:
        return True
    return False


def source_is_symbol_only(source_text: str) -> bool:
    cleaned = URL_RE.sub(" ", source_text)
    cleaned = HASHTAG_RE.sub(" ", cleaned)
    words = LATIN_WORD_RE.findall(cleaned)
    return bool(words) and all(is_market_symbol_word(word) for word in words)


def source_has_translatable_english(source_text: str) -> bool:
    cleaned = URL_RE.sub(" ", source_text)
    cleaned = HASHTAG_RE.sub(" ", cleaned)
    for word in LATIN_WORD_RE.findall(cleaned):
        if is_market_symbol_word(word):
            continue
        return True
    return False


def translatable_word_counts(text: str) -> tuple[list[str], list[str]]:
    """Split a text into latin and Cyrillic content words.

    Links, hashtags, tickers and other market symbols are dropped: they stay
    latin in any correct Russian translation, so counting them says nothing
    about whether the text was translated.
    """
    cleaned = URL_RE.sub(" ", text)
    cleaned = HASHTAG_RE.sub(" ", cleaned)
    latin = [word for word in LATIN_WORD_RE.findall(cleaned) if not is_market_symbol_word(word)]
    cyrillic = CYRILLIC_WORD_RE.findall(cleaned)
    return latin, cyrillic


def latin_word_share(latin_words: list[str], cyrillic_words: list[str]) -> float:
    total = len(latin_words) + len(cyrillic_words)
    if not total:
        return 0.0
    return len(latin_words) / total


def leftover_english_issue_for_translation(source_text: str, output_text: str) -> str | None:
    """Detect an untranslated output without punishing name-heavy posts.

    A flat cap on latin words sat right on top of normal traffic: a legitimate
    list of companies or a sanctioned-exchange roundup carries 13-41 latin
    words and was killed after five attempts. What actually separates a failed
    translation from a name-heavy one is how much of the latin survived: a real
    translation converts most English words to Russian and so drops the latin
    share well below the source, while an untranslated output keeps it.
    """
    if not CYRILLIC_RE.search(output_text):
        if LATIN_WORD_RE.findall(output_text) and not source_is_symbol_only(source_text):
            return "output has no Cyrillic text"
        return None

    output_latin, output_cyrillic = translatable_word_counts(output_text)
    if len(output_latin) <= LEFTOVER_ENGLISH_MIN_WORDS:
        return None

    output_share = latin_word_share(output_latin, output_cyrillic)
    if output_share <= LEFTOVER_ENGLISH_MIN_SHARE:
        return None

    source_latin, source_cyrillic = translatable_word_counts(source_text)
    source_share = latin_word_share(source_latin, source_cyrillic)
    if source_share and output_share < source_share * LEFTOVER_ENGLISH_SOURCE_SHARE_FACTOR:
        return None

    total_words = len(output_latin) + len(output_cyrillic)
    return (
        f"many latin words remain: {len(output_latin)} of {total_words} words "
        f"({output_share:.0%}); source share {source_share:.0%}"
    )


def source_requires_trading_halt_terminology(source_text: str) -> bool:
    """Report whether the source really describes an exchange trading halt.

    A bare "halted" is not enough: a grain terminal that "has halted loading"
    is not a trading halt, and demanding "торги приостановлены" for it burned
    every translation attempt on such posts. Either the wording is explicitly
    about trading, or the halt has to share a sentence with market vocabulary.
    """
    if SOURCE_TRADING_HALT_RE.search(source_text):
        return True
    for sentence in SENTENCE_BOUNDARY_RE.split(source_text):
        if HALT_WORD_RE.search(sentence) and TRADING_CONTEXT_RE.search(sentence):
            return True
    return False


def market_terminology_issues(source_text: str, output_text: str) -> list[str]:
    issues: list[str] = []
    if SOURCE_LIMIT_UP_RE.search(source_text):
        if OUTPUT_LIMIT_UP_BAD_RE.search(output_text) or not OUTPUT_LIMIT_UP_GOOD_RE.search(output_text):
            issues.append("bad market terminology: translate limit up as верхняя планка or планка роста")
    if source_requires_trading_halt_terminology(source_text):
        if OUTPUT_TRADING_HALT_BAD_RE.search(output_text) or not OUTPUT_TRADING_HALT_GOOD_RE.search(output_text):
            issues.append(
                "bad market terminology: translate circuit breaker/trading halt as торги приостановлены, волатильностная пауза, остановка торгов, or дискретный аукцион"
            )
    if SOURCE_SHORT_POSITION_RE.search(source_text):
        if OUTPUT_SHORT_POSITION_BAD_RE.search(output_text) or not OUTPUT_SHORT_POSITION_GOOD_RE.search(output_text):
            issues.append("bad market terminology: translate short positions as шортовые позиции")
    if SOURCE_LONG_POSITION_RE.search(source_text):
        if OUTPUT_LONG_POSITION_BAD_RE.search(output_text) or not OUTPUT_LONG_POSITION_GOOD_RE.search(output_text):
            issues.append("bad market terminology: translate long positions as лонговые позиции")
    return issues


def translation_issues(source_text: str, output_text: str) -> list[str]:
    issues = preservation_issues(source_text, output_text)
    issues.extend(structure_issues(source_text, output_text))
    issues.extend(unexpected_addition_issues(source_text, output_text))
    issues.extend(market_terminology_issues(source_text, output_text))
    leftover = leftover_english_issue_for_translation(source_text, output_text)
    if leftover:
        issues.append(leftover)
    return issues
