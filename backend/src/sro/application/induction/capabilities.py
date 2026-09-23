from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.execution.answer import read_answer
from sro.application.induction.sites import parse_json, url_path_segments
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest

_ASSETS = (".png", ".jpg", ".gif", ".svg", ".css", ".js", ".woff", ".ico")


@dataclass(frozen=True, slots=True)
class ReadCapability:
    request: CapturedRequest
    entity: str

    rows: int

    counted: int | None = None


def normalise(name: str) -> str:
    lowered = "".join(character for character in name.lower() if character.isalnum())
    for prefix in ("warehouse", "wm", "data"):
        if lowered.startswith(prefix) and len(lowered) > len(prefix) + 2:
            lowered = lowered[len(prefix) :]
    return lowered[:-1] if lowered.endswith("s") else lowered


def reads_about(frames: tuple[ActionFrame, ...], entity: str) -> tuple[ReadCapability, ...]:
    wanted = normalise(entity)
    found: dict[str, ReadCapability] = {}

    for frame in frames:
        for request in frame.requests:
            if not _is_a_read(request):
                continue
            resource = _resource_of(request.url)
            if not resource or wanted not in normalise(resource):
                continue
            counted = read_answer(request.response_text, url=request.url)
            if counted is None:
                continue
            rows = counted.rows
            if not _records_of(request, frames):
                continue
            found.setdefault(
                normalise(resource),
                ReadCapability(request, resource, rows, counted=counted.counted),
            )

    return tuple(sorted(found.values(), key=lambda read: (normalise(read.entity) != wanted,)))


def _records_of(request: CapturedRequest, frames: tuple[ActionFrame, ...]) -> bool:
    shape = _written_shape(frames)
    if not shape:
        return True
    return len(shape & _record_fields(request.response_text)) >= 2


def _written_shape(frames: tuple[ActionFrame, ...]) -> frozenset[str]:
    for frame in frames:
        for request in frame.requests:
            if not request.is_mutation or not request.succeeded:
                continue
            document = parse_json(request.request_text)
            payload = document.get("data") if isinstance(document, dict) else None
            if isinstance(payload, dict):
                return frozenset(payload)
            if isinstance(document, dict):
                return frozenset(document)
    return frozenset()


def _record_fields(text: str | None) -> frozenset[str]:
    document = parse_json(text) if text else None
    data = document.get("data") if isinstance(document, dict) else None
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else None
    return frozenset(data) if isinstance(data, dict) else frozenset()


def _is_a_read(request: CapturedRequest) -> bool:
    if request.method.upper() != "GET" or request.status is None:
        return False
    if not 200 <= request.status < 300:
        return False
    if is_background_traffic(request.url):
        return False
    path = urlsplit(request.url).path.lower()
    return not path.endswith(_ASSETS)


def _resource_of(url: str) -> str:
    segments = url_path_segments(url)
    for segment in reversed(segments):
        if any(character.isalpha() for character in segment):
            return segment
    return ""


def wrote_to(frames: tuple[ActionFrame, ...]) -> str | None:
    for frame in reversed(frames):
        for request in frame.requests:
            if request.is_mutation and request.status and 200 <= request.status < 300:
                collection = _collection_of(request.url)
                if collection:
                    return collection
    return None


def _collection_of(url: str) -> str:
    for segment in reversed(url_path_segments(url)):
        if any(character.isalpha() for character in segment) and not _is_a_record(segment):
            return segment
    return ""


def _is_a_record(segment: str) -> bool:
    return any(character.isdigit() for character in segment) or len(segment) > 24
