"""The transcript pipeline, from a video id to a transcript result (spec 5)."""

import os
import time
from dataclasses import dataclass
from importlib.metadata import version

from yt_digest_node.clean import clean_cues
from yt_digest_node.contracts.transcript_result import TranscriptResult
from yt_digest_node.extract import Extraction, Extractor, choose_track
from yt_digest_node.log import emit
from yt_digest_node.paginate import count_words, paginate, truncate
from yt_digest_node.sponsorblock import fetch_segments, sponsor_ratio
from yt_digest_node.vtt import parse_vtt


@dataclass(frozen=True)
class Config:
    langs: list[str]
    max_words: int
    page_words: int

    @classmethod
    def from_env(cls, langs: str | None = None) -> "Config":
        """Read the environment (spec 5.1); raises ValueError on a bad value."""
        raw = langs or os.environ.get("TRANSCRIPT_LANGS") or "fr,en"
        parsed = [lang.strip() for lang in raw.split(",") if lang.strip()]
        if not parsed:
            raise ValueError("no language given")
        max_words = int(os.environ.get("MAX_WORDS") or 60000)
        page_words = int(os.environ.get("PAGE_WORDS") or 12000)
        if max_words < 1 or page_words < 1:
            raise ValueError("MAX_WORDS and PAGE_WORDS must be positive")
        return cls(parsed, max_words, page_words)


def _empty(video_id: str, status: str) -> TranscriptResult:
    return TranscriptResult.model_validate(
        {
            "video_id": video_id,
            "status": status,
            "lang": None,
            "source": None,
            "word_count": 0,
            "truncated": False,
            "sponsor_ratio": None,
            "pages": [],
        }
    )


def run(
    video_id: str,
    config: Config,
    extractor: Extractor,
    request_id: str | None = None,
) -> TranscriptResult:
    """Run the whole pipeline and log `fetch.transcript`; never logs transcript text."""
    started = time.monotonic()
    extraction = extractor.extract(video_id)
    attrs: dict[str, object] = {}
    if isinstance(extraction, Extraction):
        result = _transcribe(video_id, config, extraction, request_id, attrs)
    else:
        result = _empty(video_id, extraction)
    attrs["outcome"] = result.status.value
    attrs["words"] = result.word_count
    attrs["pages"] = len(result.pages)
    attrs["duration_ms"] = round((time.monotonic() - started) * 1000)
    emit("fetch.transcript", video_id=video_id, request_id=request_id, attrs=attrs)
    return result


def _transcribe(
    video_id: str,
    config: Config,
    extraction: Extraction,
    request_id: str | None,
    attrs: dict[str, object],
) -> TranscriptResult:
    track = choose_track(extraction.tracks, config.langs)
    if track is None:
        return _empty(video_id, "no_transcript")
    sponsors = fetch_segments(video_id, request_id=request_id)
    ratio = (
        None if sponsors.state == "error" else sponsor_ratio(sponsors.segments, extraction.duration)
    )
    paragraphs = clean_cues(parse_vtt(track.vtt), sponsors.segments)
    paragraphs, truncated = truncate(paragraphs, config.max_words)
    pages = paginate(paragraphs, config.page_words)
    attrs["source"] = track.source
    attrs["sponsor_ratio"] = ratio
    attrs["sponsorblock"] = sponsors.state
    return TranscriptResult.model_validate(
        {
            "video_id": video_id,
            "status": "ok",
            "lang": track.lang,
            "source": track.source,
            "word_count": count_words(paragraphs),
            "truncated": truncated,
            "sponsor_ratio": ratio,
            "pages": pages,
        }
    )


def package_version() -> str:
    return version("yt-digest-node")
