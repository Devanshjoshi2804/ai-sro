"""Work that alternated between two systems, and what the miner makes of it.

A job can be two halves in two tabs -- read the mail, create the thing it asks
for -- and `shared_values` is the only rule that links them. It links on a
TYPED VALUE appearing in both systems, so a mail somebody read but never typed
into links nothing, however plainly the work follows from it.

    uv run python scripts/two_tabs.py            # every tenant
    uv run python scripts/two_tabs.py acme --gap 60

Reads only. For each tenant it prints the sittings where the browser went to
another system and came back -- an alternation, not a one-way trip to a login
page -- and how many of those gestures the value rule links.

Measured on 2026-09-14: on `acme`, 5 of 43 sittings alternate, carrying 219
gestures, of which 211 are linked by no shared value; the rule links 23 in the
whole store. The consequence is visible in the output: an `acme` sitting at
15:00 where the operator read a mail whose subject is "create a customer type
:", typed the value into the warehouse six seconds later, and the job mined
from it has no mail step at all.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from urllib.parse import urlsplit

from sro.container import build_container
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.values import frequencies_over, shared_values
from sro.domain.shared.identifiers import TenantId


def _sittings(gestures: list[Gesture], gap: float) -> list[list[Gesture]]:
    """Stretches with no more than `gap` seconds of silence in them.

    A sitting rather than a day: what makes two tabs one job is somebody
    working in both, and an hour of quiet between them is two sittings however
    the day is sliced.
    """
    if not gestures:
        return []
    sittings: list[list[Gesture]] = []
    run = [gestures[0]]
    for gesture in gestures[1:]:
        if gesture.at is not None and run[-1].at is not None and gesture.at - run[-1].at <= gap:
            run.append(gesture)
        else:
            sittings.append(run)
            run = [gesture]
    sittings.append(run)
    return sittings


def _turns(sitting: list[Gesture]) -> int:
    """How many times the browser changed system inside this sitting."""
    order = [gesture.system for gesture in sitting]
    return sum(1 for i in range(len(order) - 1) if order[i] != order[i + 1])


def _woven(sitting: list[Gesture]) -> bool:
    """Whether this sitting went to another system and came BACK.

    A one-way trip is not evidence of one job: every warehouse session starts
    at a login host. Coming back is what says somebody was using two tabs for
    one piece of work.
    """
    order = [gesture.system for gesture in sitting]
    return any(
        order[i] != order[i + 1] and order[i] in order[i + 2 :] for i in range(len(order) - 2)
    )


async def _read(tenant: str, gap: float, show: int) -> None:
    container = build_container()
    tenant_id = TenantId(tenant)
    async with container.unit_of_work() as uow:
        gestures = [
            gesture
            for gesture in await uow.gestures.gestures_for(tenant_id)
            if gesture.at and gesture.system
        ]
        intents = {
            intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)
        }
        jobs = await uow.workflows.known(tenant_id)

    gestures.sort(key=lambda gesture: gesture.at or 0.0)
    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    linked = {gesture_id for ids in crossings.values() for gesture_id in ids}
    cited = {cite: job.title for job in jobs for step in job.steps for cite in step.cites}

    sittings = _sittings(gestures, gap)
    woven = [
        sitting for sitting in sittings if len({g.system for g in sitting}) > 1 and _woven(sitting)
    ]
    # Loudest first. A login dance -- warehouse, identity provider, keycloak,
    # warehouse -- changes system three times and is plumbing. Somebody working
    # a mail against a warehouse form changes it five times in three minutes and
    # is one job. Printed in that order, the difference is the first line.
    woven.sort(key=_turns, reverse=True)
    inside = {gesture.id for sitting in woven for gesture in sitting}

    print(f"\n== {tenant}: {len(gestures)} gestures, {len(sittings)} sittings at {gap:.0f}s")
    print(
        f"   the value rule links {len(linked)} gesture(s) across systems,"
        f" by {len(crossings)} value(s)"
    )
    print(f"   {len(woven)} sitting(s) went to another system and came back, holding {len(inside)}")
    print(f"   of those, {len(inside - linked)} are linked by no shared value")

    for sitting in woven[:show]:
        start = dt.datetime.fromtimestamp(sitting[0].at or 0, dt.UTC)
        hosts: dict[str, int] = {}
        for gesture in sitting:
            host = urlsplit(gesture.url or "").netloc
            hosts[host] = hosts.get(host, 0) + 1
        named = ", ".join(f"{host} ({count})" for host, count in sorted(hosts.items()))
        mined = {cited[g.id] for g in sitting if g.id in cited}
        print(
            f"\n   {start:%Y-%m-%d %H:%M} · {len(sitting)} gestures ·"
            f" {_turns(sitting)} changes of system · {named}"
        )
        print(f"      mined into: {', '.join(sorted(mined)) or 'nothing'}")
        for host in hosts:
            half = [g for g in sitting if urlsplit(g.url or "").netloc == host]
            kept = len([g for g in half if g.id in cited])
            print(f"      {host}: {kept} of {len(half)} gestures cited by a job")


async def _every(tenants: list[str], gap: float, show: int) -> int:
    for tenant in tenants:
        await _read(tenant, gap, show)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tenants", nargs="*", default=["acme", "new"])
    parser.add_argument(
        "--gap", type=float, default=60.0, help="seconds of silence that end a sitting"
    )
    parser.add_argument("--show", type=int, default=3, help="how many sittings to print in full")
    args = parser.parse_args()
    return asyncio.run(_every(args.tenants or ["acme", "new"], args.gap, args.show))


if __name__ == "__main__":
    raise SystemExit(main())
