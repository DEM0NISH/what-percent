"""Offline parsing and unit-conversion tests."""

from decimal import Decimal

import pytest

from whatpercent.parsing import parse_price, parse_rating, to_base_quantity


@pytest.mark.parametrize(
    ("text", "expected", "flags"),
    [
        ("₹ 1,299", "1299", ()),
        ("Rs. 1,299.50", "1299.50", ()),
        ("INR 999", "999", ()),
        ("₹1,23,456", "123456", ()),
        ("₹\u00a099.25", "99.25", ()),
        ("MRP ₹ 349.00", "349.00", ()),
        ("₹ 250 - ₹ 300", "250", ("price_range_lower_bound",)),
        ("Rs. 250–300", "250", ("price_range_lower_bound",)),
        ("INR 250 to 300", "250", ("price_range_lower_bound",)),
        ("₹ 0", "0", ()),
        ("₹ 12.5", "12.5", ()),
        ("Rs 2,499", "2499", ()),
        ("INR 12,34,567.89", "1234567.89", ()),
        ("sale price: ₹ 675", "675", ()),
        ("price unavailable", None, ()),
        ("12.5", None, ()),
        ("₹ xyz", None, ()),
        ("", None, ()),
    ],
)
def test_parse_price(text: str, expected: str | None, flags: tuple[str, ...]) -> None:
    parsed = parse_price(text)
    assert parsed.value == (Decimal(expected) if expected is not None else None)
    assert parsed.flags == flags
    assert parsed.currency == ("INR" if expected is not None else None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4.5 out of 5", "4.5"),
        ("Rating 4.8", "4.8"),
        ("0/5", "0"),
        ("6/5", None),
        ("no rating", None),
    ],
)
def test_parse_rating(text: str, expected: str | None) -> None:
    assert parse_rating(text) == (Decimal(expected) if expected is not None else None)


@pytest.mark.parametrize(
    ("value", "unit", "expected", "base_unit"),
    [
        (1, "L", "1000", "ml"),
        (500, "ml", "500", "ml"),
        (1, "kg", "1000", "g"),
        (250, "gm", "250", "g"),
        (2, "pcs", "2", "pcs"),
        (500, "mg", "0.500", "g"),
    ],
)
def test_to_base_quantity(value: int, unit: str, expected: str, base_unit: str) -> None:
    assert to_base_quantity(value, unit) == (Decimal(expected), base_unit)


def test_to_base_quantity_rejects_unknown_unit() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        to_base_quantity(10, "bottles")
