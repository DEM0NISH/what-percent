"""Offline extractor tests use an explicitly synthetic, hand-written HTML fixture."""

from decimal import Decimal
from pathlib import Path

import pytest

from whatpercent.extractors import (
    ExtractionError,
    JsonLdProductExtractor,
    extract_jsonld_product,
    extract_mamaearth_product,
)

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_product_jsonld.html"
REAL_FIXTURE = (
    Path(__file__).parent / "fixtures" / "trimmed" / "mamaearth_vitamin_c_daily_glow_serum.html"
)


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


def test_mamaearth_real_fixture_extracts_sale_and_strikethrough_prices() -> None:
    extracted = extract_jsonld_product(REAL_FIXTURE.read_text(encoding="utf-8"))
    assert extracted.title == (
        "Vitamin C Daily Glow Face Serum With Vitamin C & Turmeric for Radiant Skin - 30 ml"
    )
    assert extracted.price == Decimal("374.0")
    assert extracted.mrp == Decimal("499.0")
    assert extracted.rating == Decimal("4.83")
    assert extracted.currency == "INR"


def test_real_fixture_has_pack_size_stock_and_field_strategy_provenance() -> None:
    extracted = extract_mamaearth_product(REAL_FIXTURE.read_text(encoding="utf-8"))
    assert extracted.pack_size_value == Decimal("30")
    assert extracted.pack_size_unit == "ml"
    assert extracted.availability is True
    assert extracted.strategy_by_field["price"] == "jsonld"
    assert extracted.strategy_by_field["mrp"] == "jsonld"


def test_simulated_layout_change_uses_saved_page_alternate_css() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(REAL_FIXTURE.read_text(encoding="utf-8"), "lxml")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        script.decompose()
    for node in soup.select(".hdt-price__sale"):
        node.attrs["class"] = [name for name in node.get("class", []) if name != "hdt-price__sale"]
    extracted = extract_mamaearth_product(str(soup))
    assert extracted.title.startswith("Vitamin C Daily Glow")
    assert extracted.price == Decimal("374")
    assert extracted.mrp == Decimal("499")
    assert extracted.strategy_by_field["price"] == "css2"
    assert extracted.strategy_by_field["mrp"] == "css2"


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
