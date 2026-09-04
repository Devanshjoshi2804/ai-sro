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
    # The tab's own url, as opposed to `url`, which is the frame's.
    page_url: str | None = None
    requests: list[Request] = field(default_factory=list)
    page_events: list[PageEvent] = field(default_factory=list)


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
    # Part of out_tokens, as on Answer: what the model thought and nobody read.
    thought_tokens: int = 0
    cost_usd: float = 0.0
    # Mirrors Answer.unpriced: True when cost_usd cannot be trusted.
    unpriced: bool = False
    error: str | None = None
