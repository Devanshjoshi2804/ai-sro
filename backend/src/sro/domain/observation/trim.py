"""A2 — what one gesture looks like to the model that reads it.

Token discipline, because A3 runs once per gesture and a day is thousands of
them. css_path and xpath are excluded on purpose: long, meaningless to a model,
and the two locators that break. The runner still reads them from the stored row.

Ported from `new_agent_arch/src/rig/trim.py`. `body_keys` below is the
prompt-side belt: the wire's `Request` already redacted a body on its way to the
store, and this runs the same rules again on the way to the model. Those rules
are `sro.domain.observation.redaction`, which came out of the rig's wire module
with this file and was split back out of it -- one address for the credential
vocabulary, imported by both belts.
"""

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
    """True when nothing here would tell a model what the control is.

    A targetless gesture (a scroll) is thin by definition -- there is no
    control to name.
    """
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
    """/data/WM/wm/addresses/1183 -> /data/WM/wm/addresses/*"""
    parts = urlparse(url).path.split("/")
    return "/".join("*" if looks_like_an_id(part) else part for part in parts)


def looks_like_an_id(part: str) -> bool:
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
    """Keys and short values. Never the prose, never the whole payload.

    The prompt-side belt. The wire's `Request` already redacted this text on its
    way to the store, and this runs again on the way to the model: two belts,
    neither relying on the other. Every one of the four ways out of here is
    redacted, which was the defect -- one of them was, and a form body with no
    mime type, a SOAP login, a JSON array and a bare JSON string took the other
    three.
    """
    if body is None or not body.text:
        # "There was no body" and "there was a body and we declined to keep it"
        # are different facts, and returning None for both told the model the
        # first when the truth was the second. The extension names the failure
        # in its own comment -- a suppressed body "reads to a reviewer as a body
        # that was checked and found clean" -- and redacted_fields is where it
        # says which: «not captured», «dropped: larger than the tenant's
        # max_body_bytes». One key and one line, because this goes in a prompt.
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
        # Unparseable, or parsed to something that has no keys at all: an
        # array, a bare string. There is nothing to name, so the text goes in
        # whole -- through the same rule the store's copy went through, which
        # covers the shapes json.loads never sees.
        return {"_": (redact_body(body.text, body.mime_type) or "")[:VALUE_CHARS]}

    # The name is kept and the value is not: that a login carried a password is
    # worth reading, what the password was is not. redact_data recurses, because
    # {"auth": {"password": ...}} is the same credential one level down and the
    # flat version of this rule let it through.
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
        # Carried for the same reason failure_reason is. A request the browser's
        # own policy blocked has no status and no failure, so without this it
        # arrives as `status: null, failed: null` -- indistinguishable from a
        # call still in flight or one that vanished.
        "blocked": call.blocked_reason,
        "body_keys": body_keys(call.request_body),
        "response_keys": body_keys(call.response_body),
    }


def is_secret(gesture: Gesture) -> bool:
    """Whether this gesture's value is a credential.

    Belt-and-braces: the wire parser already drops a credential value at parse
    time, but that validator does not re-run if a nested Target is mutated
    after the fact. A credential reaching a prompt is not a thing to hold by
    inheritance alone. A scroll has no target at all, so this falls back to
    gesture.action.secret alone.
    """
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
