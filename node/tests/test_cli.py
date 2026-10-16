import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from yt_digest_node.contracts.log_event import LogEvent
from yt_digest_node.contracts.transcript_result import TranscriptResult

SECRET = "Bonjour"
VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
Bonjour tout le monde

00:00:10.000 --> 00:00:12.000
Achetez ce produit maintenant

00:00:20.000 --> 00:00:22.000
Merci et à bientôt
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if "okokokokok1" in self.path:
            body = json.dumps([{"segment": [9, 15]}]).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def sponsorblock() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def fake_dir(tmp_path: Path) -> Path:
    def make(video_id: str, meta: dict[str, Any], tracks: dict[str, str] | None = None) -> None:
        directory = tmp_path / video_id
        directory.mkdir()
        (directory / "meta.json").write_text(json.dumps(meta))
        for name, text in (tracks or {}).items():
            (directory / name).write_text(text)

    make("okokokokok1", {"duration": 30}, {"fr.manual.vtt": VTT})
    make("notranscri1", {"duration": 30}, {"de.manual.vtt": VTT})
    make("blockedvid1", {"duration": 30, "status": "blocked"})
    return tmp_path


def run_cli(fake_dir: Path, sponsorblock: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "FETCHER_FAKE_YTDLP": "1",
        "FAKE_YTDLP_DIR": str(fake_dir),
        "SPONSORBLOCK_URL": sponsorblock,
    }
    return subprocess.run(
        [sys.executable, "-m", "yt_digest_node", "transcript", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def log_events(stderr: str) -> list[LogEvent]:
    return [LogEvent.model_validate_json(line) for line in stderr.splitlines()]


def test_ok_with_sponsor_cut(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "okokokokok1", "--request-id", "req-1")
    assert proc.returncode == 0
    result = TranscriptResult.model_validate_json(proc.stdout)
    assert result.status == "ok"
    assert (result.lang, result.source) == ("fr", "manual")
    assert result.pages == ["Bonjour tout le monde\n\nMerci et à bientôt"]
    assert result.word_count == 8
    assert result.sponsor_ratio == 0.2
    events = log_events(proc.stderr)
    assert [e.event for e in events] == ["service.started", "sponsorblock.call", "fetch.transcript"]
    fetch = events[-1]
    assert fetch.video_id == "okokokokok1" and fetch.request_id == "req-1"
    assert fetch.attrs["outcome"] == "ok"
    assert fetch.attrs["sponsorblock"] == "ok"
    assert fetch.attrs["words"] == 8 and fetch.attrs["pages"] == 1


def test_logs_hold_no_transcript_text(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "okokokokok1")
    assert SECRET not in proc.stderr and "Merci" not in proc.stderr


def test_no_transcript(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "notranscri1")
    assert proc.returncode == 0
    result = TranscriptResult.model_validate_json(proc.stdout)
    assert result.status == "no_transcript" and result.pages == []
    assert log_events(proc.stderr)[-1].attrs["outcome"] == "no_transcript"


def test_unavailable(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "missingvid1")
    assert proc.returncode == 0
    assert TranscriptResult.model_validate_json(proc.stdout).status == "unavailable"


def test_blocked(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "blockedvid1")
    assert proc.returncode == 0
    assert TranscriptResult.model_validate_json(proc.stdout).status == "blocked"


def test_langs_option_selects_language(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "notranscri1", "--langs", "de")
    assert TranscriptResult.model_validate_json(proc.stdout).status == "ok"


def test_invalid_video_id_exits_2(fake_dir: Path, sponsorblock: str) -> None:
    proc = run_cli(fake_dir, sponsorblock, "short")
    assert proc.returncode == 2
    assert proc.stdout == ""
