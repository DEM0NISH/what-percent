"""Fingerprints ignore text and content outside the saved product-info region."""

from pathlib import Path

from whatpercent.fingerprint import (
    jaccard_similarity,
    load_skeletons,
    product_info_skeleton,
    save_skeletons,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "trimmed" / "mamaearth_vitamin_c_daily_glow_serum.html"
)


def test_identical_product_info_has_similarity_one() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    skeleton = product_info_skeleton(html)
    assert skeleton
    assert jaccard_similarity(skeleton, product_info_skeleton(html)) == 1.0


def test_simulated_product_layout_change_drops_similarity() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    original = product_info_skeleton(html)
    changed = html.replace("hdt-price__container", "changed-price-container")
    similarity = jaccard_similarity(original, product_info_skeleton(changed))
    assert similarity < 0.80


def test_text_and_outside_ad_change_do_not_affect_skeleton() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    changed = html.replace("₹374", "₹375").replace(
        "</body>", '<aside class="advertisement">added ad</aside></body>'
    )
    assert jaccard_similarity(product_info_skeleton(html), product_info_skeleton(changed)) == 1.0


def test_numeric_and_hashed_class_suffixes_are_normalized() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    numeric = html.replace("hdt-price__container", "hdt-price__container-123")
    hashed = html.replace("hdt-price__container", "hdt-price__container-a1b2c3d4e5f6")
    baseline = product_info_skeleton(html)
    assert product_info_skeleton(numeric) == baseline
    assert product_info_skeleton(hashed) == baseline


def test_skeleton_persistence_is_per_site_and_atomic(tmp_path: Path) -> None:
    expected = {"mamaearth": {"div/a", "div/b"}}
    path = save_skeletons(tmp_path, expected)
    assert path.parent == tmp_path
    assert load_skeletons(tmp_path) == expected
