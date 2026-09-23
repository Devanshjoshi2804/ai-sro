from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from datetime import timedelta
from urllib.parse import urlsplit

from sro.container import build_container
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId

BESIDE = timedelta(minutes=3)


def _said(candidate: TaskCandidate) -> str:
    named = candidate.title or repr(candidate.signature)
    return f"{named} ({len(candidate.episodes)}x on {candidate.host})"


def _beside(episode: Episode, gestures: list[Gesture]) -> dict[str, int]:
    start = (episode.touched_from or episode.started_at) - BESIDE
    end = (episode.touched_until or episode.ended_at) + BESIDE
    found: dict[str, int] = {}
    for gesture in gestures:
        if gesture.at is None or not (start.timestamp() <= gesture.at <= end.timestamp()):
            continue
        host = urlsplit(gesture.url or "").netloc
        if host and host != episode.host:
            found[host] = found.get(host, 0) + 1
    return found


def _elsewhere(candidate: TaskCandidate, gestures: list[Gesture]) -> str:
    seen: dict[str, int] = {}
    sittings = 0
    for episode in candidate.episodes:
        beside = _beside(episode, gestures)
        if beside:
            sittings += 1
        for host, count in beside.items():
            seen[host] = seen.get(host, 0) + count
    if not seen:
        return "        nothing else was worked in around these doings"
    named = ", ".join(f"{host} ({count} gestures)" for host, count in sorted(seen.items()))
    return f"        {sittings} of {len(candidate.episodes)} doings sat beside work in: {named}"


async def _ask(tenant: str, first: int = 0) -> int:
    container = build_container()
    async with container.unit_of_work() as uow:
        candidates = await uow.candidates.list_for_tenant(TenantId(tenant))
        gestures = [g for g in await uow.gestures.gestures_for(TenantId(tenant)) if g.at]
    by_id = {candidate.id.value: candidate for candidate in candidates}

    asked: set[frozenset[str]] = set()
    questions = first
    for candidate in candidates:
        for join in candidate.joins:
            if join.answered is not None:
                continue
            pair = frozenset({candidate.id.value, join.other_id.value})
            if pair in asked:
                continue
            asked.add(pair)
            other = by_id.get(join.other_id.value)
            questions += 1
            print(f"\n{questions}. [{join.kind}] on {tenant}")
            print(f"   {_said(candidate)}")
            print(_elsewhere(candidate, gestures))
            print(f"   {_said(other) if other else 'a candidate this tenant no longer holds'}")
            if other:
                print(_elsewhere(other, gestures))
            print(f"   the model's reason: {join.because}")
            print(
                f"   answer:  POST /v1/candidates/{candidate.id.value}/joins"
                f'  {{"other_id": "{join.other_id.value}", "kind": "{join.kind.value}",'
                '  "answer": "same|different"}'
            )
    if questions == first:
        print(f"{tenant}: nothing is waiting on a person")
    print(_split(candidates), end="")
    return questions


def _split(candidates: Sequence[TaskCandidate]) -> str:
    hosts: dict[str, set[str]] = {}
    for candidate in candidates:
        hosts.setdefault(candidate.host, set()).add(candidate.principal_id.value)
    split = {host: who for host, who in hosts.items() if len(who) > 1}
    if not split:
        return ""
    lines = [
        "\n   note: this tenant's work is split across principals, and a pair",
        "\n   needs one principal on both sides, so these can never be joined:",
    ]
    lines += [f"\n     {host}: {', '.join(sorted(who))}" for host, who in sorted(split.items())]
    return "".join(lines) + "\n"


async def _every(tenants: list[str]) -> int:
    total = 0
    for tenant in tenants:
        total = await _ask(tenant, total)
    if total:
        print(
            f"\n{total} question(s). `same` on a variant dismisses one as a duplicate of"
            " the other and names it; `different` is kept too, so a question already"
            " answered is not asked again next week as though it were new."
        )
    return 0


def main() -> int:
    tenants = sys.argv[1:] or ["acme", "new"]
    return asyncio.run(_every(tenants))


if __name__ == "__main__":
    raise SystemExit(main())
