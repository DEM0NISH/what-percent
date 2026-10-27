"""Per-site collection health metrics and suspect-run decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SiteHealth:
    """Summary of observed field completeness and validity for one source."""

    site: str
    rows: int
    ok: int
    fallback_ok: int
    rejected: int
    blocked: int
    skipped: int
    price_fill: float
    title_fill: float
    mrp_fill: float
    validity_rate: float
    drift_similarity: float | None
    suspect: bool
    reasons: tuple[str, ...]

    def to_run_record(self, *, run_id: str, started_at: str) -> dict[str, object]:
        """Map health fields to the durable per-site runs.csv schema."""
        return {
            "run_id": run_id,
            "started_at": started_at,
            "site": self.site,
            "rows": self.rows,
            "ok": self.ok,
            "fallback_ok": self.fallback_ok,
            "rejected": self.rejected,
            "blocked": self.blocked,
            "price_fill": f"{self.price_fill:.4f}",
            "title_fill": f"{self.title_fill:.4f}",
            "mrp_fill": f"{self.mrp_fill:.4f}",
            "validity_rate": f"{self.validity_rate:.4f}",
            "drift_similarity": ""
            if self.drift_similarity is None
            else f"{self.drift_similarity:.4f}",
            "suspect": str(self.suspect).lower(),
            "skipped": self.skipped,
            "reasons": ";".join(self.reasons),
        }


def evaluate_site(
    site: str,
    observations: list[dict[str, Any]],
    *,
    min_fill_price: float = 0.90,
    min_fill_name: float = 0.90,
    min_fill_mrp: float = 0.70,
    min_validity: float = 0.90,
    drift_min_similarity: float = 0.80,
    drift_similarity: float | None = None,
    previous: dict[str, float] | None = None,
) -> SiteHealth:
    """Mark a site suspect for low completeness, validity, or corroborated drift."""
    total = len(observations)
    counts = {status: 0 for status in ("ok", "fallback_ok", "rejected", "blocked")}
    for row in observations:
        status = str(row.get("status", "fetch_error"))
        if status in counts:
            counts[status] += 1
    price_fill = sum(bool(row.get("price")) for row in observations) / total if total else 0.0
    title_fill = sum(bool(row.get("title")) for row in observations) / total if total else 0.0
    mrp_fill = sum(bool(row.get("mrp")) for row in observations) / total if total else 0.0
    valid = sum(row.get("status") in {"ok", "fallback_ok"} for row in observations)
    validity_rate = valid / total if total else 0.0
    skipped = sum(
        row.get("status") in {"skipped_robots", "fetch_error", "skipped"} for row in observations
    )
    reasons: list[str] = []
    if total and price_fill < min_fill_price:
        reasons.append("price_fill_low")
    if total and title_fill < min_fill_name:
        reasons.append("title_fill_low")
    if total and mrp_fill < min_fill_mrp:
        reasons.append("mrp_fill_low")
    if total and validity_rate < min_validity:
        reasons.append("validity_low")
    if total and valid == 0:
        reasons.append("zero_usable_rows")
    if drift_similarity is not None and drift_similarity < drift_min_similarity and previous:
        dropped = (
            price_fill < previous.get("price_fill", price_fill)
            or title_fill < previous.get("title_fill", title_fill)
            or validity_rate < previous.get("validity_rate", validity_rate)
        )
        if dropped:
            reasons.append("drift_with_fill_drop")
    return SiteHealth(
        site=site,
        rows=total,
        ok=counts["ok"],
        fallback_ok=counts["fallback_ok"],
        rejected=counts["rejected"],
        blocked=counts["blocked"],
        skipped=skipped,
        price_fill=price_fill,
        title_fill=title_fill,
        mrp_fill=mrp_fill,
        validity_rate=validity_rate,
        drift_similarity=drift_similarity,
        suspect=bool(reasons),
        reasons=tuple(reasons),
    )


def evaluate_run(sites: dict[str, SiteHealth]) -> tuple[bool, str]:
    """Return overall suspect state and readable per-site details without hiding failures."""
    suspect = any(site.suspect for site in sites.values())
    lines = [
        f"{name}: {'suspect (' + ', '.join(site.reasons) + ')' if site.suspect else 'healthy'}"
        for name, site in sites.items()
    ]
    return suspect, "\n".join(lines)
