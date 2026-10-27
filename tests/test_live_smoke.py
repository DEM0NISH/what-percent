"""Explicitly gated smoke test; excluded from every offline and CI run."""

import pytest

from whatpercent.config import load_settings
from whatpercent.fetcher import PoliteFetcher


@pytest.mark.live
def test_authorized_single_product_smoke_request() -> None:
    settings = load_settings()
    result = PoliteFetcher(settings.user_agent).fetch(
        "https://mamaearth.in/products/vitamin-c-daily-glow-face-serum-with-vitamin-c-turmeric-for-radiant-skin-30-ml"
    )
    assert result.status == 200, (
        f"Expected an authorized 200; received {result.status}, "
        f"Server={result.headers.get('Server')}, Retry-After={result.retry_after}"
    )
