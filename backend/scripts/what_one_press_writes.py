"""What one press of each mined job would write, and what depends on what.

    uv run python scripts/what_one_press_writes.py            # acme and new
    uv run python scripts/what_one_press_writes.py acme
    uv run python scripts/what_one_press_writes.py --all      # every tenant in the store

Reads only. Nothing here starts a run, touches a warehouse or writes a row.

Written because three defects in one day came out of running the real code over
the real store rather than over its own fixtures, and every one of them was
invisible to a green suite:

* the only `uses` edge in three tenants was a step depending on itself -- a
  confirming read-back counted as a value the warehouse minted, and two steps
  citing one click read the same call from both sides;
* four steps stood on a doing that wrote TWICE, and the deterministic replay
  sends one call, so a run made half a supplier and reported `held`;
* the offer card, built on the single call a replay would send, named the
  address a supplier create edits and never the supplier.

So this is the shape of question that has to be asked of the store and not of a
fixture. Four sections, each one a rule the product depends on:

    1. what one press writes   what the card now says, per job
    2. a Save that writes twice  the cascade the replay must refuse
    3. which step uses which     `Step.uses`, as the producer reads it today
    4. one job into another      the chain composition (7) has no instance of
    5. what can be taken back    which job undoes which, and what the runs made
    6. one call into the next    a cascade: a write carrying an id the write
                                 before it returned, both behind one press

Run it against a deployment by running it ON the deployment -- the settings
already name that database, and a report about a store is worth what the store
is.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sro.container import build_container
from sro.domain.execution.cascade import flows_in
from sro.domain.execution.evidence import READ_METHODS
from sro.domain.execution.uses_edges import K_SHORTEST, uses_edges
from sro.domain.execution.verified_writes import verified_write_for
from sro.domain.execution.what_it_writes import what_it_writes
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.reversals import addresses, asks_for, identifies, undoes
from sro.domain.skill.workflow import Workflow
from sro.infrastructure.knowledge.write_endpoints import load_verified_writes

K_RUNS = 500
"""How many runs back to read. Every run this system has ever done, on every
deployment there is: the number is a bound, not a window."""

_LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)
"""Every tenant that has ever uploaded. `tenants_since` is the one tenant-blind
read this system has, and it is what "every tenant" can honestly mean here."""


async def _look(tenant: str) -> None:
    container = build_container()
    ledger = load_verified_writes()
    who = TenantId(tenant)
    async with container.unit_of_work() as uow:
        jobs = list(await uow.workflows.known(who))
        gestures = list(await uow.gestures.gestures_for(who))
    by_id = {gesture.id: gesture for gesture in gestures}

    head = f"{tenant}: {len(jobs)} jobs, {len(gestures)} gestures"
    print(f"\n{head}\n{'═' * len(head)}")
    async with container.unit_of_work() as uow:
        runs = list(await uow.workflow_runs.recent(who, limit=K_RUNS))
    _what_a_press_writes(jobs, by_id)
    _a_save_that_writes_twice(jobs, by_id, ledger)
    _which_step_uses_which(jobs, by_id)
    _one_job_into_another(jobs, by_id)
    _what_can_be_taken_back(jobs, by_id, runs)
    _one_call_into_the_next(jobs, by_id)


def _what_a_press_writes(jobs: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> None:
    """Section 1. Exactly what the offer card will say before the press."""
    print("\n1. what one press writes")
    silent = 0
    for job in jobs:
        said = what_it_writes(job, by_id)
        if not said:
            silent += 1
            continue
        for one in said:
            where = one["on"].split("//")[-1]
            print(
                f"   {job.title[:38]:40} It will {one['does']} a {one['record']} record on {where}"
            )
    print(f"   ({silent} of {len(jobs)} jobs write nothing the evidence can name)")


def _a_save_that_writes_twice(
    jobs: Sequence[Workflow], by_id: Mapping[str, Gesture], ledger: tuple[object, ...]
) -> None:
    """Section 2. One logical create is often several physical resources.

    Counted per DOING and only over writes the ledger recognises -- a step
    cites one gesture per demonstration, and the same click fires keepalives
    and telemetry. `plan_step` refuses the deterministic replay for exactly
    this shape; anything printed here is a step that now clicks Save instead.
    """
    print("\n2. a Save that writes twice (the replay refuses these)")
    found = 0
    for job in jobs:
        for step in sorted(job.steps, key=lambda one: one.order):
            for cited in step.cites:
                doing = by_id.get(cited)
                if doing is None:
                    continue
                known = [
                    call
                    for call in doing.requests
                    if verified_write_for(call, ledger) is not None  # type: ignore[arg-type]
                ]
                if len(known) < 2:
                    continue
                found += 1
                wrote = ", ".join(f"{call.method} {_short(call.url)}" for call in known)
                print(f"   {job.title[:34]:36} step {step.order}: {wrote}")
                break
    if not found:
        print("   none: every doing wrote at most once")


def _which_step_uses_which(jobs: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> None:
    """Section 3. `Step.uses`, read off the evidence rather than off the row.

    Printed beside what the STORE holds, because the two disagreeing is the
    interesting case: a job mined before the producer was fixed carries edges
    nothing would draw today.
    """
    print("\n3. which step uses which")
    steps = sum(len(job.steps) for job in jobs)
    read = 0
    for job in jobs:
        edges = uses_edges(job, by_id)
        stored = {step.order: list(step.uses) for step in job.steps if step.uses}
        if edges or stored:
            read += 1
            print(f"   {job.title[:30]:32} evidence {edges or '{}'}, the row {stored or '{}'}")
    if not read:
        print(f"   none: 0 edges over {steps} steps, and none stored")


def _one_job_into_another(jobs: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> None:
    """Section 4. The chain item 7 needs and has never seen.

    A value one job's answer MINTED, taken by another job later in the same
    browsing stream. Minted means: in a mutation's response, not in its own
    request, and not typed or sent by anybody earlier in that stream -- which
    is the subtraction the first version of this measurement lacked, and it
    reported 329 chains on a tenant that has none.
    """
    print("\n4. one job into another")
    typed = _first_typed(by_id)
    made = {job.id: _minted(job, by_id, typed) for job in jobs}
    took = {job.id: _taken(job, by_id) for job in jobs}
    pairs = found = 0
    for first in jobs:
        for second in jobs:
            if first.id == second.id:
                continue
            pairs += 1
            crossed = {
                value
                for stream, at, value in made[first.id]
                for other, later, value2 in took[second.id]
                if stream == other and at < later and value == value2
            }
            if crossed:
                found += 1
                print(f"   {first.title[:30]!r} -> {second.title[:30]!r}: {sorted(crossed)[:4]}")
    if not found:
        print(f"   none: 0 chains over {pairs} ordered pairs")


def _what_can_be_taken_back(
    jobs: Sequence[Workflow], by_id: Mapping[str, Gesture], runs: Sequence[WorkflowRun]
) -> None:
    """Section 5. The compensation story, as the store actually holds it.

    Three questions in one: which job undoes which (`reversals.undoes`, matched
    on the endpoint and never on a name), which runs made a record this system
    could address, and how many runs say which run they take back.

    The last is what `7aa7645d` added and is `0` until somebody presses an
    undo. It is here so that the day it is not zero, the pair is readable.
    """
    print("\n5. what can be taken back")
    named = {job.id: job.title for job in jobs}
    by_job = {job.id: job for job in jobs}
    # Which job takes back which, and which field that job's delete addresses a
    # record by -- the two halves the card needs before it can offer a press.
    takes_back: dict[str, tuple[str, frozenset[str]]] = {}
    pairs = 0
    for job in jobs:
        other = undoes(job, dict(by_id), jobs)
        if other is not None:
            pairs += 1
            field = identifies(by_job[other], by_id)
            takes_back[job.id] = (other, field)
            says = (
                f" by {', '.join(sorted(field))}"
                if field
                else " (and nothing says which field addresses it)"
            )
            print(f"   {job.title[:34]:36} is taken back by {named.get(other, other)!r}{says}")
    if not pairs:
        print("   no job of this tenant's undoes another")
    made = [run for run in runs if any(step.made for step in run.steps)]
    print(f"   {len(runs)} runs read, {len(made)} made a record this can name")
    for run in made[:5]:
        other, field = takes_back.get(run.workflow_id, ("", frozenset()))
        which = addresses([step.made for step in run.steps if step.made], field)
        # What the press would actually send: the value, under the name the
        # UNDO asks for. A press in the warehouse's vocabulary names a
        # parameter the job does not have.
        asks = asks_for(by_job[other]) if other in by_job else None
        press = f"{asks} = {which[1]}" if which and asks else "nothing to press"
        print(f"      {run.id} {named.get(run.workflow_id, run.workflow_id)[:26]!r} {press}")
    print(f"   runs that say which run they take back: {sum(1 for r in runs if r.undoes_run)}")


def _one_call_into_the_next(jobs: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> None:
    """Section 6. The chain that is really there, one level below section 4.

    `KNOWLEDGE-BASE.md` 3b, watched on the live host: creating one client fires
    four POSTs behind a single Save -- addresses, clients, clientWarehouse,
    packingConfigurations -- **each carrying an id the one before it
    returned**. That is a value flowing out of one write's answer and into the
    next write's body, which is what composition IS; it happens inside one
    doing rather than between two jobs.

    `domain/execution/cascade.flows_in` is the rule, so this and `plan_step`
    read the evidence the same way.
    """
    print("\n6. one call into the next")
    typed = _first_typed(by_id)
    found = 0
    for job in jobs:
        for step in sorted(job.steps, key=lambda one: one.order):
            for cited in step.cites:
                doing = by_id.get(cited)
                if doing is None:
                    continue
                for flow in flows_in(doing, typed):
                    found += 1
                    print(
                        f"   {job.title[:28]:30} step {step.order}: {flow.key} from"
                        f" {flow.made_at} sent on as {flow.into} to {flow.used_at}"
                    )
    if not found:
        print("   none: no write carried a value the write before it returned")


def _first_typed(by_id: Mapping[str, Gesture]) -> dict[str, float]:
    """When each value was first typed or sent by anybody, across every stream.

    A value the operator typed at 10:01 and the server echoed at 10:05 is not a
    value the server made, and without this every read-back reads as a mint.

    Across streams and not within one, which the first version got wrong and
    tenant `new` said so: a stream is a BROWSER's lifetime, so an operator who
    signed in during an earlier one and then created a work area has a create
    whose answer carries `RKUCHIYAGM` -- their own username, stamped by the
    warehouse -- with no typing of it in that stream to subtract. Read per
    stream, that is a work-area job "producing" a value the login job "takes",
    which is two jobs sharing a person rather than a chain.
    """
    first: dict[str, float] = {}
    for gesture in by_id.values():
        for value in _put_in(gesture):
            first[value] = min(first.get(value, gesture.at), gesture.at)
    return first


def _minted(
    job: Workflow, by_id: Mapping[str, Gesture], typed: Mapping[str, float]
) -> list[tuple[str, float, str]]:
    made: list[tuple[str, float, str]] = []
    for gesture in _doings(job, by_id):
        for call in gesture.requests:
            if call.method.upper() in READ_METHODS or call.response_body is None:
                continue
            sent = set(_values(call.request_body.text if call.request_body else None))
            for value in _values(call.response_body.text):
                if value in sent:
                    continue
                when = typed.get(value)
                if when is not None and when <= gesture.at:
                    continue
                made.append((gesture.stream_id, gesture.at, value))
    return made


def _taken(job: Workflow, by_id: Mapping[str, Gesture]) -> list[tuple[str, float, str]]:
    return [
        (gesture.stream_id, gesture.at, value)
        for gesture in _doings(job, by_id)
        for value in _put_in(gesture)
    ]


def _put_in(gesture: Gesture) -> set[str]:
    """Everything this doing put in: typed into a control, or sent in a body."""
    values = set()
    typed = gesture.action.value
    if isinstance(typed, str) and len(typed.strip()) >= K_SHORTEST:
        values.add(typed.strip())
    for call in gesture.requests:
        values |= set(_values(call.request_body.text if call.request_body else None))
    return values


def _values(text: str | None) -> list[str]:
    """A body's leaf strings, long enough to carry an identity."""
    if not text:
        return []
    try:
        document = json.loads(text)
    except ValueError:
        return []
    if not isinstance(document, dict):
        return []
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return [
        value.strip()
        for value in record.values()
        if isinstance(value, str) and len(value.strip()) >= K_SHORTEST
    ]


def _doings(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    return [by_id[cited] for step in job.steps for cited in step.cites if cited in by_id]


def _short(url: str) -> str:
    path = url.split("?")[0].split("//")[-1]
    return path[-44:]


async def _every(tenants: Sequence[str]) -> int:
    for tenant in tenants:
        await _look(tenant)
    print(
        "\nReads only. Section 2 is the shape `plan_step` refuses to replay;"
        " section 4 is what composition (7) still has no instance of."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tenants", nargs="*", default=[], help="tenant ids; acme and new by default"
    )
    parser.add_argument("--all", action="store_true", help="every tenant the store holds")
    args = parser.parse_args()
    if args.all:
        return asyncio.run(_all())
    return asyncio.run(_every(args.tenants or ["acme", "new"]))


async def _all() -> int:
    container = build_container()
    async with container.unit_of_work() as uow:
        found = await uow.gestures.tenants_since(_LONG_AGO)
    return await _every(sorted({one.value for one in found}))


if __name__ == "__main__":
    raise SystemExit(main())
