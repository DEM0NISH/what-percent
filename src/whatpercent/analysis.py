"""Sale-window metrics; functions accept collected observations or labelled test data."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

from whatpercent.storage import (
    GOOD_STATUSES,
    build_database,
    load_observations,
    load_spotchecks,
)


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def calculate_analysis(
    observations: list[dict[str, Any]],
    *,
    sale_start: str,
    sale_end: str,
    sale_day_bump_pp: float = 10.0,
    sale_day_share_min: float = 0.40,
    min_baseline_days: int = 7,
    good_baseline_days: int = 14,
    min_coverage: float = 0.80,
    advertised_min_pct: float = 20.0,
    gap_min_pp: float = 15.0,
    mrp_jump_min_pct: float = 10.0,
    runup_window_days: int = 7,
    runup_min_pct: float = 10.0,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Compute per-product sale metrics and cross-product detected sale days."""
    start, end = date.fromisoformat(sale_start), date.fromisoformat(sale_end)
    if end < start:
        raise ValueError("sale_end must not precede sale_start")
    good = [
        row.copy()
        for row in observations
        if row.get("status") in GOOD_STATUSES
        and _number(row.get("price")) is not None
        and _number(row.get("mrp")) is not None
    ]
    by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_product_day: dict[str, dict[str, float]] = defaultdict(dict)
    for row in good:
        product = str(row.get("product_id", ""))
        by_product[product].append(row)
        price, mrp = _number(row.get("price")), _number(row.get("mrp"))
        if price and mrp:
            by_product_day[product][str(row.get("date_utc"))] = (mrp - price) / mrp * 100
    detected: set[str] = set()
    trailing: dict[str, list[float]] = defaultdict(list)
    all_days = sorted({day for daily in by_product_day.values() for day in daily})
    for day in all_days:
        current = [
            (product, daily[day])
            for product, daily in by_product_day.items()
            if day in daily and trailing[product]
        ]
        bumped = sum(
            pct - median(trailing[product]) >= sale_day_bump_pp for product, pct in current
        )
        is_sale_day = bool(current) and bumped / len(current) >= sale_day_share_min
        if is_sale_day:
            detected.add(day)
        else:
            for product, daily in by_product_day.items():
                if day in daily:
                    trailing[product].append(daily[day])

    result: list[dict[str, Any]] = []
    for product, rows in by_product.items():
        dated = [(date.fromisoformat(str(row["date_utc"])), row) for row in rows]
        baseline = [row for day, row in dated if day < start and str(day) not in detected]
        sale = [row for day, row in dated if start <= day <= end]
        expected = max((end - start).days + 1, 1)
        coverage = len({str(row.get("date_utc")) for row in sale}) / expected
        item: dict[str, Any] = {"product_id": product, "coverage": coverage}
        if len({str(row.get("date_utc")) for row in baseline}) < min_baseline_days:
            item.update(status="insufficient_baseline", reason="fewer than minimum baseline days")
            result.append(item)
            continue
        if coverage < min_coverage:
            item.update(
                status="insufficient_coverage",
                reason="sale-window coverage below threshold",
            )
            result.append(item)
            continue
        if not sale:
            item.update(status="insufficient_coverage", reason="no sale-window observations")
            result.append(item)
            continue
        bp = median(_number(row["price"]) for row in baseline if _number(row["price"]))
        bm = median(_number(row["mrp"]) for row in baseline if _number(row["mrp"]))
        sp = median(_number(row["price"]) for row in sale if _number(row["price"]))
        sm = median(_number(row["mrp"]) for row in sale if _number(row["mrp"]))
        if not all((bp, bm, sp, sm)):
            item.update(status="insufficient_baseline", reason="missing price or MRP")
            result.append(item)
            continue
        advertised = (sm - sp) / sm * 100
        historical = (bp - sp) / bp * 100
        gap = advertised - historical
        mrp_change = (sm - bm) / bm * 100
        pre_sale = [
            row
            for day, row in dated
            if start.toordinal() - runup_window_days <= day.toordinal() < start.toordinal()
        ]
        earlier = [
            row
            for day, row in dated
            if day < start and start.toordinal() - runup_window_days > day.toordinal()
        ]
        runup = None
        if pre_sale and earlier:
            prior_median = median(_number(row["price"]) for row in earlier if _number(row["price"]))
            window_median = median(
                _number(row["price"]) for row in pre_sale if _number(row["price"])
            )
            if prior_median:
                runup = (window_median - prior_median) / prior_median * 100
        tags = []
        if advertised >= advertised_min_pct and gap >= gap_min_pp:
            label = "gap_flagged"
        elif advertised < advertised_min_pct:
            label = "no_big_discount"
        else:
            label = "consistent"
        if mrp_change >= mrp_jump_min_pct:
            tags.append("mrp_jump")
        if runup is not None and runup >= runup_min_pct:
            tags.append("pre_sale_runup")
        item.update(
            status="ok",
            baseline_days=len({str(row.get("date_utc")) for row in baseline}),
            baseline_quality=(
                "limited"
                if len({str(row.get("date_utc")) for row in baseline}) < good_baseline_days
                else "good"
            ),
            advertised_discount_pct=advertised,
            historical_price_reduction_pct=historical,
            discount_gap_pp=gap,
            mrp_change_pct=mrp_change,
            pre_sale_runup_pct=runup,
            sale_min_price=min(_number(row["price"]) for row in sale if _number(row["price"])),
            new_low=min(_number(row["price"]) for row in sale if _number(row["price"]))
            < min(_number(row["price"]) for row in baseline if _number(row["price"])),
            label=label,
            signals=";".join(tags),
        )
        result.append(item)
    return result, detected


def run_analysis(data_dir: Path | str, config_path: Path | str = "products.yaml") -> Path | None:
    """Write a summary only when real durable observations and sale dates exist."""
    import yaml

    frame = load_observations(data_dir)
    if frame.empty:
        return None
    document = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    settings = document.get("settings", {})
    sale_start, sale_end = settings.get("sale_start"), settings.get("sale_end")
    if not sale_start or not sale_end:
        return None
    source_rows = frame.to_dict(orient="records")
    build_database(data_dir)
    rows, detected = calculate_analysis(
        source_rows,
        sale_start=sale_start,
        sale_end=sale_end,
        **{
            key: settings[key]
            for key in (
                "sale_day_bump_pp",
                "sale_day_share_min",
                "min_baseline_days",
                "good_baseline_days",
                "min_coverage",
                "advertised_min_pct",
                "gap_min_pp",
                "mrp_jump_min_pct",
                "runup_window_days",
                "runup_min_pct",
            )
            if key in settings
        },
    )
    reports = Path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    target = reports / "summary.csv"
    columns = sorted({key for row in rows for key in row})
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    good_rows = sum(row.get("status") in GOOD_STATUSES for row in source_rows)
    spotchecks = load_spotchecks(data_dir)
    matches = sum(row.get("result") == "match" for row in spotchecks)
    checked = sum(row.get("result") in {"match", "mismatch"} for row in spotchecks)
    try:
        product_document = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        product_document = {}
    categories = {
        str(product.get("id")): str(product.get("category", "unknown"))
        for product in product_document.get("products", [])
        if isinstance(product, dict) and product.get("id")
    }
    by_product = defaultdict(list)
    for row in source_rows:
        if row.get("status") in GOOD_STATUSES:
            by_product[str(row.get("product_id", ""))].append(row)
    _write_charts(reports, source_rows, rows, categories, sale_start, sale_end)
    date_values = sorted(str(row.get("date_utc", "")) for row in source_rows if row.get("date_utc"))
    eligible = [row for row in rows if row.get("status") == "ok"]
    excluded = [row for row in rows if row.get("status") != "ok"]
    baseline_lengths = [int(row["baseline_days"]) for row in eligible]
    accuracy_text = f"{matches / checked:.1%}" if checked else "not available (0 checks)"
    small_sample_note = "The sample is too small to conclude. " if len(eligible) < 3 else ""
    exclusions_text = (
        "; ".join(
            f"{row['product_id']}: {row.get('status')} ({row.get('reason', '')})"
            for row in excluded
        )
        or "none"
    )
    report = reports / "REPORT.md"
    report.write_text(
        "# Analysis report\n\n"
        f"The dataset contains {len(by_product)} products tracked on mamaearth.in and "
        f"{good_rows} usable observations. Collection dates: "
        f"{date_values[0] if date_values else 'unknown'} to "
        f"{date_values[-1] if date_values else 'unknown'}.\n\n"
        f"Sale window: {sale_start} through {sale_end}. Detected sale days excluded from "
        f"baseline: {len(detected)}. Eligible products: {len(eligible)} of {len(rows)}.\n\n"
        f"Baseline length: {min(baseline_lengths) if baseline_lengths else 0}–"
        f"{max(baseline_lengths) if baseline_lengths else 0} days; coverage threshold: "
        f"{settings.get('min_coverage', 0.80):.0%}.\n\n"
        f"Exclusions: {exclusions_text}.\n\n"
        "## Method\n\n"
        "Advertised discount = (sale MRP − sale price) / sale MRP. Historical price "
        "reduction = (baseline price − sale price) / baseline price. Discount gap is the "
        "difference in percentage points. Baseline medians use non-sale days before the "
        "sale window; sale metrics use observations inside it. Products with fewer than "
        "seven baseline days or below 80% sale-window coverage are excluded from headline "
        "metrics. Fewer than 14 baseline days is described as limited.\n\n"
        f"Manual spot-check sample: {checked}; matches: {matches}; accuracy: "
        f"{accuracy_text}.\n\n"
        "## Limitations\n\n"
        "Single source, intended 15-product catalog, daily snapshots, and not representative "
        f"of the market. {small_sample_note}"
        "Gap-flagged describes a pattern and does not establish intent.\n",
        encoding="utf-8",
    )
    return target


def _write_charts(
    reports: Path,
    observations: list[dict[str, Any]],
    results: list[dict[str, Any]],
    categories: dict[str, str],
    sale_start: str,
    sale_end: str,
) -> None:
    """Write aggregated charts only from the real observations passed by run_analysis."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    good = [row for row in observations if row.get("status") in GOOD_STATUSES]
    product_ids = sorted({str(row.get("product_id", "")) for row in good})[:6]
    if not good:
        return
    figure, axis = plt.subplots(figsize=(10, 5))
    for product_id in product_ids:
        points = sorted(
            (str(row["date_utc"]), float(row["price"]))
            for row in good
            if str(row.get("product_id")) == product_id and _number(row.get("price"))
        )
        if points:
            axis.plot([p[0] for p in points], [p[1] for p in points], marker=".", label=product_id)
    axis.axvspan(sale_start, sale_end, alpha=0.15, color="orange", label="sale window")
    axis.set(title="Tracked prices", xlabel="UTC collection date", ylabel="Price (INR)")
    axis.legend()
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(reports / "price_history.png")
    plt.close(figure)

    eligible = [row for row in results if row.get("status") == "ok"]
    if not eligible:
        return
    figure, axis = plt.subplots(figsize=(7, 5))
    axis.scatter(
        [row["advertised_discount_pct"] for row in eligible],
        [row["historical_price_reduction_pct"] for row in eligible],
    )
    axis.set(
        title="Advertised discount vs historical reduction",
        xlabel="Advertised discount (%)",
        ylabel="Historical price reduction (%)",
    )
    figure.tight_layout()
    figure.savefig(reports / "discount_comparison.png")
    plt.close(figure)

    category_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    signal_counts: dict[str, int] = defaultdict(int)
    for row in eligible:
        category = categories.get(str(row["product_id"]), "unknown")
        category_totals[category][0] += 1
        category_totals[category][1] += row.get("label") == "gap_flagged"
        for signal in filter(None, str(row.get("signals", "")).split(";")):
            signal_counts[signal] += 1
    figure, axis = plt.subplots(figsize=(7, 5))
    names = sorted(category_totals)
    shares = [category_totals[name][1] / category_totals[name][0] for name in names]
    axis.bar(names, shares)
    axis.set(title="Share gap-flagged by category", ylabel="Share of eligible products")
    figure.tight_layout()
    figure.savefig(reports / "flagged_by_category.png")
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 5))
    axis.bar(sorted(signal_counts), [signal_counts[key] for key in sorted(signal_counts)])
    axis.set(title="Signal counts", ylabel="Eligible products")
    figure.tight_layout()
    figure.savefig(reports / "signal_counts.png")
    plt.close(figure)
