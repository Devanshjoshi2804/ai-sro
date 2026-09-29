from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sro.domain.execution.compose import normal
from sro.domain.execution.evidence import control_names
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})

COMMAND_KINDS = KINDS | frozenset(
    {"ui.perform_at", "ui.url", "screenshot", "abort", "tab.open", "calls.since", "sign_in"}
)

LIVE_FETCHABLE_HEADERS = frozenset({"csrf-encrypt-token", "x-requested-with"})


@dataclass(frozen=True, slots=True)
class Look:
    url: str | None
    screenshot: bytes | None
    digest: str
    width: int = 0
    height: int = 0
    refused: str = ""

    elsewhere: str = ""

    elsewhere_is_ours: bool = False

    signed_out: bool = False

    dialog: str = ""

    loading: bool = False


@dataclass(frozen=True, slots=True)
class Planned:
    kind: str
    payload: dict[str, object]
    why: str
    answer: Answer
    opens: bool = False

    rewrote: bool = False

    filled: Mapping[str, str] = MappingProxyType({})

    confirm: Mapping[str, str] = MappingProxyType({})

    by: str = ""


def own_parameter(step: Step, gesture: Gesture) -> str | None:
    names = {normal(name) for name in control_names(gesture)}
    named = [name for name in step.parameters if normal(name) in names]
    if named:
        return named[0]
    return step.parameters[0] if len(step.parameters) == 1 else None


def value_for(
    step: Step, gesture: Gesture, values: Mapping[str, str], said: str | None
) -> str | None:
    if is_secret(gesture):
        return None
    target = gesture.action.target
    component = target.component if target else None
    own = own_parameter(step, gesture)
    for name in (
        component.item_id if component else None,
        component.field_label if component else None,
        target.name if target else None,
        own,
    ):
        if name and name in values:
            return values[name]
    if said:
        return said
    return None if step.parameters else gesture.action.value


def shown_after(step: Step, gesture: Gesture, value: str | None) -> str | None:
    after = gesture.action.after
    if value is not None or after is None or step.parameters:
        return value
    return after.value


def unreplayable(call: Call) -> bool:
    if REDACTED in call.url:
        return True
    body = call.request_body
    if body is None:
        return False
    if body.text is None:
        return bool(body.blob_uri or body.redacted_fields)
    return REDACTED in body.text
