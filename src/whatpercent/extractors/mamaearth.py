"""Mamaearth field fallbacks grounded in the saved serum product markup."""

from __future__ import annotations

import re
from decimal import Decimal

from bs4 import BeautifulSoup

from whatpercent.extractors.base import ExtractedProduct
from whatpercent.extractors.jsonld import extract_jsonld_product
from whatpercent.parsing import parse_price

TITLE_SELECTORS = (
    "h1.hdt-product__title",
    "div.hdt-product-info__item.hdt-product__title h1",
)
PRICE_SELECTORS = (
    ".hdt-price__sale hdt-price .hdt-money",
    ".hdt-price__container hdt-price .hdt-money",
)
MRP_SELECTORS = (
    ".hdt-price__sale hdt-compare-at-price .hdt-money",
    ".hdt-price__container hdt-compare-at-price .hdt-money",
)
_SALE_TEXT = re.compile(r"(?i)sale\s+price\s*(?:₹|INR|Rs\.?\s*)\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?")
_MRP_TEXT = re.compile(
    r"(?i)(?:M\.?R\.?P\.?|regular\s+price)\s*(?:₹|INR|Rs\.?\s*)\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?"
)
_PACK_SIZE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(ml|l|kg|gm|g|mg|pcs?)\b", re.I)


def _text_for_selector(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    value = node.get_text(" ", strip=True) if node else ""
    return value or None


def _price_from_selectors(
    soup: BeautifulSoup, selectors: tuple[str, ...]
) -> tuple[Decimal | None, str]:
    for index, selector in enumerate(selectors, start=1):
        text = _text_for_selector(soup, selector)
        parsed = parse_price(text)
        if parsed.value is not None:
            return parsed.value, f"css{index}"
    return None, "missing"


def _regex_price(region_text: str, pattern: re.Pattern[str]) -> Decimal | None:
    match = pattern.search(region_text)
    return parse_price(match.group(0)).value if match else None


def extract_mamaearth_product(html: str) -> ExtractedProduct:
    """Extract per field JSON-LD → verified CSS → scoped product-info regex values."""
    soup = BeautifulSoup(html, "lxml")
    try:
        structured = extract_jsonld_product(html)
    except ValueError:
        structured = ExtractedProduct("", None, None, None, None)

    strategies: dict[str, str] = {}
    title = structured.title
    if title:
        strategies["title"] = "jsonld"
    else:
        title = None
        for index, selector in enumerate(TITLE_SELECTORS, start=1):
            title = _text_for_selector(soup, selector)
            if title:
                strategies["title"] = f"css{index}"
                break
    if not title:
        title = ""
        strategies["title"] = "missing"

    price = structured.price
    strategies["price"] = "jsonld" if price is not None else "missing"
    if price is None:
        price, strategies["price"] = _price_from_selectors(soup, PRICE_SELECTORS)

    mrp = structured.mrp
    strategies["mrp"] = "jsonld" if mrp is not None else "missing"
    if mrp is None:
        mrp, strategies["mrp"] = _price_from_selectors(soup, MRP_SELECTORS)

    region = soup.select_one(".hdt-product-info__list")
    region_text = region.get_text(" ", strip=True) if region else ""
    if price is None and region_text:
        price = _regex_price(region_text, _SALE_TEXT)
        strategies["price"] = "regex" if price is not None else "missing"
    if mrp is None and region_text:
        mrp = _regex_price(region_text, _MRP_TEXT)
        strategies["mrp"] = "regex" if mrp is not None else "missing"

    pack_match = _PACK_SIZE.search(title)
    pack_value = Decimal(pack_match.group(1)) if pack_match else None
    pack_unit = pack_match.group(2).lower() if pack_match else None
    strategies.update(
        {
            "rating": "jsonld" if structured.rating is not None else "missing",
            "availability": "jsonld" if structured.availability is not None else "missing",
            "pack_size": "title" if pack_value is not None else "missing",
        }
    )
    fallback_strategies = {
        value for value in strategies.values() if value.startswith(("css", "regex"))
    }
    if not fallback_strategies:
        strategy = "jsonld"
    else:
        strategy = ";".join(f"{field}={value}" for field, value in strategies.items())
    return ExtractedProduct(
        title=title,
        mrp=mrp,
        price=price,
        rating=structured.rating,
        currency=structured.currency or ("INR" if price is not None or mrp is not None else None),
        strategy=strategy,
        availability=structured.availability,
        pack_size_value=pack_value,
        pack_size_unit=pack_unit,
        strategy_by_field=strategies,
    )
