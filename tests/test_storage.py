"""CSV and SQLite storage tests use isolated temporary directories."""

import csv
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from whatpercent.config import load_settings
from whatpercent.storage import (
    RUN_COLUMNS,
    SNAPSHOT_COLUMNS,
    append_observations,
    append_run,
    build_database,
    load_observations,
)


def observation(**overrides: str) -> dict[str, str]:
    row = {
        "date_utc": "2026-10-26",
        "observed_at": "2026-10-26T12:00:00+00:00",
        "product_id": "p001",
        "site": "mamaearth",
        "price": "374",
        "mrp": "499",
        "status": "ok",
        "flags": "",
        "strategy": "jsonld",
    }
    row.update(overrides)
    return row


def test_csv_header_idempotency_and_force(tmp_path: Path) -> None:
    added, skipped, path = append_observations(tmp_path, [observation()])
    assert (added, skipped) == (1, 0)
    added, skipped, _ = append_observations(tmp_path, [observation()])
    assert (added, skipped) == (0, 1)
    added, skipped, _ = append_observations(tmp_path, [observation()], force=True)
    assert (added, skipped) == (1, 0)
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    assert tuple(rows[0]) == SNAPSHOT_COLUMNS
    assert len(rows) == 3


def test_idempotency_applies_to_rejected_rows_too(tmp_path: Path) -> None:
    rejected = observation(status="rejected", flags="simulated_parse_error", price="")
    assert append_observations(tmp_path, [rejected])[:2] == (1, 0)
    assert append_observations(tmp_path, [rejected])[:2] == (0, 1)


def test_incomplete_or_malformed_csv_is_rejected(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    path = snapshots / "2026-10.csv"
    path.write_text("date_utc,price\n2026-10-26,374\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_observations(tmp_path)
    path.write_text(
        ",".join(SNAPSHOT_COLUMNS) + "\n" + ",".join(["x"] * 10) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="extra fields"):
        load_observations(tmp_path)


def test_failed_atomic_replace_leaves_previous_csv_intact(tmp_path: Path, monkeypatch) -> None:
    _, _, path = append_observations(tmp_path, [observation()])
    before = path.read_bytes()

    def fail_replace(source, destination):
        raise OSError("simulated crash before atomic replace")

    monkeypatch.setattr("whatpercent.storage.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated crash"):
        append_observations(tmp_path, [observation(product_id="p002")])
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


def test_build_database_and_loader_rebuild_from_durable_csv(tmp_path: Path) -> None:
    append_observations(tmp_path, [observation()])
    run = dict.fromkeys(RUN_COLUMNS, "")
    run.update(
        {
            "run_id": "run-1",
            "started_at": "2026-10-26T12:00:00+00:00",
            "site": "mamaearth",
            "rows": "1",
            "ok": "1",
        }
    )
    append_run(tmp_path, run)
    db_path = build_database(tmp_path)
    with closing(sqlite3.connect(db_path)) as connection:
        stored = connection.execute("SELECT * FROM snapshots").fetchall()
        runs = connection.execute("SELECT run_id, site, rows FROM runs").fetchall()
        connection.commit()
    rebuilt = build_database(tmp_path)
    with closing(sqlite3.connect(rebuilt)) as connection:
        assert connection.execute("SELECT * FROM snapshots").fetchall() == stored
        assert connection.execute("SELECT run_id, site, rows FROM runs").fetchall() == runs
        connection.commit()
    assert stored == [
        (
            "2026-10-26",
            "2026-10-26T12:00:00+00:00",
            "p001",
            "mamaearth",
            "374",
            "499",
            "ok",
            "",
            "jsonld",
        )
    ]
    assert runs == [("run-1", "mamaearth", 1)]
    frame = load_observations(tmp_path)
    assert list(frame.columns) == list(SNAPSHOT_COLUMNS)
    assert frame.to_dict(orient="records")[0]["price"] == "374"


def test_all_csv_storage_uses_configured_whatpct_data_path(tmp_path: Path) -> None:
    data_path = tmp_path / "private-data"
    settings = load_settings(
        environ={
            "WHATPCT_REPO_URL": "https://example.test/repo",
            "WHATPCT_CONTACT_EMAIL": "bot@example.test",
            "WHATPCT_DATA": str(data_path),
        },
        dotenv_path=tmp_path / "missing.env",
    )
    append_observations(settings.data_dir, [observation()])
    run = {column: "" for column in RUN_COLUMNS}
    run.update({"run_id": "run-1", "site": "mamaearth"})
    run_path = append_run(settings.data_dir, run)
    db_path = build_database(settings.data_dir)
    assert (data_path / "snapshots" / "2026-10.csv").is_file()
    assert run_path.parent == data_path
    assert db_path.parent == data_path
