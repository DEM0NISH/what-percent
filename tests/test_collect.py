"""The collection command is exercised with hashed synthetic HTML fixtures."""

from __future__ import annotations

import yaml

from whatpercent.__main__ import build_parser
from whatpercent.collect import collect_products, load_products
from whatpercent.fetcher import offline_fixture_name

SYNTHETIC_HTML = """<!doctype html><script type='application/ld+json'>
{"@type":"Product","name":"Mamaearth Synthetic Vitamin C Daily Glow Serum 30 ml",
"offers":{"@type":"Offer","priceCurrency":"INR","price":"374",
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
