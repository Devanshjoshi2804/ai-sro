"""What the rig keeps of a gesture, as the arithmetic reads it.

Frozen, framework-free. The wire format the extension speaks is
`sro.application.capture.rig_wire`; `correlate` there turns one into these.
Every module in the domain that reads a control's identity, a typed value or
a recorded call reads it from here and from nowhere else.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["click", "type", "select", "press", "upload", "scroll", "hover"]


def new_gesture_id() -> str:
    return "ges_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class Component:
    """What an ExtJS page knows about the control; None on plain HTML."""

    item_id: str | None = None
    query: str | None = None
    field_label: str | None = None
    name: str | None = None
    xtype: str | None = None


@dataclass(frozen=True, slots=True)
class Target:
    tag: str | None = None
    role: str | None = None
    name: str | None = None
    secret: bool = False
    text: str | None = None
    test_id: str | None = None
    css_path: str | None = None
    xpath: str | None = None
    component: Component | None = None


@dataclass(frozen=True, slots=True)
class Action:
    """The gesture itself: what was done, to what, with what typed."""

    kind: Kind
    at: float
    value: str | None = None
    secret: bool = False
    url: str | None = None
    target: Target | None = None


@dataclass(frozen=True, slots=True)
class Body:
    text: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    redacted_fields: tuple[str, ...] = ()
    blob_uri: str | None = None


@dataclass(frozen=True, slots=True)
class Call:
    """A recorded exchange, the part of it the belts read: never a response
    body's text beyond what `confirming_read` compares."""

    method: str
    url: str
    # The rig's wire `request_id` is a required string, so a call that came off
    # a batch always has one; "" is what a hand-built call has instead of None,
    # which keeps the type a plain str for everything that reads it.
    request_id: str = ""
    started_at: float | None = None
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: Body | None = None
    status: int | None = None
    response_body: Body | None = None
    failure_reason: str | None = None
    blocked_reason: str | None = None
    tab_id: int | None = None


@dataclass(frozen=True, slots=True)
class PageMark:
    at: float
    page_kind: str
    url: str | None = None
    detail: str | None = None
    tab_id: int | None = None


@dataclass
class Gesture:
    id: str
    tenant: str
    stream_id: str
    batch_id: str
    at: float
    url: str | None
    system: str | None
    tab_id: int | None
    frame_url: str | None
    action: Action
    page_url: str | None = None
    requests: list[Call] = field(default_factory=list)
    page_events: list[PageMark] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ValueSeen:
    field: str
    value: str


@dataclass
class Intent:
    gesture_id: str
    tenant: str
    act: str | None = None
    object: str | None = None
    system: str | None = None
    page: str | None = None
    values_seen: list[ValueSeen] = field(default_factory=list)
    continues: str | None = None
    confidence: str | None = None
    why: str | None = None
    model: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
