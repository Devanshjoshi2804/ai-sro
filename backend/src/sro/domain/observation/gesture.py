from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Literal

from sro.domain.shared.hosts import origin_of

Kind = Literal["click", "type", "select", "press", "upload", "scroll", "hover"]


def new_gesture_id() -> str:
    return "ges_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class Component:
    item_id: str | None = None
    query: str | None = None
    field_label: str | None = None
    name: str | None = None
    xtype: str | None = None
    required: bool | None = None
    chain: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Landmark:
    role: str
    name: str


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
    required: bool | None = None

    component: Component | None = None
    bounds: dict[str, float] = field(default_factory=dict, hash=False)
    attributes: dict[str, object] = field(default_factory=dict, hash=False)
    landmarks: tuple[Landmark, ...] = ()


@dataclass(frozen=True, slots=True)
class FrameHop:
    index: int
    url: str | None = None


@dataclass(frozen=True, slots=True)
class AfterState:
    value: str | None = None
    visible: bool | None = None
    enabled: bool | None = None


@dataclass(frozen=True, slots=True)
class OutlineField:
    role: str
    label: str
    required: bool | None = None
    options: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class OutlineMessage:
    role: str


@dataclass(frozen=True, slots=True)
class Outline:
    headings: tuple[str, ...] = ()
    landmarks: tuple[Landmark, ...] = ()
    fields: tuple[OutlineField, ...] = ()
    buttons: tuple[str, ...] = ()
    messages: tuple[OutlineMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class Action:
    kind: Kind
    at: float
    value: str | None = None
    secret: bool = False
    url: str | None = None
    target: Target | None = None
    modifiers: tuple[str, ...] = ()
    frame_path: tuple[FrameHop, ...] | None = None
    detail: int | None = None
    trusted: bool | None = None
    after: AfterState | None = None
    outlines: tuple[Outline, ...] = ()


@dataclass(frozen=True, slots=True)
class Body:
    text: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    redacted_fields: tuple[str, ...] = ()
    blob_uri: str | None = None


@dataclass(frozen=True, slots=True)
class Call:
    method: str
    url: str
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
    opener_tab_id: int | None = None


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
class GestureBatch:
    batch_id: str
    device_id: str
    tenant: str
    mode: str
    received_at: str
    started_at: str = ""
    ended_at: str = ""
    recording_id: str | None = None
    accepted: int = 0
    rejected: int = 0


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
    page: str | None = None
    values_seen: list[ValueSeen] = field(default_factory=list)
    confidence: str | None = None
    why: str | None = None
    model: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None


def passed_through(gesture: Gesture) -> bool:
    here = origin_of(gesture.system or "")
    return any(mark.url and origin_of(mark.url) not in ("", here) for mark in gesture.page_events)
