"""Shared product extractor contract for ordered, testable parsing strategies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ExtractedProduct:
    """Fields needed by identity checks and price validation, kept in memory only."""

    title: str
    mrp: Decimal | None
    price: Decimal | None
    rating: Decimal | None
    currency: str | None
    strategy: str = "jsonld"
    availability: bool | None = None
    pack_size_value: Decimal | None = None
    pack_size_unit: str | None = None
    strategy_by_field: Mapping[str, str] = field(default_factory=dict)


class ProductExtractor(Protocol):
    """Minimal interface every source extractor implements."""

    def extract(self, html: str) -> ExtractedProduct:
        """Extract the displayed product identity and prices from one saved page."""
