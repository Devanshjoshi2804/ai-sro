from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from sro.application.observation.admit import Event
from sro.domain.recording.redaction import redact_body
from sro.domain.recording.sensitivity import (
    REDACTED,
    SignInFlow,
    classify_header,
    is_secret,
    is_secret_field,
    is_sign_in_field,
    redact_shapes,
    redact_url,
)

_URL_KEYS = ("url", "frame_url", "page_url", "location")

_PROSE = ("name", "text", "fieldLabel")

_KEEPS_ITS_VALUE = ("press", "scroll")

_PATHS = frozenset({"cssPath", "xpath", "query", "chain"})

_ABSOLUTE = ("http://", "https://")


def redact_events(events: Sequence[Event]) -> tuple[Event, ...]:
    signing_in = _signing_in(events)
    typed = _typed(event for index, event in enumerate(events) if index in signing_in)
    return tuple(
        _structure_only(_event(event), typed) if index in signing_in else _event(event)
        for index, event in enumerate(events)
    )


def _signing_in(events: Sequence[Event]) -> set[int]:
    flows: dict[object, SignInFlow] = {}
    visits: dict[object, int] = {}
    pages: list[tuple[object, int, str | None]] = []
    found: set[int] = set()
    for index, event in enumerate(events):
        tab = event.get("tab_id")
        page = _page_of(event)
        flow = flows.setdefault(tab, SignInFlow())
        if event.get("kind") == "page" and event.get("page_kind") == "navigated":
            visits[tab] = visits.get(tab, 0) + 1
        inside = flow.navigated(page) if event.get("kind") == "page" and page else False
        pages.append((tab, visits.get(tab, 0), page))
        if inside or flow.redirect is not None or _marked(event) or _on_a_sign_in_field(event):
            found.add(index)
    seen = {pages[index] for index in found}
    return found | {index for index, where in enumerate(pages) if where in seen}


def _page_of(event: Event) -> str | None:
    gesture = event.get("gesture")
    for value in (
        event.get("page_url"),
        event.get("frame_url"),
        event.get("url"),
        gesture.get("url") if isinstance(gesture, Mapping) else None,
    ):
        if isinstance(value, str) and value:
            return value
    return None


def _marked(event: Event) -> bool:
    gesture = event.get("gesture")
    return event.get("sign_in") is True or (
        isinstance(gesture, Mapping) and gesture.get("sign_in") is True
    )


def _on_a_sign_in_field(event: Event) -> bool:
    gesture = event.get("gesture")
    target = gesture.get("target") if isinstance(gesture, Mapping) else None
    attributes = target.get("attributes") if isinstance(target, Mapping) else None
    return isinstance(attributes, Mapping) and is_sign_in_field(attributes)


def _typed(events: Iterable[Event]) -> tuple[str, ...]:
    values = [
        value
        for event in events
        if isinstance(gesture := event.get("gesture"), Mapping)
        and gesture.get("kind") not in _KEEPS_ITS_VALUE
        and isinstance(value := gesture.get("value"), str)
        and value
    ]
    joined = "".join(values)
    return tuple(
        sorted({value for value in (*values, joined) if len(value) > 1}, key=len, reverse=True)
    )


def _structure_only(event: Event, typed: tuple[str, ...]) -> Event:
    out = dict(event)
    out["sign_in"] = True
    gesture = out.get("gesture")
    if isinstance(gesture, Mapping):
        kept = dict(gesture) | {"sign_in": True}
        if kept.get("kind") not in _KEEPS_ITS_VALUE:
            kept["value"] = None
        target = kept.get("target")
        if isinstance(target, Mapping):
            kept["target"] = _without(
                {**target, "attributes": _valueless(target.get("attributes"))}, typed
            )
        out["gesture"] = kept
    request = out.get("request")
    if isinstance(request, Mapping):
        out["request"] = {**request, "request_body": None, "response_body": None}
    if out.get("kind") == "snapshot":
        out["snapshot"] = {}
    return out


def _valueless(attributes: object) -> dict[str, object]:
    if not isinstance(attributes, Mapping):
        return {}
    return {str(key): value for key, value in attributes.items() if key != "value"}


def _without(node: object, typed: tuple[str, ...]) -> object:
    if isinstance(node, str):
        for value in typed:
            node = node.replace(value, REDACTED)
        return node
    if isinstance(node, Mapping):
        return {
            key: value if key in _PATHS else _without(value, typed) for key, value in node.items()
        }
    if isinstance(node, list):
        return [_without(value, typed) for value in node]
    return node


def _event(event: Event) -> Event:
    out = dict(event)
    _urls(out)
    gesture = out.get("gesture")
    if isinstance(gesture, Mapping):
        out["gesture"] = _gesture(gesture)
    request = out.get("request")
    if isinstance(request, Mapping):
        out["request"] = _request(request)
    snapshot = out.get("snapshot")
    if isinstance(snapshot, Mapping):
        out["snapshot"] = _shapes_only(snapshot)

    detail = out.get("detail")
    if isinstance(detail, str) and detail:
        out["detail"] = redact_body(detail, content_type=None)[0]
    return out


def _shapes_only(node: object) -> object:
    if isinstance(node, str):
        return redact_url(node) if node.startswith(_ABSOLUTE) else redact_shapes(node)
    if isinstance(node, Mapping):
        return {key: _shapes_only(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_shapes_only(value) for value in node]
    return node


def _urls(node: dict[str, object]) -> None:
    for key in _URL_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value:
            node[key] = redact_url(value)


def _gesture(gesture: Mapping[str, object]) -> dict[str, object]:
    out = dict(gesture)
    _urls(out)
    target = out.get("target")
    marked = bool(out.get("secret")) or (isinstance(target, Mapping) and bool(target.get("secret")))
    value = out.get("value")
    if marked:
        out["value"] = None
    elif isinstance(value, str) and value:
        out["value"] = redact_shapes(value)
    if isinstance(target, Mapping):
        out["target"] = _element(target)
    return out


def _element(node: Mapping[str, object]) -> dict[str, object]:
    out = dict(node)
    for key in _PROSE:
        value = out.get(key)
        if isinstance(value, str) and value:
            out[key] = redact_shapes(value)
    attributes = out.get("attributes")
    if isinstance(attributes, Mapping):
        out["attributes"] = _attributes(attributes)
    component = out.get("component")
    if isinstance(component, Mapping):
        out["component"] = _element(component)
    return out


def _attributes(node: object) -> object:
    if isinstance(node, Mapping):
        return {
            key: REDACTED if is_secret_field(str(key)) else _attributes(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_attributes(item) for item in node]
    if isinstance(node, str):
        return redact_url(node)
    return node


def _request(request: Mapping[str, object]) -> dict[str, object]:
    out = dict(request)
    _urls(out)
    for key in ("request_headers", "response_headers"):
        headers = out.get(key)
        if isinstance(headers, Mapping):
            out[key] = _headers(headers)
    for key in ("request_body", "response_body"):
        body = out.get(key)
        if isinstance(body, Mapping):
            out[key] = _body(body)
    chain = out.get("redirect_chain")
    if isinstance(chain, list):
        out["redirect_chain"] = [_hop(hop) if isinstance(hop, Mapping) else hop for hop in chain]
    return out


def _headers(headers: Mapping[str, object]) -> dict[str, object]:
    return {
        name: REDACTED
        if is_secret(classify_header(str(name)))
        else (redact_shapes(value) if isinstance(value, str) else value)
        for name, value in headers.items()
    }


def _body(body: Mapping[str, object]) -> dict[str, object]:
    out = dict(body)
    text = out.get("text")
    if not isinstance(text, str) or not text:
        return out
    mime = out.get("mime_type")
    cleaned, removed = redact_body(text, content_type=mime if isinstance(mime, str) else None)
    out["text"] = cleaned
    if removed:
        already = out.get("redacted_fields")
        existing = list(already) if isinstance(already, list) else []
        out["redacted_fields"] = list(dict.fromkeys([*existing, *removed]))
    return out


def _hop(hop: Mapping[str, object]) -> dict[str, object]:
    out = dict(hop)
    _urls(out)
    for key, value in list(out.items()):
        if "headers" in str(key) and isinstance(value, Mapping):
            out[key] = _headers(value)
    return out
