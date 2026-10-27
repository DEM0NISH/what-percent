"""Optional local raw-page checks; raw HTML is user-supplied and gitignored."""

from pathlib import Path

import pytest

from whatpercent.extractors import extract_mamaearth_product

RAW_DIR = Path(__file__).parent / "fixtures" / "raw"
PRODUCT_SLUGS = (
    "ubtan-natural-glow-face-wash-with-turmeric-saffron-for-tan-removal-200-ml",
    "aloe-vera-face-wash-with-aloe-vera-ashwagandha-for-a-youthful-glow-100-ml",
    "tea-tree-face-wash-charcoal-face-wash",
    "ubtan-foaming-face-wash-with-turmeric-saffron-for-tan-removal-150ml",
    "vitamin-c-daily-glow-sunscreen-with-vitamin-c-turmeric-for-sun-protection-glow-125-g",
    "skin-illuminate-sunscreen-gel-spf-50-with-vitamin-c-turmeric-for-uva-b-protection-50-g",
    "rice-night-cream-with-rice-water-niacinamide-for-glass-skin-50-g",
    "rosemary-hair-growth-oil-150ml",
    "onion-hair-oil-for-hair-regrowth-hair-fall-control-with-redensyl-150ml",
    "lemon-anti-dandruff-shampoo-with-lemon-ginger-400-ml",
    "mamaearth-onion-shampoo-for-hair-growth-hair-fall-control-with-onion-oil-plant-keratin-250-ml",
    "mamaearth-onion-conditioner-for-hair-growth-hair-fall-control-with-onion-coconut-250ml",
    "onion-hair-serum-with-onion-biotin-for-strong-frizz-free-hair-100-ml",
    "charcoal-face-scrub-for-oily-skin-normal-skin-with-charcoal-walnut-for-deep-exfoliation-100g",
    "vitamin-c-daily-glow-face-pack-with-vitamin-c-turmeric-for-illuminating-skin-200-g",
)


def test_user_supplied_raw_fixtures_parse_when_present() -> None:
    existing = [
        RAW_DIR / f"{slug}.html" for slug in PRODUCT_SLUGS if (RAW_DIR / f"{slug}.html").is_file()
    ]
    if not existing:
        pytest.skip("raw browser-saved fixtures are not present in this checkout")
    for path in existing:
        result = extract_mamaearth_product(path.read_text(encoding="utf-8"))
        assert result.title, f"missing title in {path.name}"
