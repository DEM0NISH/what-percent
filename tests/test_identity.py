"""Offline title identity tests."""

import pytest

from whatpercent.identity import normalize_title, title_matches, validate_expected_tokens


def test_normalizes_case_whitespace_and_number_unit_spacing() -> None:
    assert normalize_title("  Vitamin C   Daily Glow 30 ml ") == "vitamin c daily glow 30ml"


def test_title_matches_short_phrases_and_compact_size() -> None:
    title = "Vitamin C Daily Glow Face Serum With Turmeric - 30 ml"
    assert title_matches(title, ["vitamin c", "daily glow", "30ml"])


def test_title_matches_is_case_insensitive_and_collapses_whitespace() -> None:
    assert title_matches(
        "  MAMAEARTH   RICE   FACE WASH 100 ml", ["mamaearth", "rice face", "100ml"]
    )


def test_title_mismatch_for_missing_size_phrase() -> None:
    assert not title_matches("Vitamin C Daily Glow Face Serum 10 ml", ["daily glow", "30ml"])


def test_title_mismatch_for_different_brand() -> None:
    assert not title_matches("Other Brand Vitamin C Face Serum 30 ml", ["mamaearth", "vitamin c"])


def test_single_character_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="too short"):
        validate_expected_tokens(["c"])


def test_empty_expected_tokens_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        title_matches("Vitamin C", [])
