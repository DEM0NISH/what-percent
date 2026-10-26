"""Polite HTTP fetching with robots checks and explicit retry rules."""

from __future__ import annotations

import hashlib
import logging
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests

from whatpercent.config import load_settings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    """Result of a public-page request, including why a fetch was skipped."""

    html: str | None
    status: int | None
    skipped_reason: str | None
    elapsed: float
    retry_after: float | None = None
    headers: Mapping[str, str] = field(default_factory=dict)


def offline_fixture_name(url: str) -> str:
    """Return a stable fixture name so offline tests never need network access."""
    return f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.html"


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Parse either a delta-seconds value or an HTTP-date Retry-After header."""
    if value is None:
        return None
    try:
        seconds = float(value.strip())
        return max(seconds, 0.0)
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return max((retry_at - current).total_seconds(), 0.0)


class PoliteFetcher:
    """Fetch public pages while honoring robots rules and per-host politeness."""

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        timeout: float = 15.0,
        minimum_delay: float = 2.0,
        jitter: float = 2.0,
        session: requests.Session | None = None,
        offline_dir: Path | str | None = None,
        dev_cache_dir: Path | str | None = None,
        cache_ttl_seconds: float = 3600.0,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        random_value: Callable[[], float] = random.random,
        retry_429: bool = True,
    ) -> None:
        settings = load_settings() if user_agent is None else None
        self.user_agent = user_agent or settings.user_agent
        self.timeout = timeout
        self.minimum_delay = minimum_delay
        self.jitter = jitter
        self.session = session or requests.Session()
        self.offline_dir = Path(offline_dir) if offline_dir is not None else None
        self.dev_cache_dir = Path(dev_cache_dir) if dev_cache_dir is not None else None
        self.cache_ttl_seconds = cache_ttl_seconds
        self._sleep = sleeper
        self._clock = clock
        self._random = random_value
        self.retry_429 = retry_429
        self._robots: dict[str, RobotFileParser | None] = {}
        self._crawl_delays: dict[str, float] = {}
        self._last_request_at: dict[str, float] = {}
        self._blocked_hosts: set[str] = set()

    def fetch(self, url: str) -> FetchResult:
        """Fetch one page, returning an explicit skip when policy forbids access."""
        started = self._clock()
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return FetchResult(None, None, "invalid_url", 0.0)
        host = parts.hostname.lower()
        if self.offline_dir is not None:
            return self._read_offline(url, started)
        if host in self._blocked_hosts:
            return self._result(None, 429, "host_stopped_after_429", started)
        robots = self._load_robots(parts)
        if robots is None:
            return self._result(None, None, "robots_unavailable", started)
        if not robots.can_fetch(self.user_agent, url):
            return self._result(None, None, "robots_disallowed", started)
        cached = self._read_dev_cache(url, started)
        if cached is not None:
            return cached
        response, retry_after, reason = self._request_with_policy(url, host)
        if response is None:
            return self._result(None, None, reason or "fetch_error", started, retry_after)
        if response.status_code == 403:
            return self._result(None, 403, "http_403", started, headers=response.headers)
        if response.status_code == 429:
            return self._result(None, 429, "http_429", started, retry_after, response.headers)
        if not 200 <= response.status_code < 300:
            return self._result(
                None, response.status_code, "http_error", started, headers=response.headers
            )
        body = response.text
        self._write_dev_cache(url, body)
        return self._result(body, response.status_code, None, started, headers=response.headers)

    def _load_robots(self, target: SplitResult) -> RobotFileParser | None:
        parts = target
        host = parts.hostname.lower()
        if host in self._robots:
            return self._robots[host]
        robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        response, _, _ = self._request_with_policy(robots_url, host)
        if response is None or response.status_code != 200:
            self._robots[host] = None
            return None
        parser = RobotFileParser(robots_url)
        parser.parse(response.text.splitlines())
        self._robots[host] = parser
        self._crawl_delays[host] = float(parser.crawl_delay(self.user_agent) or 0.0)
        return parser

    def _request_with_policy(
        self, url: str, host: str
    ) -> tuple[requests.Response | None, float | None, str | None]:
        retries = 0
        retried_429 = False
        latest_retry_after: float | None = None
        while True:
            self._wait_for_host(host)
            try:
                response = self.session.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    timeout=self.timeout,
                    allow_redirects=False,
                )
            except requests.exceptions.Timeout:
                if retries >= 3:
                    return None, latest_retry_after, "timeout"
                self._sleep(2**retries)
                retries += 1
                continue
            except requests.RequestException:
                return None, latest_retry_after, "connection_error"
            if response.status_code == 403:
                return response, latest_retry_after, None
            if response.status_code == 429:
                latest_retry_after = parse_retry_after(response.headers.get("Retry-After"))
                if (
                    not self.retry_429
                    or retried_429
                    or latest_retry_after is None
                    or latest_retry_after > 60.0
                ):
                    self._blocked_hosts.add(host)
                    return response, latest_retry_after, None
                retried_429 = True
                self._wait_for_host(host, extra=latest_retry_after)
                continue
            if 500 <= response.status_code < 600:
                if retries >= 3:
                    return response, latest_retry_after, None
                self._sleep(2**retries)
                retries += 1
                continue
            return response, latest_retry_after, None

    def _wait_for_host(self, host: str, extra: float = 0.0) -> None:
        now = self._clock()
        previous = self._last_request_at.get(host)
        delay = max(self.minimum_delay, self._crawl_delays.get(host, 0.0)) + self.jitter * min(
            max(self._random(), 0.0), 1.0
        )
        if previous is None:
            wait_seconds = max(extra, 0.0)
        else:
            wait_seconds = max(previous + delay - now, extra, 0.0)
        if wait_seconds > 0:
            self._sleep(wait_seconds)
        self._last_request_at[host] = self._clock()

    def _read_offline(self, url: str, started: float) -> FetchResult:
        path = self.offline_dir / offline_fixture_name(url)
        if not path.is_file():
            return self._result(None, 404, "offline_fixture_not_found", started)
        return self._result(path.read_text(encoding="utf-8"), 200, None, started)

    def _cache_path(self, url: str) -> Path:
        return self.dev_cache_dir / offline_fixture_name(url)

    def _read_dev_cache(self, url: str, started: float) -> FetchResult | None:
        if self.dev_cache_dir is None:
            return None
        path = self._cache_path(url)
        if not path.is_file() or time.time() - path.stat().st_mtime > self.cache_ttl_seconds:
            return None
        return self._result(path.read_text(encoding="utf-8"), 200, "dev_cache", started)

    def _write_dev_cache(self, url: str, body: str) -> None:
        if self.dev_cache_dir is None:
            return
        self.dev_cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(url).write_text(body, encoding="utf-8")

    def _result(
        self,
        html: str | None,
        status: int | None,
        reason: str | None,
        started: float,
        retry_after: float | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> FetchResult:
        return FetchResult(
            html=html,
            status=status,
            skipped_reason=reason,
            elapsed=max(self._clock() - started, 0.0),
            retry_after=retry_after,
            headers=dict(headers or {}),
        )
