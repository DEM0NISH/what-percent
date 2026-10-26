"""Offline-capable collection orchestration for approved product URLs."""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from whatpercent.config import ConfigurationError, load_settings
from whatpercent.extractors import ExtractionError, extract_jsonld_product
from whatpercent.fetcher import PoliteFetcher
from whatpercent.parsing import to_base_quantity
from whatpercent.storage import append_observations, append_run, load_observations
from whatpercent.validation import validate_observation

LOGGER = logging.getLogger(__name__)
KNOWN_SITE_HOSTS = {"mamaearth": "mamaearth.in"}


def load_products(config_path: Path | str) -> list[dict[str, Any]]:
    """Load and validate product identities without creating a products file."""
    path = Path(config_path)
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Product config not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("products"), list):
        raise ConfigurationError("Config must contain a products list.")
    products: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, product in enumerate(document["products"], start=1):
        if not isinstance(product, dict):
            raise ConfigurationError(f"products[{index}] must be a mapping.")
        product_id = str(product.get("id", "")).strip()
        if not product_id or product_id in seen_ids:
            raise ConfigurationError(f"products[{index}] has a missing or duplicate id.")
        seen_ids.add(product_id)
        for field in ("brand", "variant", "category"):
            if not str(product.get(field, "")).strip():
                raise ConfigurationError(f"products[{index}] requires {field}.")
        try:
            size = Decimal(str(product["pack_size_value"]))
            unit = str(product["pack_size_unit"])
            to_base_quantity(size, unit)
        except (KeyError, ValueError, ArithmeticError) as exc:
            raise ConfigurationError(f"products[{index}] has an invalid pack size.") from exc
        tokens = product.get("expected_tokens")
        if (
            not isinstance(tokens, list)
            or not tokens
            or any(not isinstance(token, str) for token in tokens)
        ):
            raise ConfigurationError(
                f"products[{index}] expected_tokens must be a non-empty string list."
            )
        urls = product.get("urls")
        if not isinstance(urls, dict) or not urls:
            raise ConfigurationError(f"products[{index}] requires at least one approved site URL.")
        for site, url in urls.items():
            if site not in KNOWN_SITE_HOSTS:
                raise ConfigurationError(f"Unknown or unapproved site key: {site!r}.")
            if not isinstance(url, str) or urlsplit(url).hostname != KNOWN_SITE_HOSTS[site]:
                raise ConfigurationError(f"URL for {site!r} must use {KNOWN_SITE_HOSTS[site]}.")
        products.append(product)
    return products


def collect_products(
    *,
    config_path: Path | str = "products.yaml",
    limit: int | None = None,
    site: str | None = None,
    offline_dir: Path | str | None = None,
    force: bool = False,
    fetcher: PoliteFetcher | None = None,
) -> dict[str, dict[str, int]]:
    """Fetch, extract, validate, and append configured product observations."""
    products = load_products(config_path)
    if site is not None:
        if site not in KNOWN_SITE_HOSTS:
            raise ConfigurationError(f"Unknown or unapproved site key: {site!r}.")
        products = [product for product in products if site in product["urls"]]
    if limit is not None:
        if limit < 1:
            raise ConfigurationError("--limit must be a positive integer.")
        products = products[:limit]
    settings = load_settings()
    client = fetcher or PoliteFetcher(settings.user_agent, offline_dir=offline_dir)
    history = load_observations(settings.data_dir)
    latest_good: dict[tuple[str, str], Decimal] = {}
    for row in history.to_dict(orient="records"):
        if row.get("status") in {"ok", "fallback_ok"} and row.get("price"):
            try:
                latest_good[(str(row["product_id"]), str(row["site"]))] = Decimal(str(row["price"]))
            except Exception:
                continue

    started_at = datetime.now(UTC)
    observed_at = started_at.isoformat(timespec="seconds")
    date_utc = started_at.date().isoformat()
    already_collected = {
        (str(row["product_id"]), str(row["site"]))
        for row in history.to_dict(orient="records")
        if row.get("date_utc") == date_utc and row.get("status") in {"ok", "fallback_ok"}
    }
    observations: list[dict[str, object]] = []
    site_stats: dict[str, Counter[str]] = {}
    for product in products:
        for site_key, url in product["urls"].items():
            counts = site_stats.setdefault(site_key, Counter())
            if not force and (str(product["id"]), site_key) in already_collected:
                counts["idempotent_skipped"] += 1
                continue
            result = client.fetch(url)
            common = {
                "date_utc": date_utc,
                "observed_at": observed_at,
                "product_id": product["id"],
                "site": site_key,
                "price": "",
                "mrp": "",
                "flags": "",
                "strategy": "",
            }
            if result.html is None:
                reason = result.skipped_reason or "fetch_error"
                status = (
                    "skipped_robots"
                    if reason == "robots_disallowed"
                    else (
                        "blocked"
                        if result.status in {403, 429} or reason == "host_stopped_after_429"
                        else "fetch_error"
                    )
                )
                observations.append({**common, "status": status, "flags": reason})
                counts[status] += 1
                continue
            try:
                extracted = extract_jsonld_product(result.html)
            except ExtractionError:
                observations.append({**common, "status": "rejected", "flags": "parse_failed"})
                counts["rejected"] += 1
                continue
            validation = validate_observation(
                price=extracted.price,
                mrp=extracted.mrp,
                currency=extracted.currency,
                title=extracted.title,
                expected_tokens=product["expected_tokens"],
                last_good_price=latest_good.get((str(product["id"]), site_key)),
            )
            status = validation.status
            observations.append(
                {
                    **common,
                    "price": str(extracted.price) if extracted.price is not None else "",
                    "mrp": str(extracted.mrp) if extracted.mrp is not None else "",
                    "status": status,
                    "flags": ";".join(validation.flags),
                    "strategy": extracted.strategy,
                }
            )
            counts[status] += 1

    added, skipped, _ = append_observations(settings.data_dir, observations, force=force)
    for site_key, counts in site_stats.items():
        site_rows = [row for row in observations if row["site"] == site_key]
        row_count = len(site_rows)
        price_fill = sum(bool(row["price"]) for row in site_rows) / row_count if row_count else 0.0
        mrp_fill = sum(bool(row["mrp"]) for row in site_rows) / row_count if row_count else 0.0
        valid = counts["ok"] + counts["fallback_ok"]
        append_run(
            settings.data_dir,
            {
                "run_id": str(uuid.uuid4()),
                "started_at": observed_at,
                "site": site_key,
                "rows": row_count,
                "ok": counts["ok"],
                "fallback_ok": counts["fallback_ok"],
                "rejected": counts["rejected"],
                "blocked": counts["blocked"],
                "price_fill": f"{price_fill:.4f}",
                "mrp_fill": f"{mrp_fill:.4f}",
                "validity_rate": f"{valid / row_count:.4f}" if row_count else "0.0000",
                "drift_similarity": "",
                "suspect": "",
            },
        )
        LOGGER.info(
            "%s collected=%d fallback=%d rejected=%d blocked=%d skipped=%d",
            site_key,
            counts["ok"],
            counts["fallback_ok"],
            counts["rejected"],
            counts["blocked"],
            counts["skipped_robots"] + counts["fetch_error"] + counts["idempotent_skipped"],
        )
    LOGGER.info("CSV rows added=%d idempotent skips=%d", added, skipped)
    return {key: dict(counts) for key, counts in site_stats.items()}
