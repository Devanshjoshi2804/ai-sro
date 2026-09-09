"""What the next pass will be offered first, and what it will not.

Ported from `new_agent_arch/src/rig/api.py:794`. Its docstring is the reason
this exists: ``retired`` is the record `pool.py` says must exist -- evidence
that stopped being privileged, when it entered and under which cap it aged out
-- and nothing over the wire could read it. A pass whose window quietly stopped
carrying yesterday's tail looked exactly like one that had nothing left to
carry.

Two reads and never one. ``PoolRepository`` says it in its own words: a retired
entry is not a deleted one, it stops being offered ahead of fresh evidence and
goes on being packed on its own merits, so the live entries and the retired
ones are two lists and an entry is retired exactly when it has a ``reason``.
Folding them into one list with a flag would put the two on the same footing,
which is the thing the pool is deliberately not.

Nothing here computes, and nothing here ages. Reading the pool must not move
it: `mine_pass` is what calls ``age``, once per pass, and a door that aged what
it looked at would retire evidence for being read about.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.pool import PoolEntry


@dataclass(frozen=True, slots=True)
class Pool:
    waiting: tuple[PoolEntry, ...]
    """Live entries, oldest first -- the order the next pass will draw them in."""

    retired: tuple[PoolEntry, ...]
    """What the pool stopped offering, each carrying why. Still packed as
    ordinary evidence at its own strength; what it lost is the bonus."""


class ReadPool:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> Pool:
        async with self._uow as uow:
            return Pool(
                waiting=await uow.pool.waiting(ctx.tenant_id),
                retired=await uow.pool.retired(ctx.tenant_id),
            )
