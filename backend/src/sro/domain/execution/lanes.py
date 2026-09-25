from __future__ import annotations

import hashlib
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from sro.domain.observation.gesture import Call
from sro.domain.observation.trim import path_shape
from sro.domain.skill.workflow import Step

K_SIGHT_ACTIONS = 6


class Lane(StrEnum):
    TOOL = "tool"
    API = "api"
    UI = "ui"
    SIGHT = "sight"


Verdict = Literal["done", "read", "failed", "unknown"]


@dataclass(frozen=True, slots=True)
class SeenCall:
    method: str
    url: str
    status: int | None
    body: str | None = None
    request_body: str | None = None
    request_content_type: str | None = None
    own_frame: bool = True


@dataclass(frozen=True, slots=True)
class StepResult:
    verdict: Verdict
    lane: Lane
    reason: str = ""
    never_left: bool = False
    read: Mapping[str, str] = field(default_factory=dict)
    calls: tuple[SeenCall, ...] = ()
    learned: Mapping[str, str] = field(default_factory=dict)
    fingerprint: str = ""
    expired: bool = False
    keyed: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Broken:
    step: int
    lane: Lane
    fingerprint: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cites_key(step: Step) -> str:
    return _digest("\n".join(step.cites))


def fingerprint_of(lane: Lane, kind: str, evidence: str = "") -> str:
    return _digest(f"{lane}|{kind}|{evidence}")


def lanes_for(
    order: int, *, tool: bool, api: bool, browser: bool, broken: Collection[Broken]
) -> tuple[Lane, ...]:
    ladder = (
        (Lane.TOOL,)
        if tool
        else ((Lane.API,) if api else ()) + ((Lane.UI, Lane.SIGHT) if browser else ())
    )
    dead = {one.lane for one in broken if one.step == order}
    last = ladder[-1]
    return (*(lane for lane in ladder[:-1] if lane not in dead), last)


def accepts(status: int | None, wanted: Collection[int]) -> bool:
    return status is not None and (status in wanted or (not wanted and 200 <= status < 300))


def write_confirmed(
    *, recorded: Call | None, wanted: Collection[int], calls: Collection[SeenCall]
) -> Verdict | None:
    if recorded is None:
        return None
    method, shape = recorded.method.upper(), path_shape(recorded.url)
    statuses = [
        call.status
        for call in calls
        if call.status is not None
        and call.method.upper() == method
        and path_shape(call.url) == shape
    ]
    if any(accepts(status, wanted) for status in statuses):
        return "done"
    if any(status >= 500 for status in statuses):
        return "unknown"
    if any(400 <= status < 500 for status in statuses):
        return "failed"
    return None


def never_left_step(tried: Collection[StepResult]) -> bool:
    return all(result.never_left for result in tried)
