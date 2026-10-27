"""Spot-check tests use temporary CSV data and no site access."""

import random
from pathlib import Path

import yaml

from whatpercent.spotcheck import make_row_key, record_result, sample_rows, summarize
from whatpercent.storage import RUN_COLUMNS, append_observations, append_run


def test_sample_record_and_summary(tmp_path: Path) -> None:
    row = {
        "date_utc": "2026-10-27",
        "observed_at": "2026-10-27T00:00:00+00:00",
        "product_id": "p1",
        "site": "mamaearth",
        "price": "374",
        "mrp": "499",
        "status": "ok",
        "flags": "",
        "strategy": "jsonld",
    }
    append_observations(tmp_path, [row])
    config = tmp_path / "products.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "products": [
                    {
                        "id": "p1",
                        "variant": "Serum",
                        "urls": {"mamaearth": "https://mamaearth.in/products/example"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    sampled = sample_rows(tmp_path, config, rng=random.Random(7))
    assert len(sampled) == 1
    assert sampled[0]["product"] == "Serum"
    assert sampled[0]["url"].startswith("https://mamaearth.in/")
    key = make_row_key(row)
    record_result(tmp_path, key, "match", "same price")
    record_result(tmp_path, key, "mismatch", "changed")
    assert summarize(tmp_path) == (1, 2, 50.0)


def test_empty_spotcheck_has_no_accuracy_claim(tmp_path: Path) -> None:
    assert summarize(tmp_path) == (0, 0, None)
    assert sample_rows(tmp_path) == []


def test_spotcheck_and_health_cli_commands(tmp_path: Path, monkeypatch, capsys) -> None:
    from whatpercent import __main__ as cli

    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "private"
    monkeypatch.setenv("WHATPCT_REPO_URL", "https://example.test/repo")
    monkeypatch.setenv("WHATPCT_CONTACT_EMAIL", "bot@example.test")
    monkeypatch.setenv("WHATPCT_DATA", str(data_dir))
    config = {
        "products": [
            {
                "id": "p1",
                "variant": "Serum",
                "urls": {"mamaearth": "https://mamaearth.in/products/serum"},
            }
        ]
    }
    (tmp_path / "products.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    row = {
        "date_utc": "2026-10-27",
        "observed_at": "2026-10-27T00:00:00+00:00",
        "product_id": "p1",
        "site": "mamaearth",
        "price": "374",
        "mrp": "499",
        "status": "ok",
        "flags": "",
        "strategy": "jsonld",
    }
    append_observations(data_dir, [row])
    run = {column: "" for column in RUN_COLUMNS}
    run.update(
        {
            "run_id": "run-1",
            "started_at": row["observed_at"],
            "site": "mamaearth",
            "rows": "1",
            "price_fill": "1.0000",
            "title_fill": "1.0000",
            "mrp_fill": "1.0000",
            "validity_rate": "1.0000",
            "suspect": "false",
            "reasons": "",
        }
    )
    append_run(data_dir, run)
    key = make_row_key(row)

    monkeypatch.setattr("sys.argv", ["whatpercent", "spotcheck", "sample"])
    cli.main()
    assert "Serum" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["whatpercent", "spotcheck", "record", key, "match"])
    cli.main()
    assert "saved privately" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["whatpercent", "spotcheck", "summary"])
    cli.main()
    assert "100.0% (1/1 matched)" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["whatpercent", "health", "--run", "latest"])
    cli.main()
    assert "mamaearth: healthy" in capsys.readouterr().out
