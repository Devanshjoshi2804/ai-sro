from __future__ import annotations

import re
from enum import StrEnum
from urllib.parse import unquote_plus

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

_SESSION_COOKIE_HINTS = ("sess", "sid", "auth", "token", "jwt", "login", "sso")

_TRACE_HEADERS = frozenset(
    {"traceparent", "tracestate", "x-request-id", "x-correlation-id", "x-b3-traceid", "baggage"}
)

_TRACE_HINTS = ("trace", "nonce", "request-id", "correlation", "idempotency", "-ts", "timestamp")

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

    CSRF = "csrf"

    SESSION = "session"

    TRACE = "trace"

    TRANSPORT = "transport"

    SEMANTIC = "semantic"


def classify_header(name: str) -> Sensitivity:
    lowered = name.lower().strip()
    if lowered.startswith(":"):
        return Sensitivity.TRANSPORT
    if lowered in _AUTH_HEADERS:
        return Sensitivity.AUTH
    if lowered in _CSRF_HEADERS or any(hint in lowered for hint in _CSRF_HINTS):
        return Sensitivity.CSRF
    if lowered == "cookie":
        return Sensitivity.SESSION
    if any(hint in lowered for hint in _SESSION_COOKIE_HINTS):
        return Sensitivity.AUTH
    if lowered in _TRACE_HEADERS or any(hint in lowered for hint in _TRACE_HINTS):
        return Sensitivity.TRACE
    if lowered in _TRANSPORT_HEADERS:
        return Sensitivity.TRANSPORT
    return Sensitivity.SEMANTIC


SECRET_TOKENS = frozenset(
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
        "passcode",
        "mfa",
        "onetimecode",
        "onetimepasscode",
        "verificationcode",
        "cookie",
        "jwt",
        "bearer",
        "sso",
        "saml",
        "accesskey",
        "secretkey",
        "secretaccesskey",
        "privatekey",
        "privkey",
        "authtoken",
        "authkey",
        "authorization",
        "sessionid",
        "sessiontoken",
        "sessionkey",
        "jsessionid",
        "phpsessid",
        "csrftoken",
        "xsrftoken",
        "csrf",
        "xsrf",
        "clientsecret",
        "appsecret",
        "apisecret",
        "consumersecret",
        "consumerkey",
        "idtoken",
        "oauthtoken",
        "samlresponse",
        "samlrequest",
        "relaystate",
        "encryptionkey",
        "machinekey",
        "connectionstring",
        "keystore",
        "truststore",
        "htpasswd",
        "sshkey",
        "rsakey",
        "idrsa",
        "totp",
        "hotp",
        "resettoken",
        "recoverycode",
        "backupcode",
        "secretanswer",
        "xapikey",
        "xauthtoken",
    }
)

_SECRET_TOKENS = SECRET_TOKENS


REDACTED = "«redacted»"


SECRET_SHAPES: tuple[tuple[str, str], ...] = (
    ("jwt", r"eyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]*){2,4}"),
    ("aws_key_id", r"(?:AKIA|ASIA|AIDA|AROA)[A-Z0-9]{16}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    ("github_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("google_api_key", r"AIza[A-Za-z0-9_-]{35}"),
    ("slack_token", r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    (
        "private_key",
        (
            r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"
            r"(?:[\s\S]*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----)?"
        ),
    ),
)

SECRET_SHAPES_ANY_CASE: tuple[tuple[str, str], ...] = (
    ("bearer", r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
    ("basic_auth", r"\bbasic\s+[A-Za-z0-9+/]{16,}={0,2}"),
)


def _shape_matcher(shapes: tuple[tuple[str, str], ...], flags: int = 0) -> re.Pattern[str]:
    return re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in shapes), flags)


_SHAPE = _shape_matcher(SECRET_SHAPES)
_SHAPE_ANY_CASE = _shape_matcher(SECRET_SHAPES_ANY_CASE, re.IGNORECASE)


def shapes_in(text: str) -> tuple[str, ...]:
    found = dict.fromkeys(
        match.lastgroup
        for matcher in (_SHAPE, _SHAPE_ANY_CASE)
        for match in matcher.finditer(text or "")
        if match.lastgroup
    )
    return tuple(found)


def redact_shapes(text: str) -> str:
    if not text:
        return text
    return _SHAPE_ANY_CASE.sub(REDACTED, _SHAPE.sub(REDACTED, text))


_ACRONYM_BOUNDARY = (
    (re.compile(r"([a-z0-9])([A-Z])"), r"\1 \2"),
    (re.compile(r"([A-Z]{2,})([A-Z][a-z])"), r"\1 \2"),
)
_NOT_LETTERS = re.compile(r"[^A-Za-z]+")


def _words(name: str) -> list[str]:
    spaced = name or ""
    for pattern, replacement in _ACRONYM_BOUNDARY:
        spaced = pattern.sub(replacement, spaced)
    return [word.lower() for word in _NOT_LETTERS.split(spaced) if word]


def is_secret_field(name: str) -> bool:
    words = _words(name)
    if any(word in _SECRET_TOKENS for word in words):
        return True
    return "".join(words) in _SECRET_TOKENS


OAUTH_COMPANIONS = frozenset(
    {
        "client_id",
        "code_challenge",
        "code_verifier",
        "grant_type",
        "id_token",
        "nonce",
        "redirect_uri",
        "response_type",
        "state",
    }
)


def _redact_query(raw: str) -> str:
    pairs = raw.split("&")
    names = [unquote_plus(pair.partition("=")[0]).lower() for pair in pairs]
    oauth = any(name in OAUTH_COMPANIONS for name in names)
    for index, pair in enumerate(pairs):
        if not pair:
            continue
        key = pair.partition("=")[0]
        if is_secret_field(unquote_plus(key)) or (oauth and names[index] == "code"):
            pairs[index] = f"{key}={REDACTED}"
    return "&".join(pairs)


def redact_url(url: str) -> str:
    if not url:
        return url

    hash_at = url.find("#")
    head, fragment = (url, "") if hash_at == -1 else (url[:hash_at], url[hash_at + 1 :])
    query_at = head.find("?")
    if query_at != -1:
        head = head[: query_at + 1] + _redact_query(head[query_at + 1 :])
    if "=" in fragment:
        fragment = _redact_query(fragment)
    return redact_shapes(head if hash_at == -1 else f"{head}#{fragment}")


def classify_cookie(name: str) -> Sensitivity:
    lowered = name.lower()
    if any(hint in lowered for hint in _SESSION_COOKIE_HINTS):
        return Sensitivity.SESSION
    return Sensitivity.SEMANTIC


def is_secret(sensitivity: Sensitivity) -> bool:
    return sensitivity in {Sensitivity.AUTH, Sensitivity.SESSION, Sensitivity.CSRF}


def is_replayable(sensitivity: Sensitivity) -> bool:
    return sensitivity is Sensitivity.SEMANTIC
