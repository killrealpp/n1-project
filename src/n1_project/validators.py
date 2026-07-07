from __future__ import annotations

import re

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"(?:\d{1,3}(?:[,\.\u00a0\u202f ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?:%|x|st|nd|rd|th|bps?|pps?|pts?|trln|bln|mln|bn|mn|[kmbt])?"
    r"(?!\w)",
    re.IGNORECASE,
)
PERIOD_NUMBER_RE = re.compile(r"\b[HQ]([1-4])\b", re.IGNORECASE)
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
HASHTAG_RE = re.compile(r"#[\w_]+", re.UNICODE)
LATIN_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
EMOJI_RE = re.compile(r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]")
LEADING_EMOJI_RE = re.compile(r"^\s*((?:[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]\ufe0f?\s*)+)")
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


def extract_numbers(text: str) -> set[str]:
    numbers = set(NUMBER_RE.findall(text))
    numbers.update(PERIOD_NUMBER_RE.findall(text))
    normalized = text.lower()
    for value, patterns in RU_PERIOD_WORD_PATTERNS.items():
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
    output_number_keys = {normalize_number_token(value) for value in extract_numbers(output_text)}
    missing_numbers = sorted(value for value in source_numbers if normalize_number_token(value) not in output_number_keys)
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

    source_number_keys = {normalize_number_token(value) for value in extract_numbers(source_text)}
    output_numbers = extract_numbers(output_text)
    added_numbers = sorted(value for value in output_numbers if normalize_number_token(value) not in source_number_keys)
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
        if line:
            current.append(line)
            continue
        if current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return "\n\n".join(blocks)


def format_dzen_article_text(text: str, article_date_label: str | None = None) -> str:
    article = ensure_title_is_sentence(text)
    title, rest = split_first_sentence(article)
    if not title:
        return ""

    rest = normalize_article_paragraphs(rest)
    blocks = [title]
    if article_date_label:
        summary = f"Сводка за {article_date_label}:"
        if rest.lower().startswith("сводка за "):
            summary_candidate, summary_rest = rest.split(":", 1) if ":" in rest else (summary, "")
            summary = summary_candidate.strip() + ":"
            rest = summary_rest.strip()
        blocks.append(summary)
    if rest:
        blocks.append(rest)
    return "\n\n".join(blocks)


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
    if not word.isupper():
        return False
    if word in KNOWN_ATTRIBUTIONS:
        return True
    if len(word) <= 5:
        return True
    if len(word) == 6 and word[:3] in CURRENCY_CODES and word[3:] in CURRENCY_CODES:
        return True
    return False


def source_is_symbol_only(source_text: str) -> bool:
    cleaned = URL_RE.sub(" ", source_text)
    cleaned = HASHTAG_RE.sub(" ", cleaned)
    words = LATIN_WORD_RE.findall(cleaned)
    return bool(words) and all(is_market_symbol_word(word) for word in words)


def leftover_english_issue_for_translation(source_text: str, output_text: str) -> str | None:
    latin_words = LATIN_WORD_RE.findall(output_text)
    has_cyrillic = bool(CYRILLIC_RE.search(output_text))
    if has_cyrillic and len(latin_words) > 12:
        return f"many latin words remain: {len(latin_words)}"
    if not has_cyrillic and latin_words and not source_is_symbol_only(source_text):
        return "output has no Cyrillic text"
    return None


def translation_issues(source_text: str, output_text: str) -> list[str]:
    issues = preservation_issues(source_text, output_text)
    issues.extend(structure_issues(source_text, output_text))
    issues.extend(unexpected_addition_issues(source_text, output_text))
    leftover = leftover_english_issue_for_translation(source_text, output_text)
    if leftover:
        issues.append(leftover)
    return issues
