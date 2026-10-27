# Product fixture status

The saved product pages supplied by the owner are in the ignored `tests/fixtures/raw/` directory. Catalog entries use the product's own JSON-LD offer and identity details from those saved pages. No live requests were made to recover these fixtures.

## Active catalog

Ten products are configured in `products.yaml`. Each was listed in stock in the saved page and had a product-specific current price and strikethrough MRP. The offline collector parsed all 10 with no rejected or blocked rows.

- Aloe Vera Face Wash, 100 ml
- Charcoal Face Wash, 100 ml — used as the replacement for the unavailable Tea Tree/Charcoal candidate; URL is `/products/best-charcoal-face-wash`.
- Lemon Anti-Dandruff Shampoo, 400 ml
- Onion Conditioner, 250 ml
- Onion Shampoo, 250 ml
- Onion Hair Oil with Redensyl, 150 ml
- Rosemary Hair Growth Oil, 150 ml
- Skin Illuminate Sunscreen, 50 g
- Ubtan Foaming Face Wash, 150 ml
- Mineral Based Sunscreen, 50 ml

The Mineral Based Sunscreen page is titled “Mamaearth Baby Sunscreen for UV Rays Protection -50ml,” while its Product JSON-LD confirms the requested URL and product name “Mineral Based Sunscreen 50ml.” Its offer lists ₹150 MRP and ₹129 current price.

## Excluded supplied pages

- Rice Night Cream: the saved offer reports `OutOfStock`.
- Charcoal Face Scrub, Onion Hair Serum, Ubtan Natural Glow Face Wash, Vitamin C Face Pack, Vitamin C Daily Glow Sunscreen: the saved product-specific offer did not contain both its own MRP and current price. Nearby recommended-product prices were not treated as that product's MRP.

The held Tea Tree/Charcoal page was not present. Catalog identity tokens are recorded in `products.yaml` and passed the offline collector's identity checks. The catalog is ready for the documented live approval gates; no live collection has run.
