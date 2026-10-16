from yt_digest_node.paginate import MARKER, count_words, paginate, truncate


def words(n: int, start: int = 0) -> str:
    return " ".join(f"w{i}" for i in range(start, start + n))


def test_truncate_keeps_head_and_tail_around_marker() -> None:
    paragraphs, truncated = truncate([words(25)], 10)
    assert truncated
    assert paragraphs == [words(5), MARKER, words(5, 20)]
    assert count_words(paragraphs) == 10


def test_truncate_keeps_paragraph_breaks_inside_parts() -> None:
    paragraphs, truncated = truncate([words(3), words(3, 3), words(10, 6), words(3, 16)], 8)
    assert truncated
    assert paragraphs == [words(3), words(1, 3), MARKER, words(1, 15), words(3, 16)]


def test_truncate_not_applied_at_the_threshold() -> None:
    assert truncate([words(10)], 10) == ([words(10)], False)


def test_paginate_groups_paragraphs_within_limit() -> None:
    assert paginate([words(3), words(2, 3), words(4, 5)], 5) == [
        words(3) + "\n\n" + words(2, 3),
        words(4, 5),
    ]


def test_paginate_cuts_long_paragraph_and_keeps_order() -> None:
    paragraphs = [words(2), words(12, 2), words(1, 14)]
    pages = paginate(paragraphs, 5)
    assert all(len(p.split()) <= 5 for p in pages)
    assert all(p for p in pages)
    assert " ".join(pages).split() == " ".join(paragraphs).split()


def test_paginate_joins_back_when_nothing_is_cut() -> None:
    paragraphs = [words(3), words(4, 3), words(2, 7)]
    assert "\n\n".join(paginate(paragraphs, 5)) == "\n\n".join(paragraphs)


def test_marker_does_not_count_in_pages() -> None:
    pages = paginate([words(5), MARKER, words(5, 5)], 5)
    assert pages == [words(5) + "\n\n" + MARKER, words(5, 5)]
    assert count_words([q for page in pages for q in page.split("\n\n")]) == 10
