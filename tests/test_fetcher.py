"""Offline tests for polite HTTP behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from whatpercent.fetcher import PoliteFetcher, offline_fixture_name, parse_retry_after


class FakeResponse:
    def __init__(
        self, status_code: int = 200, text: str = "ok", headers: dict[str, str] | None = None
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class FakeSession:
    def __init__(self, items: list[Any]) -> None:
        self.items = list(items)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def client(items: list[Any], waits: list[float] | None = None) -> tuple[PoliteFetcher, FakeSession]:
    session = FakeSession(items)
    fetcher = PoliteFetcher(
        "WhatPercentBot/1.0 (+https://example.test/repo; contact: bot@example.test)",
        session=session,  # type: ignore[arg-type]
        sleeper=(waits if waits is not None else []).append,
        clock=lambda: 100.0,
        random_value=lambda: 0.0,
    )
    return fetcher, session


def test_robots_disallow_is_fail_closed() -> None:
    fetcher, session = client([FakeResponse(text="User-agent: *\nDisallow: /products/private")])
    result = fetcher.fetch("https://shop.test/products/private/item")
    assert result.skipped_reason == "robots_disallowed"
    assert len(session.calls) == 1


def test_robots_failure_is_fail_closed() -> None:
    fetcher, session = client(
        [
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
        ]
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.skipped_reason == "robots_unavailable"
    assert len(session.calls) == 4


def test_robots_crawl_delay_is_honored() -> None:
    waits: list[float] = []
    fetcher, _ = client(
        [
            FakeResponse(text="User-agent: *\nCrawl-delay: 5\nAllow: /"),
            FakeResponse(text="product"),
        ],
        waits,
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.html == "product"
    assert any(wait >= 5 for wait in waits)


def test_403_is_not_retried() -> None:
    fetcher, session = client(
        [FakeResponse(text="User-agent: *\nAllow: /"), FakeResponse(status_code=403)]
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.status == 403
    assert result.skipped_reason == "http_403"
    assert len(session.calls) == 2


def test_short_429_retry_after_is_honoured_once() -> None:
    waits: list[float] = []
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=429, headers={"Retry-After": "5"}),
            FakeResponse(text="product"),
        ],
        waits,
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.html == "product"
    assert len(session.calls) == 3
    assert any(wait >= 5 for wait in waits)


def test_long_429_stops_host_for_rest_of_run() -> None:
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=429, headers={"Retry-After": "61"}),
        ]
    )
    first = fetcher.fetch("https://shop.test/products/item")
    second = fetcher.fetch("https://shop.test/products/other")
    assert first.status == 429
    assert first.skipped_reason == "http_429"
    assert second.skipped_reason == "host_stopped_after_429"
    assert len(session.calls) == 2


def test_repeated_short_429_stops_host_after_single_retry() -> None:
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=429, headers={"Retry-After": "1"}),
            FakeResponse(status_code=429, headers={"Retry-After": "1"}),
        ]
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.status == 429
    assert len(session.calls) == 3


def test_one_shot_mode_returns_429_headers_without_retry() -> None:
    response_headers = {
        "Retry-After": "17",
        "Server": "example-edge",
        "Content-Type": "text/html; charset=utf-8",
    }
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=429, text="rate limited", headers=response_headers),
        ]
    )
    fetcher.retry_429 = False
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.status == 429
    assert result.retry_after == 17
    assert result.headers == response_headers
    assert len(session.calls) == 2  # robots.txt plus exactly one product-page request


def test_one_shot_mode_does_not_retry_transient_errors() -> None:
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=503, headers={"Server": "example-edge"}),
        ]
    )
    fetcher.retry_429 = False
    fetcher.retry_transient = False
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.status == 503
    assert result.headers == {"Server": "example-edge"}
    assert len(session.calls) == 2


def test_5xx_uses_exponential_retry_limit() -> None:
    waits: list[float] = []
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            FakeResponse(status_code=503),
            FakeResponse(status_code=502),
            FakeResponse(status_code=500),
            FakeResponse(text="product"),
        ],
        waits,
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.html == "product"
    assert len(session.calls) == 5
    assert {1.0, 2.0, 4.0}.issubset(set(waits))


def test_timeout_retries_at_most_three_times() -> None:
    fetcher, session = client(
        [
            FakeResponse(text="User-agent: *\nAllow: /"),
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
        ]
    )
    result = fetcher.fetch("https://shop.test/products/item")
    assert result.skipped_reason == "timeout"
    assert len(session.calls) == 5


def test_offline_mode_reads_hash_named_fixture(tmp_path: Path) -> None:
    url = "https://shop.test/products/item"
    (tmp_path / offline_fixture_name(url)).write_text("saved", encoding="utf-8")
    fetcher = PoliteFetcher("bot", offline_dir=tmp_path)
    result = fetcher.fetch(url)
    assert result.html == "saved"
    assert result.status == 200


def test_dev_cache_prevents_repeated_page_request(tmp_path: Path) -> None:
    url = "https://shop.test/products/item"
    cache = tmp_path / "cache"
    fetcher, session = client(
        [FakeResponse(text="User-agent: *\nAllow: /"), FakeResponse(text="live")]
    )
    fetcher.dev_cache_dir = cache
    first = fetcher.fetch(url)
    second = fetcher.fetch(url)
    assert first.html == second.html == "live"
    assert second.skipped_reason == "dev_cache"
    assert len(session.calls) == 2


def test_retry_after_delta_and_http_date() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_retry_after("12", now) == 12
    assert parse_retry_after("Thu, 01 Jan 2026 00:00:20 GMT", now) == 20
    assert parse_retry_after("invalid", now) is None
