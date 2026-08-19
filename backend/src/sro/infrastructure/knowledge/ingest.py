"""Load the recorded knowledge base into the store.

Run with `make ingest-kb`. Re-runnable by construction: a claim whose source and
body have not changed is judged unchanged and nothing is written, so the second
run reports zero and costs one read per claim.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from sro.application.context import RequestContext
from sro.container import build_container
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.knowledge.catalogue import read_catalogue
from sro.observability import configure_logging

# Named rather than `__name__`: run as `python -m`, this module is `__main__`,
# which is outside the `sro` tree the log configuration raises to INFO -- so
# every line of the job's own progress would go nowhere.
logger = logging.getLogger("sro.knowledge.ingest")

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base"
"""``index/`` and ``http/`` sit directly under this. There is no
``blue-yonder-sce`` subdirectory -- an extra path segment here meant every
default-args run of `make ingest-kb` found nothing and exited 1 without
anybody noticing, because the module also logs a clean warning per missing
file first, which reads as "an empty knowledge base" rather than as broken."""


async def ingest(*, tenant: str, system: str, root: Path) -> None:
    claims = read_catalogue(root, system=system)
    if not claims:
        logger.error("no claims found under %s", root)
        raise SystemExit(1)

    container = build_container()
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("knowledge-base"))
    logger.info("read %d claims from %s", len(claims), root)

    recorded = await container.record_claims().execute(ctx, claims)
    logger.info(
        "believed %d · unchanged %d · recorded but not believed %d",
        recorded.believed,
        recorded.unchanged,
        recorded.recorded_not_believed,
    )

    # Unchanged claims are deliberately not rewritten, so anything stored before
    # embeddings were switched on still has no vector. Filling those in is the
    # normal case rather than an edge one.
    filled = await container.backfill_embeddings().execute(ctx)
    if filled:
        logger.info("backfilled %d embeddings", filled)


def main() -> None:
    configure_logging()
    tenant = sys.argv[1] if len(sys.argv) > 1 else "acme"
    system = sys.argv[2] if len(sys.argv) > 2 else "blue_yonder"
    root = Path(sys.argv[3]) if len(sys.argv) > 3 else _DEFAULT_ROOT
    asyncio.run(ingest(tenant=tenant, system=system, root=root))


if __name__ == "__main__":
    main()
