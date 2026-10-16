"""WebVTT parsing (spec 5.4, step 1)."""

import re
from dataclasses import dataclass

_TIMESTAMP = r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})"
_TIMING = re.compile(rf"^\s*{_TIMESTAMP}\s+-->\s+{_TIMESTAMP}(?:\s.*)?$")
_IGNORED_BLOCKS = ("NOTE", "STYLE", "REGION")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    lines: tuple[str, ...]


def _seconds(hours: str | None, minutes: str, seconds: str, millis: str) -> float:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def _is_ignored(first_line: str) -> bool:
    head = first_line.split(maxsplit=1)[0] if first_line.strip() else ""
    return head in _IGNORED_BLOCKS or first_line.startswith("WEBVTT")


def parse_vtt(text: str) -> list[Cue]:
    """Parse VTT text into cues, ignoring the header, NOTE/STYLE/REGION blocks and cue settings."""
    cues: list[Cue] = []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip("\n")
    for block in re.split(r"\n[ \t]*\n", normalized):
        lines = block.split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines or _is_ignored(lines[0]):
            continue
        # A cue identifier may precede the timing line.
        for index, line in enumerate(lines[:2]):
            match = _TIMING.match(line)
            if match:
                g = match.groups()
                cues.append(Cue(_seconds(*g[0:4]), _seconds(*g[4:8]), tuple(lines[index + 1 :])))
                break
    return cues
