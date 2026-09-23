import json
import re
from urllib.parse import unquote_plus, urlparse

from sro.domain.shared.hosts import REDACTED

SECRET_HEADERS = frozenset(
    {
        "api-key",
        "authentication",
        "authorization",
        "csrf-token",
        "proxy-authorization",
        "x-access-token",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
        "x-csrftoken",
        "x-infor-token",
        "x-moca-session",
        "x-requested-with",
        "x-session-key",
        "x-xsrf-token",
    }
)
SECRET_HEADER_HINTS = (
    "auth",
    "cookie",
    "csrf",
    "jwt",
    "login",
    "sess",
    "sid",
    "sso",
    "token",
    "xsrf",
)

SECRET_WORDS = frozenset(
    {
        "accesskey",
        "accesstoken",
        "apikey",
        "apisecret",
        "appsecret",
        "authkey",
        "authorization",
        "authtoken",
        "backupcode",
        "bearer",
        "clientsecret",
        "connectionstring",
        "consumerkey",
        "consumersecret",
        "cookie",
        "credential",
        "credentials",
        "csrf",
        "csrftoken",
        "cvv",
        "encryptionkey",
        "hotp",
        "htpasswd",
        "idrsa",
        "idtoken",
        "jsessionid",
        "jwt",
        "keystore",
        "machinekey",
        "mfa",
        "oauthtoken",
        "onetimecode",
        "onetimepasscode",
        "otp",
        "pass",
        "passcode",
        "passphrase",
        "passwd",
        "password",
        "phpsessid",
        "pin",
        "privatekey",
        "privkey",
        "pwd",
        "recoverycode",
        "refreshtoken",
        "relaystate",
        "resettoken",
        "rsakey",
        "saml",
        "samlrequest",
        "samlresponse",
        "secret",
        "secretaccesskey",
        "secretanswer",
        "secretkey",
        "securityanswer",
        "securitycode",
        "sessionid",
        "sessionkey",
        "sessiontoken",
        "sshkey",
        "ssn",
        "sso",
        "token",
        "totp",
        "truststore",
        "verificationcode",
        "xapikey",
        "xauthtoken",
        "xsrf",
        "xsrftoken",
    }
)
UNINSPECTABLE = "«whole body: could not be parsed to redact»"

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

_SHAPE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in SECRET_SHAPES))
_SHAPE_ANY_CASE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in SECRET_SHAPES_ANY_CASE), re.IGNORECASE
)


def shapes_in(text: str | None) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            match.lastgroup
            for matcher in (_SHAPE, _SHAPE_ANY_CASE)
            for match in matcher.finditer(text or "")
            if match.lastgroup
        )
    )


def redact_shapes(text: str) -> str:
    if not text:
        return text
    return _SHAPE_ANY_CASE.sub(REDACTED, _SHAPE.sub(REDACTED, text))


def _words_of(text: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    spaced = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", spaced)
    return [word.lower() for word in re.split(r"[^A-Za-z]+", spaced) if word]


def is_secret_name(name: str) -> bool:
    words = _words_of(name)
    return any(word in SECRET_WORDS for word in words) or "".join(words) in SECRET_WORDS


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
        if is_secret_name(unquote_plus(key)) or (oauth and names[index] == "code"):
            pairs[index] = f"{key}={REDACTED}"
    return "&".join(pairs)


def redact_url(url: str) -> str:
    if not url:
        return url
    try:
        urlparse(url)
    except ValueError:
        return url

    hash_at = url.find("#")
    head, fragment = (url, "") if hash_at == -1 else (url[:hash_at], url[hash_at + 1 :])
    query_at = head.find("?")
    if query_at != -1:
        head = head[: query_at + 1] + _redact_query(head[query_at + 1 :])
    if "=" in fragment:
        fragment = _redact_query(fragment)
    return redact_shapes(head if hash_at == -1 else f"{head}#{fragment}")


_XML_FIELD = re.compile(r"<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)</\1>")
_XML_ATTR = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')
_PAIR = re.compile(r"([A-Za-z_][\w.-]*)(\s*[=:]\s*)([^\s&;,]*)")
_MULTIPART_BOUNDARY = re.compile(r'boundary=(?:"([^"]+)"|([^;]+))', re.IGNORECASE)
_PART_NAME = re.compile(r'name="([^"]*)"', re.IGNORECASE)
_HEADER_GAP = re.compile(r"\r?\n\r?\n")
_PART_END = re.compile(r"\r?\n--")


def redact_data(node: object) -> object:
    if isinstance(node, dict):
        return {
            key: REDACTED if is_secret_name(str(key)) else redact_data(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [redact_data(item) for item in node]
    return node


def _redact_pairs(text: str) -> str:
    return _PAIR.sub(
        lambda found: f"{found[1]}{found[2]}{REDACTED}" if is_secret_name(found[1]) else found[0],
        text,
    )


def _redact_json(text: str) -> str:
    try:
        document = json.loads(text)
    except ValueError:
        return UNINSPECTABLE
    if isinstance(document, str):
        return json.dumps(_redact_pairs(document), ensure_ascii=False)
    cleaned = redact_data(document)
    return text if cleaned == document else json.dumps(cleaned, ensure_ascii=False)


def _redact_xml(text: str) -> str:
    def element(found: re.Match[str]) -> str:
        name = found[1]
        if not is_secret_name(name.split(":")[-1]):
            return found[0]
        return f"<{name}{found[2]}>{REDACTED}</{name}>"

    def attribute(found: re.Match[str]) -> str:
        name = found[1]
        if not is_secret_name(name.split(":")[-1]):
            return found[0]
        return f'{name}="{REDACTED}"'

    return _XML_ATTR.sub(attribute, _XML_FIELD.sub(element, text))


def _redact_multipart(text: str, mime_type: str | None) -> str:
    found = _MULTIPART_BOUNDARY.search(mime_type or "")
    boundary = (found[1] or found[2]).strip() if found else ""
    if not boundary:
        return _redact_pairs(text)
    parts = []
    for part in text.split(f"--{boundary}"):
        gap = _HEADER_GAP.search(part)
        name = _PART_NAME.search(part[: gap.start()]) if gap else None
        if gap is None or name is None or not is_secret_name(name[1]):
            parts.append(part)
            continue
        rest = part[gap.end() :]
        end = _PART_END.search(rest)
        parts.append(part[: gap.end()] + REDACTED + (rest[end.start() :] if end else ""))
    return f"--{boundary}".join(parts)


def _redact_named(text: str | None, mime_type: str | None) -> str | None:
    if not text:
        return text
    kind = (mime_type or "").lower()
    stripped = text.lstrip()
    if "json" in kind or stripped[:1] in ("{", "["):
        return _redact_json(text)
    if "xml" in kind or stripped.startswith("<"):
        return _redact_xml(text)
    if "multipart/form-data" in kind:
        return _redact_multipart(text, mime_type)
    if "form-urlencoded" in kind or ("=" in text and "\n" not in text):
        return _redact_query(text)
    return _redact_pairs(text)


def redact_body(text: str | None, mime_type: str | None) -> str | None:
    cleaned = _redact_named(text, mime_type)
    return cleaned if cleaned is None else redact_shapes(cleaned)
