"""Ask one question of every system this deployment knows about.

    uv run python scripts/look_up.py new "which suppliers are set up at SG"
    ... --send          # actually go and look, through a connected browser

Dry by default, and the dry run is the whole plan: which system, a call or a
screen, the exact target, and the knowledge each lookup was built from. A
question that reaches a warehouse is not something to send on a flag somebody
typed by accident -- even a read opens a tab in somebody's browser.

`--send` needs a connected browser and will not find one from here: the socket
is held by whichever process the extension dialled, which is the API. See
`create_by_api.py` for the same wall and the same reason. What this prints
instead is the address each lookup resolved to, which is the part worth
reading before anything goes out.
"""

from __future__ import annotations

import argparse
import asyncio

from sro.application.context import RequestContext
from sro.container import build_container
from sro.domain.lookup.address import address_for
from sro.domain.shared.identifiers import PrincipalId, TenantId


async def _ask(tenant: str, question: str, *, send: bool) -> int:
    container = build_container()
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("scripts"))

    planned = await container.plan_lookups().execute(ctx, question=question)
    print(f"Q: {planned.plan.question}")
    if planned.plan.asks is not None:
        asked = planned.plan.asks
        print(f"   stopped on an open question: {asked.question}")
        print(f"   options: {', '.join(asked.options) or 'none recorded'}")
        for because in asked.because:
            print(f"   because: {because}")
        return 0
    if planned.refused:
        print(f"   refused: {planned.refused}")
        return 1
    print(f"   why: {planned.plan.why}")

    async with container.unit_of_work() as uow:
        gestures = list(await uow.gestures.gestures_for(TenantId(tenant)))

    for lookup in planned.plan.lookups:
        print(f"\n{lookup.how.upper()} {lookup.system} {lookup.target}")
        print(f"   why: {lookup.why}")
        print(f"   cites: {', '.join(lookup.cites)}")
        address = address_for(lookup, gestures)
        if address is None:
            print("   nowhere: nothing here has ever been to that")
            continue
        print(f"   url: {address.url}")
        if address.live_headers:
            print(f"   live headers: {', '.join(address.live_headers)}")
        if address.struck:
            print(f"   struck out: {', '.join(address.struck)}")

    if not send:
        print("\ndry. Add --send to go and look.")
        return 0

    answers = await container.run_lookups().execute(ctx, plan=planned.plan)
    for looked in answers.looked:
        print(f"\n{looked.lookup.target}: {'ok' if looked.ok else looked.detail}")
        body = looked.answer.get("body")
        if isinstance(body, str):
            print(f"   {body[:400]}")
    return 0 if answers.any_answered else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tenant")
    parser.add_argument("question")
    parser.add_argument("--send", action="store_true", help="actually go and look")
    args = parser.parse_args()
    return asyncio.run(_ask(args.tenant, args.question, send=args.send))


if __name__ == "__main__":
    raise SystemExit(main())
