"""Small environment configuration helpers for local and scheduled runs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing or malformed."""


@dataclass(frozen=True)
class Settings:
    """Runtime values read from environment variables and a local .env file."""

    repo_url: str
    contact_email: str
    data_dir: Path

    @property
    def user_agent(self) -> str:
        """Build an honest, identifiable User-Agent from configured values."""
        return f"WhatPercentBot/1.0 (+{self.repo_url}; contact: {self.contact_email})"


def _dotenv_values(path: Path) -> dict[str, str]:
    """Read simple KEY=value entries without making dotenv a runtime dependency."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_settings(
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | str = ".env",
) -> Settings:
    """Load required identity and data-path settings, with process env taking priority."""
    values = _dotenv_values(Path(dotenv_path))
    values.update(dict(environ if environ is not None else os.environ))
    repo_url = values.get("WHATPCT_REPO_URL", "").strip()
    contact_email = values.get("WHATPCT_CONTACT_EMAIL", "").strip()
    if not repo_url or not contact_email:
        raise ConfigurationError(
            "Set WHATPCT_REPO_URL and WHATPCT_CONTACT_EMAIL in .env or the environment."
        )
    data_dir = Path(values.get("WHATPCT_DATA", "./data")).expanduser()
    return Settings(repo_url=repo_url, contact_email=contact_email, data_dir=data_dir)
