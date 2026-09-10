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


def already_running(device_id: str, run_id: str | None) -> str:
    """One browser, one hand -- said once, because two places discover it.

    The press reads `in_flight` and refuses, which is the friendly answer and
    the one that happens almost every time. The unique partial index on
    `(tenant_id, device_id) WHERE outcome = 'running'` refuses the ones that
    got past that read: between it and the commit there are two more awaits,
    and on one event loop a second press can be scheduled in either of them.

    The two must be indistinguishable. A caller able to tell "you were late"
    from "you lost a race" learns whether this deployment has a lock, and a
    refusal that reads differently on the rare path is a refusal nobody has
    ever seen rendered. So the sentence is here rather than spelled twice --
    the domain owns what the refusal says, and the two discoverers agree by
    construction rather than by somebody remembering.

    `run_id` is optional for one case only: the index refused the claim and the
    winner finished before the losing side could read back which run it was.
    """
    return f"{device_id} is already running {run_id or 'a run this press cannot see'}"


def new_run_id() -> str:
    """A workflow run's id -- and NOT an `sro.domain.shared.identifiers.RunId`.

    Same shape as `UuidFactory.new_run_id`: `run_` followed by 32 hex
    characters. Two id spaces that look alike -- that one names a row in the
    backend's own `runs`, this one a row in `workflow_runs` -- so a string that
    round-trips through the wrong repository will be looked up, found missing,
    and read as a run that does not exist rather than as a type error. The
    shape is the rig's and stays; the types are what keep them apart.
    """
    return "run_" + secrets.token_hex(16)


@dataclass
class RunStep:
    """One step of a run, as the panel and the register read it afterwards.

    `sent` is what was planned, not proof that it went out: a step parked on a
    person carries the command a tap would release, and `verdict == "awaiting"`
    is what tells the two apart. A reader treating `sent` as "this reached the
    warehouse" would report an unapproved write as a performed one.
    """

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

    from_step: int = 0
    """How many steps the operator performed themselves before the offer was
    made. A request input, not a progress marker: the runner never advances it.
    Kept on the row because it is the fourth thing a press asks for, and a
    re-press that carries a different one finishes a different job under this
    run's id -- steps redone against a live warehouse, or steps nobody did
    recorded as done."""

    steps: list[RunStep] = field(default_factory=list)
    withheld: list[dict[str, object]] = field(default_factory=list)
    """The writes a dry run produced and did not send, in full. This is what a
    person reads before pressing through to live."""

    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
