"""When a job has earned the right to write without asking.

D2 of the autonomous-workflows design: autonomy is earned by verified effect,
not by counting runs. A write counts only when the verifier decided `held` by
state -- a status the server answered, or a read that showed the record -- and
never by a picture. A failed write un-earns the job: the next runs ask again.
"""

import json

from rig.store import Store

K_EARNED_RUNS = 3
"""Live runs whose every write verified by state before the tap goes away.
Three is a job that worked on three different days' values, not a job that
worked once."""

STATE_BELTS = ("status", "read")
"""The two verdicts that saw the state itself. `screen` is a model reading a
picture, and a picture is not an effect."""


def record_effect(
    store: Store, *, workflow_id: str, run_id: str, order: int, verified_by: str, at: str
) -> None:
    if verified_by not in STATE_BELTS:
        return
    store.execute(
        "INSERT OR REPLACE INTO workflow_effects (workflow_id, run_id, ord, verified_by, at)"
        " VALUES (?, ?, ?, ?, ?)",
        (workflow_id, run_id, order, verified_by, at),
    )


def forget_effects(store: Store, workflow_id: str) -> int:
    """Everything this job had earned, and how much there was of it."""
    with store.connect() as connection:
        return int(
            connection.execute(
                "DELETE FROM workflow_effects WHERE workflow_id = ?", (workflow_id,)
            ).rowcount
        )


def earned(store: Store, workflow_id: str, *, tenant: str | None = None) -> bool:
    """Three live runs that held, each with every write step verified by state.

    A write step is a `run_steps` row whose stored result says `wrote`; the
    runner marks it so at send time, because SQL cannot ask `writes()`. A run
    with no write in it proves nothing about writing and is not counted.
    """
    counted = 0
    # The tenant first when the caller has it, so the query walks the
    # (tenant, workflow_id, started_at) index rather than the table.
    where, params = (
        ("tenant = ? AND workflow_id = ?", (tenant, workflow_id))
        if tenant is not None
        else ("workflow_id = ?", (workflow_id,))
    )
    for run in store.query(
        f"SELECT id FROM runs WHERE {where} AND live = 1 AND outcome = 'held'",
        params,
    ):
        wrote = {
            row["ord"]
            for row in store.query(
                "SELECT ord, result FROM run_steps WHERE run_id = ?", (run["id"],)
            )
            if row["result"] and json.loads(row["result"]).get("wrote")
        }
        verified = {
            row["ord"]
            for row in store.query(
                "SELECT ord FROM workflow_effects WHERE workflow_id = ? AND run_id = ?",
                (workflow_id, run["id"]),
            )
        }
        if wrote and wrote <= verified:
            counted += 1
            if counted >= K_EARNED_RUNS:
                return True
    return False
