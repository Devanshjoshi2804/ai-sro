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
    target: Target
    value: str | None = None  # absent on click and press
    secret: bool = False  # absent on everything but a credential field
    modifiers: list[str] = Field(default_factory=list)
    at: float  # Unix seconds, float — recorder.js's format
    url: str | None = None

    @model_validator(mode="after")
    def a_credential_value_is_dropped_here(self) -> "Gesture":
        """AGENTS.md: credential values never reach storage. This is the boundary."""
        if self.secret or self.target.secret:
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
    adapter: TypeAdapter[Event] = TypeAdapter(Event)
    events: list[Any] = []
    rejected: list[RejectedEvent] = []

    for index, event in enumerate(raw.get("events") or []):
        try:
            events.append(adapter.validate_python(event))
        except ValidationError as problem:
            first = problem.errors()[0]
            rejected.append(RejectedEvent(index=index, reason=first.get("msg", "invalid event")))

    return Batch.model_validate({**raw, "events": events}), tuple(rejected)
