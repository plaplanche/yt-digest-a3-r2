import json
from typing import Any

import pytest

from yt_digest_node.log import emit


def test_emit_writes_one_valid_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    emit("sponsorblock.call", video_id="dQw4w9WgXcQ", attrs={"status": 200, "segments": 2})
    out = capsys.readouterr().err
    assert out.endswith("\n") and out.count("\n") == 1
    record = json.loads(out)
    assert record["event"] == "sponsorblock.call"
    assert record["level"] == "info"
    assert record["service"] == "node"
    assert record["attrs"] == {"status": 200, "segments": 2}
    assert record["ts"].endswith("Z")
    assert "request_id" not in record


def test_emit_rejects_an_event_outside_the_catalogue(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError):
        emit("made.up")
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("fields", [{"extra": 1}, {"ts": "x"}, {"service": "worker"}])
def test_emit_rejects_unknown_or_reserved_fields(fields: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        emit("service.started", **fields)


def test_emit_rejects_an_unknown_level() -> None:
    with pytest.raises(ValueError):
        emit("service.started", level="fatal")
