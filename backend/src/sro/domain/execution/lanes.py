from __future__ import annotations

import hashlib
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from sro.domain.observation.gesture import AfterState, Call
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
    return tuple(lane for lane in ladder if lane not in dead)


def write_confirmed(
    *, recorded: Call | None, wanted: Collection[int], calls: Collection[SeenCall]
) -> Verdict | None:
    if recorded is None:
        return None
    method, shape = recorded.method.upper(), path_shape(recorded.url)
    for call in reversed(tuple(calls)):
        if call.status is None or call.method.upper() != method or path_shape(call.url) != shape:
            continue
        if call.status >= 400:
            return "failed"
        if call.status in wanted or (not wanted and 200 <= call.status < 300):
            return "done"
    return None


def after_matches(
    expected: AfterState | None, seen: AfterState | None, *, value: str | None
) -> bool:
    if expected is None or seen is None:
        return False
    want = value if value is not None else expected.value
    return (
        (expected.visible is None or seen.visible == expected.visible)
        and (expected.enabled is None or seen.enabled == expected.enabled)
        and (want is None or seen.value == want)
    )
