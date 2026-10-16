"""Structured logger: one JSON line per event on standard error, validated against the catalogue."""

import sys
from datetime import UTC, datetime
from typing import Any

from yt_digest_node.contracts.log_event import LogEvent

_RESERVED = {"ts", "service"}


def emit(event: str, level: str = "info", **fields: Any) -> None:
    """Write one log line; raises ValueError for an unknown event, level or field."""
    reserved = _RESERVED & fields.keys()
    if reserved:
        raise ValueError(f"fields set by the logger: {sorted(reserved)}")
    ts = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    record = LogEvent.model_validate(
        {"ts": ts, "level": level, "service": "node", "event": event, "attrs": {}, **fields}
    )
    sys.stderr.write(record.model_dump_json(exclude_none=True) + "\n")
