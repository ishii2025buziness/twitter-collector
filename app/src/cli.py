"""Service CLI entry point."""

from __future__ import annotations

from common.job_cli import run_job_cli

from src.pipeline import check_pipeline, run_pipeline, smoke_pipeline


def main(argv: list[str] | None = None) -> int:
    return run_job_cli(
        "service-name",
        run_fn=run_pipeline,
        smoke_fn=smoke_pipeline,
        check_fn=check_pipeline,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
