from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from typing import cast

from eye_collector.config import CollectorConfig
from eye_collector.db import PostgresRepository
from eye_collector.http import HttpClient
from eye_collector.logging_utils import JsonLogFormatter, safe_error_summary
from eye_collector.models import ImportResult
from eye_collector.runner import CollectorRunner
from eye_collector.sources.fixture import FixtureSourceAdapter, FixtureTransport


def _region_code(value: str) -> str:
    if len(value) != 6 or not value.isdigit():
        raise argparse.ArgumentTypeError("region must contain exactly six digits")
    return value


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("limit must be an integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("limit must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eye-collector")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one approved source import")
    run.add_argument("--source", required=True, choices=("fixture",))
    run.add_argument("--region", required=True, type=_region_code)
    run.add_argument("--limit", type=_positive_int)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--fixture-revision", choices=("stable", "updated"), default="stable")
    return parser


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def _result_json(result: ImportResult) -> str:
    return json.dumps(
        {
            "run_id": result.run_id,
            "status": result.status,
            "dry_run": result.dry_run,
            "counts": result.counts.as_dict(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging()
    repository: PostgresRepository | None = None
    http: HttpClient | None = None
    try:
        config = CollectorConfig.from_env()
        if args.source != "fixture":
            raise ValueError("only the offline fixture source is available in P2")
        http = HttpClient(
            timeout_seconds=config.http_timeout_seconds,
            max_response_bytes=config.http_max_response_bytes,
            max_attempts=config.http_max_attempts,
            backoff_base_seconds=config.http_backoff_base_seconds,
            user_agent=config.http_user_agent,
            transport=FixtureTransport(revision=args.fixture_revision),
        )
        adapter = FixtureSourceAdapter(http, revision=args.fixture_revision)
        repository = PostgresRepository.connect(config.database_url)
        result = CollectorRunner(repository, adapter).run(
            cast(str, args.region),
            limit=args.limit,
            dry_run=args.dry_run,
        )
        print(_result_json(result))
        return 0 if result.status == "succeeded" else 1
    except KeyboardInterrupt:
        logging.getLogger("eye_collector.cli").warning(
            "collector_cancelled",
            extra={"event": "collector_cancelled"},
        )
        return 130
    except Exception as error:
        logging.getLogger("eye_collector.cli").error(
            "collector_error",
            extra={"event": "collector_error", "error": safe_error_summary(error)},
        )
        return 2
    finally:
        if http is not None:
            http.close()
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
