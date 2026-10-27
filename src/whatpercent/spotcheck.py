"""Manual spot-check sampling and result recording for stored observations."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from whatpercent.storage import append_spotcheck, load_observations, load_spotchecks


def make_row_key(row: dict[str, Any]) -> str:
    """Return a stable key for one daily product/site observation."""
    return "|".join(str(row.get(key, "")) for key in ("date_utc", "product_id", "site"))


def sample_rows(
    data_dir: Path | str,
    config_path: Path | str = "products.yaml",
    *,
    count: int = 5,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """Pick up to five recent usable rows and attach display identity and URL."""
    frame = load_observations(data_dir)
    rows = frame.to_dict(orient="records")
    candidates = [row for row in rows if row.get("status") in {"ok", "fallback_ok"}]
    if not candidates:
        return []
    candidates.sort(key=lambda row: (str(row.get("date_utc", "")), str(row.get("observed_at", ""))))
    recent = candidates[-max(count * 5, count) :]
    chooser = rng or random.SystemRandom()
    selected = chooser.sample(recent, min(count, len(recent)))
    try:
        document = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        document = {}
    products = {
        str(product.get("id")): product
        for product in document.get("products", [])
        if isinstance(product, dict) and product.get("id")
    }
    for row in selected:
        product = products.get(str(row.get("product_id", "")), {})
        row["row_key"] = make_row_key(row)
        row["product"] = product.get("variant") or row.get("product_id", "")
        row["url"] = (product.get("urls") or {}).get(str(row.get("site", "")), "")
    return selected


def record_result(
    data_dir: Path | str,
    row_key: str,
    result: str,
    note: str = "",
) -> Path:
    """Record a manual match/mismatch result for a previously stored row key."""
    if result not in {"match", "mismatch"}:
        raise ValueError("result must be match or mismatch")
    valid_keys = {
        make_row_key(row) for row in load_observations(data_dir).to_dict(orient="records")
    }
    if row_key not in valid_keys:
        raise ValueError(f"unknown row_key: {row_key}")
    checked_at = datetime.now(UTC).isoformat(timespec="seconds")
    return append_spotcheck(
        data_dir,
        {"row_key": row_key, "checked_at": checked_at, "result": result, "note": note},
    )


def summarize(data_dir: Path | str) -> tuple[int, int, float | None]:
    """Return match count, sample size, and accuracy when any checks exist."""
    rows = load_spotchecks(data_dir)
    matches = sum(row.get("result") == "match" for row in rows)
    total = sum(row.get("result") in {"match", "mismatch"} for row in rows)
    return matches, total, (matches / total * 100 if total else None)
