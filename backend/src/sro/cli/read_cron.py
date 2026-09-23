from __future__ import annotations

import argparse
import asyncio
import json

from sro.application.context import RequestContext
from sro.application.shared.refusals import OverCap
from sro.container import build_container
from sro.domain.shared.identifiers import PrincipalId, TenantId

MAX_PASSES = 25


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read each named tenant's unread gestures.")
    parser.add_argument("tenants", nargs="+", help="tenant ids to read, one pass each")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args.tenants))


async def _run(tenants: list[str]) -> int:
    container = build_container()
    report: dict[str, object] = {}
    broke = False

    for tenant in tenants:
        ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("cron"))
        read = 0
        try:
            for _ in range(MAX_PASSES):
                got = await container.read_gestures().execute(ctx)
                read += got
                if got == 0:
                    break
        except OverCap as stopped:
            report[tenant] = {"read": read, "stopped": str(stopped)}
        except Exception as problem:
            broke = True
            report[tenant] = {"read": read, "error": f"{type(problem).__name__}: {problem}"}
        else:
            report[tenant] = {"read": read}

    print(json.dumps(report, indent=2))
    return 1 if broke else 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
