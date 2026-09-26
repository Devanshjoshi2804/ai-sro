from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Literal

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
