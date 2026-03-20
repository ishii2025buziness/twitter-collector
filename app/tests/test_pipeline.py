from __future__ import annotations

import asyncio
from pathlib import Path

from src.pipeline import check_pipeline, run_pipeline, smoke_pipeline


def test_smoke_pipeline_reports_config(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "service.config.yaml"
    config.write_text("service_name: demo\nartifact_root: .artifacts\n", encoding="utf-8")
    monkeypatch.setattr("src.pipeline.CONFIG_PATH", config)
    monkeypatch.setattr("src.pipeline.REPO_ROOT", tmp_path)

    result = smoke_pipeline()
    assert result["service_name"] == "demo"
    assert result["service_config_exists"] is True


def test_check_pipeline_reports_artifact_root(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "service.config.yaml"
    config.write_text("service_name: demo\nartifact_root: out\n", encoding="utf-8")
    monkeypatch.setattr("src.pipeline.CONFIG_PATH", config)
    monkeypatch.setattr("src.pipeline.REPO_ROOT", tmp_path)

    result = check_pipeline()
    assert result["service_name"] == "demo"
    assert result["artifact_root"] == str((tmp_path / "out").resolve())


def test_run_pipeline_returns_valid_job_result(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "service.config.yaml"
    config.write_text("service_name: demo\nartifact_root: out\n", encoding="utf-8")
    monkeypatch.setattr("src.pipeline.CONFIG_PATH", config)
    monkeypatch.setattr("src.pipeline.REPO_ROOT", tmp_path)

    result = asyncio.run(run_pipeline())
    assert result.job_name == "demo"
    assert result.status == "success"
    assert result.stages[0].stage == "bootstrap-check"
