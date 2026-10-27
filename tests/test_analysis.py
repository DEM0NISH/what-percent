"""Analysis assertions use a hand-computed synthetic price history."""

from datetime import date, timedelta

from whatpercent.analysis import calculate_analysis


def series(days: int = 21) -> list[dict[str, str]]:
    rows = []
    start = date(2026, 1, 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        price = 100 if offset < 7 else 110 if offset < 14 else 70
        mrp = 140 if offset >= 14 else 120
        rows.append(
            {
                "date_utc": day.isoformat(),
                "product_id": "p1",
                "site": "mamaearth",
                "price": str(price),
                "mrp": str(mrp),
                "status": "ok",
            }
        )
    return rows


def test_synthetic_sale_metrics_and_detected_days_are_hand_computed() -> None:
    result, detected = calculate_analysis(series(), sale_start="2026-01-15", sale_end="2026-01-21")
    row = result[0]
    assert row["status"] == "ok"
    assert row["baseline_days"] == 14
    assert row["baseline_quality"] == "good"
    assert row["advertised_discount_pct"] == 50
    assert round(row["historical_price_reduction_pct"], 2) == 33.33
    assert round(row["discount_gap_pp"], 2) == 16.67
    assert round(row["mrp_change_pct"], 2) == 16.67
    assert row["pre_sale_runup_pct"] == 10
    assert row["new_low"] is True
    assert row["label"] == "gap_flagged"
    assert set(row["signals"].split(";")) == {"mrp_jump", "pre_sale_runup"}
    assert detected == {f"2026-01-{day:02d}" for day in range(15, 22)}


def test_synthetic_baseline_and_coverage_exclusions() -> None:
    short = series(10)
    result, _ = calculate_analysis(short, sale_start="2026-01-07", sale_end="2026-01-13")
    assert result[0]["status"] == "insufficient_baseline"
    sparse = series()
    sparse = [row for row in sparse if row["date_utc"] not in {"2026-01-19", "2026-01-20"}]
    result, _ = calculate_analysis(sparse, sale_start="2026-01-15", sale_end="2026-01-21")
    assert result[0]["status"] == "insufficient_coverage"


def test_analyze_cli_keeps_findings_pending_without_real_data(
    tmp_path, monkeypatch, capsys
) -> None:
    from whatpercent import __main__ as cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHATPCT_REPO_URL", "https://example.test/repo")
    monkeypatch.setenv("WHATPCT_CONTACT_EMAIL", "bot@example.test")
    monkeypatch.setenv("WHATPCT_DATA", str(tmp_path / "private-data"))
    monkeypatch.setattr("sys.argv", ["whatpercent", "analyze"])
    cli.main()
    assert "Analysis pending" in capsys.readouterr().out
    assert not (tmp_path / "reports" / "REPORT.md").exists()
