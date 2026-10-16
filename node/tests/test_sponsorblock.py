import json
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from yt_digest_node.sponsorblock import fetch_segments, sponsor_ratio

REQUESTS: list[str] = []


class _Handler(BaseHTTPRequestHandler):
    status = 200
    body: bytes = b"[]"

    def do_GET(self) -> None:
        REQUESTS.append(self.path)
        self.send_response(self.status)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def server() -> Iterator[tuple[type[_Handler], str]]:
    REQUESTS.clear()
    handler = type("Handler", (_Handler,), {})
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield handler, f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def _log(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    record: dict[str, Any] = json.loads(lines[0])
    return record


def test_200_returns_segments_and_logs(
    server: tuple[type[_Handler], str], capsys: pytest.CaptureFixture[str]
) -> None:
    handler, url = server
    handler.body = json.dumps(
        [{"segment": [1.5, 4], "category": "sponsor"}, {"segment": [10, 12.25]}]
    ).encode()
    result = fetch_segments("dQw4w9WgXcQ", url, request_id="r1")
    assert (result.segments, result.state) == ([(1.5, 4.0), (10.0, 12.25)], "ok")
    request = urlparse(REQUESTS[0])
    assert request.path == "/api/skipSegments"
    query = parse_qs(request.query)
    assert query["videoID"] == ["dQw4w9WgXcQ"]
    assert json.loads(query["categories"][0]) == ["sponsor", "selfpromo", "interaction"]
    record = _log(capsys)
    assert record["event"] == "sponsorblock.call"
    assert record["video_id"] == "dQw4w9WgXcQ"
    assert record["request_id"] == "r1"
    assert record["attrs"]["status"] == 200
    assert record["attrs"]["segments"] == 2
    assert record["attrs"]["duration_ms"] >= 0


def test_404_is_none(
    server: tuple[type[_Handler], str], capsys: pytest.CaptureFixture[str]
) -> None:
    handler, url = server
    handler.status = 404
    result = fetch_segments("dQw4w9WgXcQ", url)
    assert (result.segments, result.state) == ([], "none")
    attrs = _log(capsys)["attrs"]
    assert (attrs["status"], attrs["segments"]) == (404, 0)


def test_500_is_error(
    server: tuple[type[_Handler], str], capsys: pytest.CaptureFixture[str]
) -> None:
    handler, url = server
    handler.status = 500
    result = fetch_segments("dQw4w9WgXcQ", url)
    assert (result.segments, result.state) == ([], "error")
    attrs = _log(capsys)["attrs"]
    assert (attrs["status"], attrs["segments"]) == (500, 0)


def test_connection_refused_is_error_with_status_0(capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    result = fetch_segments("dQw4w9WgXcQ", f"http://127.0.0.1:{port}")
    assert (result.segments, result.state) == ([], "error")
    attrs = _log(capsys)["attrs"]
    assert (attrs["status"], attrs["segments"]) == (0, 0)


def test_malformed_200_body_is_error(
    server: tuple[type[_Handler], str], capsys: pytest.CaptureFixture[str]
) -> None:
    handler, url = server
    handler.body = b"not json"
    result = fetch_segments("dQw4w9WgXcQ", url)
    assert (result.segments, result.state) == ([], "error")
    assert _log(capsys)["attrs"]["status"] == 200


def test_base_url_defaults_to_the_environment(
    server: tuple[type[_Handler], str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, url = server
    monkeypatch.setenv("SPONSORBLOCK_URL", url)
    assert fetch_segments("dQw4w9WgXcQ").state == "ok"
    assert len(REQUESTS) == 1


def test_ratio_without_segments_is_zero() -> None:
    assert sponsor_ratio([], 100) == 0.0


def test_ratio_counts_overlapping_segments_once() -> None:
    assert sponsor_ratio([(0, 10), (5, 15), (12, 20), (50, 60)], 100) == 0.3


def test_ratio_clips_a_segment_past_the_end() -> None:
    assert sponsor_ratio([(90, 500)], 100) == 0.1
    assert sponsor_ratio([(150, 200)], 100) == 0.0


def test_ratio_clips_negative_start_and_rounds_to_three_decimals() -> None:
    assert sponsor_ratio([(-5, 10)], 100) == 0.1
    assert sponsor_ratio([(0, 1)], 3) == 0.333
