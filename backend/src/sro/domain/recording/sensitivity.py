"""Classification of headers and cookies. See docs/11-capture-completeness.md.

This module labels. It never deletes. Everything is captured; classification
decides only which plane a value may travel to -- evidence keeps all of it,
skills keep a vault reference instead of a secret, telemetry keeps neither.
"""

from __future__ import annotations

import re
from enum import StrEnum

_AUTH_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-access-token",
        "x-session-key",
        "x-moca-session",
        "x-infor-token",
        "authentication",
    }
)

_CSRF_HEADERS = frozenset(
    {"x-csrf-token", "x-xsrf-token", "csrf-token", "x-requested-with", "x-csrftoken"}
)

_CSRF_HINTS = ("csrf", "xsrf")
"""Vendors name this header what they like.

Blue Yonder sends `CSRF-ENCRYPT-TOKEN`, which no exact list predicted, and it
was written into a skill as a literal value -- a live session secret in the
plane that is meant to hold none, and stale by the time anything replayed it."""

_SESSION_COOKIE_HINTS = ("sess", "sid", "auth", "token", "jwt", "login", "sso")

_TRACE_HEADERS = frozenset(
    {"traceparent", "tracestate", "x-request-id", "x-correlation-id", "x-b3-traceid", "baggage"}
)

_TRACE_HINTS = ("trace", "nonce", "request-id", "correlation", "idempotency", "-ts", "timestamp")
"""Substrings, because every system names these differently.

Matched by name rather than by inspecting the value: a header called `X-Trace`
holds a value that is new on every call, and the two-run diff cannot tell that
apart from a value the task actually varies. Left unclassified it becomes a
parameter the operator is asked to supply, which is nonsense.
"""

_TRANSPORT_HEADERS = frozenset(
    {
        "host",
        "connection",
        "content-length",
        "accept-encoding",
        "user-agent",
        "referer",
        "origin",
        "sec-fetch-mode",
        "sec-fetch-site",
        "sec-fetch-dest",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "accept-language",
        "cache-control",
        "pragma",
        "te",
        "upgrade-insecure-requests",
    }
)


class Sensitivity(StrEnum):
    AUTH = "auth"
    """Credential. Replay needs a live one, so the skill holds a vault reference."""

    CSRF = "csrf"
    """Single-use token. Minted per session -- a replayed value is always stale."""

    SESSION = "session"
    """Session cookie. Same handling as AUTH."""

    TRACE = "trace"
    """Correlation id. Regenerate rather than replay, or traces collide."""

    TRANSPORT = "transport"
    """Set by the HTTP client. Replaying is pointless and sometimes harmful."""

    SEMANTIC = "semantic"
    """Carries meaning the call needs: tenant, facility, warehouse, content-type."""


def classify_header(name: str) -> Sensitivity:
    lowered = name.lower().strip()
    if lowered in _AUTH_HEADERS:
        return Sensitivity.AUTH
    if lowered in _CSRF_HEADERS or any(hint in lowered for hint in _CSRF_HINTS):
        return Sensitivity.CSRF
    if lowered == "cookie":
        return Sensitivity.SESSION
    if lowered in _TRACE_HEADERS or any(hint in lowered for hint in _TRACE_HINTS):
        return Sensitivity.TRACE
    if lowered.startswith(":") or lowered in _TRANSPORT_HEADERS:
        # HTTP/2 pseudo-headers (:method, :path, :scheme, :authority) are the
        # request line, recorded by CDP as though they were headers. An executor
        # that put them back on the wire would be sending the demonstration's
        # request line inside a new request.
        return Sensitivity.TRANSPORT
    return Sensitivity.SEMANTIC


_SECRET_TOKENS = frozenset(
    {
        "password",
        "passwd",
        "passphrase",
        "pass",
        "pwd",
        "secret",
        "token",
        "otp",
        "pin",
        "cvv",
        "ssn",
        "credential",
        "credentials",
        "apikey",
        "accesstoken",
        "refreshtoken",
        "securitycode",
        "securityanswer",
    }
)

_WORDS = re.compile(r"[A-Za-z][a-z0-9]*")


def is_secret_field(name: str) -> bool:
    """Whether a form or JSON field holds a credential.

    Used on request bodies: a login POST carries the password the operator typed,
    and the evidence plane keeps bodies verbatim. Matched by field name rather
    than by inspecting values -- a name is a decision the target system already
    made, while guessing from values would redact real business data.

    Matched on whole words rather than substrings, in both ``snake_case`` and
    ``camelCase``. Substring matching redacts ``passenger_count``, and a
    redaction that eats business data is how people learn to switch it off.
    """
    words = [word.lower() for word in _WORDS.findall(name)]
    if any(word in _SECRET_TOKENS for word in words):
        return True
    # Compounds that only read as credentials when joined: apiKey, api_key.
    return "".join(words) in _SECRET_TOKENS


def classify_cookie(name: str) -> Sensitivity:
    lowered = name.lower()
    if any(hint in lowered for hint in _SESSION_COOKIE_HINTS):
        return Sensitivity.SESSION
    return Sensitivity.SEMANTIC


def is_secret(sensitivity: Sensitivity) -> bool:
    """Whether the *value* must be held by reference outside the evidence plane."""
    return sensitivity in {Sensitivity.AUTH, Sensitivity.SESSION, Sensitivity.CSRF}


def is_replayable(sensitivity: Sensitivity) -> bool:
    """Whether the captured value can be sent again verbatim.

    ``SEMANTIC`` only. A CSRF token is stale, a trace id would collide, transport
    headers are the client's to set, and secrets are resolved from the vault at
    run time rather than copied.
    """
    return sensitivity is Sensitivity.SEMANTIC
