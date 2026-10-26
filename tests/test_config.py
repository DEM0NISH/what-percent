"""Offline tests for environment-based runtime configuration."""

from pathlib import Path

import pytest

from whatpercent.config import ConfigurationError, load_settings


def test_env_file_values_build_the_user_agent(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WHATPCT_REPO_URL=https://example.test/repo.git\n"
        "WHATPCT_CONTACT_EMAIL=bot@example.test\n"
        "WHATPCT_DATA=./private-data\n",
        encoding="utf-8",
    )
    settings = load_settings(environ={}, dotenv_path=env_file)
    assert settings.user_agent == (
        "WhatPercentBot/1.0 (+https://example.test/repo.git; contact: bot@example.test)"
    )
    assert settings.data_dir == Path("./private-data")


def test_environment_values_override_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WHATPCT_REPO_URL=https://example.test/old.git\nWHATPCT_CONTACT_EMAIL=old@example.test\n",
        encoding="utf-8",
    )
    settings = load_settings(
        environ={
            "WHATPCT_REPO_URL": "https://example.test/new.git",
            "WHATPCT_CONTACT_EMAIL": "new@example.test",
        },
        dotenv_path=env_file,
    )
    assert settings.repo_url.endswith("new.git")
    assert settings.contact_email == "new@example.test"


def test_missing_required_identity_values_are_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="WHATPCT_REPO_URL"):
        load_settings(environ={}, dotenv_path=tmp_path / "missing.env")
