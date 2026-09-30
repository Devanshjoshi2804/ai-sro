from __future__ import annotations

import re
import secrets
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal

from sro.domain.shared.errors import Conflict
from sro.domain.skill.workflow import Workflow

OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")
ENDED = ("held", "aborted", "failed")

Executor = Literal["extension", "steel"]

VERDICTS = (
    "held",
    "failed",
    "unclear",
    "withheld",
    "refused",
    "skipped",
    "awaiting",
    "done_by_operator",
    "not_needed",
)


def already_running(device_id: str, run_id: str | None) -> str:
    return f"{device_id} is already running {run_id or 'a run this press cannot see'}"


class OfferTaken(Conflict):
    """A second start of one offer. The run the first start made is the answer."""

    def __init__(self, offer: str, run_id: str) -> None:
        super().__init__(f"the offer {offer} has already started a run")
        self.run_id = run_id


def new_run_id() -> str:
    return "run_" + secrets.token_hex(16)


@dataclass
class RunStep:
    order: int

    says: str
    verdict: str
    verdict_by: str = ""
    reason: str = ""
    planned_by: str | None = None
    sent: dict[str, object] | None = None
    result: dict[str, object] | None = None
    matched_by: str | None = None
    stale: bool = False
    before_url: str | None = None
    after_url: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False

    notes: list[str] = field(default_factory=list)

    made: dict[str, str] = field(default_factory=dict)

    of_step: int = 0

    item: int | None = None


@dataclass
class WorkflowRun:
    id: str
    tenant: str
    workflow_id: str
    device_id: str
    values: dict[str, str]
    started_by: str
    live: bool
    allow_focus: bool
    started_at: str
    finished_at: str | None = None
    outcome: str = "running"

    items: list[dict[str, str]] = field(default_factory=list)

    from_step: int = 0

    steps: list[RunStep] = field(default_factory=list)
    withheld: list[dict[str, object]] = field(default_factory=list)

    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False

    watched: bool = False

    doing: str = ""

    gathered: dict[str, dict[str, str]] = field(default_factory=dict)

    unasked: list[str] = field(default_factory=list)

    needs: list[str] = field(default_factory=list)

    undoes_run: str | None = None

    asked_the_asker: bool = False

    awaiting: dict[str, str] | None = None

    wrong_because: str | None = None

    progress: dict[str, object] = field(default_factory=dict)

    executor: Executor = "extension"

    offer: str | None = None

    pinned: Workflow | None = None

    mail: dict[str, str] | None = None


SETTLED = frozenset({"done", "skipped", "not_needed"})


def end_the_steps(steps: list[RunStep], reason: str) -> None:
    last = steps[-1] if steps else None
    if last is None or last.verdict in SETTLED:
        order = 0 if last is None else last.order + 1
        steps.append(
            RunStep(order=order, says="", verdict="failed", verdict_by="none", reason=reason)
        )
    else:
        last.verdict, last.verdict_by, last.reason = "failed", "none", reason


def refused_by(run: WorkflowRun) -> str:
    last = max(run.steps, key=lambda one: one.order, default=None)
    return last.reason if last is not None and last.verdict == "failed" and last.result else ""


def refused_names(workflow: Workflow, values: Mapping[str, str], said: str) -> list[str]:
    given = [
        str(one.get("name")) for one in workflow.parameters if values.get(str(one.get("name")))
    ]
    heard = "".join(_words(said))
    named = [
        name
        for name in given
        if "".join(_words(name)) in heard
        or (set(_words(values[name])) <= set(_words(said))
        and bool(_words(values[name])))
    ]
    return named or given[:1]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def answers_for(run: WorkflowRun, principal: str, *, opened_by: str = "") -> bool:
    return principal in {run.started_by, opened_by} - {""}


def pin(workflow: Workflow) -> Workflow:
    return deepcopy(workflow)
