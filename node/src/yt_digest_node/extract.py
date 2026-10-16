"""Extractors and subtitle track choice (spec 5.2)."""

import importlib
import json
import os
import random
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, Protocol

Failure = Literal["unavailable", "blocked"]
Source = Literal["manual", "auto"]

DEFAULT_DELAY = "2-5"
TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Track:
    lang: str
    source: Source
    vtt: str


@dataclass(frozen=True)
class Extraction:
    duration: float
    tracks: list[Track]


class Extractor(Protocol):
    def extract(self, video_id: str) -> Extraction | Failure: ...


class FakeExtractor:
    """Reads `<root>/<video_id>/` with `meta.json` and `<lang>.<manual|auto>.vtt` files."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def extract(self, video_id: str) -> Extraction | Failure:
        directory = self.root / video_id
        if not directory.is_dir():
            return "unavailable"
        meta: dict[str, Any] = {}
        meta_file = directory / "meta.json"
        if meta_file.is_file():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("status") == "unavailable":
            return "unavailable"
        if meta.get("status") == "blocked":
            return "blocked"
        tracks: list[Track] = []
        for path in sorted(directory.glob("*.vtt")):
            lang, _, rest = path.name.removesuffix(".vtt").rpartition(".")
            if lang and rest in ("manual", "auto"):
                source: Source = "manual" if rest == "manual" else "auto"
                tracks.append(Track(lang, source, path.read_text(encoding="utf-8")))
        return Extraction(float(meta.get("duration", 0)), tracks)


def parse_delay(value: str) -> tuple[float, float]:
    """Parse `YT_DELAY_SECONDS`: a range `2-5` or a single number."""
    low, sep, high = value.partition("-")
    first = float(low)
    return (first, float(high) if sep else first)


def _download(url: str) -> str:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return str(response.read().decode("utf-8"))


_BLOCKED_MARKERS = ("confirm you", "not a bot", "sign in to confirm")


def _classify(message: str) -> Failure:
    text = message.lower()
    if any(marker in text for marker in _BLOCKED_MARKERS):
        return "blocked"
    return "unavailable"


class YtDlpExtractor:
    """yt-dlp as a library; `ydl_module` and `download` are replaceable for tests."""

    def __init__(
        self,
        delay: tuple[float, float] = (2.0, 5.0),
        ydl_module: ModuleType | Any = None,
        download: Callable[[str], str] = _download,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.delay = delay
        self.ydl_module = ydl_module
        self.download = download
        self.sleep = sleep

    def options(self) -> dict[str, Any]:
        return {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "quiet": True,
            "no_warnings": True,
        }

    def extract(self, video_id: str) -> Extraction | Failure:
        module: Any = self.ydl_module
        if module is None:
            module = importlib.import_module("yt_dlp")  # lazy: only the real extractor needs it
        self.sleep(random.uniform(*self.delay))
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with module.YoutubeDL(self.options()) as ydl:
                info: dict[str, Any] = ydl.extract_info(url, download=False)
        except module.utils.DownloadError as error:
            return _classify(str(error))
        tracks: list[Track] = []
        sources: list[tuple[str, Source]] = [
            ("subtitles", "manual"),
            ("automatic_captions", "auto"),
        ]
        for key, source in sources:
            for lang, formats in (info.get(key) or {}).items():
                for fmt in formats:
                    if fmt.get("ext") == "vtt" and fmt.get("url"):
                        self.sleep(random.uniform(*self.delay))
                        tracks.append(Track(lang, source, self.download(fmt["url"])))
                        break
        return Extraction(float(info.get("duration") or 0), tracks)


def make_extractor(env: dict[str, str] | None = None) -> Extractor:
    """The fake extractor when `FETCHER_FAKE_YTDLP=1`, else yt-dlp (spec 5.1)."""
    values = os.environ if env is None else env
    if values.get("FETCHER_FAKE_YTDLP") == "1":
        directory = values.get("FAKE_YTDLP_DIR")
        if not directory:
            raise ValueError("FAKE_YTDLP_DIR is required when FETCHER_FAKE_YTDLP=1")
        return FakeExtractor(Path(directory))
    return YtDlpExtractor(parse_delay(values.get("YT_DELAY_SECONDS") or DEFAULT_DELAY))


def choose_track(tracks: list[Track], langs: list[str]) -> Track | None:
    """Manual tracks in language order, then auto tracks in language order."""
    for source in ("manual", "auto"):
        for lang in langs:
            for track in tracks:
                if track.source == source and track.lang == lang:
                    return track
    return None
