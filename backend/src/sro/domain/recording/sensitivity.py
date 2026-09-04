"""Classification of headers and cookies. See docs/11-capture-completeness.md.

This module labels. It never deletes. Everything is captured; classification
decides only which plane a value may travel to -- evidence keeps all of it,
skills keep a vault reference instead of a secret, telemetry keeps neither.
"""

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
    if lowered.startswith(":"):
        # HTTP/2 pseudo-headers (:method, :path, :scheme, :authority) are the
        # request line, recorded by CDP as though they were headers. An executor
        # that put them back on the wire would be sending the demonstration's
        # request line inside a new request.
        #
        # Decided FIRST, before any substring hint, because `:authority` -- the
        # host -- contains "auth". A pseudo-header is a structural fact about the
        # frame; a hint is a guess about a name, and the fact wins.
        return Sensitivity.TRANSPORT
    if lowered in _AUTH_HEADERS:
        return Sensitivity.AUTH
    if lowered in _CSRF_HEADERS or any(hint in lowered for hint in _CSRF_HINTS):
        return Sensitivity.CSRF
    if lowered == "cookie":
        return Sensitivity.SESSION
    if any(hint in lowered for hint in _SESSION_COOKIE_HINTS):
        # The half of this pair that runs in the browser has had these hints all
        # along: generate_extension_recorder builds `isSecretHeader` from
        # _CSRF_HINTS | _SESSION_COOKIE_HINTS | {"cookie"}, so the extension
        # already refuses `X-Vault-Token`, `X-Amz-Security-Token` and
        # `X-Auth-Key` while this function, which generates it, called all three
        # SEMANTIC -- meaning is_replayable() said yes and a skill would hold the
        # live value verbatim. One generated pair, two different answers about
        # what a credential is.
        #
        # Inferred rather than measured, and said plainly: the captured corpus
        # has only 26 distinct header names and none of those three is among
        # them. What IS measured is the cost -- exactly one of the 26 changes
        # class, the response header `authenticated: "true"`, which becomes a
        # vault reference to a boolean. The extension has treated it that way
        # since it was generated; this makes the two agree rather than
        # introducing anything new.
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
        # Kept, and the cost is real: measured over 3,256 distinct field names
        # from the acme store plus knowledge-base/http/exchanges, the bare word
        # blanks two live warehouse fields -- `onePassOnly` and
        # `passAssignmentUnassignWork` -- because in this domain a pass is a
        # picking operation. (It blanked two more, `pickNPassAutoDropLocation`
        # and `pickNPassDropWorkZone`, until the splitter above stopped cutting
        # at a lone capital.)
        #
        # It stays because dropping it opens `db_pass`, `user_pass`, `adminPass`
        # and a plain `?pass=` -- whole-word matches that NO compound in this
        # list covers, and every one of them a live credential. Two unreadable
        # field names in a prompt against a password in the store is not a close
        # trade. Revisit only with a measurement showing a `*_pass` credential
        # shape does not occur in the deployments this ships to.
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
        # A one-time code is a credential for the minute it lives. These were
        # missing from every list: a WMS that mails a six-digit code called it a
        # "Verification Code", the recorder kept it verbatim, and induction then
        # offered it as a parameter to be stored, displayed and replayed.
        "passcode",
        "mfa",
        "onetimecode",
        "onetimepasscode",
        "verificationcode",
        # A session is a credential for as long as it lives, and `{"sessionId":
        # "..."}` in a request body was redacted nowhere: these words were in
        # the header lists on both sides and in neither field list, so the
        # header form was dropped and the body form stored verbatim.
        #
        # Safe here only because this rule matches whole words: as SUBSTRINGS
        # these would blank five real fields -- `addressId`, `codAddressId`,
        # `shipperAddressId` and `residentialAddress` all contain "sid", and
        # `NLSSORTSetting` contains "sso". They must never be copied into a
        # substring rule.
        #
        # Bare `session` is deliberately NOT here, and was, for one session. It
        # was added on a measurement over 217 field names from one tenant
        # subset; re-measured over 3,256 distinct real names (the acme store
        # plus knowledge-base/http/exchanges) it blanks three live warehouse
        # fields -- `sessionGroup`, `sessionNumber`, `sessionTag` -- because in
        # a WMS a session is a unit of picking work, not a login. The compounds
        # below carry the credential meaning and cost nothing: `sessionId`,
        # `sessionKey` and `sessionToken` all still match through the joined
        # form, and `session_token` matches on `token`. The ceiling this leaves,
        # written down rather than discovered: a name whose words JOIN to
        # something longer, `mySessionId`, matches neither the words nor the
        # joined form. That is the same ceiling `apiKey` has always had.
        "cookie",
        "jwt",
        "bearer",
        "sso",
        "saml",
        # Measured over the same 3,256 names: every one of these matches ZERO
        # of them, so they are free. The single exception is `csrf`, whose only
        # hit is `CSRF-ENCRYPT-TOKEN` -- the Blue Yonder header named at the top
        # of this file, already matched by `token`, and a true positive rather
        # than a cost.
        #
        # They exist because the vocabulary had exactly one compound in it
        # (`apikey`) and neither `access` nor `key` is a word here, so
        # `accessKey`, `privateKey`, `sshKey` and `encryptionKey` -- an
        # AWS-shaped body -- reached the store and the prompt verbatim.
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
"""Every word that names a credential, in one place.

There were three of these lists -- here, in ``recorder.js``, and in the egress
guard -- and they had drifted apart in both directions. The recorder is now
generated from this one, so a word added here reaches the page that does the
redacting rather than only the code that checks it afterwards.
"""

_SECRET_TOKENS = SECRET_TOKENS


REDACTED = "«redacted»"
"""The one marker. A value taken out by shape is indistinguishable in the
output from one taken out by name, on purpose: `redaction.py`, the rig and the
extension all write these exact characters, and a second convention would mean
a reviewer grepping stored evidence for it found only some of the holes."""


SECRET_SHAPES: tuple[tuple[str, str], ...] = (
    ("jwt", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*"),
    ("aws_key_id", r"(?:AKIA|ASIA|AIDA|AROA)[A-Z0-9]{16}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    ("github_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("google_api_key", r"AIza[A-Za-z0-9_-]{35}"),
    ("slack_token", r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    # The whole block, not the BEGIN line: a pattern that matched only the
    # header would replace it and leave the base64 key material sitting under
    # a marker that says it was removed. The END clause is optional so a
    # truncated capture still loses its opening line.
    (
        "private_key",
        (
            r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"
            r"(?:[\s\S]*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----)?"
        ),
    ),
)
"""What a credential looks like, regardless of what it is called.

The name lists above are the secondary signal, and they have to be: a field
name is chosen by whoever wrote the vendor's API -- an open vocabulary, guessed
at forever, against systems nobody here controls. Six words added to close
gaps in that vocabulary blanked three real warehouse fields in the same round,
and the comment justifying them was measured on a subset and was false at full
size. A value shape is not open in the same way. A JWT is a JWT whatever the
field is called, and a warehouse dock code is never a PEM block.

Measured over 47,969 distinct string values from the real acme store plus
knowledge-base/http/exchanges -- the values, not the names, which nothing had
ever measured: every pattern here matches ZERO of them, so the whole set costs
no live evidence. `new_agent_arch/tests/test_corpus.py` is that measurement as
a test, and fails naming the value if one ever starts matching.

High-entropy detection is deliberately absent. Measured over the same values,
a Shannon threshold of 4.5 bits on runs of 20+ token characters blanks 791 of
them, 4.0 blanks 14,419 and 3.5 blanks 21,250 -- warehouse activity codes and
`self_uri` URLs, not credentials. There is no threshold between "useless" and
"destroys the evidence": 5.0 blanks nothing at all. It stays out.
"""

SECRET_SHAPES_ANY_CASE: tuple[tuple[str, str], ...] = (
    ("bearer", r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
    ("basic_auth", r"\bbasic\s+[A-Za-z0-9+/]{16,}={0,2}"),
)
"""The two shapes that are a scheme name plus a blob, and so are case-blind.

Separate from the set above rather than folded into it with an inline flag:
`AKIA`, `AIza` and `eyJ` are case-SENSITIVE prefixes and matching them blind
widens each one over the lowercase identifiers this corpus is full of. Two
expressions, one of each kind, is what both engines read the same way --
JavaScript's inline `(?i:...)` is too new to rely on in a content script.
"""


def _shape_matcher(shapes: tuple[tuple[str, str], ...], flags: int = 0) -> re.Pattern[str]:
    return re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in shapes), flags)


_SHAPE = _shape_matcher(SECRET_SHAPES)
_SHAPE_ANY_CASE = _shape_matcher(SECRET_SHAPES_ANY_CASE, re.IGNORECASE)


def shapes_in(text: str) -> tuple[str, ...]:
    """Which credential shapes appear in this text, in the order first seen.

    Separate from the redaction so a body can say *why* it lost something.
    "We redacted this because it looked like a JWT" is a different fact from
    "we redacted this because it was called password", and a reviewer wants to
    tell them apart -- while the marker left behind stays the same either way,
    so nothing downstream has to learn a second convention.
    """
    found = dict.fromkeys(
        match.lastgroup
        for matcher in (_SHAPE, _SHAPE_ANY_CASE)
        for match in matcher.finditer(text or "")
        if match.lastgroup
    )
    return tuple(found)


def redact_shapes(text: str) -> str:
    """The same text with every credential-shaped run replaced.

    A substitution rather than a whole-value verdict: a shape can sit inside a
    larger string -- a bearer scheme in free text, a PEM block in a log line --
    and every byte that did not match is left exactly as it arrived. Text with
    no credential in it comes back identical, which is what lets this run on a
    URL that must not be re-encoded.
    """
    if not text:
        return text
    return _SHAPE_ANY_CASE.sub(REDACTED, _SHAPE.sub(REDACTED, text))


# camelCase, snake_case, kebab-case and "Shipping Date" alike, split into words.
# One rule, three copies: this one, `wordsOf` in recorder.js, and the rig's
# `_words_of`. They must stay identical, and did not: this used to be a
# `[A-Za-z][a-z0-9]*` findall, which starts a new word at every capital and so
# split `pickNPassAutoDropLocation` into `pick/n/pass/...` -- blanking a real
# warehouse field ("Pick N Pass") that the browser's own splitter kept.
#
# The second substitution is why the acronym run must be *two or more* capitals:
# `([A-Z]+)([A-Z][a-z])` would split the lone `N` off `NPass` and leave `Pass`
# bare, which is the same false positive by a shorter route. `([A-Z]{2,})`
# needs three capitals in a row before it cuts, so `SAMLResponse` becomes
# `saml/response` while `NPass` stays whole.
#
# Measured over 3,270 distinct field, header and query-parameter names from the
# real acme capture plus knowledge-base/http/exchanges: the two-or-more rule
# changes nothing at all, the naive rule wrongly blanks two, and this file's
# previous findall wrongly blanked those same two.
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
    """Whether a form or JSON field holds a credential.

    Used on request bodies: a login POST carries the password the operator typed,
    and the evidence plane keeps bodies verbatim. Matched by field name rather
    than by inspecting values -- a name is a decision the target system already
    made, while guessing from values would redact real business data.

    Matched on whole words rather than substrings, in both ``snake_case`` and
    ``camelCase``. Substring matching redacts ``passenger_count``, and a
    redaction that eats business data is how people learn to switch it off.

    An all-caps acronym stuck to a word counts as two words, so ``SAMLResponse``
    matches ``saml``. See ``_words`` for the measurement that says this is free.
    """
    words = _words(name)
    if any(word in _SECRET_TOKENS for word in words):
        return True
    # Compounds that only read as credentials when joined: apiKey, api_key.
    return "".join(words) in _SECRET_TOKENS


def _redact_query(raw: str) -> str:
    """An ``a=b&c=d`` run with every credential-named value replaced.

    Spliced by hand rather than round-tripped through ``parse_qsl`` +
    ``urlencode``, which is the extension's rule and its stated reason:
    re-encoding touches every pair rather than the one that matched -- it
    collapses a repeated key to one, turns a literal space into ``+``, and
    percent-encodes the marker itself, so grepping stored evidence for the same
    «redacted» every other redaction path writes finds nothing on a URL.
    Splicing leaves every untouched byte -- encoding, order, duplicates --
    exactly as the operator's browser sent it. ``split('&')`` then ``join('&')``
    is lossless, so a run with nothing to redact comes back byte-identical.

    A pair with no ``=`` is given one, as the JavaScript does: the name alone is
    what matched, and there is no value to leave in place.
    """
    pairs = raw.split("&")
    for index, pair in enumerate(pairs):
        if not pair:
            continue
        key = pair.partition("=")[0]
        # The raw key is judged decoded and written back raw: `api%5Fkey` names
        # the same credential as `api_key`, and re-encoding the ones that did
        # not match is the round-trip this splicing exists to avoid.
        if is_secret_field(unquote_plus(key)):
            pairs[index] = f"{key}={REDACTED}"
    return "&".join(pairs)


def redact_url(url: str) -> str:
    """A URL with credential-named query and fragment values replaced.

    ``?token=...`` is as much a credential as the header form, and a URL is
    stored on every event there is -- a navigation, a request, and the frame a
    gesture happened in. This is the Python half of ``redactUrl``, which until
    now existed only as JavaScript emitted by ``generate_extension_recorder``:
    a rule that runs only in the browser is one a browser can be made not to
    run, and the audit found a `&code=<jwt>` in the evidence store to prove it.

    The fragment is judged by the same rule as the query when it is shaped like
    one: ``#access_token=...`` is exactly how an OAuth implicit flow hands a
    token back. A fragment with no ``=`` in it is an ordinary ``#section``
    anchor and is left alone rather than split into pairs it never had.

    The shape pass runs last, over the whole rebuilt URL rather than only the
    query, because a token can sit in a path segment where there is no
    parameter name to judge it by. It substitutes, so **a URL carrying no
    credential comes back byte-identical** -- the property the hand-splicing in
    ``_redact_query`` exists to keep, and the one
    ``test_a_url_with_nothing_in_it_is_not_touched`` asserts.

    A relative URL is redacted too, unlike the JavaScript copy. The extension
    leaves one alone because it cannot RESOLVE it -- a service worker has no
    page to resolve against -- and that reasoning is about resolution, which
    nothing here does: the query and fragment are spliced by raw string
    position and need no scheme or host. The rig measured the cost of the
    guard: every one of the 611 distinct URLs in its captured knowledge base is
    relative, so a guard meant to be careful excluded 100% of real evidence.
    """
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
    """Whether the *value* must be held by reference outside the evidence plane."""
    return sensitivity in {Sensitivity.AUTH, Sensitivity.SESSION, Sensitivity.CSRF}


def is_replayable(sensitivity: Sensitivity) -> bool:
    """Whether the captured value can be sent again verbatim.

    ``SEMANTIC`` only. A CSRF token is stale, a trace id would collide, transport
    headers are the client's to set, and secrets are resolved from the vault at
    run time rather than copied.
    """
    return sensitivity is Sensitivity.SEMANTIC
