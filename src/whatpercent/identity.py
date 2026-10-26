"""Product-title normalization and identity checks."""

from __future__ import annotations

import re
from collections.abc import Sequence

_UNIT_SPACING = re.compile(r"(?<=\d)\s+(?=(?:ml|l|kg|g|gm|mg|pcs?|pieces?)\b)", re.I)
_WHITESPACE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lowercase, compact number-unit spacing, and collapse title whitespace."""
    lowered = title.lower().replace("\u00a0", " ")
    compacted = _UNIT_SPACING.sub("", lowered)
    return _WHITESPACE.sub(" ", compacted).strip()


def _normalize_phrase(phrase: str) -> str:
    return normalize_title(phrase).strip(" \t\r\n,.;:()[]{}")


def validate_expected_tokens(expected_tokens: Sequence[str]) -> None:
    """Require phrase tokens and reject fragile one-character entries."""
    if not expected_tokens:
        raise ValueError("expected_tokens must contain at least one phrase")
    for token in expected_tokens:
        normalized = _normalize_phrase(token)
        if not normalized:
            raise ValueError("expected_tokens cannot contain empty phrases")
        if len(normalized) == 1:
            raise ValueError(
                f"expected token {token!r} is too short; use a phrase such as 'vitamin c'"
            )


def title_matches(title: str, expected_tokens: Sequence[str]) -> bool:
    """Return true only when every configured phrase appears as a whole phrase."""
    validate_expected_tokens(expected_tokens)
    normalized_title = normalize_title(title)
    for token in expected_tokens:
        phrase = _normalize_phrase(token)
        if not re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized_title):
            return False
    return True
