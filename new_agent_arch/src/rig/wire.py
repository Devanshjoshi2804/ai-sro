"""The extension's wire shapes, from docs/14-extension-protocol.md.

Copied rather than imported: see 'Decision: no path dependency' in the plan.
Proved against new-chrome-extension/fixtures/, which a real browser produced.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator


class Component(BaseModel):
    framework: str | None = None
    xtype: str | None = None
    itemId: str | None = None
    name: str | None = None
    fieldLabel: str | None = None
    text: str | None = None
    query: str | None = None
    chain: list[str] = Field(default_factory=list)


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
        return self


class GestureEvent(BaseModel):
    kind: Literal["gesture"]
    gesture: Gesture
    tab_id: int | None = None
    frame_url: str | None = None
    page_url: str | None = None


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
    return lowered in SECRET_HEADERS or any(hint in lowered for hint in SECRET_HEADER_HINTS)


class Request(BaseModel):
    request_id: str
    method: str
    url: str
    resource_type: str | None = None
    started_at: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Body | None = None
    status: int | None = None  # null on a failed request
    status_text: str | None = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Body | None = None
    redirect_chain: list[Any] = Field(default_factory=list)
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
                if is_secret_header(name):
                    headers[name] = REDACTED
        return self


class RequestEvent(BaseModel):
    kind: Literal["request"]
    request: Request
    tab_id: int | None = None
    frame_url: str | None = None


class PageEvent(BaseModel):
    kind: Literal["page"]
    at: str
    page_kind: str
    url: str | None = None
    detail: str | None = None
    tab_id: int | None = None


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
            rejected.append(RejectedEvent(index=index, reason=first.get("msg", "invalid event")))

    return Batch.model_validate({**raw, "events": events}), tuple(rejected)
