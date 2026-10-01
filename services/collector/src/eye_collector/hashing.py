from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Hash a JSON object using stable UTF-8 serialization."""
    try:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("payload cannot be encoded as canonical JSON") from error
    return hashlib.sha256(serialized).hexdigest()
