"""Product-region layout fingerprints that signal drift without proving failure."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup, Tag

_IGNORED_REGION = re.compile(r"ad|recommend|upsell|related-product|recently-viewed", re.I)
_LONG_HEX_SUFFIX = re.compile(r"[-_]?[0-9a-f]{8,}$", re.I)
_NUMERIC_SUFFIX = re.compile(r"[-_]?\d+$")


def _normalized_node_name(node: Tag) -> str:
    classes = []
    for value in sorted(node.get("class", [])):
        token = _LONG_HEX_SUFFIX.sub("", str(value))
        token = _NUMERIC_SUFFIX.sub("", token).lower()
        classes.append(token)
    return node.name + ("." + ".".join(classes) if classes else "")


def product_info_skeleton(
    html: str,
    *,
    selector: str = ".hdt-product-info__list",
    depth_limit: int = 6,
) -> set[str]:
    """Return normalized tag paths for the product-info subtree only."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one(selector)
    if root is None:
        return set()
    skeleton: set[str] = set()

    def visit(node: Tag, prefix: tuple[str, ...], depth: int) -> None:
        if depth > depth_limit:
            return
        identity = " ".join([str(node.get("id", "")), *map(str, node.get("class", []))])
        if _IGNORED_REGION.search(identity):
            return
        path = (*prefix, _normalized_node_name(node))
        skeleton.add("/".join(path))
        for child in node.find_all(recursive=False):
            if isinstance(child, Tag):
                visit(child, path, depth + 1)

    visit(root, (), 0)
    return skeleton


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    """Compare two layout path sets, treating two missing regions as unavailable/equal."""
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def load_skeletons(data_dir: Path | str) -> dict[str, set[str]]:
    """Load per-site last-good skeletons from the private data directory."""
    path = Path(data_dir) / "skeletons.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    return {site: set(paths) for site, paths in document.items() if isinstance(paths, list)}


def save_skeletons(data_dir: Path | str, skeletons: dict[str, set[str]]) -> Path:
    """Atomically save normalized skeletons outside the public code repository."""
    path = Path(data_dir) / "skeletons.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".skeletons-", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({site: sorted(paths) for site, paths in skeletons.items()}, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path
