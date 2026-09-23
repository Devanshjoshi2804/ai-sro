from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.observation.admit import Event
from sro.domain.recording.redaction import redact_body
from sro.domain.recording.sensitivity import (
    REDACTED,
    classify_header,
    is_secret,
    is_secret_field,
    redact_shapes,
    redact_url,
)

_URL_KEYS = ("url", "frame_url", "page_url", "location")

_PROSE = ("name", "text", "fieldLabel")


def redact_events(events: Sequence[Event]) -> tuple[Event, ...]:
    return tuple(_event(event) for event in events)


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
        return redact_shapes(node)
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
