import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from yt_digest_node.contracts.log_event import Event, LogEvent
from yt_digest_node.contracts.transcript_result import TranscriptResult

REPO = Path(__file__).resolve().parents[2]
TS_DIR = "worker/src/contracts"
PY_DIR = "node/src/yt_digest_node/contracts"


def result(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "video_id": "dQw4w9WgXcQ",
        "status": "ok",
        "lang": "en",
        "source": "manual",
        "word_count": 3,
        "truncated": False,
        "sponsor_ratio": 0.5,
        "pages": ["one two three"],
    }
    return {**base, **changes}


def line(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ts": "2026-10-16T12:00:00.000Z",
        "level": "info",
        "service": "node",
        "event": "service.started",
        "attrs": {"version": "0.1.0"},
    }
    return {**base, **changes}


def test_valid_result_is_accepted() -> None:
    assert TranscriptResult.model_validate(result()).word_count == 3
    empty = result(status="no_transcript", lang=None, source=None, sponsor_ratio=None, pages=[])
    assert TranscriptResult.model_validate(empty).pages == []


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": 1},
        {"video_id": "short"},
        {"video_id": "bad id with sp"},
        {"status": "done"},
        {"source": "robot"},
        {"word_count": -1},
        {"sponsor_ratio": 1.5},
        {"truncated": "yes"},
    ],
)
def test_invalid_result_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        TranscriptResult.model_validate(result(**changes))


def test_valid_log_line_is_accepted() -> None:
    assert LogEvent.model_validate(line(video_id="dQw4w9WgXcQ")).event is Event.SERVICE_STARTED


@pytest.mark.parametrize(
    "changes",
    [
        {"event": "made.up"},
        {"level": "fatal"},
        {"service": "browser"},
        {"ts": "yesterday"},
        {"x": 1},
    ],
)
def test_invalid_log_line_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LogEvent.model_validate(line(**changes))


def test_catalogue_matches_the_schema() -> None:
    schema = json.loads((REPO / "contracts/log-event.schema.json").read_text())
    assert [e.value for e in Event] == schema["properties"]["event"]["enum"]


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "repo"
    for name in ("contracts", "scripts", "node", "worker/src"):
        shutil.copytree(
            REPO / name,
            dest / name,
            ignore=shutil.ignore_patterns(".venv", "node_modules", "__pycache__", ".*_cache"),
        )
    return dest


def check(repo: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": sys.prefix}
    return subprocess.run(
        ["./scripts/contracts.sh", "--check"],
        check=False,
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_check_passes_on_committed_files(repo_copy: Path) -> None:
    done = check(repo_copy)
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("target", [f"{TS_DIR}/log-event.ts", f"{PY_DIR}/transcript_result.py"])
def test_check_fails_when_a_generated_file_is_edited(repo_copy: Path, target: str) -> None:
    with (repo_copy / target).open("a") as f:
        f.write("// hand edit\n")
    done = check(repo_copy)
    assert done.returncode == 1
    assert target in done.stderr


def test_check_fails_when_a_schema_changes_without_regeneration(repo_copy: Path) -> None:
    schema = repo_copy / "contracts/log-event.schema.json"
    schema.write_text(
        schema.read_text().replace('"sponsorblock.call"', '"sponsorblock.call", "new.event"')
    )
    done = check(repo_copy)
    assert done.returncode == 1
    assert f"{TS_DIR}/log-event.ts" in done.stderr
    assert f"{PY_DIR}/log_event.py" in done.stderr


def test_check_fails_when_a_generated_file_is_missing(repo_copy: Path) -> None:
    (repo_copy / TS_DIR / "transcript-result.ts").unlink()
    done = check(repo_copy)
    assert done.returncode == 1
    assert f"{TS_DIR}/transcript-result.ts" in done.stderr
