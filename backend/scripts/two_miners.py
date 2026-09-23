from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.container import build_container
from sro.domain.shared.identifiers import PrincipalId, TenantId


async def _report(tenant: str, *, hours: int, run_rules: bool, run_model: bool) -> int:
    container = build_container()
    tenant_id = TenantId(tenant)
    ctx = RequestContext(tenant_id=tenant_id, principal_id=PrincipalId("two_miners"))
    now = datetime.now(UTC)
    since = now - timedelta(hours=hours)
    print(f"== {tenant}, the {hours} hours to {now.isoformat(timespec='seconds')}\n")

    if run_rules:
        mined = await container.mine_observations().execute(ctx, since=since)
        print(f"-- the rule-based miner ran: {mined}\n")
    if run_model:
        result = await container.mine_pass().execute(ctx)
        print(f"-- the model pass ran: kept {result.kept}, cost ${result.cost_usd:.2f}\n")

    async with container.unit_of_work() as uow:
        batches = await uow.observations.between(tenant_id, since=since, until=None)
        gestures = [g for g in await uow.gestures.gestures_for(tenant_id) if g.at]
        candidates = await uow.candidates.list_for_tenant(tenant_id)
        workflows = await uow.workflows.known(tenant_id)
        passes = await uow.workflows.passes(tenant_id)

    lately = [g for g in gestures if g.at >= since.timestamp()]
    print(f"evidence in the window: {len(batches)} batches, {len(lately)} gestures")
    spent = sum(p.cost_usd for p in passes)
    print(f"the model path has cost ${spent:.2f} over {len(passes)} passes\n")

    print(f"-- the rule-based path named {len(candidates)} candidate(s)")
    for candidate in sorted(candidates, key=lambda c: -len(c.episodes))[:40]:
        print(f"   {len(candidate.episodes):3}x  {candidate.title or candidate.signature}")

    print(f"\n-- the model path named {len(workflows)} job(s)")
    for workflow in workflows:
        print(f"   {len(workflow.steps):3} steps  {workflow.title}")

    print(
        "\nWhat a person still has to say: which of each list is work worth "
        "automating, and what one path found that the other missed. That is the "
        "half of the precondition a count cannot answer."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tenant")
    parser.add_argument("--window-hours", type=int, default=24 * 30)
    parser.add_argument(
        "--rule-based", action="store_true", help="run the rule-based miner (writes candidates)"
    )
    parser.add_argument(
        "--model", action="store_true", help="run a model pass (costs a 150K-token call)"
    )
    args = parser.parse_args()
    return asyncio.run(
        _report(
            args.tenant,
            hours=args.window_hours,
            run_rules=args.rule_based,
            run_model=args.model,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
