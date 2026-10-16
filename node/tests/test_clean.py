from pathlib import Path

from yt_digest_node.clean import clean_cues
from yt_digest_node.vtt import Cue, parse_vtt

FIXTURES = Path(__file__).parent / "fixtures" / "vtt"


def _fixture(name: str, segments: list[tuple[float, float]] | None = None) -> list[str]:
    cues = parse_vtt((FIXTURES / f"{name}.vtt").read_text(encoding="utf-8"))
    return clean_cues(cues, segments or [])


def test_manual_track_paragraphs() -> None:
    assert _fixture("manual") == [
        "Bonjour à tous, bienvenue sur la chaîne. Aujourd'hui, un sujet simple.",
        "Premier point.",
        "Une heure plus tard.",
    ]


def test_auto_track_drops_rolling_duplicates_and_inline_tags() -> None:
    assert _fixture("auto") == ["hello everyone welcome to the show today we cook", "and eat"]


def test_annotations_are_removed_and_entities_decoded() -> None:
    assert _fixture("annotated") == [
        "Tom & Jerry are here. 5 < 6 and it's true done",
    ]


def test_annotation_only_cue_does_not_count_as_kept_for_gaps() -> None:
    cues = [Cue(0, 1, ("a",)), Cue(1, 4, ("[Musique]",)), Cue(4, 5, ("b",))]
    assert clean_cues(cues, []) == ["a", "b"]


def test_gap_of_exactly_two_seconds_starts_a_paragraph() -> None:
    cues = [Cue(1.1, 3.1, ("a",)), Cue(5.1, 6.0, ("b",))]
    assert clean_cues(cues, []) == ["a", "b"]


def test_gap_of_one_point_nine_seconds_does_not() -> None:
    cues = [Cue(1.0, 3.0, ("a",)), Cue(4.9, 6.0, ("b",))]
    assert clean_cues(cues, []) == ["a b"]


def test_duplicate_is_compared_with_the_previous_kept_line_across_paragraphs() -> None:
    cues = [Cue(0, 1, ("a",)), Cue(10, 11, ("a", "b"))]
    assert clean_cues(cues, []) == ["a", "b"]


def test_sponsor_segments_drop_cues_by_midpoint_start_inclusive_end_exclusive() -> None:
    cues = [Cue(0, 2, ("in",)), Cue(3, 5, ("edge",)), Cue(5, 7, ("out",)), Cue(8, 9, ("kept",))]
    # midpoints: 1 (inside), 4 (inside), 6 (== end, kept), 8.5
    assert clean_cues(cues, [(1.0, 6.0)]) == ["out kept"]
    assert clean_cues([Cue(0, 2, ("x",))], [(1.0, 5.0)]) == []


def test_empty_input() -> None:
    assert clean_cues([], []) == []
