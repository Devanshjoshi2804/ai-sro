from __future__ import annotations

from collections.abc import Iterator

from sro.application.induction import jsonutil
from sro.application.induction.sites import parse_json
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest


def _writes(frame: ActionFrame) -> Iterator[CapturedRequest]:
    return (
        request
        for request in frame.requests
        if request.is_mutation and request.succeeded and not is_background_traffic(request.url)
    )


def write_document(frame: ActionFrame) -> jsonutil.JsonValue | None:
    write = next(_writes(frame), None)
    return parse_json(write.request_text) if write is not None else None


def key_filled_by(frame: ActionFrame, within: ActionFrame) -> str | None:
    typed = frame.action.value
    if not typed or frame.action.secret:
        return None

    wanted = tidied(typed)
    if not wanted:
        return None

    documents = [
        document
        for request in _writes(within)
        if isinstance(document := parse_json(request.request_text), dict)
    ]
    found = [
        pointer
        for document in documents
        for pointer, leaf in jsonutil.leaves(document)
        if tidied(jsonutil.as_text(leaf)) == wanted
    ]
    if len(found) > 1:
        named = _named(frame)
        found = [pointer for pointer in found if tidied(pointer.rsplit("/", 1)[-1]) in named]
    return found[0] if len(found) == 1 else None


def _named(frame: ActionFrame) -> frozenset[str]:
    target = frame.action.target
    if target is None:
        return frozenset()
    component = target.component
    candidates = (
        component.item_id if component else None,
        component.name if component else None,
        target.attributes.get("name"),
    )
    return frozenset(tidied(name) for name in candidates if name and name.strip())


def tidied(value: str) -> str:
    return value.strip().casefold()
