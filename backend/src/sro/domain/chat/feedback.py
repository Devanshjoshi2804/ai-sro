"""What went wrong in a chat, as the code can see it: kept so a person can review it.

Only objective signals (the operator undid a run, a code guard refused the model, a run the
brain started failed, the brain and the old chain would have done different kinds of thing, the
turn hit its budget). Nothing here decides anything; a row is evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sro.domain.chat.asking import ASKS
from sro.domain.chat.brain_turn import ToolCall, ToolResult
from sro.domain.chat.thread import Said
from sro.domain.recording.sensitivity import is_secret_field, redact_shapes, without_secrets

UNDO = "undo"
GUARD_REFUSAL = "guard_refusal"
RUN_FAILED = "run_failed"
DISAGREEMENT = "disagreement"
BUDGET = "budget"
KINDS = (UNDO, GUARD_REFUSAL, RUN_FAILED, DISAGREEMENT, BUDGET)

NEW = "new"
REVIEWED = "reviewed"
PROMOTED = "promoted"
DISMISSED = "dismissed"
STATUSES = (NEW, REVIEWED, PROMOTED, DISMISSED)

# What a turn did, as one of four kinds of thing: a run was (or would be) started, the operator
# was asked something, something was read out to them, or none of these.
START = "start"
ASK = "ask"
ANSWER = "answer"
NONE = "none"
CATEGORIES = (START, ASK, ANSWER, NONE)

K_SAID = 500

_STARTS = frozenset({"start_job", "undo_run"})
_READS = frozenset({"lookup", "check_mail", "run_status", "work_it_out"})


@dataclass(frozen=True, slots=True)
class Feedback:
    id: str
    tenant: str
    operator: str
    thread_id: str
    message_id: str
    kind: str
    created_at: datetime
    said: str = ""
    brain: dict[str, object] = field(default_factory=dict)
    other: dict[str, object] = field(default_factory=dict)
    status: str = NEW
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind!r} is not something feedback is kept for")
        if self.status not in STATUSES:
            raise ValueError(f"{self.status!r} is not a status of feedback")


WITHHELD = "[withheld: it names a secret]"


def said_of(text: str) -> str:
    """Words said (the operator's, or the model's echo of them) as they may be kept: secret
    shapes gone, then bounded. A password typed in prose has no shape to find, so a sentence that
    names a secret field at all is not kept."""
    if any(is_secret_field(word) for word in re.findall(r"\w+", text)):
        return WITHHELD
    return redact_shapes(text)[:K_SAID]


def kept(value: object) -> object:
    """Evidence as it may be kept: no secret field's value or secret shape, each text bounded."""
    cleaned = without_secrets(value)

    def cut(one: object) -> object:
        if isinstance(one, Mapping):
            return {k: cut(v) for k, v in one.items()}
        if isinstance(one, list):
            return [cut(v) for v in one]
        return one[:K_SAID] if isinstance(one, str) else one

    return cut(cleaned)


def brain_category(steps: Sequence[tuple[ToolCall, ToolResult]]) -> str:
    """What the brain's turn did, from the tools that went through (a refused one did nothing)."""
    done = {call.tool for call, result in steps if result.ok}
    if done & _STARTS:
        return START
    if "ask_operator" in done:
        return ASK
    return ANSWER if done & _READS else NONE


def chain_category(decision: Mapping[str, object]) -> str:
    """What the old chain's reply did, from the decision it wrote with it."""
    kind = decision.get("kind")
    if kind in ASKS or kind == "which_job":
        return ASK
    if kind == "job":
        return ASK if decision.get("missing") else START
    if kind == Said.RUN:
        return START
    if kind in (Said.LOOKED, Said.MAIL_LOOKED, Said.MAIL_MATCH):
        return ANSWER
    if kind is not None:
        return NONE
    # The chain's own resolution, written without a kind.
    if decision.get("run_id"):
        return START
    if decision.get("derived"):
        return ANSWER
    return ASK if decision.get("missing_parameters") or decision.get("choices") else NONE
