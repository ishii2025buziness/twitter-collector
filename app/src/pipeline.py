"""Example pipeline implementation for new services."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import yaml

from common.artifacts import ArtifactStore
from common.contracts import JobResult, JobStatus, StageResult, StageStatus


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "service.config.yaml"


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    loaded = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _service_name(config: dict[str, Any]) -> str:
    value = config.get("service_name")
    return value if isinstance(value, str) and value.strip() else "service-name"


def _artifact_root(config: dict[str, Any]) -> Path:
    raw = config.get("artifact_root", ".artifacts")
    path = Path(raw)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


async def run_pipeline() -> JobResult:
    """Main pipeline skeleton. Replace with actual stages."""
    started = perf_counter()
    config = _load_config()
    service_name = _service_name(config)
    artifacts = ArtifactStore(_artifact_root(config), service_name)

    payload = {"service_name": service_name, "run_id": artifacts.run_id, "status": "ok"}
    output_path = artifacts.write_json("bootstrap-check", "example.json", payload)
    stage = StageResult(
        status=StageStatus.SUCCESS,
        stage="bootstrap-check",
        input_count=0,
        output_count=1,
        artifact_paths=[output_path],
        duration_ms=int((perf_counter() - started) * 1000),
    )

    return JobResult(
        status=JobStatus.SUCCESS,
        job_name=service_name,
        run_id=artifacts.run_id,
        stages=[stage],
        artifact_root=artifacts.run_dir,
        duration_ms=int((perf_counter() - started) * 1000),
    )


def smoke_pipeline() -> dict[str, Any]:
    config = _load_config()
    return {
        "service_name": _service_name(config),
        "artifact_root": str(_artifact_root(config)),
        "service_config_exists": CONFIG_PATH.exists(),
    }


def check_pipeline() -> dict[str, Any]:
    config = _load_config()
    return {
        "service_name": _service_name(config),
        "service_config_path": str(CONFIG_PATH),
        "service_config_exists": CONFIG_PATH.exists(),
        "artifact_root": str(_artifact_root(config)),
    }
