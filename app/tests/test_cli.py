from __future__ import annotations

import cli
from common.contracts import JobResult, JobStatus


def test_cli_run_passes_config(monkeypatch, capsys):
    received: dict[str, str | None] = {}

    def fake_run_pipeline(config_path: str | None = None) -> JobResult:
        received["config_path"] = config_path
        return JobResult(
            status=JobStatus.SUCCESS,
            job_name="twitter-collector",
            run_id="20260316T000000",
            stages=[],
            artifact_root="artifacts/twitter-collector/20260316T000000",
            duration_ms=1,
        )

    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)

    exit_code = cli.main(["run", "--config", "/tmp/custom.yaml"])

    assert exit_code == 0
    assert received["config_path"] == "/tmp/custom.yaml"
    assert "twitter-collector" in capsys.readouterr().out

