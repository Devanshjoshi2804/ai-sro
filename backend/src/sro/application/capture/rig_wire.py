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
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as bad:
        raise ValueError(f"not an RFC3339 timestamp: {value!r}") from bad
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value!r}")
    return value


Timestamp = Annotated[str, AfterValidator(_a_timestamp)]


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

    query: str | None = None
    chain: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def a_credential_on_the_control_is_dropped_here(self) -> "Component":
        for prose in _COMPONENT_PROSE:
            value = getattr(self, prose)
            if value:
                setattr(self, prose, redact_shapes(value))
        return self


class Landmark(BaseModel):
    role: str
    name: str

    @model_validator(mode="after")
    def a_credential_in_a_landmark_is_dropped_here(self) -> "Landmark":
        self.name = redact_shapes(self.name)
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

    bounds: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    component: Component | None = None
    landmarks: list[Landmark] = Field(default_factory=list)

    @model_validator(mode="after")
    def must_carry_some_signal(self) -> "Target":
        if not any((self.role, self.name, self.text, self.testId, self.cssPath, self.xpath)):
            raise ValueError("element fingerprint carries no usable signal")
        return self

    @model_validator(mode="after")
    def a_credential_on_the_element_is_dropped_here(self) -> "Target":
        for prose in _TARGET_PROSE:
            value = getattr(self, prose)
            if value:
                setattr(self, prose, redact_shapes(value))
        if self.secret:
            self.attributes.pop("value", None)
        if self.attributes:
            self.attributes = redact_attributes(self.attributes)
        return self


class Gesture(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    kind: Literal["click", "type", "select", "press", "upload", "scroll", "hover"]
    target: Target | None = None
    value: str | None = None
    secret: bool = False
    modifiers: list[str] = Field(default_factory=list)
    at: float
    url: str | None = None

    @model_validator(mode="after")
    def a_credential_value_is_dropped_here(self) -> "Gesture":
        if self.secret or (self.target is not None and self.target.secret):
            object.__setattr__(self, "value", None)
        elif self.value:
            object.__setattr__(self, "value", redact_shapes(self.value))
        return self

    @model_validator(mode="after")
    def a_credential_in_the_url_is_dropped_here(self) -> "Gesture":
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
    lowered = (name or "").lower().strip()
    if lowered.startswith(":"):
        return False
    return lowered in SECRET_HEADERS or any(hint in lowered for hint in SECRET_HEADER_HINTS)


def redact_attributes(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: REDACTED if is_secret_name(str(key)) else redact_attributes(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [redact_attributes(item) for item in node]
    if isinstance(node, str):
        return redact_shapes(redact_url(node))
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
    status: int | None = None
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
        for headers in (self.request_headers, self.response_headers):
            for name in list(headers):
                if is_secret_header(name):
                    headers[name] = REDACTED
                else:
                    headers[name] = redact_shapes(headers[name])
        return self

    @model_validator(mode="after")
    def a_credential_elsewhere_on_the_call_is_dropped_here(self) -> "Request":
        self.url = redact_url(self.url)
        for body in (self.request_body, self.response_body):
            if body is not None:
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
    opener_tab_id: int | None = None

    @model_validator(mode="after")
    def a_credential_on_a_page_event_is_dropped_here(self) -> "PageEvent":
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
    if not isinstance(raw.get("events"), list):
        return Batch.model_validate(raw), ()

    adapter: TypeAdapter[Event] = TypeAdapter(Event)
    events: list[Any] = []
    rejected: list[RejectedEvent] = []

    for index, event in enumerate(raw["events"]):
        try:
            events.append(adapter.validate_python(event))
        except ValidationError as problem:
            first = problem.errors()[0]
            where = ".".join(str(part) for part in first.get("loc", ()))
            reason = first.get("msg", "invalid event")
            rejected.append(
                RejectedEvent(index=index, reason=f"{where}: {reason}" if where else reason)
            )

    return Batch.model_validate({**raw, "events": events}), tuple(rejected)
