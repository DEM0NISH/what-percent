# What% — What % of the sale is real?

[![CI](https://github.com/DEM0NISH/what-percent/actions/workflows/ci.yml/badge.svg)](https://github.com/DEM0NISH/what-percent/actions/workflows/ci.yml)

A self-monitoring price tracker for one approved brand site. It validates product identity, pack size, price and MRP, then describes gap-flagged discount patterns. A gap flag does not establish intent.

## Current result

A one-time offline snapshot from user-supplied Mamaearth HTML contains 10 in-stock product pages with product-specific current price and MRP. The advertised discount averages 14.9%, with a 14.0% median and a 10.0–20.0% range. The offline collector parsed all 10 pages with healthy field fill. This does not establish price history or whether any sale is genuine. See [reports/initial_snapshot.md](reports/initial_snapshot.md).

## What it does

The two goals are data quality (product identity, pack size, price and MRP validation) and pipeline reliability (fallback tracking, layout fingerprints, per-site health and recoverable storage).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): fetch → extract → validate → fingerprint → health → private CSV store → rebuildable SQLite cache → analyze.

## Quick start

Create `.env` from `.env.example` and set the honest User-Agent values. The 10-product catalog is fixture-verified. Live collection remains subject to the documented go-live gates. For local development:

```powershell
python -m pip install -e . -r requirements-dev.txt
ruff check .
pytest -q -m "not live"
```

The `@pytest.mark.live` smoke test is excluded from CI and must not run without explicit authorization.

## Storage and scheduling

Monthly CSV observations, run health, spot-checks and fingerprints belong in a separate private data repository. SQLite is derived and never committed. Raw HTML, personal data and unnecessary page content are not published. The public repository contains code, tests, documentation and aggregated reports only. See [docs/SCHEDULING.md](docs/SCHEDULING.md); the daily schedule remains disabled until the owner enables it.

## Fixture recovery

The browser-saved pages have been recovered into the gitignored `tests/fixtures/raw/` directory. Ten entries are active in the catalog; pages that were out of stock or lacked a product-specific MRP were excluded. See [docs/PENDING_PRODUCTS.md](docs/PENDING_PRODUCTS.md).

## Responsible scraping

Source approval and the owner's risk note are recorded in [SOURCES.md](SOURCES.md). The fetcher uses an identifying User-Agent, observes robots rules and polite delays, and does not bypass access controls. The live go-live gates have not been run.

## Limitations and future work

The current sample is 10 products from one brand site and one saved snapshot. It is not representative of the market and cannot support historical sale claims. Real collection, sale-window dates, and spot-check accuracy remain pending. The private data repository and owner-authorized live gates are required before scheduled collection.
