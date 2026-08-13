"""Classification of headers and cookies. See docs/11-capture-completeness.md.

This module labels. It never deletes. Everything is captured; classification
decides only which plane a value may travel to -- evidence keeps all of it,
skills keep a vault reference instead of a secret, telemetry keeps neither.
"""

from __future__ import annotations

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

_SESSION_COOKIE_HINTS = ("sess", "sid", "auth", "token", "jwt", "login", "sso")

_TRACE_HEADERS = frozenset(
    {"traceparent", "tracestate", "x-request-id", "x-correlation-id", "x-b3-traceid", "baggage"}
)

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
    if lowered in _CSRF_HEADERS:
        return Sensitivity.CSRF
    if lowered == "cookie":
        return Sensitivity.SESSION
    if lowered in _TRACE_HEADERS:
        return Sensitivity.TRACE
    if lowered in _TRANSPORT_HEADERS:
        return Sensitivity.TRANSPORT
    return Sensitivity.SEMANTIC


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
