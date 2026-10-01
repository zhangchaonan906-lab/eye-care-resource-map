from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

_HEADER_SECRET = re.compile(
    r"(?i)\b(authorization|cookie|set-cookie)\s*:\s*"
    r"(?:(?:bearer|basic)\s+)?[^\s,;]+"
)
_NAMED_SECRET = re.compile(
    r"(?i)\b(token|secret|password|api[_-]?key)([\"']?\s*[:=]\s*[\"']?)[^&\s,;\"']+"
)
_QUERY_VALUE = re.compile(r"([?&][^=&\s]+)=([^&\s]+)")


def _redact(text: str) -> str:
    text = _HEADER_SECRET.sub(lambda match: f"{match.group(1)}: <redacted>", text)
    text = _NAMED_SECRET.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", text)
    return _QUERY_VALUE.sub(r"\1=<redacted>", text).replace("\r", " ").replace("\n", " ")


def safe_error_summary(error: BaseException) -> str:
    summary = f"{type(error).__name__}: {_redact(str(error))}".strip()
    return summary[:500] or type(error).__name__


class JsonLogFormatter(logging.Formatter):
    """Serialize only a fixed set of collector fields; arbitrary extras are ignored."""

    _fields = (
        "event",
        "run_id",
        "source_id",
        "source_name",
        "region_code",
        "source_key",
        "request_attempt",
        "http_status",
        "url",
        "error",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": _redact(record.getMessage()),
        }
        for field in self._fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = _redact(value) if isinstance(value, str) else value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def safe_log_origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.hostname or ''}"
