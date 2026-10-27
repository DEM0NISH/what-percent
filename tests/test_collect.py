"""The collection command is exercised with hashed synthetic HTML fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whatpercent.__main__ import build_parser
from whatpercent.collect import collect_products, load_products, save_debug_snippet
from whatpercent.fetcher import offline_fixture_name

SYNTHETIC_HTML = """<!doctype html><script type='application/ld+json'>
{"@type":"Product","name":"Mamaearth Synthetic Vitamin C Daily Glow Serum 30 ml",
"offers":{"@type":"Offer","availability":"https://schema.org/InStock",
"priceCurrency":"INR","price":"374",
"priceSpecification":{"@type":"PriceSpecification","priceType":"ListPrice","priceCurrency":"INR","price":"499"}}}
</script>"""


def config_doc(url: str) -> dict:
    return {
        "settings": {},
        "products": [
            {
                "id": "p001",
                "brand": "Mamaearth",
                "variant": "Synthetic Vitamin C Daily Glow Serum",
                "pack_size_value": 30,
                "pack_size_unit": "ml",
                "category": "serum",
                "expected_tokens": ["vitamin c", "daily glow", "30ml"],
                "urls": {"mamaearth": url},
                "verified": True,
                "verified_at": "2026-10-27",
                "verified_by": "manual-browser",
                "source": "fixture",
                "fixture_observed": {"mrp": "499", "price": "374", "date": "2026-10-27"},
            }
        ],
    }


def test_collect_cli_accepts_offline_dir_and_selection_flags() -> None:
    args = build_parser().parse_args(
        [
            "collect",
            "--config",
            "products.yaml",
            "--limit",
            "3",
            "--site",
            "mamaearth",
            "--offline-dir",
            "fixtures",
            "--force",
        ]
    )
    assert args.command == "collect"
    assert args.config == "products.yaml"
    assert args.limit == 3
    assert args.site == "mamaearth"
    assert str(args.offline_dir) == "fixtures"
    assert args.force is True


def test_collect_reads_fixture_and_writes_configured_csv(tmp_path, monkeypatch) -> None:
    url = "https://mamaearth.in/products/synthetic-vitamin-c-daily-glow-serum-30ml"
    config_path = tmp_path / "products.yaml"
    config_path.write_text(yaml.safe_dump(config_doc(url)), encoding="utf-8")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / offline_fixture_name(url)).write_text(SYNTHETIC_HTML, encoding="utf-8")
    data_dir = tmp_path / "private-data"
    monkeypatch.setenv("WHATPCT_REPO_URL", "https://example.test/repo")
    monkeypatch.setenv("WHATPCT_CONTACT_EMAIL", "bot@example.test")
    monkeypatch.setenv("WHATPCT_DATA", str(data_dir))

    result = collect_products(config_path=config_path, offline_dir=fixtures)
    assert result == {"mamaearth": {"ok": 1}}
    snapshot = next((data_dir / "snapshots").glob("*.csv"))
    contents = snapshot.read_text(encoding="utf-8")
    assert ",374,499,ok,,jsonld" in contents
    assert (data_dir / "runs.csv").is_file()
    result = collect_products(config_path=config_path, offline_dir=tmp_path / "empty-offline")
    assert result == {"mamaearth": {"idempotent_skipped": 1}}


def test_product_config_rejects_unapproved_site(tmp_path) -> None:
    doc = config_doc("https://example.test/products/item")
    path = tmp_path / "products.yaml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    try:
        load_products(path)
    except ValueError as exc:
        assert "mamaearth.in" in str(exc)
    else:
        raise AssertionError("unapproved host was accepted")


def test_fixture_verified_catalog_loads_without_public_price_rows() -> None:
    products = load_products("products.yaml")
    assert len(products) == 10
    assert all(product["fixture_observed"] == {"date": "2026-10-27"} for product in products)


def test_catalog_gate_lists_all_unverified_missing_token_and_duplicate_ids(tmp_path) -> None:
    doc = config_doc("https://mamaearth.in/products/item")
    second = dict(doc["products"][0])
    second["expected_tokens"] = []
    second["verified"] = False
    doc["products"].append(second)
    path = tmp_path / "products.yaml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_products(path)
    message = str(error.value)
    assert "p001" in message
    assert "duplicate id" in message
    assert "verified must be true" in message
    assert "expected_tokens is missing" in message


def test_cli_config_gate_exits_two_before_fetching(tmp_path, monkeypatch) -> None:
    from whatpercent import __main__ as cli
    from whatpercent import collect as collection

    def unexpected_fetcher(*args, **kwargs):
        raise AssertionError("fetcher must not be constructed before the config gate passes")

    path = tmp_path / "products.yaml"
    path.write_text("products: []\n", encoding="utf-8")
    monkeypatch.setattr(collection, "PoliteFetcher", unexpected_fetcher)
    monkeypatch.setattr("sys.argv", ["whatpercent", "collect", "--config", str(path)])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2


def test_runtime_failure_is_recorded_and_other_products_continue(tmp_path, monkeypatch) -> None:
    first_url = "https://mamaearth.in/products/synthetic-vitamin-c-daily-glow-serum-30ml"
    second_url = "https://mamaearth.in/products/synthetic-other-serum-30ml"
    document = config_doc(first_url)
    second = dict(document["products"][0])
    second["id"] = "p002"
    second["variant"] = "Synthetic Other Serum"
    second["urls"] = {"mamaearth": second_url}
    document["products"].append(second)
    config_path = tmp_path / "products.yaml"
    config_path.write_text(yaml.safe_dump(document), encoding="utf-8")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / offline_fixture_name(first_url)).write_text(SYNTHETIC_HTML, encoding="utf-8")
    data_dir = tmp_path / "private-data"
    monkeypatch.setenv("WHATPCT_REPO_URL", "https://example.test/repo")
    monkeypatch.setenv("WHATPCT_CONTACT_EMAIL", "bot@example.test")
    monkeypatch.setenv("WHATPCT_DATA", str(data_dir))
    result = collect_products(config_path=config_path, offline_dir=fixtures)
    assert result.suspect is True
    rows = next((data_dir / "snapshots").glob("*.csv")).read_text(encoding="utf-8")
    assert "p001" in rows and "ok" in rows
    assert "p002" in rows and "fetch_error" in rows
    assert (data_dir / "runs.csv").is_file()


def test_offline_collect_refuses_public_or_private_real_data_store(tmp_path, monkeypatch) -> None:
    url = "https://mamaearth.in/products/synthetic-vitamin-c-daily-glow-serum-30ml"
    config_path = tmp_path / "products.yaml"
    config_path.write_text(yaml.safe_dump(config_doc(url)), encoding="utf-8")
    monkeypatch.setenv("WHATPCT_REPO_URL", "https://example.test/repo")
    monkeypatch.setenv("WHATPCT_CONTACT_EMAIL", "bot@example.test")
    monkeypatch.setenv("WHATPCT_DATA", str(Path.cwd() / "data"))
    with pytest.raises(ValueError, match="throwaway WHATPCT_DATA"):
        collect_products(config_path=config_path, offline_dir=tmp_path / "fixtures")


def test_debug_snippets_are_trimmed_bounded_and_limited_per_run(tmp_path) -> None:
    html = (
        Path(__file__)
        .parent.joinpath("fixtures", "trimmed", "mamaearth_vitamin_c_daily_glow_serum.html")
        .read_text(encoding="utf-8")
    )
    paths = [
        save_debug_snippet(html, tmp_path, run_id="run-1", product_id=f"p{index:03}")
        for index in range(6)
    ]
    saved = [path for path in paths if path is not None]
    assert len(saved) == 5
    for path in saved:
        assert path.stat().st_size <= 30_000
        text = path.read_text(encoding="utf-8")
        assert "hdt-product-info__list" in text
        assert "application/ld+json" not in text


def test_debug_snippet_directory_keeps_only_latest_twenty(tmp_path) -> None:
    html = (
        Path(__file__)
        .parent.joinpath("fixtures", "trimmed", "mamaearth_vitamin_c_daily_glow_serum.html")
        .read_text(encoding="utf-8")
    )
    for index in range(21):
        save_debug_snippet(html, tmp_path, run_id=f"run-{index:02}", product_id="p001")
    assert len(list((tmp_path / "debug").glob("*.html"))) == 20
