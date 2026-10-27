"""Workflow guardrails are checked locally without invoking GitHub Actions."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_collection_workflow_is_manual_and_preserves_suspect_data() -> None:
    text = (ROOT / ".github" / "workflows" / "collect.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "# schedule:" in text
    assert '#   - cron: "30 3 * * *"' in text
    assert "repository: DEM0NISH/what-percent-data" in text
    assert "token: ${{ secrets.DATA_REPO_TOKEN }}" in text
    assert "path: data-repo" in text
    assert "git -C data-repo check-ignore debug/" in text
    assert "continue-on-error: true" in text
    assert 'echo "exit_code=$code" >> "$GITHUB_OUTPUT"' in text
    assert "if: always() && steps.collect.outcome != 'skipped'" in text
    assert "git -C data-repo commit" in text
    assert "retention-days: 7" in text


def test_ci_excludes_live_tests_and_runs_docker_help() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert 'pytest -q -m "not live"' in text
    assert "docker build -t what-percent ." in text
    assert "docker run --rm what-percent --help" in text
