"""What a run leaves behind. *Why did it do that* has a file.

The rig's `Run`, renamed: `sro.domain.execution.run.Run` is already the
backend's own word for a different thing. Mutable, unlike most of this layer,
because a run is written step by step -- the runner appends to `steps` as it
goes and the orphan sweep rewrites the last verdict of a run nobody is driving.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")
"""running: in flight. held: every step held. stopped: a step failed twice and
the run stopped to ask. refused: a planned command named an origin outside the
allowlist, or the step budget ran out. aborted: the stop button. failed: the
browser went away."""

VERDICTS = (
    "held",
    "failed",
    "unclear",
    "withheld",
    "refused",
    "skipped",
    "awaiting",
    "done_by_operator",
)
"""awaiting: shown to a person and waiting on their word. done_by_operator: the
operator performed it themselves before the rig was asked to finish the job."""


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
    steps: list[RunStep] = field(default_factory=list)
    withheld: list[dict[str, object]] = field(default_factory=list)
    """The writes a dry run produced and did not send, in full. This is what a
    person reads before pressing through to live."""

    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
