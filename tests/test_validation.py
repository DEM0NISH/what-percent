"""Offline observation-validation tests."""

from decimal import Decimal

import pytest

from whatpercent.validation import validate_fallback_observation, validate_observation


def valid(**overrides: object):
    values: dict[str, object] = {
        "price": Decimal("374"),
        "mrp": Decimal("499"),
        "currency": "INR",
        "title": "Vitamin C Daily Glow Face Serum - 30 ml",
        "expected_tokens": ["vitamin c", "daily glow", "30ml"],
    }
    values.update(overrides)
    return validate_observation(**values)  # type: ignore[arg-type]


def test_valid_observation_passes() -> None:
    assert valid().status == "ok"


@pytest.mark.parametrize("price", [None, 0, -1, "NaN", "not a price"])
def test_invalid_price_is_rejected(price: object) -> None:
    result = valid(price=price)
    assert result.status == "rejected"
    assert "invalid_price" in result.flags


@pytest.mark.parametrize("currency", [None, "USD", "CAD", ""])
def test_non_inr_currency_is_rejected(currency: str | None) -> None:
    assert valid(currency=currency).flags == ("currency_unrecognized",)


def test_rupee_symbol_is_recognized_as_inr() -> None:
    assert valid(currency="₹").valid


def test_invalid_mrp_is_rejected() -> None:
    assert valid(mrp=0).flags == ("invalid_mrp",)


def test_price_above_mrp_is_rejected_and_flagged() -> None:
    result = valid(price=500, mrp=499)
    assert result.status == "rejected"
    assert result.flags == ("price_gt_mrp",)


def test_title_mismatch_is_rejected() -> None:
    result = valid(title="Other Brand Brightening Serum 30 ml")
    assert result.flags == ("title_mismatch",)


def test_large_day_over_day_jump_is_kept_but_flagged() -> None:
    result = valid(price=200, mrp=499, last_good_price=100)
    assert result.status == "ok"
    assert result.flags == ("jump70",)


def test_exactly_seventy_percent_jump_is_not_flagged() -> None:
    assert valid(price=170, mrp=499, last_good_price=100).flags == ()


def test_unavailable_mrp_is_allowed() -> None:
    assert valid(mrp=None).status == "ok"


def test_invalid_identity_token_configuration_is_rejected() -> None:
    result = valid(expected_tokens=["c"])
    assert result.flags == ("invalid_identity_tokens",)


def test_validated_fallback_requires_and_accepts_close_last_good_price() -> None:
    result = validate_fallback_observation(
        price=400,
        mrp=499,
        currency="INR",
        title="Vitamin C Daily Glow Face Serum - 30 ml",
        expected_tokens=["vitamin c", "daily glow", "30ml"],
        last_good_price=374,
    )
    assert result.status == "fallback_ok"


def test_fallback_without_baseline_is_rejected() -> None:
    result = validate_fallback_observation(
        price=400,
        mrp=499,
        currency="INR",
        title="Vitamin C Daily Glow Face Serum - 30 ml",
        expected_tokens=["vitamin c", "daily glow", "30ml"],
        last_good_price=None,
    )
    assert result.flags == ("fallback_no_baseline",)


def test_simulated_plausible_but_wrong_fallback_price_is_rejected() -> None:
    result = validate_fallback_observation(
        price=600,
        mrp=999,
        currency="INR",
        title="Vitamin C Daily Glow Face Serum - 30 ml",
        expected_tokens=["vitamin c", "daily glow", "30ml"],
        last_good_price=374,
    )
    assert result.status == "rejected"
    assert result.flags == ("fallback_deviation",)


def test_fallback_above_mrp_is_rejected() -> None:
    result = validate_fallback_observation(
        price=500,
        mrp=499,
        currency="INR",
        title="Vitamin C Daily Glow Face Serum - 30 ml",
        expected_tokens=["vitamin c", "daily glow", "30ml"],
        last_good_price=374,
    )
    assert result.flags == ("price_gt_mrp",)
