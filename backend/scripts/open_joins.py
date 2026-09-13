"""The joins nobody has answered, as questions a person can answer.

The last unmet item on phase 7's precondition
(`docs/new-agent-doc-arc/two-miners-one-day.md`) and the only one no script can
close: a model may notice that two candidates look like one piece of work and
say why, and **a person decides whether they are**. The answer names who said
so, because "these two are the same task" is a claim about somebody's work.

    uv run python scripts/open_joins.py            # every tenant
    uv run python scripts/open_joins.py acme

Reads only. It prints each question once -- a join is stored on both
candidates, so the store holds two rows per question -- with the evidence
either side and the exact call that answers it.
"""

from __future__ import annotations

import asyncio
import sys

from sro.container import build_container
from sro.domain.observation.candidate import TaskCandidate
from sro.domain.shared.identifiers import TenantId


def _said(candidate: TaskCandidate) -> str:
    named = candidate.title or repr(candidate.signature)
    return f"{named} ({len(candidate.episodes)}x on {candidate.host})"


async def _ask(tenant: str, first: int = 0) -> int:
    container = build_container()
    async with container.unit_of_work() as uow:
        candidates = await uow.candidates.list_for_tenant(TenantId(tenant))
    by_id = {candidate.id.value: candidate for candidate in candidates}

    asked: set[frozenset[str]] = set()
    questions = first
    for candidate in candidates:
        for join in candidate.joins:
            if join.answered is not None:
                continue
            pair = frozenset({candidate.id.value, join.other_id.value})
            if pair in asked:
                # The same question from the other side. One decision, not two.
                continue
            asked.add(pair)
            other = by_id.get(join.other_id.value)
            questions += 1
            print(f"\n{questions}. [{join.kind}] on {tenant}")
            print(f"   {_said(candidate)}")
            print(f"   {_said(other) if other else 'a candidate this tenant no longer holds'}")
            print(f"   the model's reason: {join.because}")
            print(
                f"   answer:  POST /v1/candidates/{candidate.id.value}/joins"
                f'  {{"other_id": "{join.other_id.value}", "answer": "same|different"}}'
            )
    if questions == first:
        print(f"{tenant}: nothing is waiting on a person")
    return questions


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
