"""A2 — what one gesture looks like to the model that reads it.

Token discipline, because A3 runs once per gesture and a day is thousands of
them. cssPath and xpath are excluded on purpose: long, meaningless to a model,
and the two locators that break. The runner still reads them from the stored row.
"""

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlparse

from rig.records import Gesture
from rig.wire import Body, Request, Target

VALUE_CHARS = 80
BODY_KEYS = 40

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def thin(target: Target) -> bool:
    """True when nothing here would tell a model what the control is."""
    component = target.component
    return not any(
        (
            target.name,
            target.text,
            component.fieldLabel if component else None,
            component.itemId if component else None,
        )
    )


def path_shape(url: str) -> str:
    """/data/WM/wm/addresses/1183 -> /data/WM/wm/addresses/*"""
    parts = urlparse(url).path.split("/")
    return "/".join("*" if _looks_like_an_id(part) else part for part in parts)


def _looks_like_an_id(part: str) -> bool:
    """Digits are what make a segment an id, not hyphens and length.

    The rule this replaced starred any long hyphenated segment, which erased
    ordinary route words -- /api/order-status became /api/* -- and still missed
    short numeric slugs like sku-123456.
    """
    if not part:
        return False
    if part.isdigit() or _UUID.match(part):
        return True
    digits = sum(character.isdigit() for character in part)
    return len(part) >= 8 and digits >= len(part) // 2


def body_keys(body: Body | None) -> dict[str, str] | None:
    """Keys and short values. Never the prose, never the whole payload."""
    if body is None or not body.text:
        return None

    parsed: object
    if body.mime_type == "application/x-www-form-urlencoded":
        parsed = dict(parse_qsl(body.text))
    else:
        try:
            parsed = json.loads(body.text)
        except (ValueError, TypeError):
            return {"_": body.text[:VALUE_CHARS]}

    if not isinstance(parsed, dict):
        return {"_": str(parsed)[:VALUE_CHARS]}

    return {key: str(parsed[key])[:VALUE_CHARS] for key in list(parsed)[:BODY_KEYS]}


def _call(request: Request) -> dict[str, Any]:
    return {
        "method": request.method,
        "path": path_shape(request.url),
        "host": urlparse(request.url).netloc,
        "status": request.status,
        "failed": request.failure_reason,
        "body_keys": body_keys(request.request_body),
        "response_keys": body_keys(request.response_body),
    }


def trim(gesture: Gesture) -> dict[str, Any]:
    target = gesture.gesture.target
    component = target.component
    # Belt-and-braces: wire.Gesture already drops a credential value at parse
    # time, but that validator does not re-run if a nested Target is mutated
    # after the fact. A credential reaching a prompt is not a thing to hold
    # by inheritance alone, so trim() checks it again itself.
    secret = gesture.gesture.secret or target.secret
    return {
        "kind": gesture.gesture.kind,
        "target": {
            "role": target.role,
            "name": target.name,
            "text": target.text,
            "testId": target.testId,
            "itemId": component.itemId if component else None,
            "fieldLabel": component.fieldLabel if component else None,
            "xtype": component.xtype if component else None,
            "query": component.query if component else None,
        },
        "value": None if secret else gesture.gesture.value,
        "url": path_shape(gesture.url) if gesture.url else None,
        "host": urlparse(gesture.url).netloc if gesture.url else None,
        "calls": [_call(request) for request in gesture.requests],
        "page": [event.page_kind for event in gesture.page_events],
    }
