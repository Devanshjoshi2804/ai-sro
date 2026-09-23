from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sro.application.induction.headers import build_header_plans
from sro.domain.recording.network import Body, CapturedRequest, RedirectHop, primary_of
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.template import Template

_UNREPLAYABLE_RESOURCE_TYPES = frozenset({"websocket"})


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _when(value: object) -> datetime | None:
    text = _text(value)
    if text is None:
        return None
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _epoch(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _headers(value: object) -> dict[str, str]:
    return {
        name: raw
        for name, raw in _mapping(value).items()
        if isinstance(name, str) and name.strip() and isinstance(raw, str)
    }


UNINSPECTABLE = "«whole body: could not be parsed to redact»"

REDACTED = "«redacted»"


def _body(value: object) -> Body | None:
    found = _mapping(value)
    if not found:
        return None
    text = _text(found.get("text"))
    blob = _text(found.get("blob_uri"))
    if text == UNINSPECTABLE:
        text = None
        blob = None
    if text is None and blob is None:
        return None
    return Body(
        text=text,
        blob_uri=blob,
        size_bytes=_int(found.get("size_bytes")) or (len(text) if text else 0),
        mime_type=_text(found.get("mime_type")),
        encoding=_text(found.get("encoding")),
    )


def request_from_rig(stored: Mapping[str, object], *, at: datetime) -> CapturedRequest | None:
    method, url = _text(stored.get("method")), _text(stored.get("url"))
    if not method or not url:
        return None
    return CapturedRequest(
        request_id=_text(stored.get("request_id")) or url,
        method=method,
        url=url,
        resource_type=_text(stored.get("resource_type")) or "xhr",
        started_at=_when(stored.get("started_at")) or at,
        request_headers=_headers(stored.get("request_headers")),
        request_body=_body(stored.get("request_body")),
        status=_int(stored.get("status")),
        status_text=_text(stored.get("status_text")),
        response_headers=_headers(stored.get("response_headers")),
        response_body=_body(stored.get("response_body")),
        redirect_chain=tuple(
            RedirectHop(
                url=hop_url,
                status=_int(hop.get("status")) or 0,
                location=_text(hop.get("location")),
            )
            for hop in _sequence(stored.get("redirect_chain"))
            if isinstance(hop, Mapping) and (hop_url := _text(hop.get("url")))
        ),
        duration_ms=_int(stored.get("duration_ms")),
        from_cache=stored.get("from_cache") is True,
        failure_reason=_text(stored.get("failure_reason")),
        blocked_reason=_text(stored.get("blocked_reason")),
    )


def network_plan_for_gesture(
    gesture: Mapping[str, object],
    requests: Sequence[object],
    *,
    target_system: str = "",
    facility: str,
    bindings: Mapping[str, frozenset[str]] | None = None,
) -> NetworkPlan | None:
    at = _when(gesture.get("at")) or _epoch(gesture.get("at"))

    captured = []
    for stored in requests:
        if not isinstance(stored, Mapping):
            continue
        when = _when(stored.get("started_at")) or at
        if when is None:
            continue
        request = request_from_rig(stored, at=when)
        if request is not None:
            captured.append(request)
    primary = primary_of(captured)
    if primary is None:
        return None

    body = primary.request_body
    unreplayable = _unreplayable(primary)
    return NetworkPlan(
        method=primary.method.strip().upper(),
        url=Template(raw=_bind(primary.url, bindings)),
        headers=build_header_plans(
            primary,
            target_system=target_system or urlsplit(primary.url).hostname or "",
            facility=facility,
        ),
        body=Template(raw=_bind(body.text, bindings)) if body and body.text else None,
        body_blob_uri=body.blob_uri if body and not body.text else None,
        expected_status=primary.status if primary.succeeded else None,
        content_type=primary.header("content-type"),
        replayable=unreplayable is None,
        unreplayable_reason=unreplayable,
    )


def _unreplayable(primary: CapturedRequest) -> str | None:
    if primary.resource_type.strip().lower() in _UNREPLAYABLE_RESOURCE_TYPES:
        return f"the demonstration performed this over {primary.resource_type}"
    if primary.failure_reason:
        return f"the call did not complete: {primary.failure_reason}"
    if primary.blocked_reason:
        return f"the browser blocked the call: {primary.blocked_reason}"
    return None


def _bind(raw: str, bindings: Mapping[str, frozenset[str]] | None) -> str:
    if not bindings:
        return raw.replace("$", "$$")
    try:
        loaded = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw.replace("$", "$$")
    if not isinstance(loaded, dict):
        return raw.replace("$", "$$")

    sentinel = "@@SRO-PARAM-{}@@"
    if "@@SRO-PARAM-" in raw:
        return raw.replace("$", "$$")
    bound: dict[str, object] = {}
    named: list[str] = []
    for key, value in loaded.items():
        if isinstance(value, str) and value in bindings.get(key, frozenset()):
            bound[key] = sentinel.format(len(named))
            named.append(key)
        else:
            bound[key] = value
    text = json.dumps(bound, ensure_ascii=False).replace("$", "$$")
    for index, key in enumerate(named):
        text = text.replace(sentinel.format(index), f"${key}")
    return text
