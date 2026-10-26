"""Shared product extractor contract for ordered, testable parsing strategies."""

from __future__ import annotations

from dataclasses import dataclass
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


class ProductExtractor(Protocol):
    """Minimal interface every source extractor implements."""

    def extract(self, html: str) -> ExtractedProduct:
        """Extract the displayed product identity and prices from one saved page."""
