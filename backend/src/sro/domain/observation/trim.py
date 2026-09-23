import json
import re
from urllib.parse import parse_qsl, urlparse

from sro.domain.observation.gesture import Body, Call, Gesture, Target
from sro.domain.observation.redaction import is_secret_name, redact_body, redact_data
from sro.domain.shared.hosts import REDACTED

VALUE_CHARS = 80
BODY_KEYS = 40

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def thin(target: Target | None) -> bool:
    if target is None:
        return True
    component = target.component
    return not any(
        (
            target.name,
            target.text,
            component.field_label if component else None,
            component.item_id if component else None,
        )
    )


def path_shape(url: str) -> str:
    parts = urlparse(url).path.split("/")
    return "/".join("*" if looks_like_an_id(part) else part for part in parts)


def looks_like_an_id(part: str) -> bool:
    if not part:
        return False
    if part.isdigit() or _UUID.match(part):
        return True
    digits = sum(character.isdigit() for character in part)
    return len(part) >= 8 and digits >= len(part) // 2


def body_keys(body: Body | None) -> dict[str, str] | None:
    if body is None or not body.text:
        if body is not None and body.redacted_fields:
            return {"_": ", ".join(body.redacted_fields)[:VALUE_CHARS]}
        return None

    parsed: object = None
    if body.mime_type == "application/x-www-form-urlencoded":
        parsed = dict(parse_qsl(body.text))
    else:
        try:
            parsed = json.loads(body.text)
        except (ValueError, TypeError):
            parsed = None

    if not isinstance(parsed, dict):
        return {"_": (redact_body(body.text, body.mime_type) or "")[:VALUE_CHARS]}

    fields: dict[object, object] = parsed
    return {
        str(key): REDACTED
        if is_secret_name(str(key))
        else str(redact_data(fields[key]))[:VALUE_CHARS]
        for key in list(fields)[:BODY_KEYS]
    }


def _call(call: Call) -> dict[str, object]:
    return {
        "method": call.method,
        "path": path_shape(call.url),
        "host": urlparse(call.url).netloc,
        "status": call.status,
        "failed": call.failure_reason,
        "blocked": call.blocked_reason,
        "body_keys": body_keys(call.request_body),
        "response_keys": body_keys(call.response_body),
    }


def is_secret(gesture: Gesture) -> bool:
    target = gesture.action.target
    return gesture.action.secret or (target.secret if target else False)


def trim(gesture: Gesture) -> dict[str, object]:
    target = gesture.action.target
    component = target.component if target else None
    secret = is_secret(gesture)
    return {
        "kind": gesture.action.kind,
        "target": {
            "role": target.role if target else None,
            "name": target.name if target else None,
            "text": target.text if target else None,
            "test_id": target.test_id if target else None,
            "item_id": component.item_id if component else None,
            "field_label": component.field_label if component else None,
            "xtype": component.xtype if component else None,
            "query": component.query if component else None,
        },
        "value": None if secret else gesture.action.value,
        "url": path_shape(gesture.url) if gesture.url else None,
        "host": urlparse(gesture.url).netloc if gesture.url else None,
        "calls": [_call(call) for call in gesture.requests],
        "page": [event.page_kind for event in gesture.page_events],
    }
