from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest

from yt_digest_node.extract import (
    Extraction,
    FakeExtractor,
    Track,
    YtDlpExtractor,
    choose_track,
    make_extractor,
    parse_delay,
)

FAKE = Path(__file__).parent / "fixtures" / "fake"


def test_fake_missing_directory_is_unavailable() -> None:
    assert FakeExtractor(FAKE).extract("zzzzzzzzzzz") == "unavailable"


def test_fake_meta_status_is_returned() -> None:
    assert FakeExtractor(FAKE).extract("bbbbbbbbbbb") == "blocked"


def test_fake_reads_tracks_and_duration() -> None:
    result = FakeExtractor(FAKE).extract("abcdefghijk")
    assert isinstance(result, Extraction)
    assert result.duration == 60
    assert {(t.lang, t.source) for t in result.tracks} == {("fr", "auto"), ("en", "manual")}


def test_manual_track_beats_auto_track() -> None:
    result = FakeExtractor(FAKE).extract("abcdefghijk")
    assert isinstance(result, Extraction)
    chosen = choose_track(result.tracks, ["fr", "en"])
    assert chosen is not None
    assert (chosen.lang, chosen.source) == ("en", "manual")


def test_auto_used_in_language_order_when_no_manual() -> None:
    tracks = [Track("en", "auto", "e"), Track("fr", "auto", "f")]
    chosen = choose_track(tracks, ["fr", "en"])
    assert chosen is not None and chosen.lang == "fr"


def test_no_matching_track() -> None:
    result = FakeExtractor(FAKE).extract("ccccccccccc")
    assert isinstance(result, Extraction)
    assert choose_track(result.tracks, ["fr", "en"]) is None


def test_make_extractor_selection(tmp_path: Path) -> None:
    fake = make_extractor({"FETCHER_FAKE_YTDLP": "1", "FAKE_YTDLP_DIR": str(tmp_path)})
    assert isinstance(fake, FakeExtractor)
    with pytest.raises(ValueError):
        make_extractor({"FETCHER_FAKE_YTDLP": "1"})
    real = make_extractor({"YT_DELAY_SECONDS": "1-3"})
    assert isinstance(real, YtDlpExtractor) and real.delay == (1.0, 3.0)


def test_parse_delay() -> None:
    assert parse_delay("2-5") == (2.0, 5.0)
    assert parse_delay("0") == (0.0, 0.0)


class _DownloadError(Exception):
    pass


class _Stub:
    """Stands in for the yt_dlp module."""

    utils = SimpleNamespace(DownloadError=_DownloadError)

    def __init__(self, info: dict[str, Any] | None = None, error: str | None = None) -> None:
        self.info = info
        self.error = error
        self.options: dict[str, Any] = {}
        self.urls: list[str] = []

    def YoutubeDL(self, options: dict[str, Any]) -> "_Stub":
        self.options = options
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool) -> dict[str, Any]:
        self.urls.append(url)
        assert download is False
        if self.error:
            raise _DownloadError(self.error)
        assert self.info is not None
        return self.info


def _extractor(stub: _Stub, delays: list[float] | None = None) -> YtDlpExtractor:
    return YtDlpExtractor(
        delay=(2.0, 5.0),
        ydl_module=stub,
        download=lambda url: f"vtt:{url}",
        sleep=(delays if delays is not None else []).append,
    )


def test_ytdlp_options_and_tracks() -> None:
    info = {
        "duration": 42,
        "subtitles": {"en": [{"ext": "json3", "url": "x"}, {"ext": "vtt", "url": "u-en"}]},
        "automatic_captions": {"fr": [{"ext": "vtt", "url": "u-fr"}]},
    }
    stub = _Stub(info)
    delays: list[float] = []
    result = _extractor(stub, delays).extract("abcdefghijk")
    assert stub.options["skip_download"] is True
    assert stub.options["writesubtitles"] is True
    assert stub.options["writeautomaticsub"] is True
    assert stub.options["subtitlesformat"] == "vtt"
    assert "cookiefile" not in stub.options and "cookiesfrombrowser" not in stub.options
    assert result == Extraction(
        42.0, [Track("en", "manual", "vtt:u-en"), Track("fr", "auto", "vtt:u-fr")]
    )
    assert delays and all(2.0 <= d <= 5.0 for d in delays)


def test_ytdlp_private_video_is_unavailable() -> None:
    stub = _Stub(error="ERROR: [youtube] abc: Private video. Sign in if you've been granted access")
    assert _extractor(stub).extract("abcdefghijk") == "unavailable"


def test_ytdlp_bot_check_is_blocked() -> None:
    stub = _Stub(error="ERROR: [youtube] abc: Sign in to confirm you're not a bot")
    assert _extractor(stub).extract("abcdefghijk") == "blocked"
