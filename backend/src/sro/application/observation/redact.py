from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from sro.application.capture.rig_wire import (
    EffectEvent,
    FrameHop,
    GestureEvent,
    PageEvent,
    RequestEvent,
    SnapshotEvent,
)
from sro.application.capture.rig_wire import Gesture as WireGesture
from sro.application.observation.admit import Event
from sro.domain.observation.outline import K_OUTLINES_PER_GESTURE, outline_kept
from sro.domain.observation.seen import (
    choice_kept,
    cookies_kept,
    effect_kept,
    extras_kept,
    mail_thread_kept,
    place_kept,
)
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

_TOGGLES = ("checkbox", "radio", "switch")
_TOGGLED = ("checked", "unchecked")

_EVENT_KEYS = {
    kind: frozenset(model.model_fields)
    for kind, model in (
        ("gesture", GestureEvent),
        ("request", RequestEvent),
        ("page", PageEvent),
        ("snapshot", SnapshotEvent),
        ("effect", EffectEvent),
    )
}
K_EFFECT_HOPS = 16
_HOP_KEYS = tuple(FrameHop.model_fields)
_GESTURE_KEYS = frozenset(WireGesture.model_fields)


def redact_events(events: Sequence[Event]) -> tuple[Event, ...]:
    made: dict[str, Mapping[str, object]] = {}
    for event in events:
        gesture = event.get("gesture")
        if isinstance(gesture, Mapping) and isinstance(gesture.get("ref"), str):
            made[_made(event, gesture, gesture["ref"])] = gesture
    return tuple(_event(event, made) for event in events)


def _made(event: Event, gesture: Mapping[str, object], ref: object) -> str:
    return json.dumps(
        [event.get("tab_id"), gesture.get("frame_path"), ref], sort_keys=True, default=str
    )


def _event(event: Event, made: Mapping[str, Mapping[str, object]]) -> Event:
    keys = _EVENT_KEYS.get(str(event.get("kind")))
    out = {key: value for key, value in event.items() if keys is None or key in keys}
    _urls(out)
    gesture = out.get("gesture")
    if isinstance(gesture, Mapping):
        prior_of = gesture.get("prior_of")
        before = made.get(_made(event, gesture, prior_of)) if isinstance(prior_of, str) else None
        out["gesture"] = _gesture(gesture, before)
    request = out.get("request")
    if isinstance(request, Mapping):
        out["request"] = _request(request)
    if out.get("kind") == "effect":
        out["effect"] = effect_kept(out.get("effect")) or {}
        frame_path = out.get("frame_path")
        if isinstance(frame_path, list):
            out["frame_path"] = [
                _hop({key: hop[key] for key in _HOP_KEYS if key in hop})
                for hop in frame_path[:K_EFFECT_HOPS]
                if isinstance(hop, Mapping)
            ]
    if "cookies" in out:
        out["cookies"] = cookies_kept(out["cookies"])
    if "mail_thread" in out:
        out["mail_thread"] = mail_thread_kept(out["mail_thread"])
    out.pop("snapshot", None)

    detail = out.get("detail")
    if isinstance(detail, str) and detail:
        out["detail"] = redact_body(detail, content_type=None)[0]
    return out


def _urls(node: dict[str, object]) -> None:
    for key in _URL_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value:
            node[key] = redact_url(value)


def _gesture(
    gesture: Mapping[str, object], before: Mapping[str, object] | None
) -> dict[str, object]:
    out = {key: value for key, value in gesture.items() if key in _GESTURE_KEYS}
    _urls(out)
    if "outlines" in out:
        raw = out["outlines"]
        out["outlines"] = [
            kept
            for one in (raw if isinstance(raw, list) else [])[-K_OUTLINES_PER_GESTURE:]
            if (kept := outline_kept(one)) is not None
        ]
    if "place" in out:
        out["place"] = place_kept(out["place"])
    if "choice" in out:
        out["choice"] = choice_kept(out["choice"])
    frame_path = out.get("frame_path")
    if isinstance(frame_path, list):
        out["frame_path"] = [_hop(hop) if isinstance(hop, Mapping) else hop for hop in frame_path]
    if "prior" in out:
        out["prior"] = _state(out["prior"], before)
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


def _state(prior: object, before: Mapping[str, object] | None) -> dict[str, object] | None:
    if not isinstance(prior, Mapping):
        return None
    visible, enabled = prior.get("visible"), prior.get("enabled")
    return {
        "value": _setting(prior.get("value"), before),
        "visible": visible if isinstance(visible, bool) else None,
        "enabled": enabled if isinstance(enabled, bool) else None,
    }


def _setting(value: object, before: Mapping[str, object] | None) -> str | None:
    if not isinstance(value, str) or before is None or before.get("secret"):
        return None
    target = before.get("target")
    if not isinstance(target, Mapping) or target.get("secret"):
        return None
    if target.get("role") in _TOGGLES:
        return value if value in _TOGGLED else None
    if target.get("tag") == "select":
        return redact_shapes(value)
    return None


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
    if any(key in out for key in ("labelText", "fullName", "siblingIndex", "siblingCount")):
        out |= extras_kept(out)
        if out.get("secret"):
            out["labelText"] = out["fullName"] = None
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
