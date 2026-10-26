"""Conservative schema.org Product JSON-LD extraction."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup

from whatpercent.extractors.base import ExtractedProduct
from whatpercent.parsing import parse_price, parse_rating


class ExtractionError(ValueError):
    """Raised when a saved page contains no usable Product JSON-LD record."""


class JsonLdProductExtractor:
    """Concrete default extractor implementing the shared extractor interface."""

    def extract(self, html: str) -> ExtractedProduct:
        """Use structured product metadata without depending on unverified selectors."""
        return extract_jsonld_product(html)


def _walk_products(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _walk_products(item)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(item).lower().endswith("product") for item in types):
            yield value
        for key, item in value.items():
            if key in {"@graph", "mainEntity", "itemListElement"}:
                yield from _walk_products(item)


def _decimal_price(value: Any, currency: str | None) -> Decimal | None:
    if value is None or not currency:
        return None
    parsed = parse_price(f"{currency} {value}")
    return parsed.value


def _offers(product: dict[str, Any]) -> list[dict[str, Any]]:
    offers = product.get("offers", [])
    if isinstance(offers, dict):
        offers = [offers]
    return [offer for offer in offers if isinstance(offer, dict)]


def _price_specifications(offer: dict[str, Any]) -> list[dict[str, Any]]:
    specifications = offer.get("priceSpecification", [])
    if isinstance(specifications, dict):
        specifications = [specifications]
    if not isinstance(specifications, list):
        return []
    return [item for item in specifications if isinstance(item, dict)]


def _price_marker(specification: dict[str, Any]) -> str:
    return " ".join(
        str(specification.get(key, "")) for key in ("priceType", "name", "description")
    ).lower()


def _offer_currency(offer: dict[str, Any]) -> str | None:
    currency = offer.get("priceCurrency")
    if currency:
        return str(currency).strip().upper()
    for specification in _price_specifications(offer):
        currency = specification.get("priceCurrency")
        if currency:
            return str(currency).strip().upper()
    return None


def _selling_price_from_offer(offer: dict[str, Any], currency: str | None) -> Decimal | None:
    if offer.get("price") is not None:
        return _decimal_price(offer["price"], currency)
    specifications = _price_specifications(offer)
    preferred = [
        item
        for item in specifications
        if any(term in _price_marker(item) for term in ("sale", "offer price"))
    ]
    other = [
        item
        for item in specifications
        if not any(
            term in _price_marker(item)
            for term in ("listprice", "list price", "mrp", "strikethrough")
        )
        and item not in preferred
    ]
    for specification in preferred + other:
        price = _decimal_price(
            specification.get("price"),
            specification.get("priceCurrency", currency),
        )
        if price is not None:
            return price
    return None


def _mrp_from_offer(offer: dict[str, Any], currency: str | None) -> Decimal | None:
    for specification in _price_specifications(offer):
        marker = _price_marker(specification)
        if any(label in marker for label in ("listprice", "list price", "mrp", "strikethrough")):
            value = specification.get("price", specification.get("maxPrice"))
            return _decimal_price(value, specification.get("priceCurrency", currency))
    return None


def extract_jsonld_product(html: str) -> ExtractedProduct:
    """Return the first named Product with a priced INR offer, without guessing MRP."""
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for product in _walk_products(parsed):
            title = product.get("name")
            if not isinstance(title, str) or not title.strip():
                continue
            aggregate = product.get("aggregateRating") or {}
            rating_value = aggregate.get("ratingValue") if isinstance(aggregate, dict) else None
            rating = parse_rating(str(rating_value)) if rating_value is not None else None
            for offer in _offers(product):
                currency = _offer_currency(offer)
                price = _selling_price_from_offer(offer, currency)
                if price is None:
                    continue
                mrp = _mrp_from_offer(offer, currency)
                return ExtractedProduct(
                    title=title.strip(),
                    mrp=mrp,
                    price=price,
                    rating=rating,
                    currency=currency,
                    strategy="jsonld",
                )
    raise ExtractionError("no named Product with a parseable JSON-LD offer")
