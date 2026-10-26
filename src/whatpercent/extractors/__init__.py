"""Shared and source-specific product extraction strategies."""

from whatpercent.extractors.base import ExtractedProduct, ProductExtractor
from whatpercent.extractors.jsonld import (
    ExtractionError,
    JsonLdProductExtractor,
    extract_jsonld_product,
)

__all__ = [
    "ExtractedProduct",
    "ExtractionError",
    "JsonLdProductExtractor",
    "ProductExtractor",
    "extract_jsonld_product",
]
