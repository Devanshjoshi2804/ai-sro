from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from sro.application.context import RequestContext
from sro.application.skill.version_from_rig import version_from_rig
from sro.container import build_container
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.objective import Direction, ObjectiveKey


class Unreachable(Exception): ...


def _get(base: str, path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310 - an operator-supplied base url
        f"{base.rstrip('/')}{path}", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:  # noqa: S310
            loaded = json.load(answer)
    except urllib.error.HTTPError as refused:
        hint = (
            " -- a rig started before this route existed answers 404 here; restart it"
            if refused.code == 404
            else ""
        )
        raise Unreachable(f"{path}: HTTP {refused.code} {refused.reason}{hint}") from refused
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as problem:
        raise Unreachable(f"{path}: {problem}") from problem
    return loaded if isinstance(loaded, dict) else {}


async def _adopt(args: argparse.Namespace, workflows: list[dict[str, Any]]) -> int:
    missing = [
        flag
        for flag, value in (
            ("--workflow", args.workflow),
            ("--objective", args.objective),
            ("--entity", args.entity),
            ("--system", args.system),
            ("--facility", args.facility),
            ("--direction", args.direction),
            ("--principal", args.principal),
        )
        if not value
    ]
    if missing:
        print("adopting needs a person to name the job: " + ", ".join(missing))
        return 1
    if len(workflows) != 1:
        print(f"--workflow names {len(workflows)} workflows; adoption takes exactly one")
        return 1

    workflow = workflows[0]
    try:
        evidence = _get(args.rig, f"/v1/workflows/{workflow['id']}/evidence", args.token)
    except Unreachable as problem:
        print(f"the rig at {args.rig}: {problem}")
        return 1
    container = build_container()
    try:
        adopted = await container.adopt_rig_workflow().execute(
            RequestContext(
                tenant_id=TenantId(args.tenant), principal_id=PrincipalId(args.principal)
            ),
            workflow=workflow,
            gestures=evidence.get("gestures") or {},
            recordings=evidence.get("recordings") or [],
            requests=evidence.get("requests") or {},
            objective=ObjectiveKey(
                objective_type=args.objective,
                target_system=args.system,
                entity_type=args.entity,
                facility=args.facility,
                direction=Direction(args.direction),
            ),
        )
    except DomainError as refused:
        print(f"refused: {refused}")
        return 1

    version = adopted.version
    calls = [step.network_plan for step in version.steps if step.network_plan]
    fresh = "  (new)" if adopted.created_the_skill else ""
    print(f"skill {adopted.skill_id} v{version.version}{fresh}")
    print(
        f"  {len(version.steps)} steps, {len(calls)} of them a call,"
        f" {len(version.parameters)} parameter(s)"
    )
    print(
        f"  stage {version.stage.value} -- nobody has reviewed it,"
        " and the runner refuses it until they do"
    )
    if version.needs_a_person:
        print("  needs a person: some step is a gesture with no call behind it")
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", default="http://127.0.0.1:8099")
    parser.add_argument("--token", required=True)
    parser.add_argument(
        "--facility",
        default="",
        help="the facility a credential reference is filed under; without it "
        "the network recipe is skipped rather than filed under a guess",
    )
    parser.add_argument("--workflow", default="", help="one workflow; default is every one")
    parser.add_argument(
        "--adopt",
        action="store_true",
        help="store it as a skill. Needs --workflow and the objective fields "
        "below: naming what a job is FOR is a person's, not a default",
    )
    parser.add_argument("--objective", default="", help="objective_type, e.g. create_work_area")
    parser.add_argument("--entity", default="", help="entity_type, e.g. work_area")
    parser.add_argument("--system", default="", help="target_system, e.g. blue_yonder")
    parser.add_argument("--direction", default="", choices=["", "inbound", "outbound"])
    parser.add_argument("--principal", default="", help="who is adopting it")
    parser.add_argument("--tenant", default="acme")
    args = parser.parse_args()

    try:
        listing = _get(args.rig, "/v1/workflows", args.token)
    except Unreachable as problem:
        print(f"the rig at {args.rig}: {problem}")
        return 1

    workflows = [w for w in listing.get("workflows", []) if isinstance(w, dict)]
    if args.workflow:
        workflows = [w for w in workflows if w.get("id") == args.workflow]
    if not workflows:
        print("no workflows")
        return 1

    if args.adopt:
        return await _adopt(args, workflows)

    print(
        f"{'workflow':40s} {'steps':>5s} {'calls':>5s} {'writes':>6s} {'params':>6s} {'holes':>5s}"
    )
    built = 0
    for workflow in workflows:
        try:
            evidence = _get(args.rig, f"/v1/workflows/{workflow['id']}/evidence", args.token)
        except Unreachable as problem:
            print(f"the rig at {args.rig}: {problem}")
            return 1
        missing = evidence.get("missing") or []
        version = version_from_rig(
            workflow,
            evidence.get("gestures") or {},
            recordings=evidence.get("recordings") or [],
            induced_by="rig",
            induced_at=datetime.now(tz=UTC),
            requests=evidence.get("requests") or {},
            facility=args.facility,
        )
        title = str(workflow.get("title") or workflow["id"])[:40]
        if version is None:
            print(f"{title:40s}    -- refused (no evidence, or no recording it came from)")
            continue
        built += 1
        calls = [step.network_plan for step in version.steps if step.network_plan]
        holes: set[str] = set()
        for step in version.steps:
            holes |= step.placeholders
        print(
            f"{title:40s} {len(version.steps):5d} {len(calls):5d}"
            f" {sum(1 for c in calls if c.method not in ('GET', 'HEAD')):6d}"
            f" {len(version.parameters):6d} {len(holes):5d}"
            + (f"   {len(missing)} citation(s) with no evidence" if missing else "")
        )

    print(f"\n{built} of {len(workflows)} built. Every one is RECORDED: nobody has reviewed them.")
    print("An ObjectiveKey is what a Skill still needs, and that is a person's to name.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
