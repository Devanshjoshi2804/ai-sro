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
from sro.domain.skill.shape import in_time_order, put_by
from sro.domain.skill.workflow import Workflow, ordered_cites

TYPED = "•"


def _gestures_of(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[dict[str, Any]]:
    cited = in_time_order(workflow, by_id)
    seen: set[str] = set()
    for parameter in workflow.parameters:
        values = parameter.get("seen_values") if isinstance(parameter, dict) else None
        if isinstance(values, list):
            seen.update(str(value) for value in values)
    return [
        {
            "triple": list(triple),
            "value": TYPED if seen & put_by(gesture) else None,
            "secret": bool(
                gesture.action.secret or (gesture.action.target and gesture.action.target.secret)
            ),
            "at": gesture.at,
        }
        for gesture, triple in zip(cited, shape_key(cited), strict=True)
    ]


async def replay(shapes: ServeShapes, uow: UnitOfWork, ctx: RequestContext) -> dict[str, Any]:
    served = [shape.as_json() for shape in await shapes.execute(ctx, device_id=None)]
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
