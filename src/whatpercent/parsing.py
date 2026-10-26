"""Pure parsing helpers for prices, ratings, and package quantities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_CURRENCY_AMOUNT = re.compile(r"(?i)(₹|\bINR\b|\bRs\.?)[\s\u00a0]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
_RANGE_AFTER = re.compile(r"(?i)^\s*(?:-|–|—|to)\s*(?:(?:₹|INR\b|Rs\.?)\s*)?[0-9]")
_RATING = re.compile(r"(?<![\d.])(\d+(?:\.[0-9]+)?)(?:\s*(?:/\s*5|out of 5))?", re.I)
_SIZE_UNIT = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(ml|l|kg|g|gm|mg|pcs?|pieces?)\s*$", re.I)


@dataclass(frozen=True)
class ParsedPrice:
    """Parsed INR amount and any caution needed when interpreting it."""

    value: Decimal | None
    flags: tuple[str, ...] = ()
    currency: str | None = None


def parse_price(text: str | None) -> ParsedPrice:
    """Parse an INR amount; for a range, preserve its lower bound and mark it."""
    if not text:
        return ParsedPrice(None)
    normalized = text.replace("\u00a0", " ").strip()
    match = _CURRENCY_AMOUNT.search(normalized)
    if not match:
        return ParsedPrice(None)
    try:
        value = Decimal(match.group(2).replace(",", ""))
    except InvalidOperation:
        return ParsedPrice(None)
    if not value.is_finite():
        return ParsedPrice(None)
    flags = ("price_range_lower_bound",) if _RANGE_AFTER.match(normalized[match.end() :]) else ()
    return ParsedPrice(value=value, flags=flags, currency="INR")


def parse_rating(text: str | None) -> Decimal | None:
    """Return the first valid five-point rating without confusing review counts."""
    if not text:
        return None
    match = _RATING.search(text.replace("\u00a0", " "))
    if not match:
        return None
    try:
        rating = Decimal(match.group(1))
    except InvalidOperation:
        return None
    return rating if Decimal("0") <= rating <= Decimal("5") else None


def to_base_quantity(value: Decimal | int | float | str, unit: str) -> tuple[Decimal, str]:
    """Convert supported pack sizes to ml, g, or pieces for unit-price analysis."""
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0:
        raise ValueError("pack size must be a positive finite number")
    normalized_unit = unit.strip().lower().rstrip(".")
    conversions = {
        "ml": (Decimal("1"), "ml"),
        "l": (Decimal("1000"), "ml"),
        "g": (Decimal("1"), "g"),
        "gm": (Decimal("1"), "g"),
        "kg": (Decimal("1000"), "g"),
        "mg": (Decimal("0.001"), "g"),
        "pc": (Decimal("1"), "pcs"),
        "pcs": (Decimal("1"), "pcs"),
        "piece": (Decimal("1"), "pcs"),
        "pieces": (Decimal("1"), "pcs"),
    }
    try:
        multiplier, base_unit = conversions[normalized_unit]
    except KeyError as exc:
        raise ValueError(f"unsupported pack-size unit: {unit!r}") from exc
    return amount * multiplier, base_unit
