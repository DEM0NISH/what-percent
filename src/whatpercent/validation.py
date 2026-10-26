"""Validation rules applied before observations are stored or analysed."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from whatpercent.identity import title_matches


@dataclass(frozen=True)
class ValidationResult:
    """Validation outcome with stable short flags for storage and reports."""

    status: str
    flags: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """Whether this observation may enter price analysis."""
        return self.status in {"ok", "fallback_ok"}


def _decimal(value: Decimal | int | float | str | None) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _is_inr(currency: str | None) -> bool:
    if not currency:
        return False
    return currency.strip().upper().replace(".", "") in {"INR", "₹", "RS"}


def validate_observation(
    *,
    price: Decimal | int | float | str | None,
    mrp: Decimal | int | float | str | None,
    currency: str | None,
    title: str,
    expected_tokens: Sequence[str],
    last_good_price: Decimal | int | float | str | None = None,
    jump_threshold_pct: Decimal | int | float | str = "70",
) -> ValidationResult:
    """Reject unusable or misidentified prices and flag large day-over-day jumps."""
    flags: list[str] = []
    parsed_price = _decimal(price)
    if parsed_price is None or parsed_price <= 0:
        return ValidationResult("rejected", ("invalid_price",))
    if not _is_inr(currency):
        return ValidationResult("rejected", ("currency_unrecognized",))
    parsed_mrp = _decimal(mrp)
    if mrp is not None and (parsed_mrp is None or parsed_mrp <= 0):
        return ValidationResult("rejected", ("invalid_mrp",))
    if parsed_mrp is not None and parsed_price > parsed_mrp:
        return ValidationResult("rejected", ("price_gt_mrp",))
    try:
        matches = title_matches(title, expected_tokens)
    except ValueError:
        return ValidationResult("rejected", ("invalid_identity_tokens",))
    if not matches:
        return ValidationResult("rejected", ("title_mismatch",))
    previous = _decimal(last_good_price)
    threshold = _decimal(jump_threshold_pct)
    if previous is not None and previous > 0 and threshold is not None and threshold >= 0:
        change_pct = abs(parsed_price - previous) / previous * Decimal("100")
        if change_pct > threshold:
            flags.append("jump70")
    return ValidationResult("ok", tuple(flags))
