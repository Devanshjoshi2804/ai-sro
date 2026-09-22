"""The extension's batch protocol, as the rig defined it. Pydantic, because it is a wire format.

Copied rather than imported: see 'Decision: no path dependency' in the plan.
Proved against new-chrome-extension/fixtures/, which a real browser produced.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

# The credential vocabulary and the rules that act on it, imported rather than
# held here: they live in `sro.domain.observation.redaction`, because the other
# belt -- `sro.domain.observation.trim.body_keys`, which applies the same three
# rules to every body that reaches a prompt -- is in the domain, the domain may
# not import this module, and one rule with two copies is the thing that has
# already gone wrong once. Re-exported under their own names so this module
# stays the one address for the wire's redaction.
from sro.domain.observation.redaction import SECRET_HEADER_HINTS as SECRET_HEADER_HINTS
from sro.domain.observation.redaction import SECRET_HEADERS as SECRET_HEADERS
from sro.domain.observation.redaction import SECRET_SHAPES as SECRET_SHAPES
from sro.domain.observation.redaction import SECRET_SHAPES_ANY_CASE as SECRET_SHAPES_ANY_CASE
from sro.domain.observation.redaction import SECRET_WORDS as SECRET_WORDS
from sro.domain.observation.redaction import UNINSPECTABLE as UNINSPECTABLE
from sro.domain.observation.redaction import is_secret_name as is_secret_name
from sro.domain.observation.redaction import redact_body as redact_body
from sro.domain.observation.redaction import redact_shapes as redact_shapes
from sro.domain.observation.redaction import redact_url as redact_url
from sro.domain.observation.redaction import shapes_in as shapes_in
from sro.domain.shared.hosts import REDACTED as REDACTED
from sro.domain.shared.hosts import headers_without_markers as headers_without_markers


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
    required: bool | None = None
    """Ext's own `allowBlank: false`, where the component said."""

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
    required: bool | None = None
    """Whether the PAGE says this field must be filled -- `aria-required`, the
    HTML5 attribute, or a star on its label. Three states kept as three: None
    is a page that said nothing, and coercing it to False would be this system
    claiming a form said something it never said."""

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
