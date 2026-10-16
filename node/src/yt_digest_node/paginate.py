"""Truncation (spec 5.5) and pages (spec 5.6)."""

from collections.abc import Sequence

MARKER = "[…]"


def count_words(paragraphs: Sequence[str]) -> int:
    """Words of the paragraphs, the truncation marker excluded."""
    return sum(len(p.split()) for p in paragraphs if p != MARKER)


def truncate(paragraphs: Sequence[str], max_words: int) -> tuple[list[str], bool]:
    """Keep the first and last `max_words // 2` words around a `[…]` paragraph when too long."""
    if count_words(paragraphs) <= max_words:
        return list(paragraphs), False
    half = max_words // 2
    head: list[str] = []
    budget = half
    for paragraph in paragraphs:
        if budget <= 0:
            break
        words = paragraph.split()
        head.append(" ".join(words[:budget]))
        budget -= len(words)
    tail: list[str] = []
    budget = half
    for paragraph in reversed(paragraphs):
        if budget <= 0:
            break
        words = paragraph.split()
        tail.append(" ".join(words[-budget:]))
        budget -= len(words)
    tail.reverse()
    return [*head, MARKER, *tail], True


def paginate(paragraphs: Sequence[str], page_words: int) -> list[str]:
    """Group paragraphs into pages of at most `page_words` words; cut an overlong paragraph."""
    pages: list[str] = []
    current: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal current, size
        if current:
            pages.append("\n\n".join(current))
        current, size = [], 0

    for paragraph in paragraphs:
        words = paragraph.split()
        if paragraph == MARKER or size + len(words) <= page_words:
            current.append(paragraph)
            size += 0 if paragraph == MARKER else len(words)
            continue
        flush()
        while len(words) > page_words:
            pages.append(" ".join(words[:page_words]))
            words = words[page_words:]
        current, size = [" ".join(words)], len(words)
    flush()
    return pages
