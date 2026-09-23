from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from sro.domain.observation.gesture import Call
from sro.domain.observation.trim import looks_like_an_id


@dataclass(frozen=True, slots=True)
class VerifiedWrite:
    method: str
    path_pattern: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())


def _segments(path: str) -> tuple[str, ...]:
    return tuple(segment for segment in path.split("/") if segment)


def _is_traversal_segment(segment: str) -> bool:
    decoded = unquote(segment)
    return decoded in (".", "..") or "/" in decoded or "\\" in decoded


def _matches_path(path: str, pattern: str) -> bool:
    path_segments, pattern_segments = _segments(path), _segments(pattern)
    if len(path_segments) != len(pattern_segments):
        return False
    if any(_is_traversal_segment(segment) for segment in path_segments):
        return False
    return all(
        (pattern_segment.startswith("{") and pattern_segment.endswith("}"))
        or pattern_segment == path_segment
        for path_segment, pattern_segment in zip(path_segments, pattern_segments, strict=True)
    )


def learned_pattern(url: str, values: Mapping[str, str]) -> str:
    said = {value.strip().lower() for value in values.values() if value.strip()}
    segments = _segments(urlsplit(url).path)
    last = len(segments) - 1
    return "/" + "/".join(
        "{id}"
        if (nth == last and segment.lower() in said) or looks_like_an_id(segment)
        else segment
        for nth, segment in enumerate(segments)
    )


def verified_write_for(call: Call, verified: tuple[VerifiedWrite, ...]) -> VerifiedWrite | None:
    method = call.method.upper()
    path = urlsplit(call.url).path
    for entry in verified:
        if entry.method == method and _matches_path(path, entry.path_pattern):
            return entry
    return None
