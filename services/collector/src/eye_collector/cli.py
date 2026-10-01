from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from datetime import datetime
from typing import cast
from uuid import UUID

from eye_collector.config import CollectorConfig
from eye_collector.db import PostgresRepository
from eye_collector.etl.pipeline import Pipeline
from eye_collector.etl.repository import ETLRepository
from eye_collector.geocoding.config import GeocodingConfig
from eye_collector.geocoding.pipeline import GeocodingPipeline
from eye_collector.geocoding.providers.fixture import FixtureGeocoder, FixtureGeocodeTransport
from eye_collector.geocoding.repository import GeocodeRepository
from eye_collector.http import HttpClient
from eye_collector.logging_utils import JsonLogFormatter, safe_error_summary
from eye_collector.models import FileImportProvenance, ImportResult, SourceDescriptor
from eye_collector.runner import CollectorRunner
from eye_collector.sources.fixture import FixtureSourceAdapter, FixtureTransport
from eye_collector.sources.open_data_file import (
    BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS,
    BEIJING_HOSPITALS,
    SHENZHEN_BAOAN_HOSPITALS,
    OpenDataDataset,
    OpenDataFileAdapter,
    inspect_open_data_file,
)

_OPEN_DATA_DATASETS: dict[str, tuple[OpenDataDataset, str]] = {
    dataset.source_key: (dataset, region)
    for dataset, region in (
        (BEIJING_HOSPITALS, "110000"),
        (BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS, "110000"),
        (SHENZHEN_BAOAN_HOSPITALS, "440306"),
    )
}


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


def _candidate_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("candidate-id must be a UUID") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eye-collector")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one approved source import")
    run.add_argument("--source", required=True, choices=("fixture", *_OPEN_DATA_DATASETS.keys()))
    run.add_argument("--region", required=True, type=_region_code)
    run.add_argument("--file", help="operator-downloaded official CSV, XLS, or XLSX file")
    run.add_argument("--limit", type=_positive_int)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--fixture-revision", choices=("stable", "updated"), default="stable")
    run.add_argument("--operator")
    run.add_argument(
        "--obtained-at", help="official file acquisition time in ISO-8601 with offset"
    )
    inspect = commands.add_parser("inspect-file", help="read-only official file preflight")
    inspect.add_argument("--source", required=True, choices=tuple(_OPEN_DATA_DATASETS))
    inspect.add_argument("--file", required=True, help="operator-downloaded official source file")
    process = commands.add_parser(
        "process", help="process approved source snapshots through P3 ETL"
    )
    process.add_argument("--limit", type=_positive_int)
    geocode = commands.add_parser(
        "geocode", help="geocode candidate records using the offline fixture provider"
    )
    geocode.add_argument("--provider", required=True, choices=("fixture",))
    geocode.add_argument("--limit", type=_positive_int)
    geocode.add_argument("--candidate-id", type=_candidate_id)
    geocode.add_argument("--dry-run", action="store_true")
    pilot = commands.add_parser(
        "pilot", help="run an explicitly bounded and approved regional pilot"
    )
    pilot.add_argument("--source", required=True, choices=tuple(_OPEN_DATA_DATASETS))
    pilot.add_argument("--region", required=True, choices=("110000", "440306"))
    pilot.add_argument("--file", required=True, help="operator-downloaded official source file")
    pilot.add_argument("--limit", required=True, type=_positive_int)
    pilot.add_argument("--dry-run", action="store_true")
    pilot.add_argument("--operator")
    pilot.add_argument(
        "--obtained-at", help="official file acquisition time in ISO-8601 with offset"
    )
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
            "import_run_id": result.run_id,
            "status": result.status,
            "dry_run": result.dry_run,
            "counts": result.counts.as_dict(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _file_provenance(
    args: argparse.Namespace, adapter: OpenDataFileAdapter
) -> FileImportProvenance:
    operator = (args.operator or os.environ.get("PILOT_OPERATOR", "")).strip()
    obtained_raw = args.obtained_at or os.environ.get("PILOT_FILE_OBTAINED_AT", "")
    if not operator:
        raise ValueError("PILOT_OPERATOR or --operator is required for file provenance")
    if not obtained_raw:
        raise ValueError(
            "PILOT_FILE_OBTAINED_AT or --obtained-at is required for file provenance"
        )
    try:
        obtained_at = datetime.fromisoformat(obtained_raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            "obtained-at must be an ISO-8601 timestamp with timezone offset"
        ) from error
    if obtained_at.tzinfo is None or obtained_at.utcoffset() is None:
        raise ValueError("obtained-at must include a timezone offset")
    return FileImportProvenance(
        original_filename=adapter.original_filename,
        file_sha256=adapter.file_sha256,
        file_size_bytes=adapter.file_size_bytes,
        obtained_at=obtained_at,
        operator=operator,
        acquisition_method="official_portal_manual_download",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging()
    repository: PostgresRepository | None = None
    etl_repository: ETLRepository | None = None
    geocode_repository: GeocodeRepository | None = None
    http: HttpClient | None = None
    try:
        if args.command == "pilot":
            if os.environ.get("PILOT_REAL_DATA") != "true":
                raise ValueError("pilot requires explicit PILOT_REAL_DATA=true opt-in")
            args.command = "run"
        if args.command == "inspect-file":
            dataset, allowed_region = _OPEN_DATA_DATASETS[args.source]
            inspection = inspect_open_data_file(args.file, dataset)
            config = CollectorConfig.from_env()
            repository = PostgresRepository.connect(config.database_url)
            descriptor = SourceDescriptor(
                dataset.source_key,
                dataset.source_name,
                dataset.dataset_url,
                access_method="file",
            )
            registration = repository.inspect_source(descriptor)
            configured_limit = (
                registration.pilot_group_record_limit if registration is not None else None
            )
            current_count = registration.pilot_group_record_count if registration else 0
            remaining_capacity = (
                max(configured_limit - current_count, 0) if configured_limit is not None else 0
            )
            max_importable_records = min(
                inspection.row_count, remaining_capacity, 150
            )
            approved = bool(
                registration is not None
                and registration.status == "approved"
                and registration.access_policy == "manual_only"
                and registration.dataset_page == dataset.dataset_url
            )
            ready = bool(
                approved
                and inspection.schema_match
                and max_importable_records > 0
            )
            print(
                json.dumps(
                    {
                        "filename": inspection.original_filename,
                        "sha256": inspection.file_sha256,
                        "file_size_bytes": inspection.file_size_bytes,
                        "detected_format": inspection.detected_format,
                        "headers": list(inspection.headers),
                        "row_count": inspection.row_count,
                        "approved_dataset": dataset.source_name,
                        "dataset_page": (
                            registration.dataset_page if registration else None
                        ),
                        "source_updated_at": (
                            registration.source_updated_at.isoformat()
                            if registration and registration.source_updated_at
                            else None
                        ),
                        "source_status": registration.status if registration else "not_registered",
                        "expected_schema": list(inspection.expected_schema),
                        "schema_match": inspection.schema_match,
                        "configured_pilot_limit": configured_limit,
                        "current_pilot_records": current_count,
                        "remaining_pilot_capacity": remaining_capacity,
                        "max_records_per_run": 150,
                        "max_importable_records": max_importable_records,
                        "allowed_region": allowed_region,
                        "ready_to_import": ready,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            return 0 if ready else 1
        if args.command == "geocode":
            geocode_config = GeocodingConfig.from_env()
            geocode_repository = GeocodeRepository.connect(geocode_config.database_url)
            policy = geocode_repository.approved_policy("fixture", "fixture-v1")
            http = HttpClient(
                timeout_seconds=geocode_config.http_timeout_seconds,
                max_response_bytes=geocode_config.http_max_response_bytes,
                max_attempts=geocode_config.http_max_attempts,
                backoff_base_seconds=geocode_config.http_backoff_base_seconds,
                user_agent=geocode_config.http_user_agent,
                transport=FixtureGeocodeTransport(),
            )
            provider = FixtureGeocoder(http, policy=policy)
            geocode_stats = GeocodingPipeline(geocode_repository, provider).run(
                limit=args.limit,
                candidate_record_id=args.candidate_id,
                dry_run=args.dry_run,
            )
            print(
                json.dumps(
                    {
                        "dry_run": args.dry_run,
                        "provider": args.provider,
                        "counts": geocode_stats.as_dict(),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            return 0 if geocode_stats.errors == 0 else 1
        if args.command == "process":
            etl_database_url = os.environ.get("ETL_DATABASE_URL")
            if not etl_database_url:
                raise ValueError("ETL_DATABASE_URL is required for process")
            etl_repository = ETLRepository.connect(etl_database_url)
            stats = Pipeline(etl_repository).run(limit=args.limit)
            print(json.dumps(stats.as_dict(), ensure_ascii=False, separators=(",", ":")))
            return 0 if stats.errors == 0 else 1
        if args.source != "fixture":
            if args.file is None:
                raise ValueError("official dataset imports require --file")
            if args.limit is None:
                raise ValueError("official dataset imports require an explicit --limit")
            if os.environ.get("PILOT_REAL_DATA") != "true":
                raise ValueError("official dataset imports require PILOT_REAL_DATA=true opt-in")
            dataset, required_region = _OPEN_DATA_DATASETS[args.source]
            if args.region != required_region:
                raise ValueError("region does not match the approved dataset scope")
            config = CollectorConfig.from_env()
            file_adapter = OpenDataFileAdapter(args.file, dataset)
            file_provenance = _file_provenance(args, file_adapter)
            repository = PostgresRepository.connect(config.database_url)
            result = CollectorRunner(repository, file_adapter, file_provenance=file_provenance).run(
                cast(str, args.region),
                limit=args.limit,
                dry_run=args.dry_run,
            )
            print(_result_json(result))
            return 0 if result.status == "succeeded" else 1
        if args.file is not None:
            raise ValueError("--file is only valid for an approved official dataset source")
        config = CollectorConfig.from_env()
        http = HttpClient(
            timeout_seconds=config.http_timeout_seconds,
            max_response_bytes=config.http_max_response_bytes,
            max_attempts=config.http_max_attempts,
            backoff_base_seconds=config.http_backoff_base_seconds,
            user_agent=config.http_user_agent,
            transport=FixtureTransport(revision=args.fixture_revision),
        )
        fixture_adapter = FixtureSourceAdapter(http, revision=args.fixture_revision)
        repository = PostgresRepository.connect(config.database_url)
        result = CollectorRunner(repository, fixture_adapter).run(
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
        if etl_repository is not None:
            etl_repository.close()
        if geocode_repository is not None:
            geocode_repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
