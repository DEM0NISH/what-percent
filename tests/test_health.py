"""Per-site health tests keep a broken site visible beside a healthy one."""

from whatpercent.health import evaluate_run, evaluate_site


def test_healthy_and_broken_sites_make_overall_run_suspect_per_site() -> None:
    healthy = evaluate_site(
        "mamaearth",
        [
            {"status": "ok", "price": "374", "mrp": "499", "title": "Serum"},
            {"status": "ok", "price": "359", "mrp": "449", "title": "Wash"},
        ],
    )
    broken = evaluate_site(
        "other-approved-site",
        [
            {"status": "rejected", "price": "", "mrp": "", "title": ""},
            {"status": "rejected", "price": "", "mrp": "", "title": ""},
        ],
    )
    suspect, report = evaluate_run({healthy.site: healthy, broken.site: broken})
    assert not healthy.suspect
    assert broken.suspect
    assert suspect
    assert "other-approved-site: suspect" in report
    assert "zero_usable_rows" in report


def test_drift_alone_is_only_a_warning() -> None:
    health = evaluate_site(
        "mamaearth",
        [{"status": "ok", "price": "374", "mrp": "499", "title": "Serum"}],
        drift_similarity=0.5,
        previous={"price_fill": 1.0, "title_fill": 1.0, "validity_rate": 1.0},
    )
    assert not health.suspect
    assert health.reasons == ()


def test_drift_with_completeness_drop_is_suspect() -> None:
    health = evaluate_site(
        "mamaearth",
        [{"status": "rejected", "price": "", "mrp": "499", "title": "Serum"}],
        drift_similarity=0.5,
        previous={"price_fill": 1.0, "title_fill": 1.0, "validity_rate": 1.0},
    )
    assert "drift_with_fill_drop" in health.reasons


def test_health_row_has_expected_storage_fields() -> None:
    health = evaluate_site(
        "mamaearth",
        [{"status": "fallback_ok", "price": "374", "mrp": "499", "title": "Serum"}],
    )
    record = health.to_run_record(run_id="run-1", started_at="2026-10-27T00:00:00Z")
    assert record["fallback_ok"] == 1
    assert record["suspect"] == "false"
