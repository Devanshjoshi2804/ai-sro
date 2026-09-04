"""The extension's wire shapes, from docs/14-extension-protocol.md.

Copied rather than imported: see 'Decision: no path dependency' in the plan.
Proved against new-chrome-extension/fixtures/, which a real browser produced.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import unquote_plus, urlparse

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)


def _a_timestamp(value: str) -> str:
    """An RFC3339 string, checked here rather than where it is finally read.

    correlate._epoch parses these strictly, and it runs *after* parse_batch --
    so one unparseable `started_at` raised out of the ingest route and cost the
    whole batch a 500, taking the three hundred good events beside it. Worse
    than the loss: a 500 is not a permanent 4xx, so the extension keeps the
    rows queued and retries forever while that device's capture stalls in
    silence. The batch boundary already owns 'a rejected event does not reject
    the batch'; the format check belongs there with it, so the bad event
    becomes one named RejectedEvent and nothing downstream has to defend.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as bad:
        raise ValueError(f"not an RFC3339 timestamp: {value!r}") from bad
    if parsed.tzinfo is None:
        # The parseable-but-zone-less case, which is worse than the
        # unparseable one because nothing raises. correlate._epoch calls
        # .timestamp() on this, and a naive datetime is read as LOCAL time --
        # so on a machine at +05:30 the same instant as
        # '2026-08-31T08:40:04.812Z' lands 19800s away, every request detaches
        # from its gesture, and every gesture is read with no evidence at all.
        # Silently: no error, no orphan count that looks wrong, just worse
        # readings. AGENTS.md requires timezone-aware timestamps and this is
        # the boundary that can still say so.
        raise ValueError(f"timestamp has no timezone: {value!r}")
    return value


Timestamp = Annotated[str, AfterValidator(_a_timestamp)]


# The free-text fields of the two models below: what a person can read on the
# screen, and therefore what a page can render a credential into. `label(el)` in
# the extension's recorder falls back to innerText, so a screen showing a key
# puts that key here.
#
# Everything NOT on these lists is left alone on purpose. `itemId`, `query`,
# `xtype`, `testId`, `role` and `cssPath` are what shape.target_identity and
# shape_key are built from, and a redaction there would silently change a
# workflow's shape key so the same job stopped matching itself across
# occurrences. `chain`, `tag`, `xpath` and `bounds` are locators and geometry by
# the same argument.
#
# Only the SHAPE rule runs on these, never the name rule: a fieldLabel reading
# "Password" is a NAME, and is the single most useful thing in the evidence for
# telling a model what the operator was doing. Measured over the 83-gesture acme
# capture: 56 distinct real labels, 0 blanked.
_COMPONENT_PROSE = ("name", "fieldLabel", "text")
_TARGET_PROSE = ("name", "text")


class Component(BaseModel):
    framework: str | None = None
    xtype: str | None = None
    itemId: str | None = None
    name: str | None = None
    fieldLabel: str | None = None
    text: str | None = None
    query: str | None = None
    chain: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def a_credential_on_the_control_is_dropped_here(self) -> "Component":
        """The DOM plane's half of the rule every other model here already has.

        `fieldLabel` and `text` are stored verbatim in `gestures.gesture_json`
        AND go through trim() into the per-gesture reading prompt and
        as_evidence() into the umbrella prompt -- so a token rendered as a label
        reached both models and the disk. Same boundary as its five siblings,
        for the reason they give: a rule applied at a call site is a rule the
        next caller walks past.
        """
        for prose in _COMPONENT_PROSE:
            value = getattr(self, prose)
            if value:
                setattr(self, prose, redact_shapes(value))
        return self


class Target(BaseModel):
    tag: str | None = None
    role: str | None = None
    name: str | None = None
    secret: bool = False
    text: str | None = None
    testId: str | None = None
    cssPath: str | None = None
    xpath: str | None = None
    bounds: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    component: Component | None = None  # null on plain HTML; only ExtJS has one

    @model_validator(mode="after")
    def must_carry_some_signal(self) -> "Target":
        """The protocol refuses a fingerprint with nothing to match on."""
        if not any((self.role, self.name, self.text, self.testId, self.cssPath, self.xpath)):
            raise ValueError("element fingerprint carries no usable signal")
        return self

    @model_validator(mode="after")
    def a_credential_on_the_element_is_dropped_here(self) -> "Target":
        """`name` and `text` are prose; `attributes` is an open dump.

        Runs after must_carry_some_signal, and cannot defeat it: redact_shapes
        substitutes, so a name that was entirely a JWT comes back as the marker
        -- still a signal, and still stable across occurrences because the
        substitution is deterministic. A control whose only name is a credential
        has no identity worth keeping anyway.
        """
        for prose in _TARGET_PROSE:
            value = getattr(self, prose)
            if value:
                setattr(self, prose, redact_shapes(value))
        if self.attributes:
            self.attributes = redact_attributes(self.attributes)
        return self


class Gesture(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    kind: Literal["click", "type", "select", "press", "upload", "scroll", "hover"]
    # A scroll has no target: you scroll a page, not an element. Real capture
    # from the acme tenant carries scrolls with the key absent entirely, and
    # requiring it rejected every one of them -- 15% of that sample's gestures.
    target: Target | None = None
    value: str | None = None  # absent on click and press
    secret: bool = False  # absent on everything but a credential field
    modifiers: list[str] = Field(default_factory=list)
    at: float  # Unix seconds, float — recorder.js's format
    url: str | None = None

    @model_validator(mode="after")
    def a_credential_value_is_dropped_here(self) -> "Gesture":
        """AGENTS.md: credential values never reach storage. This is the boundary."""
        if self.secret or (self.target is not None and self.target.secret):
            object.__setattr__(self, "value", None)
        elif self.value:
            # Not flagged, and still a credential: a token pasted into an
            # ordinary search box is not typed into an input[type=password],
            # so nothing upstream marks it. The shape does.
            object.__setattr__(self, "value", redact_shapes(self.value))
        return self

    @model_validator(mode="after")
    def a_credential_in_the_url_is_dropped_here(self) -> "Gesture":
        """The same boundary, one field over. `#access_token=...` on a gesture
        url reached disk while the typed value beside it was guarded -- which
        is the shape of every credential defect this codebase has had: a rule
        applied at one field is a rule the next field walks past.
        """
        if self.url:
            object.__setattr__(self, "url", redact_url(self.url))
        return self


class GestureEvent(BaseModel):
    kind: Literal["gesture"]
    gesture: Gesture
    tab_id: int | None = None
    frame_url: str | None = None
    page_url: str | None = None

    @model_validator(mode="after")
    def a_credential_in_a_url_is_dropped_here(self) -> "GestureEvent":
        """frame_url has its own column on `gestures`; both are stored."""
        if self.frame_url:
            self.frame_url = redact_url(self.frame_url)
        if self.page_url:
            self.page_url = redact_url(self.page_url)
        return self


class Body(BaseModel):
    text: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    encoding: str | None = None
    redacted_fields: list[str] = Field(default_factory=list)
    blob_uri: str | None = None


# Mirrors SECRET_HEADERS and SECRET_HEADER_HINTS in the extension's
# new-chrome-extension/src/content/sensitivity.module.js. Note this rule is
# deliberately not the field rule: a header matches on an exact lowered name OR
# on a substring hint, because `x-acme-session-key` has to match on `sess`.
# trim.is_secret_name() matches whole words precisely because the opposite is
# true of body fields -- see the ten real shipping fields a substring rule
# blanks. These live here rather than in trim.py because trim imports from
# wire, and the Request model below is what applies them.
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
REDACTED = "«redacted»"


def is_secret_header(name: str) -> bool:
    """Whether a header called this carries a credential."""
    lowered = (name or "").lower().strip()
    # An HTTP/2 pseudo-header is the request line, not a header, and never a
    # credential -- but `:authority` (the host) contains the hint "auth", so the
    # hints below redacted it and the stored request lost its host. Mirrors the
    # same first check in the extension's isSecretHeader.
    if lowered.startswith(":"):
        return False
    return lowered in SECRET_HEADERS or any(hint in lowered for hint in SECRET_HEADER_HINTS)


# Mirrors SECRET_WORDS and isSecretName in the same extension module. This rule
# lives here rather than in trim.py -- where it used to -- for the reason the
# header rule already does: trim imports wire, the reverse would be a cycle,
# and it is the models below that have to apply it to everything that reaches
# the store. trim.py re-exports both.
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

# Stored in place of a body this process could not parse to redact. The
# extension writes the same sentence in redacted_fields for the same reason.
UNINSPECTABLE = "«whole body: could not be parsed to redact»"

# Mirrors SECRET_SHAPE and SECRET_SHAPE_ANY_CASE in the same extension module,
# which are generated from `sensitivity.SECRET_SHAPES`. The value rule beside
# the name rules, and it exists because the name rule cannot be finished: a
# field name is chosen by whoever wrote the vendor's API, an open vocabulary
# guessed at forever, and the round before this one found 57 of 85 realistic
# credential names unmatched and then blanked three real warehouse fields
# closing the gap. A shape is not open in that way -- a JWT is a JWT in any
# field, and a warehouse dock code is never a PEM block.
#
# Measured over 47,969 distinct real values from the acme store plus
# knowledge-base/http/exchanges -- the VALUES, which nothing here had ever
# measured, only the names: every pattern below matches zero of them.
# tests/test_corpus.py is that measurement as a test.
#
# High-entropy detection is deliberately absent, on the same corpus: a Shannon
# threshold of 4.5 bits over runs of 20+ token characters blanks 791 real
# values, 4.0 blanks 14,419, 3.5 blanks 21,250 -- and 5.0 blanks nothing at
# all. There is no threshold between useless and destructive.
SECRET_SHAPES: tuple[tuple[str, str], ...] = (
    ("jwt", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*"),
    ("aws_key_id", r"(?:AKIA|ASIA|AIDA|AROA)[A-Z0-9]{16}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    ("github_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("google_api_key", r"AIza[A-Za-z0-9_-]{35}"),
    ("slack_token", r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    # The whole block and not just the BEGIN line, or the substitution would
    # replace the header and leave the key material under a marker claiming it
    # had been removed. The END clause is optional so a truncated capture still
    # loses its opening line.
    (
        "private_key",
        (
            r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"
            r"(?:[\s\S]*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----)?"
        ),
    ),
)
SECRET_SHAPES_ANY_CASE: tuple[tuple[str, str], ...] = (
    # A scheme name plus a blob, and so case-blind -- kept apart from the set
    # above because `AKIA`, `AIza` and `eyJ` are case-SENSITIVE prefixes that a
    # blind match would widen over the lowercase identifiers this corpus is
    # full of.
    ("bearer", r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
    ("basic_auth", r"\bbasic\s+[A-Za-z0-9+/]{16,}={0,2}"),
)

_SHAPE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in SECRET_SHAPES))
_SHAPE_ANY_CASE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in SECRET_SHAPES_ANY_CASE), re.IGNORECASE
)


def shapes_in(text: str | None) -> tuple[str, ...]:
    """Which credential shapes appear in this text, in the order first seen.

    Kept apart from the redaction so a body can record *why* it lost something.
    "This went because it looked like a JWT" is a different fact from "this
    went because it was called password", and a reviewer wants to tell them
    apart -- while the marker left behind is the same either way, so nothing
    downstream has to learn a second convention.
    """
    return tuple(
        dict.fromkeys(
            match.lastgroup
            for matcher in (_SHAPE, _SHAPE_ANY_CASE)
            for match in matcher.finditer(text or "")
            if match.lastgroup
        )
    )


def redact_shapes(text: str) -> str:
    """The same text with every credential-shaped run replaced.

    A substitution rather than a verdict on the whole value: a shape can sit
    inside a larger string -- a bearer scheme in free text, a PEM block in a
    log line -- and every byte that did not match is left exactly as it
    arrived. Text with no credential in it comes back identical, which is what
    lets this run over a URL that must not be re-encoded.
    """
    if not text:
        return text
    return _SHAPE_ANY_CASE.sub(REDACTED, _SHAPE.sub(REDACTED, text))


def _words_of(text: str) -> list[str]:
    """camelCase, snake_case and "Shipping Date" alike, split into words.

    The acronym rule is `([A-Z]{2,})([A-Z][a-z])` and deliberately not
    `([A-Z]+)([A-Z][a-z])`: the wider one splits the lone `N` off
    `pickNPassAutoDropLocation` and leaves `Pass` bare, blanking a real
    warehouse field ("Pick N Pass"). Two-or-more needs three capitals in a row
    before it cuts, so `SAMLResponse` splits into saml/response -- which is what
    makes the word `saml` worth having -- and `NPass` stays whole. Measured over
    3,270 distinct field, header and query-parameter names from the real acme
    store plus knowledge-base/http/exchanges: it changes none of them.
    """
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    spaced = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", spaced)
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


# An OAuth authorization code is a credential; a warehouse `code` is not.
# `code` cannot join SECRET_WORDS -- that rule matches whole words, and this
# tenant's captured traffic carries 138 distinct field names ending in one
# (areaCode, locationCode, pickZoneCode, verificationCode...). So the rule is
# narrowed twice: the parameter must be named *exactly* `code`, not merely
# contain the word, and the same query or fragment must carry another OAuth
# parameter beside it -- which is what tells a callback hop from an ordinary
# call. Measured over 23,751 URLs in that capture: no `code` parameter and no
# `state` parameter appear at all, and the three query names containing "code"
# (areaCode, operationCode, barCodeTemplateId) are untouched by an exact match.
# This costs no live evidence and closes the last row of the audit's table.
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
    """An `a=b&c=d` string with every credential-named value replaced.

    Spliced by hand rather than round-tripped through parse_qsl + urlencode,
    which is the extension's rule and its stated reason: re-encoding touches
    every pair rather than the one that matched -- it collapses a repeated key,
    turns a literal space into `+`, and percent-encodes the marker itself, so
    grepping stored evidence for the «redacted» every other path writes finds
    nothing. Splicing leaves every untouched byte exactly as the browser sent
    it. A pair with no `=` is given one, as the extension does: the name alone
    is what matched.
    """
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
    """A URL with credential-named query and fragment values replaced.

    `?token=...` is as much a credential as the header form, and a URL is
    stored on every event there is -- a navigation, a request, and the frame a
    gesture happened in. The fragment is checked too when it is shaped like a
    query string: `#access_token=...` is how an OAuth implicit flow hands a
    token back, and the audit found one on disk.

    A relative URL is redacted too, unlike the extension's copy. The extension
    leaves one alone because it cannot RESOLVE it -- the service worker has no
    page to resolve against -- and that reasoning is about resolution, which
    nothing here does: the query and fragment are spliced by raw string
    position and need no scheme or host. Skipping them cost the whole corpus:
    every one of the 611 distinct URLs in the captured knowledge base is
    relative, so the guard that was meant to be conservative excluded 100% of
    real evidence from URL redaction. Zero of them redact today, so closing it
    costs nothing and covers the shape all real traffic has.

    An unparseable URL is still left alone rather than guessed at.
    """
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
    # The shape pass runs over the whole rebuilt URL rather than only the
    # query, because a token can sit in a path segment where there is no
    # parameter name to judge it by. It substitutes, so a URL carrying no
    # credential comes back byte-identical -- the property the hand-splicing
    # above exists to keep.
    return redact_shapes(head if hash_at == -1 else f"{head}#{fragment}")


_XML_FIELD = re.compile(r"<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)</\1>")
_XML_ATTR = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')
# Any `name=value` or `name: value` pair, wherever it sits in an otherwise
# unstructured body. The parsers above each want a whole well-formed document;
# this wants only a field name next to a field value, which is all a
# name-based rule needs to act -- and is what catches a graphql mutation.
_PAIR = re.compile(r"([A-Za-z_][\w.-]*)(\s*[=:]\s*)([^\s&;,]*)")
_MULTIPART_BOUNDARY = re.compile(r'boundary=(?:"([^"]+)"|([^;]+))', re.IGNORECASE)
_PART_NAME = re.compile(r'name="([^"]*)"', re.IGNORECASE)
_HEADER_GAP = re.compile(r"\r?\n\r?\n")
_PART_END = re.compile(r"\r?\n--")


def redact_data(node: Any) -> Any:
    """The same rule at every depth, through dicts and lists alike.

    The flat version of this guarded the top level of a JSON object and
    nothing else, so `{"auth": {"password": ...}}` walked straight past it.
    """
    if isinstance(node, dict):
        return {
            key: REDACTED if is_secret_name(str(key)) else redact_data(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [redact_data(item) for item in node]
    return node


def redact_attributes(node: Any) -> Any:
    """Every DOM attribute of the element the operator touched, by all three rules.

    `Target.attributes` is `dict[str, Any]` -- whatever the page happened to put
    on the element -- so no single rule reaches it. `data-auth-token` is caught
    by its NAME, `href="/cb?access_token=..."` by the URL rule inside its value,
    and an `X-Acme-Ticket` copied onto a `data-` attribute only by its SHAPE.
    redact_url ends in redact_shapes, so a string leaf gets the last two from one
    call.

    redact_data one clause longer, rather than a change to redact_data: that one
    runs over request bodies, where the shape pass already follows it in
    redact_body and a URL rule on every JSON string leaf would be a behaviour
    change to every stored body. Here nothing else runs at all -- this field was
    write-only, read by nothing and redacted by nothing.

    The field rule and not the header one, deliberately: an attribute named
    `placeholder` whose value is "Password" is a LABEL. Measured over the acme
    capture -- 13 distinct attribute names, 95 distinct values -- none move.
    """
    if isinstance(node, dict):
        return {
            key: REDACTED if is_secret_name(str(key)) else redact_attributes(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [redact_attributes(item) for item in node]
    if isinstance(node, str):
        return redact_url(node)
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
        # Not the document it claimed to be: truncated, or never JSON at all.
        # Replaced whole rather than stored unexamined -- see redact_body.
        return UNINSPECTABLE
    if isinstance(document, str):
        # A bare JSON string is a document too, and `"password=hunter2"` is
        # what one looks like when it carries a credential.
        return json.dumps(_redact_pairs(document), ensure_ascii=False)
    cleaned = redact_data(document)
    # ensure_ascii=False for the same reason the query string is spliced rather
    # than re-encoded: the default writes the marker as \u00abredacted\u00bb,
    # and then grepping stored evidence for «redacted» finds nothing. The
    # extension's JSON.stringify writes it literally; so does this.
    #
    # Unchanged means unchanged: the original bytes, not a reserialisation.
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
    """A part names its field on one line and carries the value on another, so
    the pair scanner never sees the two together and cannot act on the name."""
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
    """One body, whatever shape it is, with every credential-named value gone.

    Mirrors the extension's redactBody: JSON walked recursively (arrays and
    bare strings included), XML and SOAP, multipart, form-urlencoded --
    including when the mime type is absent and the text is merely shaped like
    a form -- and, when no parser fits, a scan for `name=value` pairs rather
    than storing the text unread.

    Where a parser was chosen and the document did not parse, the body is
    replaced wholesale. An unparsed body that might hold a credential is the
    failure; a body replaced entirely is legible and safe.
    """
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
    """The name rule above, then the shape rule over whatever it produced.

    Last and over the whole body, whatever parser ran: a shape needs no field
    name, so it reaches a credential in a value the name rule had no name to
    judge -- including through a body no parser fitted and through one replaced
    by UNINSPECTABLE, where the name rule gave up entirely.
    """
    cleaned = _redact_named(text, mime_type)
    return cleaned if cleaned is None else redact_shapes(cleaned)


class RedirectHop(BaseModel):
    """One hop of a redirect chain, typed to what actually produces one.

    The extension sends an empty list today; the Steel capture path records
    url, status and location (sro.domain.recording.network.RedirectHop), so
    those are the three fields here rather than protocol nobody sends. Typed
    at all, which the `list[Any]` this replaces was not: a hop was the one
    part of a request that nothing validated and nothing redacted, and the
    audit put both a `?code=` URL and an Authorization header on disk through
    it. A key outside these three is dropped rather than stored unexamined --
    the same ruling as a body that cannot be parsed.

    The cost of that ruling, recorded because it is a behaviour change on a
    field that used to pass everything through: the day the extension starts
    sending a fourth key on a hop, this loses it silently. Nothing warns, and
    nothing here can -- an unknown key is exactly what the `list[Any]` vector
    was. So a new hop field is a change to THIS class, declared and redacted
    like the three above, and never a widening back to `Any`.
    """

    url: str | None = None
    status: int | None = None
    location: str | None = None

    @model_validator(mode="after")
    def a_credential_on_a_hop_is_dropped_here(self) -> "RedirectHop":
        if self.url:
            self.url = redact_url(self.url)
        if self.location:
            self.location = redact_url(self.location)
        return self


class Request(BaseModel):
    request_id: str
    method: str
    url: str
    resource_type: str | None = None
    started_at: Timestamp
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Body | None = None
    status: int | None = None  # null on a failed request
    status_text: str | None = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Body | None = None
    redirect_chain: list[RedirectHop] = Field(default_factory=list)
    duration_ms: int | None = None
    from_cache: bool = False
    failure_reason: str | None = None
    blocked_reason: str | None = None

    @model_validator(mode="after")
    def a_credential_header_is_dropped_here(self) -> "Request":
        """Same boundary, same reason, as the typed credential above.

        trim._call() already keeps headers out of the prompt, so this is about
        the store: save_batch writes the request verbatim, and an Authorization
        header or a session cookie sitting in a row is the thing AGENTS.md
        forbids. The extension redacts these client-side and demonstrably does
        -- 270 markers in the real acme capture -- but a rule that runs only in
        a browser is one a browser can be made not to run.

        The name is kept and the value replaced, so a reader can still see that
        a call was authenticated.
        """
        for headers in (self.request_headers, self.response_headers):
            for name in list(headers):
                # A header nobody named a credential can still carry one: an
                # `X-Acme-Ticket` holding a JWT is the same secret as an
                # Authorization holding it, and only the value says so.
                if is_secret_header(name):
                    headers[name] = REDACTED
                else:
                    headers[name] = redact_shapes(headers[name])
        return self

    @model_validator(mode="after")
    def a_credential_elsewhere_on_the_call_is_dropped_here(self) -> "Request":
        """The header rule above covered one field of this model's eight.

        A `?session_token=` in the url, a `{"password": ...}` in either body,
        and a hop in redirect_chain are the same credential by another route,
        and the audit proved all of them on disk with the header rule right
        there in the same class. Both belts run at the parse boundary, once,
        because a rule that runs at a call site is a rule the next caller does
        not run.
        """
        self.url = redact_url(self.url)
        for body in (self.request_body, self.response_body):
            if body is not None:
                # Read off the original text, before redact_body replaces it:
                # a body that lost a value to the SHAPE rule says so in
                # redacted_fields, beside the names the extension put there for
                # the ones that went by name. Same marker in the text either
                # way; different fact about why.
                shaped = shapes_in(body.text)
                body.text = redact_body(body.text, body.mime_type)
                body.redacted_fields += [f"«shape: {shape}»" for shape in shaped]
        return self


class RequestEvent(BaseModel):
    kind: Literal["request"]
    request: Request
    tab_id: int | None = None
    frame_url: str | None = None

    @model_validator(mode="after")
    def a_credential_in_a_url_is_dropped_here(self) -> "RequestEvent":
        """An orphan request is stored as the whole event, frame_url included."""
        if self.frame_url:
            self.frame_url = redact_url(self.frame_url)
        return self


class PageEvent(BaseModel):
    kind: Literal["page"]
    at: Timestamp
    page_kind: str
    url: str | None = None
    detail: str | None = None
    tab_id: int | None = None

    @model_validator(mode="after")
    def a_credential_on_a_page_event_is_dropped_here(self) -> "PageEvent":
        """A page event is stored whole -- attached to a gesture, or in
        orphan_pages -- and the audit landed a `?magic_link_token=` in url and
        a credential in detail, which is free text and so gets the body rule.
        """
        if self.url:
            self.url = redact_url(self.url)
        self.detail = redact_body(self.detail, None)
        return self


class SnapshotEvent(BaseModel):
    kind: Literal["snapshot"]
    url: str | None = None
    taken_at: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


Event = Annotated[
    GestureEvent | RequestEvent | PageEvent | SnapshotEvent,
    Field(discriminator="kind"),
]


class Batch(BaseModel):
    batch_id: str
    device_id: str
    started_at: str
    ended_at: str
    mode: Literal["passive", "teaching"] = "passive"
    recording_id: str | None = None
    events: list[Event]


@dataclass(frozen=True, slots=True)
class RejectedEvent:
    index: int
    reason: str


def parse_batch(raw: dict[str, Any]) -> tuple[Batch, tuple[RejectedEvent, ...]]:
    """Parse a batch, keeping every event that parses and naming those that do not.

    The protocol is explicit: "A rejected event does not reject the batch." One
    unrecognised gesture kind must cost one event, not the three hundred good ones
    beside it. Losing a morning of evidence because the extension shipped a new
    gesture is the failure this system exists to prevent.
    """
    if not isinstance(raw.get("events"), list):
        # A batch whose events cannot even be enumerated is a malformed
        # ENVELOPE, not a batch containing bad events. Defaulting to [] here
        # answers 202 for a truncated body and -- because save_batch is
        # idempotent on batch_id -- permanently poisons that id, so the real
        # retry is discarded as "already had it". Silent, total loss of a batch.
        # Let the envelope model refuse it and say why; the route turns that
        # into a 422.
        return Batch.model_validate(raw), ()

    adapter: TypeAdapter[Event] = TypeAdapter(Event)
    events: list[Any] = []
    rejected: list[RejectedEvent] = []

    for index, event in enumerate(raw["events"]):
        try:
            events.append(adapter.validate_python(event))
        except ValidationError as problem:
            first = problem.errors()[0]
            # The location, not only the message: "Input should be a valid
            # number" names nothing a person can act on, and the whole point of
            # a RejectedEvent is that somebody can find out what the extension
            # sent that this could not read.
            where = ".".join(str(part) for part in first.get("loc", ()))
            reason = first.get("msg", "invalid event")
            rejected.append(
                RejectedEvent(index=index, reason=f"{where}: {reason}" if where else reason)
            )

    return Batch.model_validate({**raw, "events": events}), tuple(rejected)
