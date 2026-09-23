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

_LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)


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
    print("\n5. what can be taken back")
    named = {job.id: job.title for job in jobs}
    by_job = {job.id: job for job in jobs}
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
        asks = asks_for(by_job[other]) if other in by_job else None
        press = f"{asks} = {which[1]}" if which and asks else "nothing to press"
        print(f"      {run.id} {named.get(run.workflow_id, run.workflow_id)[:26]!r} {press}")
    print(f"   runs that say which run they take back: {sum(1 for r in runs if r.undoes_run)}")


def _one_call_into_the_next(jobs: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> None:
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
    values = set()
    typed = gesture.action.value
    if isinstance(typed, str) and len(typed.strip()) >= K_SHORTEST:
        values.add(typed.strip())
    for call in gesture.requests:
        values |= set(_values(call.request_body.text if call.request_body else None))
    return values


def _values(text: str | None) -> list[str]:
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
