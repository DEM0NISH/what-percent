"""Offline extractor tests use an explicitly synthetic, hand-written HTML fixture."""

from decimal import Decimal
from pathlib import Path

import pytest

from whatpercent.extractors import (
    ExtractionError,
    JsonLdProductExtractor,
    extract_jsonld_product,
)

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_product_jsonld.html"


def test_jsonld_product_reads_synthetic_fixture() -> None:
    extracted = extract_jsonld_product(FIXTURE.read_text(encoding="utf-8"))
    assert extracted.title == "Synthetic Vitamin C Daily Glow Serum 30 ml"
    assert extracted.price == Decimal("374")
    assert extracted.mrp == Decimal("499")
    assert extracted.rating == Decimal("4.6")
    assert extracted.currency == "INR"
    assert extracted.strategy == "jsonld"


def test_jsonld_extractor_implements_the_shared_interface() -> None:
    extracted = JsonLdProductExtractor().extract(FIXTURE.read_text(encoding="utf-8"))
    assert extracted.title.startswith("Synthetic ")


def test_jsonld_does_not_guess_mrp_from_regular_offer() -> None:
    html = """<script type="application/ld+json">
    {"@type":"Product","name":"Serum","offers":{"@type":"Offer",
    "priceCurrency":"INR","price":"200"}}</script>"""
    extracted = extract_jsonld_product(html)
    assert extracted.price == Decimal("200")
    assert extracted.mrp is None


def test_jsonld_without_product_offer_is_rejected() -> None:
    with pytest.raises(ExtractionError):
        extract_jsonld_product(
            '<script type="application/ld+json">{"@type":"Organization"}</script>'
        )
