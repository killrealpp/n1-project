from __future__ import annotations

import re


WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_social_post(text: str, max_lines: int = 3) -> str:
    """Trim whitespace while preserving the translated message structure."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def prepare_social_post_text(text: str, max_lines: int = 3, target_max_chars: int = 700) -> str:
    prepared = normalize_social_post(text, max_lines=max_lines)
    if len(prepared) <= target_max_chars:
        return prepared

    # The target is editorial, not a hard platform limit. Publishers enforce
    # hard limits separately, so we keep the full text rather than truncating.
    return prepared
