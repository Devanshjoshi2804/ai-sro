"""What the rig keeps. A1 fills `requests`; A3 produces `Intent`."""

import secrets
from dataclasses import dataclass, field

from rig.wire import Gesture as WireGesture
from rig.wire import PageEvent, Request


def new_gesture_id() -> str:
    return "ges_" + secrets.token_hex(16)


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
    gesture: WireGesture
    requests: list[Request] = field(default_factory=list)
    page_events: list[PageEvent] = field(default_factory=list)
    shot_ref: str | None = None
    ax_ref: str | None = None


@dataclass
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
    cost_usd: float = 0.0
    error: str | None = None
