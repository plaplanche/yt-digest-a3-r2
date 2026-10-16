"""SponsorBlock client and sponsor ratio (spec 5.3)."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from yt_digest_node.log import emit

DEFAULT_URL = "https://sponsor.ajay.app"
TIMEOUT_SECONDS = 10
CATEGORIES = ["sponsor", "selfpromo", "interaction"]

State = Literal["ok", "none", "error"]


@dataclass(frozen=True)
class SponsorBlockResult:
    segments: list[tuple[float, float]]
    state: State


def _parse(body: bytes) -> list[tuple[float, float]]:
    items: Any = json.loads(body)
    return [(float(item["segment"][0]), float(item["segment"][1])) for item in items]


def fetch_segments(
    video_id: str, base_url: str | None = None, request_id: str | None = None
) -> SponsorBlockResult:
    """Call SponsorBlock for a video and log `sponsorblock.call`; never raises on a bad call."""
    base = base_url or os.environ.get("SPONSORBLOCK_URL") or DEFAULT_URL
    query = urllib.parse.urlencode(
        {"videoID": video_id, "categories": json.dumps(CATEGORIES, separators=(",", ":"))}
    )
    url = f"{base.rstrip('/')}/api/skipSegments?{query}"
    started = time.monotonic()
    status = 0
    result = SponsorBlockResult([], "error")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            if status == 200:
                result = SponsorBlockResult(_parse(response.read()), "ok")
    except urllib.error.HTTPError as error:
        status = error.code
        if status == 404:
            result = SponsorBlockResult([], "none")
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        pass  # network error or malformed body: no segments, state "error"
    emit(
        "sponsorblock.call",
        video_id=video_id,
        **({"request_id": request_id} if request_id else {}),
        attrs={
            "status": status,
            "segments": len(result.segments),
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return result


def sponsor_ratio(segments: list[tuple[float, float]], duration: float) -> float:
    """Length of the union of the segments clipped to [0, duration], over duration, 3 decimals."""
    if duration <= 0:
        return 0.0
    covered = 0.0
    reach = 0.0
    for start, end in sorted((max(s, 0.0), min(e, duration)) for s, e in segments):
        if end <= start:
            continue
        start = max(start, reach)
        if end > start:
            covered += end - start
            reach = end
    return round(covered / duration, 3)
