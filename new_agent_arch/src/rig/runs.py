"""What a run leaves behind. *Why did it do that* has a file."""

import json
import secrets
from dataclasses import asdict, dataclass, field
from typing import Any

from rig.store import Store

OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")
"""running: in flight. held: every step held. stopped: a step failed twice and
the run stopped to ask. refused: a planned command named an origin outside the
allowlist, or the step budget ran out. aborted: the stop button. failed: the
browser went away."""

VERDICTS = ("held", "failed", "unclear", "withheld", "refused", "skipped")


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
    sent: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
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
class Run:
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
    withheld: list[dict[str, Any]] = field(default_factory=list)
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False


def save_run(store: Store, run: Run) -> None:
    """Whole run, every time. Called after every step so the page can poll;
    steps are replaced rather than appended so the second save does not double
    the first step."""
    with store.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO runs (id, tenant, workflow_id, device_id, values_json,"
            " started_by, live, allow_focus, started_at, finished_at, outcome, withheld,"
            " in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.id,
                run.tenant,
                run.workflow_id,
                run.device_id,
                json.dumps(run.values, ensure_ascii=False),
                run.started_by,
                int(run.live),
                int(run.allow_focus),
                run.started_at,
                run.finished_at,
                run.outcome,
                json.dumps(run.withheld, ensure_ascii=False),
                run.in_tokens,
                run.out_tokens,
                run.thought_tokens,
                run.cost_usd,
                int(run.unpriced),
            ),
        )
        connection.execute("DELETE FROM run_steps WHERE run_id = ?", (run.id,))
        for step in run.steps:
            connection.execute(
                "INSERT INTO run_steps (run_id, ord, says, planned_by, sent, result, verdict,"
                " verdict_by, reason, matched_by, stale, before_url, after_url,"
                " in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.id,
                    step.order,
                    step.says,
                    step.planned_by,
                    json.dumps(step.sent, ensure_ascii=False) if step.sent is not None else None,
                    json.dumps(step.result, ensure_ascii=False)
                    if step.result is not None
                    else None,
                    step.verdict,
                    step.verdict_by,
                    step.reason,
                    step.matched_by,
                    int(step.stale),
                    step.before_url,
                    step.after_url,
                    step.in_tokens,
                    step.out_tokens,
                    step.thought_tokens,
                    step.cost_usd,
                    int(step.unpriced),
                ),
            )


def _step(row: Any) -> RunStep:
    return RunStep(
        order=row["ord"],
        says=row["says"],
        verdict=row["verdict"],
        verdict_by=row["verdict_by"],
        reason=row["reason"],
        planned_by=row["planned_by"],
        sent=json.loads(row["sent"]) if row["sent"] else None,
        result=json.loads(row["result"]) if row["result"] else None,
        matched_by=row["matched_by"],
        stale=bool(row["stale"]),
        before_url=row["before_url"],
        after_url=row["after_url"],
        in_tokens=row["in_tokens"],
        out_tokens=row["out_tokens"],
        thought_tokens=row["thought_tokens"],
        cost_usd=row["cost_usd"],
        unpriced=bool(row["unpriced"]),
    )


def _run(store: Store, row: Any) -> Run:
    steps = [
        _step(s)
        for s in store.query("SELECT * FROM run_steps WHERE run_id = ? ORDER BY ord", (row["id"],))
    ]
    return Run(
        id=row["id"],
        tenant=row["tenant"],
        workflow_id=row["workflow_id"],
        device_id=row["device_id"],
        values=json.loads(row["values_json"]),
        started_by=row["started_by"],
        live=bool(row["live"]),
        allow_focus=bool(row["allow_focus"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        outcome=row["outcome"],
        steps=steps,
        withheld=json.loads(row["withheld"]),
        in_tokens=row["in_tokens"],
        out_tokens=row["out_tokens"],
        thought_tokens=row["thought_tokens"],
        cost_usd=row["cost_usd"],
        unpriced=bool(row["unpriced"]),
    )


def load_run(store: Store, tenant: str, run_id: str) -> Run | None:
    rows = store.query("SELECT * FROM runs WHERE tenant = ? AND id = ?", (tenant, run_id))
    return _run(store, rows[0]) if rows else None


def runs_for(store: Store, tenant: str, workflow_id: str) -> list[Run]:
    return [
        _run(store, r)
        for r in store.query(
            "SELECT * FROM runs WHERE tenant = ? AND workflow_id = ? ORDER BY started_at",
            (tenant, workflow_id),
        )
    ]


def as_json(run: Run) -> dict[str, Any]:
    """The route's view. `asdict` is exact here because nothing in a Run is a
    type json cannot carry."""
    return asdict(run)
