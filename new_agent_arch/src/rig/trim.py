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
from rig.wire import (
    REDACTED,
    SECRET_HEADER_HINTS,
    SECRET_HEADERS,
    Body,
    Request,
    Target,
    is_secret_header,
)

# Re-exported: the header rule lives in wire.py beside the Request model that
# applies it, because trim imports wire and the reverse would be a cycle.
__all__ = [
    "REDACTED",
    "SECRET_HEADERS",
    "SECRET_HEADER_HINTS",
    "SECRET_WORDS",
    "body_keys",
    "is_secret",
    "is_secret_header",
    "is_secret_name",
    "path_shape",
    "thin",
    "trim",
]

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

    # The name is kept and the value is not: that a login carried a password is
    # worth reading, what the password was is not. The extension redacts this
    # too, client-side; this is the server-side belt, and the reason for it is
    # that the client-side one can be made not to run.
    return {
        key: REDACTED if is_secret_name(key) else str(parsed[key])[:VALUE_CHARS]
        for key in list(parsed)[:BODY_KEYS]
    }


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


# Mirrors SECRET_WORDS in the extension's
# new-chrome-extension/src/content/sensitivity.module.js. Re-declared rather
# than imported, for the same reason the wire protocol is re-declared here:
# this process cannot import JavaScript, and a redaction rule that runs only
# in the browser is one a browser can be made not to run. If the extension's
# list changes, this one has to change with it -- that drift is the price of
# the guarantee, and the guarantee is worth more.
SECRET_WORDS = frozenset(
    {
        "accesstoken",
        "apikey",
        "credential",
        "credentials",
        "cvv",
        "mfa",
        "onetimecode",
        "onetimepasscode",
        "otp",
        "pass",
        "passcode",
        "passphrase",
        "passwd",
        "password",
        "pin",
        "pwd",
        "refreshtoken",
        "secret",
        "securityanswer",
        "securitycode",
        "ssn",
        "token",
        "verificationcode",
    }
)


def _words_of(text: str) -> list[str]:
    """camelCase, snake_case and "Shipping Date" alike, split into words."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    return [word.lower() for word in re.split(r"[^A-Za-z]+", spaced) if word]


def is_secret_name(name: str) -> bool:
    """Whether a field called this holds a credential.

    Whole words, not substrings, which is the extension's rule and matters:
    `"pin" in name` flags a real field in this tenant's captured data called
    "Shipping Date Escalation". The joined form is checked too, so `apiKey`
    and `api_key` both match `apikey`.
    """
    words = _words_of(name)
    return any(word in SECRET_WORDS for word in words) or "".join(words) in SECRET_WORDS


def is_secret(gesture: Gesture) -> bool:
    """Whether this gesture's value is a credential.

    Belt-and-braces: wire.Gesture already drops a credential value at parse
    time, but that validator does not re-run if a nested Target is mutated
    after the fact. A credential reaching a prompt is not a thing to hold by
    inheritance alone. A scroll has no target at all, so this falls back to
    gesture.gesture.secret alone.
    """
    target = gesture.gesture.target
    return gesture.gesture.secret or (target.secret if target else False)


def trim(gesture: Gesture) -> dict[str, Any]:
    target = gesture.gesture.target
    component = target.component if target else None
    secret = is_secret(gesture)
    return {
        "kind": gesture.gesture.kind,
        "target": {
            "role": target.role if target else None,
            "name": target.name if target else None,
            "text": target.text if target else None,
            "testId": target.testId if target else None,
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
