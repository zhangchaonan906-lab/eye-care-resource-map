from __future__ import annotations

import json
import logging

from eye_collector.logging_utils import JsonLogFormatter, safe_error_summary


def test_safe_error_summary_redacts_headers_tokens_and_url_parameters() -> None:
    summary = safe_error_summary(
        RuntimeError(
            "Authorization: Bearer abc123 Cookie: sid=private token=secret123 "
            "authorization=equals-secret https://fixture.invalid/run?api_key=hidden"
        )
    )

    assert "abc123" not in summary
    assert "private" not in summary
    assert "secret123" not in summary
    assert "equals-secret" not in summary
    assert "hidden" not in summary


def test_json_log_formatter_emits_only_approved_structured_fields() -> None:
    record = logging.LogRecord("collector", logging.INFO, "file.py", 1, "run_started", (), None)
    record.event = "run_started"
    record.run_id = "run-1"
    record.source_id = "source-1"
    record.source_name = "Fixture Directory"
    record.region_code = "110000"
    record.source_key = "clinic-1"
    record.request_attempt = 2
    record.http_status = 200
    record.error = None
    record.authorization = "should-never-be-serialized"

    parsed = json.loads(JsonLogFormatter().format(record))

    assert parsed["run_id"] == "run-1"
    assert parsed["http_status"] == 200
    assert "authorization" not in parsed
    assert "should-never-be-serialized" not in json.dumps(parsed)
    for field in (
        "run_id",
        "source_id",
        "source_name",
        "region_code",
        "source_key",
        "request_attempt",
        "http_status",
        "event",
        "error",
    ):
        assert field in parsed
    assert parsed["error"] is None


def test_json_log_formatter_supports_sync_fields_and_excludes_untrusted_payloads() -> None:
    record = logging.LogRecord("worker", logging.ERROR, "file.py", 1, "sync failed", (), None)
    record.event = "source_sync_failed"
    record.task_id = "task-1"
    record.source_id = "source-1"
    record.region_code = "110000"
    record.attempt = 2
    record.stage = "etl"
    record.import_run_id = "run-1"
    record.duration_ms = 123
    record.error_code = "ETL_FAILED"
    record.counts = {"errors": 1}
    record.raw_payload = {"secret": "private row"}

    parsed = json.loads(JsonLogFormatter().format(record))

    assert parsed["task_id"] == "task-1"
    assert parsed["attempt"] == 2
    assert parsed["stage"] == "etl"
    assert parsed["error_code"] == "ETL_FAILED"
    assert "raw_payload" not in parsed
    assert "private row" not in json.dumps(parsed)
