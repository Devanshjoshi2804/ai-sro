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

from rig.correlate import system_of
from rig.locators import allowlist, primary_gesture
from rig.mine import _ordered_cites
from rig.records import Gesture
from rig.runs import runs_for
from rig.shape import shape_key
from rig.store import Store
from rig.workflows import Step, Workflow, known_workflows


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


def _cited(store: Store, workflow: Workflow) -> list[tuple[Gesture, Step]]:
    """The cited gestures in step order, each still paired with the step that
    cited it. The pairing is what `_typed_at` needs and what a flat list of
    gestures throws away."""
    from rig.api import _row_to_gesture  # api imports this module for the route

    wanted = _ordered_cites(workflow)
    if not wanted:
        return []
    marks = ",".join("?" * len(wanted))
    rows = store.query(
        f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})",
        (workflow.tenant, *wanted),
    )
    by_id = {row["id"]: _row_to_gesture(row) for row in rows}
    return [
        (by_id[cited], step)
        for step in sorted(workflow.steps, key=lambda s: s.order)
        for cited in step.cites
        if cited in by_id
    ]


def _typed_at(cited: list[tuple[Gesture, Step]], parameter: dict[str, Any]) -> int | None:
    """Where in the shape this parameter was typed, by the step that declares it.

    Scanning every cited gesture for the first value match binds the wrong
    control on any search-then-create flow: the code is typed into the search
    box before it is typed into the field the workflow is actually filling, so
    the extension would fill the search box and stop. Only the step whose
    `parameters` names this one is asked.
    """
    name = str(parameter["name"])
    seen = {str(v) for v in parameter.get("seen_values", [])}
    for index, (gesture, step) in enumerate(cited):
        if name in step.parameters and gesture.gesture.value in seen:
            return index
    return None


def shapes_for(store: Store, tenant: str) -> list[Shape]:
    """Every proven workflow, as the extension needs it.

    A workflow that has been run is asked a harder question -- has it ever
    held -- because an offer to do a job the runner has only ever failed is an
    offer to fail in front of somebody. The gate is per workflow and not per
    tenant: one workflow's first failure must not silence every sibling that
    has simply never been run.
    """
    served: list[Shape] = []
    for workflow in known_workflows(store, tenant):
        if workflow.unproven:
            continue
        runs = runs_for(store, tenant, workflow.id)
        held = sum(1 for r in runs if r.outcome == "held")
        if runs and held == 0:
            continue
        cited = _cited(store, workflow)
        if not cited:
            continue
        gestures = [gesture for gesture, _ in cited]
        by_id = {g.id: g for g in gestures}
        first_step = min(workflow.steps, key=lambda s: s.order)
        first = primary_gesture(first_step, by_id) or gestures[0]
        starts_on = first.page_url or first.url
        hosts = sorted(allowlist(workflow, by_id))
        # `starts_on` is the tab's origin; `hosts` is what the evidence names,
        # which is the frame's. When they disagree the extension would be sent
        # to open an origin no cited gesture ever proved -- so it is not sent.
        if system_of(starts_on) not in hosts:
            continue
        served.append(
            Shape(
                id=workflow.id,
                title=workflow.title,
                starts_on=starts_on,
                hosts=hosts,
                shape=[list(triple) for triple in shape_key(gestures)],
                parameters=[
                    {"name": str(p["name"]), "at": _typed_at(cited, p)}
                    for p in workflow.parameters
                    if isinstance(p, dict) and p.get("name")
                ],
                held_runs=held,
            )
        )
    return served
