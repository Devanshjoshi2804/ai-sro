"""The offer, replayed against the backend's own stored evidence.

`make offer-replay-backend`. Writes the file
`new-chrome-extension/scripts/offer-replay.mjs` reads: every shape this
backend serves, beside the gestures each proven job was mined from, in the
order the operator made them. The `.mjs` feeds those gestures one at a time
through the same `tailWith` and `match` the service worker runs, and reports
at which gesture each job would have been offered and whether the offer named
the job the operator was actually doing.

The port of `new_agent_arch/scripts/dry_run.py`'s `--replay` half, and only
that half. The rig's script also starts every workflow over `POST /v1/runs`
against a fake browser and a model that is not a model; the runner is not in
the backend yet, and a dry run of a runner that does not exist is not a thing
to write. The replay is what the spec makes phase 4's acceptance test, and the
replay is what this emits.

Reads only. Nothing here writes, and no model is asked: the shapes come from
`ServeShapes` and the gestures from the evidence repository, both under a unit
of work that never commits.

    uv run python scripts/dry_run.py --replay /tmp/backend-replay.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.skill.serve_shapes import ServeShapes
from sro.container import build_container
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.identity import shape_key
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Workflow, ordered_cites

TYPED = "•"
"""What a gesture carrying a declared parameter's value exports as.

The matcher lifts on "a value was typed here", never on the text, so the text
does not leave the store: the replay file is written to /tmp and read by a
node script, and a customer's part number has no business in either.
"""


def _gestures_of(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[dict[str, Any]]:
    """One job's cited gestures as the extension would have seen them.

    Scrolls stay in. `recognise.js`'s `tailWith` is what drops them, and this
    is a test of `recognise.js` -- handing it a tail with the scrolls already
    removed would be marking its own homework.
    """
    cited = [by_id[gesture_id] for gesture_id in ordered_cites(workflow) if gesture_id in by_id]
    # The values a declared parameter has been seen holding, which the store
    # already records on the workflow: a typed gesture carrying one is exported
    # as a presence mark and nothing else.
    seen: set[str] = set()
    for parameter in workflow.parameters:
        values = parameter.get("seen_values") if isinstance(parameter, dict) else None
        if isinstance(values, list):
            seen.update(str(value) for value in values)
    # `shape_key` over the whole list rather than a triple built by hand here:
    # it is the function `shape_of` builds the served shape from, and a second
    # spelling of the triple is a replay that fails to match for a reason that
    # is in this file rather than in the matcher.
    return [
        {
            "triple": list(triple),
            "value": TYPED
            if gesture.action.value is not None and str(gesture.action.value) in seen
            else None,
            "secret": bool(
                gesture.action.secret or (gesture.action.target and gesture.action.target.secret)
            ),
            "at": gesture.at,
        }
        for gesture, triple in zip(cited, shape_key(cited), strict=True)
    ]


async def replay(shapes: ServeShapes, uow: UnitOfWork, ctx: RequestContext) -> dict[str, Any]:
    """`{"shapes": [...], "jobs": [...]}` -- what `offer-replay.mjs` reads.

    Every workflow is a job here, not only the served ones. A shape that is
    withheld and a job whose gestures are still replayed is exactly the case
    the matcher must answer "never offered" to, and dropping those jobs would
    hide it by never asking.

    No `device_id`: the shapes are served as they are to a browser that has
    refused nothing, which is what the rig's dry run asked for too. A device's
    own refusals rest a job on that device alone, and a corpus measurement
    taken through one browser's sulk is a measurement of the sulk.
    """
    served = [shape.as_json() for shape in await shapes.execute(ctx, device_id=None)]
    # A `UnitOfWork` has no repositories until its session opens.
    async with uow as opened:
        jobs = []
        for workflow in await opened.workflows.known(ctx.tenant_id):
            wanted = tuple(ordered_cites(workflow))
            by_id = {
                gesture.id: gesture
                for gesture in await opened.gestures.gestures_for(ctx.tenant_id, ids=wanted)
            }
            jobs.append(
                {
                    "id": workflow.id,
                    "title": workflow.title,
                    "gestures": _gestures_of(workflow, by_id),
                }
            )
    return {"shapes": served, "jobs": jobs}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", required=True, type=Path, help="where to write the JSON")
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--principal", default="scripts/dry_run.py")
    args = parser.parse_args()

    container = build_container()
    written = await replay(
        container.serve_shapes(),
        container.unit_of_work(),
        RequestContext(tenant_id=TenantId(args.tenant), principal_id=PrincipalId(args.principal)),
    )
    args.replay.write_text(json.dumps(written, indent=1))
    print(
        f"replay written to {args.replay}: {len(written['shapes'])} shape(s),"
        f" {len(written['jobs'])} job(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
