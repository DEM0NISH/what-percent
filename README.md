# What% — What % of the sale is real?

[![CI](https://github.com/DEM0NISH/what-percent/actions/workflows/ci.yml/badge.svg)](https://github.com/DEM0NISH/what-percent/actions/workflows/ci.yml)

A self-monitoring scraper with validated fallbacks for product price history. The project checks data quality and pipeline reliability, then describes gap-flagged discount patterns. It does not establish intent.

## Findings

Real-data findings are pending. The 15 browser-saved raw product fixtures are not present in this checkout, the catalog is closed pending those fixtures, and no real collection dataset exists. Synthetic tests are not reported as real findings.

## What it does

The two goals are data quality (product identity, pack size, price and MRP validation) and pipeline reliability (fallback tracking, layout fingerprints, per-site health and recoverable storage).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): fetch → extract → validate → fingerprint → health → private CSV store → rebuildable SQLite cache → analyze.

## Quick start

Create `.env` from `.env.example` and set the honest User-Agent values. Collection is blocked while `products.yaml` has no fixture-verified catalog. To check the packaged CLI without collecting:

```powershell
python -m whatpercent --help
docker build -t what-percent .
docker run --rm what-percent --help
```

Use a venv for local development. Install the project with `python -m pip install -e . -r requirements-dev.txt`, then run `ruff check .` and `pytest -q -m "not live"`. The `@pytest.mark.live` smoke test is excluded from CI and must not run without explicit authorization.

## Storage and scheduling

Monthly CSV observations, run health, spot-checks and fingerprints belong in a separate private data repository. SQLite is derived and never committed. Raw HTML, personal data and unnecessary page content are not published. The public repository contains code, tests, documentation and aggregated reports only. See [docs/SCHEDULING.md](docs/SCHEDULING.md); the daily schedule remains commented out until the owner enables it.

## What broke

The expected raw-fixture directory is missing from this checkout. Its cause is unknown; no live scraping block is implied. See [BREAKAGES.md](BREAKAGES.md) for the observed recovery issue.

## Responsible scraping

Source approval and the owner's risk note are recorded in [SOURCES.md](SOURCES.md). The fetcher uses an identifying User-Agent, observes robots rules and polite delays, and does not bypass access controls. Go-live gates are documented but have not been run.

## Limitations and future work

The intended sample is one brand site and 15 products with daily snapshots, so it is not representative of the market. Real findings, sale-window dates, and spot-check accuracy remain pending genuine data and owner decisions. Future work depends on recovering the saved fixtures, confirming the catalog tokens, and passing the go-live gates.
