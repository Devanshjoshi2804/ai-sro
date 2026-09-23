from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from sro.application.context import RequestContext
from sro.container import build_container
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.observability import configure_logging

logger = logging.getLogger("sro.knowledge.seed_skills")

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base" / "http" / "flows"


def _read_flows(root: Path) -> list[tuple[Path, dict[str, object]]]:
    return [(path, json.loads(path.read_text())) for path in sorted(root.glob("*.json"))]


async def seed(*, tenant: str, system: str, root: Path) -> None:
    flows = _read_flows(root)
    if not flows:
        logger.error("no flows found under %s", root)
        raise SystemExit(1)

    container = build_container()
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("knowledge-base"))
    seeder = container.seed_skill_from_flow()

    seeded = skipped = failed = 0
    for path, flow in flows:
        try:
            result = await seeder.execute(ctx, flow=flow, system=system, label=path.stem)
        except Exception:
            failed += 1
            logger.exception("could not seed %s", path.name)
            continue
        if result.skill_id is not None and result.recording_id is not None:
            seeded += 1
            logger.info("%s: seeded skill %s", path.name, result.skill_id.value)
        else:
            skipped += 1
            logger.info("%s: skipped (%s)", path.name, result.skipped)

    logger.info("seeded %d · skipped %d · failed %d", seeded, skipped, failed)


def main() -> None:
    configure_logging()
    tenant = sys.argv[1] if len(sys.argv) > 1 else "acme"
    system = sys.argv[2] if len(sys.argv) > 2 else "blue_yonder"
    root = Path(sys.argv[3]) if len(sys.argv) > 3 else _DEFAULT_ROOT
    asyncio.run(seed(tenant=tenant, system=system, root=root))


if __name__ == "__main__":
    main()
