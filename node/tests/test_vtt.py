from pathlib import Path

from yt_digest_node.vtt import Cue, parse_vtt

FIXTURES = Path(__file__).parent / "fixtures" / "vtt"


def test_parse_manual_track_ignores_header_blocks_and_cue_settings() -> None:
    cues = parse_vtt((FIXTURES / "manual.vtt").read_text(encoding="utf-8"))
    assert cues == [
        Cue(1.0, 3.0, ("Bonjour à tous,",)),
        Cue(3.5, 5.0, ("bienvenue sur la chaîne.", "Aujourd'hui, un sujet simple.")),
        Cue(7.0, 9.0, ("Premier point.",)),
        Cue(3610.0, 3612.0, ("Une heure plus tard.",)),
    ]


def test_parse_accepts_short_timestamps_and_crlf() -> None:
    cues = parse_vtt("WEBVTT\r\n\r\n01:02.500 --> 01:04.000 line:0\r\nhi\r\n")
    assert cues == [Cue(62.5, 64.0, ("hi",))]


def test_parse_ignores_note_style_and_region_blocks() -> None:
    text = (
        "WEBVTT\n\nNOTE 00:00:00.000 --> 00:00:01.000\nnot a cue\n\n"
        "STYLE\n::cue {}\n\nREGION\nid:a\n\n00:00:01.000 --> 00:00:02.000\nreal\n"
    )
    assert parse_vtt(text) == [Cue(1.0, 2.0, ("real",))]
