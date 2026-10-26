# What% — What % of the sale is real?

A self-monitoring scraper with validated fallbacks for collecting public product prices and analysing price history. It tracks both data quality and pipeline reliability. Source review and product configuration will be added after approval at the project checkpoints.

## Development

```powershell
python -m whatpercent --help
ruff check .
pytest -q
```

## Collection and local storage

The current `products.yaml` is provisional: its URLs and sizes came from a cached sitemap, and live titles, availability, and prices are not verified. Live collection is blocked for this catalog until those identities are checked against real saved pages. Use `--offline-dir` to exercise the pipeline with URL-hashed saved HTML fixtures and no network access:

```powershell
python -m whatpercent collect --config products.yaml --offline-dir tests/fixtures
python -m whatpercent build-db
```

The CSV files are the durable store; `build-db` recreates the ignored SQLite cache. `--force` appends another same-day observation, while the default skips already successful product/site/date keys. The JSON-LD fixture in this repository is explicitly synthetic and tests parser behavior only; it is not evidence about Mamaearth's live page structure or prices.

## Docker

After creating `.env` from `.env.example` and after the approved `products.yaml` is available:

```powershell
docker compose build
docker compose run --rm collector collect --limit 3
```

Compose mounts `./data` as `/data` and mounts `products.yaml` read-only. Keep the local data directory private and out of the public repository.
