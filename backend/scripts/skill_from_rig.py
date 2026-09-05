"""A workflow the rig mined, fetched over HTTP and built into a version.

The three bridge modules -- `from_rig`, `network_from_rig`, `version_from_rig`
-- turn a mined workflow into a `SkillVersion`. This is the proof that they can
be reached without the rig's database file, which is the whole point of
`GET /v1/workflows/{id}/evidence` existing: nothing here imports `rig`, and
nothing here opens a SQLite store.

It stops at the version and does not create a `Skill`. A `Skill` needs an
`ObjectiveKey` -- objective type, target system, entity type, facility,
direction -- and the rig produces none of those. Deriving "an inbound receipt
against BLR1" from `Create Work Area NEWTESTS` would be a guess wearing the
clothes of a finding. Naming what a job is FOR is a person's, and this prints
what a person would be naming it about.

    uv run python scripts/skill_from_rig.py --rig http://127.0.0.1:8099 \
        --token "$RIG_INGEST_TOKEN" --facility SG
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from sro.application.skill.version_from_rig import version_from_rig


def _get(base: str, path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310 - an operator-supplied base url
        f"{base.rstrip('/')}{path}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=60) as answer:  # noqa: S310
        loaded = json.load(answer)
    return loaded if isinstance(loaded, dict) else {}


def main() -> int:
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
    args = parser.parse_args()

    try:
        listing = _get(args.rig, "/v1/workflows", args.token)
    except (urllib.error.URLError, TimeoutError) as problem:
        print(f"the rig at {args.rig} did not answer: {problem}")
        return 1

    workflows = [w for w in listing.get("workflows", []) if isinstance(w, dict)]
    if args.workflow:
        workflows = [w for w in workflows if w.get("id") == args.workflow]
    if not workflows:
        print("no workflows")
        return 1

    print(
        f"{'workflow':40s} {'steps':>5s} {'calls':>5s} {'writes':>6s} {'params':>6s} {'holes':>5s}"
    )
    built = 0
    for workflow in workflows:
        evidence = _get(args.rig, f"/v1/workflows/{workflow['id']}/evidence", args.token)
        missing = evidence.get("missing") or []
        version = version_from_rig(
            workflow,
            evidence.get("gestures") or {},
            recordings=evidence.get("recordings") or [],
            induced_by="rig",
            induced_at=datetime.now(tz=UTC),
            requests=evidence.get("requests") or {},
            # No target_system. Each call files its credential reference under
            # the host it actually went to, which is what a vault key is scoped
            # by -- an earlier version of this script picked one host for a
            # whole workflow and skipped the network recipe entirely wherever a
            # job touched more than one, which cost 17 of 30 plans on this
            # corpus. A cross-system job is the thing this project exists to
            # capture; it is not the case to give up on.
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
    sys.exit(main())
