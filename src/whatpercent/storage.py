"""Atomic CSV history storage with a rebuildable SQLite cache."""

from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

SNAPSHOT_COLUMNS = (
    "date_utc",
    "observed_at",
    "product_id",
    "site",
    "price",
    "mrp",
    "status",
    "flags",
    "strategy",
)
RUN_COLUMNS = (
    "run_id",
    "started_at",
    "site",
    "rows",
    "ok",
    "fallback_ok",
    "rejected",
    "blocked",
    "price_fill",
    "title_fill",
    "mrp_fill",
    "validity_rate",
    "drift_similarity",
    "suspect",
    "skipped",
    "reasons",
)
SPOTCHECK_COLUMNS = ("row_key", "checked_at", "result", "note")
GOOD_STATUSES = {"ok", "fallback_ok"}
ALLOWED_STATUSES = GOOD_STATUSES | {
    "rejected",
    "blocked",
    "skipped_robots",
    "fetch_error",
}


def _atomic_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    """Replace one CSV atomically so interruption cannot leave a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in columns})
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_csv(
    path: Path,
    columns: Sequence[str],
    *,
    required: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header: {path}")
        missing = set(required or columns) - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV file {path} is missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError(f"CSV file has rows with extra fields: {path}")
        return rows


def append_observations(
    data_dir: Path | str,
    observations: Iterable[Mapping[str, object]],
    *,
    force: bool = False,
) -> tuple[int, int, Path]:
    """Append new observation keys to their UTC monthly file; return added/skipped counts."""
    root = Path(data_dir)
    incoming = [dict(row) for row in observations]
    if not incoming:
        now = datetime.now(UTC)
        return 0, 0, root / "snapshots" / f"{now:%Y-%m}.csv"
    now = datetime.now(UTC)
    month = str(incoming[0].get("date_utc") or now.date().isoformat())[:7]
    if len(month) != 7 or month[4] != "-":
        raise ValueError("date_utc must start with YYYY-MM")
    path = root / "snapshots" / f"{month}.csv"
    for index, row in enumerate(incoming, start=1):
        if row.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"observation {index} has an invalid status")
        if not str(row.get("product_id", "")).strip() or not str(row.get("site", "")).strip():
            raise ValueError(f"observation {index} requires product_id and site")
    existing = _read_csv(path, SNAPSHOT_COLUMNS)
    collected_keys = {
        (row.get("date_utc", ""), row.get("product_id", ""), row.get("site", ""))
        for row in existing
    }
    added = 0
    skipped = 0
    for row in incoming:
        date_utc = str(row.get("date_utc") or now.date().isoformat())
        key = (date_utc, str(row.get("product_id", "")), str(row.get("site", "")))
        row["date_utc"] = date_utc
        if not force and key in collected_keys:
            skipped += 1
            continue
        existing.append(row)
        collected_keys.add(key)
        added += 1
    if added:
        _atomic_csv(path, SNAPSHOT_COLUMNS, existing)
    return added, skipped, path


def append_run(data_dir: Path | str, run: Mapping[str, object]) -> Path:
    """Append one per-site run-health row using the same atomic replacement path."""
    path = Path(data_dir) / "runs.csv"
    rows = _read_csv(path, RUN_COLUMNS, required=RUN_COLUMNS[:8])
    rows.append(dict(run))
    _atomic_csv(path, RUN_COLUMNS, rows)
    return path


def load_run_rows(data_dir: Path | str) -> list[dict[str, str]]:
    """Read per-site health history without exposing it outside the private data path."""
    return _read_csv(Path(data_dir) / "runs.csv", RUN_COLUMNS, required=RUN_COLUMNS[:8])


def append_spotcheck(data_dir: Path | str, row: Mapping[str, object]) -> Path:
    """Append one manual comparison without changing collected observations."""
    path = Path(data_dir) / "spotchecks.csv"
    rows = _read_csv(path, SPOTCHECK_COLUMNS)
    rows.append(dict(row))
    _atomic_csv(path, SPOTCHECK_COLUMNS, rows)
    return path


def load_spotchecks(data_dir: Path | str) -> list[dict[str, str]]:
    """Read previously recorded manual comparisons."""
    return _read_csv(Path(data_dir) / "spotchecks.csv", SPOTCHECK_COLUMNS)


def build_database(data_dir: Path | str) -> Path:
    """Rebuild the disposable SQLite cache from durable CSV history."""
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "whatpercent.sqlite"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".whatpercent.", suffix=".sqlite", dir=root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            connection.execute(
                "CREATE TABLE snapshots (date_utc TEXT, observed_at TEXT, product_id TEXT, "
                "site TEXT, price TEXT, mrp TEXT, status TEXT, flags TEXT, strategy TEXT, "
                "UNIQUE(date_utc, product_id, site))"
            )
            connection.execute(
                "CREATE TABLE runs (run_id TEXT, started_at TEXT, site TEXT, rows INTEGER, "
                "ok INTEGER, fallback_ok INTEGER, rejected INTEGER, blocked INTEGER, "
                "price_fill REAL, title_fill REAL, mrp_fill REAL, validity_rate REAL, "
                "drift_similarity REAL, suspect TEXT, skipped INTEGER, reasons TEXT)"
            )
            for csv_path in sorted((root / "snapshots").glob("????-??.csv")):
                records = _read_csv(csv_path, SNAPSHOT_COLUMNS)
                connection.executemany(
                    "INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [tuple(row.get(column, "") for column in SNAPSHOT_COLUMNS) for row in records],
                )
            run_records = _read_csv(root / "runs.csv", RUN_COLUMNS, required=RUN_COLUMNS[:8])
            connection.executemany(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [tuple(row.get(column, "") for column in RUN_COLUMNS) for row in run_records],
            )
            connection.commit()
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def load_observations(data_dir: Path | str) -> pd.DataFrame:
    """Return the durable observation CSVs as a DataFrame, preserving blank values."""
    paths = sorted((Path(data_dir) / "snapshots").glob("????-??.csv"))
    records = [row for path in paths for row in _read_csv(path, SNAPSHOT_COLUMNS)]
    if not records:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return pd.DataFrame(records, columns=SNAPSHOT_COLUMNS).fillna("")
