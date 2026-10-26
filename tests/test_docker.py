"""Static checks for the requested minimal Python Docker packaging."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_docker_image_is_python312_non_root_and_runs_cli() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in dockerfile
    assert "COPY requirements.txt" in dockerfile
    assert "USER app" in dockerfile
    assert 'ENTRYPOINT ["python", "-m", "whatpercent"]' in dockerfile
    assert 'CMD ["collect"]' in dockerfile


def test_compose_mounts_data_and_read_only_product_config() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "./data:/data" in compose
    assert "./products.yaml:/app/products.yaml:ro" in compose
