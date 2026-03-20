"""Standard CLI entrypoint for twitter-collector."""

from __future__ import annotations

import argparse
import json

from common.contracts import JobStatus

from pipeline import check, run_pipeline, smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="twitter-collector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--config", help="Override config path")

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--config", help="Override config path")

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--config", help="Override config path")

    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_pipeline(config_path=args.config)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 1 if result.status == JobStatus.FAILED else 0

    if args.command == "smoke":
        print(
            json.dumps(
                {"job": "twitter-collector", "command": "smoke", "result": smoke(config_path=args.config)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {"job": "twitter-collector", "command": "check", "result": check(config_path=args.config)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

