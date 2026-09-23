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

logger = logging.getLogger("sro.knowledge.ingest")

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base"


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
