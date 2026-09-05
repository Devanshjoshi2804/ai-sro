"""What the extension matches a live tail against.

One entry per proven workflow: its shape -- (system, control identity, kind)
per cited gesture in step order, the same key `identity.py` resolves on -- and
where in that shape each declared parameter was typed. Computed from the cited
gestures rather than read from `workflow.shape_key`, so the parameter indices
are indices into the very list the extension will walk.

Nothing here carries a typed value. A shape is control identities, hosts and
parameter *names*; the values that went into those controls stay in the
gestures, which is the only place they were ever allowed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from rig.locators import allowlist
from rig.records import Gesture
from rig.runs import runs_for
from rig.shape import shape_key
from rig.store import Store
from rig.workflows import Workflow, known_workflows


@dataclass(frozen=True, slots=True)
class Shape:
    id: str
    title: str
    starts_on: str | None
    hosts: list[str]
    shape: list[list[str]]
    parameters: list[dict[str, Any]]
    held_runs: int = 0

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def _cited(store: Store, workflow: Workflow) -> list[Gesture]:
    from rig.api import _row_to_gesture  # api imports this module for the route

    wanted = [c for step in sorted(workflow.steps, key=lambda s: s.order) for c in step.cites]
    if not wanted:
        return []
    marks = ",".join("?" * len(wanted))
    rows = store.query(
        f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})",
        (workflow.tenant, *wanted),
    )
    by_id = {row["id"]: _row_to_gesture(row) for row in rows}
    return [by_id[c] for c in wanted if c in by_id]


def _typed_at(gestures: list[Gesture], parameter: dict[str, Any]) -> int | None:
    seen = {str(v) for v in parameter.get("seen_values", [])}
    for index, gesture in enumerate(gestures):
        if gesture.gesture.value is not None and gesture.gesture.value in seen:
            return index
    return None


def shapes_for(store: Store, tenant: str) -> list[Shape]:
    """Every proven workflow, as the extension needs it.

    A tenant with runs on record is asked a harder question -- has this one
    ever held -- because an offer to do a job the runner has never finished is
    an offer to fail in front of somebody. A tenant with no runs yet has to be
    offered something, or nothing is ever run.
    """
    any_runs = bool(store.query("SELECT 1 FROM runs WHERE tenant = ? LIMIT 1", (tenant,)))
    served: list[Shape] = []
    for workflow in known_workflows(store, tenant):
        if workflow.unproven:
            continue
        held = sum(1 for r in runs_for(store, tenant, workflow.id) if r.outcome == "held")
        if any_runs and held == 0:
            continue
        gestures = _cited(store, workflow)
        if not gestures:
            continue
        first = gestures[0]
        by_id = {g.id: g for g in gestures}
        served.append(
            Shape(
                id=workflow.id,
                title=workflow.title,
                starts_on=first.page_url or first.url,
                hosts=sorted(allowlist(workflow, by_id)),
                shape=[list(triple) for triple in shape_key(gestures)],
                parameters=[
                    {"name": str(p["name"]), "at": _typed_at(gestures, p)}
                    for p in workflow.parameters
                    if isinstance(p, dict) and p.get("name")
                ],
                held_runs=held,
            )
        )
    return served
