"""Offline-capable collection orchestration for approved product URLs."""

from __future__ import annotations

import logging
import os
import re
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from bs4 import BeautifulSoup

from whatpercent.config import ConfigurationError, load_settings
from whatpercent.extractors import extract_mamaearth_product
from whatpercent.fetcher import PoliteFetcher
from whatpercent.fingerprint import (
    jaccard_similarity,
    load_skeletons,
    product_info_skeleton,
    save_skeletons,
)
from whatpercent.health import evaluate_run, evaluate_site
from whatpercent.identity import validate_expected_tokens
from whatpercent.parsing import to_base_quantity
from whatpercent.storage import (
    append_observations,
    append_run,
    load_observations,
    load_run_rows,
)
from whatpercent.validation import (
    ValidationResult,
    validate_fallback_observation,
    validate_observation,
)

LOGGER = logging.getLogger(__name__)
KNOWN_SITE_HOSTS = {"mamaearth": "mamaearth.in"}
DEBUG_LIMIT_PER_RUN = 5
DEBUG_KEEP_COUNT = 20
DEBUG_MAX_BYTES = 30_000


class CollectionSummary(dict[str, dict[str, int]]):
    """Per-site counts with the run-level health decision for the CLI."""

    def __init__(self, *args: Any, suspect: bool = False, report: str = "", **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.suspect = suspect
        self.report = report


def save_debug_snippet(
    html: str,
    data_dir: Path | str,
    *,
    run_id: str,
    product_id: str,
) -> Path | None:
    """Keep only a small product-info region when a fallback result is rejected."""
    directory = Path(data_dir) / "debug"
    run_prefix = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)
    product_key = re.sub(r"[^a-zA-Z0-9_-]", "_", product_id)
    if len(list(directory.glob(f"{run_prefix}-*.html"))) >= DEBUG_LIMIT_PER_RUN:
        return None
    soup = BeautifulSoup(html, "lxml")
    region = soup.select_one(".hdt-product-info__list")
    snippet = str(region) if region else ""
    if not snippet:
        scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        product_script = next(
            (script for script in scripts if '"@type": "Product"' in script.get_text()),
            None,
        )
        snippet = str(product_script) if product_script else ""
    if not snippet:
        return None
    encoded = snippet.encode("utf-8")[:DEBUG_MAX_BYTES]
    snippet = encoded.decode("utf-8", errors="ignore")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{run_prefix}-{product_key}.html"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".debug-", suffix=".tmp", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(snippet)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    entries = sorted(directory.glob("*.html"), key=lambda item: item.stat().st_mtime)
    for old_entry in entries[:-DEBUG_KEEP_COUNT]:
        old_entry.unlink()
    return target


def load_products(config_path: Path | str) -> list[dict[str, Any]]:
    """Load only fixture-verified product entries and report all catalog gate failures."""
    path = Path(config_path)
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Product config not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("products"), list):
        raise ConfigurationError("Config must contain a products list.")
    raw_products = document["products"]
    if not raw_products:
        raise ConfigurationError(
            "Catalog is empty; add fixture-verified products before collecting."
        )
    labels = [
        str(product.get("id", "")).strip() if isinstance(product, dict) else ""
        for product in raw_products
    ]
    frequencies = Counter(label for label in labels if label)
    gate_issues: dict[str, list[str]] = defaultdict(list)
    for index, product in enumerate(raw_products, start=1):
        label = labels[index - 1] or f"products[{index}]"
        if not isinstance(product, dict):
            gate_issues[label].append("entry must be a mapping")
            continue
        if not product.get("id"):
            gate_issues[label].append("missing id")
        if label in frequencies and frequencies[label] > 1:
            gate_issues[label].append("duplicate id")
        if product.get("verified") is not True:
            gate_issues[label].append("verified must be true")
        if not product.get("expected_tokens"):
            gate_issues[label].append("expected_tokens is missing")
        elif not isinstance(product.get("expected_tokens"), list) or any(
            not isinstance(token, str) for token in product["expected_tokens"]
        ):
            gate_issues[label].append("expected_tokens must be a string list")
        else:
            try:
                validate_expected_tokens(product["expected_tokens"])
            except ValueError as exc:
                gate_issues[label].append(f"invalid expected_tokens: {exc}")
        if not str(product.get("verified_at", "")).strip():
            gate_issues[label].append("verified_at is missing")
        if product.get("verified_by") != "manual-browser":
            gate_issues[label].append('verified_by must be "manual-browser"')
        if product.get("source") != "fixture":
            gate_issues[label].append('source must be "fixture"')
        observed = product.get("fixture_observed")
        if not isinstance(observed, dict) or not str(observed.get("date", "")).strip():
            gate_issues[label].append("fixture_observed requires its verification date")
        for field in ("brand", "variant", "category"):
            if not str(product.get(field, "")).strip():
                gate_issues[label].append(f"{field} is missing")
        try:
            size = Decimal(str(product["pack_size_value"]))
            to_base_quantity(size, str(product["pack_size_unit"]))
        except (KeyError, ValueError, ArithmeticError):
            gate_issues[label].append("pack size is missing or invalid")
        urls = product.get("urls")
        if not isinstance(urls, dict) or not urls:
            gate_issues[label].append("approved site URLs are missing")
        else:
            for site, url in urls.items():
                if site not in KNOWN_SITE_HOSTS or not isinstance(url, str):
                    gate_issues[label].append(f"invalid or unapproved site key {site!r}")
                elif urlsplit(url).hostname != KNOWN_SITE_HOSTS[site]:
                    gate_issues[label].append(f"URL for {site!r} must use {KNOWN_SITE_HOSTS[site]}")
    if gate_issues:
        details = "; ".join(
            f"{product_id}: {', '.join(dict.fromkeys(issues))}"
            for product_id, issues in gate_issues.items()
        )
        raise ConfigurationError(f"Catalog verification failed: {details}")

    products: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, product in enumerate(raw_products, start=1):
        product_id = str(product.get("id", "")).strip()
        if product_id in seen_ids:
            continue
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
    catalog_settings = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    policy = catalog_settings.get("settings", {})
    fallback_deviation = str(policy.get("fallback_max_deviation", 0.50))
    if offline_dir is not None:
        configured_data = settings.data_dir.resolve()
        repository_root = Path.cwd().resolve()
        protected_paths = [repository_root / "data", repository_root / "private-data"]
        if any(
            configured_data == protected.resolve() or protected.resolve() in configured_data.parents
            for protected in protected_paths
        ):
            raise ConfigurationError(
                "Offline collection requires a throwaway WHATPCT_DATA directory "
                "outside data/ and private-data/."
            )
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
    run_id = str(uuid.uuid4())
    observed_at = started_at.isoformat(timespec="seconds")
    date_utc = started_at.date().isoformat()
    already_collected = {
        (str(row["product_id"]), str(row["site"]))
        for row in history.to_dict(orient="records")
        if row.get("date_utc") == date_utc and row.get("status") in {"ok", "fallback_ok"}
    }
    observations: list[dict[str, object]] = []
    site_stats: dict[str, Counter[str]] = {}
    page_skeletons: dict[str, set[str]] = {}
    title_by_row: dict[tuple[str, str], str] = {}
    for product in products:
        for site_key, url in product["urls"].items():
            counts = site_stats.setdefault(site_key, Counter())
            if not force and (str(product["id"]), site_key) in already_collected:
                counts["idempotent_skipped"] += 1
                continue
            try:
                result = client.fetch(url)
            except Exception as exc:
                LOGGER.warning("Fetch failed for %s (%s)", product["id"], type(exc).__name__)
                common = {
                    "date_utc": date_utc,
                    "observed_at": observed_at,
                    "product_id": product["id"],
                    "site": site_key,
                    "price": "",
                    "mrp": "",
                    "status": "fetch_error",
                    "flags": "fetch_exception",
                    "strategy": "",
                }
                observations.append(common)
                counts["fetch_error"] += 1
                continue
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
                extracted = extract_mamaearth_product(result.html)
            except Exception as exc:
                LOGGER.warning("Parse failed for %s (%s)", product["id"], type(exc).__name__)
                observations.append(
                    {
                        **common,
                        "status": "rejected",
                        "flags": "parse_error",
                        "strategy": "",
                    }
                )
                counts["rejected"] += 1
                continue
            skeleton = product_info_skeleton(result.html)
            if skeleton:
                page_skeletons[site_key] = skeleton
            fallback_used = any(
                strategy.startswith(("css", "regex"))
                for strategy in extracted.strategy_by_field.values()
            )
            price_fallback = extracted.strategy_by_field.get("price", "").startswith(
                ("css", "regex")
            )
            validation_args = dict(
                price=extracted.price,
                mrp=extracted.mrp,
                currency=extracted.currency,
                title=extracted.title,
                expected_tokens=product["expected_tokens"],
            )
            previous_price = latest_good.get((str(product["id"]), site_key))
            if price_fallback:
                validation = validate_fallback_observation(
                    **validation_args,
                    last_good_price=previous_price,
                    fallback_max_deviation=fallback_deviation,
                )
            else:
                validation = validate_observation(
                    **validation_args,
                    last_good_price=previous_price,
                )
                if fallback_used and validation.valid:
                    validation = ValidationResult("fallback_ok", validation.flags)
            expected_size = to_base_quantity(
                Decimal(str(product["pack_size_value"])), str(product["pack_size_unit"])
            )
            if extracted.mrp is None:
                validation = ValidationResult("rejected", (*validation.flags, "mrp_missing"))
            if extracted.pack_size_value is None or not extracted.pack_size_unit:
                validation = ValidationResult("rejected", (*validation.flags, "pack_size_missing"))
            else:
                actual_size = to_base_quantity(extracted.pack_size_value, extracted.pack_size_unit)
                if actual_size != expected_size:
                    validation = ValidationResult(
                        "rejected", (*validation.flags, "pack_size_mismatch")
                    )
            if extracted.availability is not True:
                stock_flag = (
                    "out_of_stock" if extracted.availability is False else "stock_unverified"
                )
                validation = ValidationResult("rejected", (*validation.flags, stock_flag))
            if validation.status == "rejected":
                LOGGER.warning(
                    "Rejected product %s with flags %s",
                    product["id"],
                    ";".join(validation.flags),
                )
                if fallback_used:
                    try:
                        save_debug_snippet(
                            result.html,
                            settings.data_dir,
                            run_id=run_id,
                            product_id=str(product["id"]),
                        )
                    except OSError:
                        LOGGER.warning("Could not save private debug snippet for %s", product["id"])
            status = validation.status
            title_by_row[(str(product["id"]), site_key)] = extracted.title
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
    previous_rows = load_run_rows(settings.data_dir)
    previous_by_site: dict[str, dict[str, float]] = {}
    for row in previous_rows:
        try:
            previous_by_site[row["site"]] = {
                key: float(row.get(key) or 0)
                for key in ("price_fill", "title_fill", "validity_rate")
            }
        except (KeyError, ValueError):
            continue
    old_skeletons = load_skeletons(settings.data_dir)
    health_by_site = {}
    for site_key in site_stats:
        site_rows = [row for row in observations if row["site"] == site_key]
        enriched = [
            {
                **row,
                "title": title_by_row.get((str(row["product_id"]), site_key), ""),
            }
            for row in site_rows
        ]
        drift = (
            jaccard_similarity(old_skeletons[site_key], page_skeletons[site_key])
            if site_key in old_skeletons and site_key in page_skeletons
            else None
        )
        health_by_site[site_key] = evaluate_site(
            site_key,
            enriched,
            min_fill_price=float(policy.get("min_fill_price", 0.90)),
            min_fill_name=float(policy.get("min_fill_name", 0.90)),
            min_fill_mrp=float(policy.get("min_fill_mrp", 0.70)),
            min_validity=float(policy.get("min_validity", 0.90)),
            drift_min_similarity=float(policy.get("drift_min_similarity", 0.80)),
            drift_similarity=drift,
            previous=previous_by_site.get(site_key),
        )
    if not observations:
        LOGGER.info("No new observations; all selected keys were already collected or skipped.")
        return CollectionSummary(
            {key: dict(counts) for key, counts in site_stats.items()},
            suspect=False,
            report="No new observations.",
        )
    for site_key, health in health_by_site.items():
        append_run(settings.data_dir, health.to_run_record(run_id=run_id, started_at=observed_at))
        LOGGER.info(
            "%s collected=%d fallback=%d rejected=%d blocked=%d skipped=%d suspect=%s reasons=%s",
            site_key,
            health.ok,
            health.fallback_ok,
            health.rejected,
            health.blocked,
            health.skipped,
            health.suspect,
            ",".join(health.reasons),
        )
    good_skeletons = {
        site: skeleton
        for site, skeleton in page_skeletons.items()
        if site in health_by_site and not health_by_site[site].suspect
    }
    if good_skeletons:
        old_skeletons.update(good_skeletons)
        save_skeletons(settings.data_dir, old_skeletons)
    LOGGER.info("CSV rows added=%d idempotent skips=%d", added, skipped)
    suspect, report = evaluate_run(health_by_site)
    return CollectionSummary(
        {key: dict(counts) for key, counts in site_stats.items()},
        suspect=suspect,
        report=report,
    )
