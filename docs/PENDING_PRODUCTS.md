# Pending products and fixture gaps

The v3 browser-verified product URLs are not configured until their saved raw HTML is present and parsed. `tests/fixtures/raw/` was absent when this continuation ran, so no product title, pack size, stock status, MRP, or price has been inferred from URL slugs.

## On hold

- **Face wash:** `tea-tree-face-wash-charcoal-face-wash` — fixture is missing. The title, whether this is one product or multiple variants, and the pack size are unknown. Include it only if the fixture confirms one product with one pack size.

## Missing raw fixtures

All 15 requested `<slug>.html` files were missing from `tests/fixtures/raw/`:

- `ubtan-natural-glow-face-wash-with-turmeric-saffron-for-tan-removal-200-ml.html`
- `aloe-vera-face-wash-with-aloe-vera-ashwagandha-for-a-youthful-glow-100-ml.html`
- `tea-tree-face-wash-charcoal-face-wash.html` (on hold)
- `ubtan-foaming-face-wash-with-turmeric-saffron-for-tan-removal-150ml.html`
- `vitamin-c-daily-glow-sunscreen-with-vitamin-c-turmeric-for-sun-protection-glow-125-g.html`
- `skin-illuminate-sunscreen-gel-spf-50-with-vitamin-c-turmeric-for-uva-b-protection-50-g.html`
- `rice-night-cream-with-rice-water-niacinamide-for-glass-skin-50-g.html`
- `rosemary-hair-growth-oil-150ml.html`
- `onion-hair-oil-for-hair-regrowth-hair-fall-control-with-redensyl-150ml.html`
- `lemon-anti-dandruff-shampoo-with-lemon-ginger-400-ml.html`
- `mamaearth-onion-shampoo-for-hair-growth-hair-fall-control-with-onion-oil-plant-keratin-250-ml.html`
- `mamaearth-onion-conditioner-for-hair-growth-hair-fall-control-with-onion-coconut-250ml.html`
- `onion-hair-serum-with-onion-biotin-for-strong-frizz-free-hair-100-ml.html`
- `charcoal-face-scrub-for-oily-skin-normal-skin-with-charcoal-walnut-for-deep-exfoliation-100g.html`
- `vitamin-c-daily-glow-face-pack-with-vitamin-c-turmeric-for-illuminating-skin-200-g.html`

The earlier Vitamin C Daily Glow serum fixture is retained only as an extra extractor test fixture; it is not a catalog item.
