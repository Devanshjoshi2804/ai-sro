from __future__ import annotations

import logging

from sro.application.context import RequestContext
from sro.application.knowledge.vectors import embed_or_none
from sro.application.ports.embedding import Embedder
from sro.application.ports.repositories import UnitOfWork

logger = logging.getLogger(__name__)

_BATCH = 200


class BackfillEmbeddings:
    def __init__(self, uow: UnitOfWork, embedder: Embedder) -> None:
        self._uow = uow
        self._embedder = embedder

    async def execute(self, ctx: RequestContext, *, limit: int = 10_000) -> int:
        if not self._embedder.available:
            logger.warning("no embedder is configured; nothing to backfill")
            return 0

        filled = 0
        while filled < limit:
            async with self._uow as uow:
                pending = await uow.knowledge.without_embedding(ctx.tenant_id, limit=_BATCH)
                if not pending:
                    break

                vectors = await embed_or_none(
                    self._embedder, tuple(f"{e.title} — {e.key}" for e in pending)
                )
                written = 0
                for entry, vector in zip(pending, vectors, strict=True):
                    if not vector:
                        continue
                    entry.embedding = vector
                    await uow.knowledge.save(entry)
                    written += 1
                await uow.commit()

            if written == 0:
                logger.warning("embedding produced no vectors; stopping with %d done", filled)
                break
            filled += written
            logger.info("embedded %d claims", filled)
        return filled
