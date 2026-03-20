"""Twitter collector pipeline job."""

from __future__ import annotations

import json
import os
import sys
import time
from importlib import import_module
from pathlib import Path

_THIS_DIR = Path(__file__).parent
ROOT = _THIS_DIR.parent
_COMMON_SRC = ROOT.parent / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.artifacts import ArtifactStore
from common.contract_validation import save_validated_job_result
from common.contracts import FailureCode, JobResult, JobStatus, StageResult, StageStatus
from common.job_metrics import export_job_result_metrics_from_env

from collector import TwitterCliCollector
from config import CollectionSpec, load_config, resolve_config_path


JOB_NAME = "twitter-collector"


def _duration_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _classify_failure(exc: Exception) -> FailureCode:
    message = str(exc).lower()
    if any(
        token in message
        for token in (
            "cookie expired or invalid",
            "no twitter cookies found",
            "failed to authenticate",
            "http 401",
            "http 403",
        )
    ):
        return FailureCode.AUTH_FAILED
    return FailureCode.UNEXPECTED_ERROR


def _persist_result(result: JobResult, store: ArtifactStore) -> JobResult:
    save_validated_job_result(result, store.summary_path())
    export_job_result_metrics_from_env(result, artifact_root=store.run_dir)
    return result


def _write_latest_manifest(
    *,
    run_id: str,
    config_path: Path,
    latest_dir: Path,
    stage_outputs: list[dict[str, object]],
) -> Path:
    manifest_path = latest_dir / "manifest.json"
    payload = {
        "job": JOB_NAME,
        "run_id": run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config_path": str(config_path),
        "collections": stage_outputs,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return manifest_path


def _build_stage_result(
    spec: CollectionSpec,
    start: float,
    *,
    status: StageStatus,
    artifact_paths: list[Path] | None = None,
    output_count: int = 0,
    warnings: list[str] | None = None,
    failure_code: FailureCode | None = None,
) -> StageResult:
    return StageResult(
        status=status,
        stage=spec.stage_name,
        input_count=0,
        output_count=output_count,
        artifact_paths=artifact_paths or [],
        warnings=warnings or [],
        failure_code=failure_code,
        duration_ms=_duration_ms(start),
    )


def _load_saved_tweet_ids(path: Path) -> list[str]:
    items = json.loads(path.read_text(encoding="utf-8"))
    tweet_ids: list[str] = []
    for item in items:
        tweet_id = item.get("id")
        if tweet_id is None:
            continue
        tweet_ids.append(str(tweet_id))
    return tweet_ids


def run_pipeline(config_path: str | None = None) -> JobResult:
    job_start = time.perf_counter()
    run_id = time.strftime("%Y%m%dT%H%M%S")
    store = ArtifactStore(ROOT / "artifacts", JOB_NAME, run_id=run_id)
    collector = TwitterCliCollector()
    config = load_config(config_path)
    resolved_config_path = resolve_config_path(config_path)
    stages: list[StageResult] = []
    stage_outputs: list[dict[str, object]] = []

    if not config.collections:
        result = JobResult(
            status=JobStatus.FAILED,
            job_name=JOB_NAME,
            run_id=run_id,
            stages=[],
            artifact_root=store.run_dir,
            failure_code=FailureCode.CONFIG_INVALID,
            warnings=["No collections configured."],
            duration_ms=_duration_ms(job_start),
        )
        return _persist_result(result, store)

    successes = 0
    failures = 0
    failure_codes: list[FailureCode] = []

    for spec in config.collections:
        stage_start = time.perf_counter()
        try:
            payload = collector.collect(spec)
            artifact_path = store.write_json(payload.stage_name, "items.json", payload.items)
            artifact_paths = [artifact_path]
            post_actions_path = None
            latest_dir = ROOT / "output" / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            latest_path = latest_dir / f"{payload.stage_name}.json"
            latest_path.write_text(artifact_path.read_text())
            artifact_paths.append(latest_path)
            stage_warnings = list(payload.warnings)
            saved_tweet_ids = _load_saved_tweet_ids(artifact_path)
            if spec.kind == "bookmarks" and spec.remove_after_collect:
                post_actions = collector.remove_bookmarks(saved_tweet_ids)
                post_actions_path = store.write_json(payload.stage_name, "post-actions.json", post_actions)
                artifact_paths.append(post_actions_path)
                stage_warnings.append(
                    f"remove_after_collect enabled; unbookmarked={post_actions['removed_count']}"
                )
                if post_actions["failed_count"]:
                    stage_warnings.append(
                        f"unbookmark failed for {post_actions['failed_count']} tweet(s)"
                    )
            if spec.kind == "likes" and spec.remove_after_collect:
                post_actions = collector.remove_likes(saved_tweet_ids)
                post_actions_path = store.write_json(payload.stage_name, "post-actions.json", post_actions)
                artifact_paths.append(post_actions_path)
                stage_warnings.append(
                    f"remove_after_collect enabled; unliked={post_actions['removed_count']}"
                )
                if post_actions["failed_count"]:
                    stage_warnings.append(
                        f"unlike failed for {post_actions['failed_count']} tweet(s)"
                    )
            if not payload.items:
                stage_warnings.append("Collection returned no items.")
            stage_outputs.append(
                {
                    "name": payload.stage_name,
                    "kind": spec.kind,
                    "output_count": len(payload.items),
                    "latest_path": str(latest_path),
                    "artifact_path": str(artifact_path),
                    "post_actions_path": str(post_actions_path) if post_actions_path else None,
                }
            )
            stages.append(
                _build_stage_result(
                    spec,
                    stage_start,
                    status=StageStatus.SUCCESS,
                    artifact_paths=artifact_paths,
                    output_count=len(payload.items),
                    warnings=stage_warnings,
                )
            )
            successes += 1
        except Exception as exc:
            failure_code = _classify_failure(exc)
            failure_log = store.write_text(spec.stage_name, "error.txt", f"{type(exc).__name__}: {exc}\n")
            stages.append(
                _build_stage_result(
                    spec,
                    stage_start,
                    status=StageStatus.FAILED,
                    artifact_paths=[failure_log],
                    warnings=[str(exc)],
                    failure_code=failure_code,
                )
            )
            failures += 1
            failure_codes.append(failure_code)

    latest_manifest = _write_latest_manifest(
        run_id=run_id,
        config_path=resolved_config_path,
        latest_dir=ROOT / "output" / "latest",
        stage_outputs=stage_outputs,
    )

    if failures == 0:
        status = JobStatus.SUCCESS
        failure_code = None
    elif successes == 0:
        status = JobStatus.FAILED
        failure_code = failure_codes[0]
    else:
        status = JobStatus.PARTIAL
        failure_code = failure_codes[0]

    result = JobResult(
        status=status,
        job_name=JOB_NAME,
        run_id=run_id,
        stages=stages,
        artifact_root=store.run_dir,
        failure_code=failure_code,
        warnings=[f"config={resolved_config_path}", f"latest_manifest={latest_manifest}"],
        duration_ms=_duration_ms(job_start),
    )
    return _persist_result(result, store)


def smoke(config_path: str | None = None) -> dict[str, object]:
    path = resolve_config_path(config_path)
    return {
        "config_path": str(path),
        "config_exists": path.exists(),
        "package_root": str(ROOT),
    }


def check(config_path: str | None = None) -> dict[str, object]:
    try:
        import_module("twitter_cli")
        twitter_cli_available = True
    except ImportError:
        twitter_cli_available = False

    return {
        "config_path": str(resolve_config_path(config_path)),
        "artifacts_dir": str(ROOT / "artifacts"),
        "output_dir_exists": (ROOT / "output").exists(),
        "twitter_cli_available": twitter_cli_available,
        "twitter_auth_token_present": bool(os.environ.get("TWITTER_AUTH_TOKEN")),
        "twitter_ct0_present": bool(os.environ.get("TWITTER_CT0")),
    }
