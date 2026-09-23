from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.config import get_settings

K_WIDE = 34

TIMELINE = """
select at,
       coalesce(system, '') as system,
       gesture->>'kind' as kind,
       coalesce(gesture->>'value', '') as value,
       coalesce((gesture->>'secret')::bool, false) as secret,
       coalesce(
           gesture->'target'->'component'->>'field_label',
           gesture->'target'->'component'->>'item_id',
           gesture->'target'->>'name',
           ''
       ) as target,
       jsonb_array_length(coalesce(requests, '[]'::jsonb)) as calls
  from gestures
 where (cast(:tenant as text) is null or tenant_id = cast(:tenant as text))
   and to_timestamp(at) > now() - make_interval(mins => cast(:since as int))
 order by at desc
 limit cast(:limit as int)
"""


def _short(said: str) -> str:
    one = " ".join(said.split())
    return one if len(one) <= K_WIDE else one[: K_WIDE - 1] + "…"


async def _timeline(tenant: str | None, since: int, limit: int, typed: bool) -> list[str]:
    engine = create_async_engine(get_settings().database_url)
    lines: list[str] = []
    async with engine.connect() as db:
        rows = list(
            (
                await db.execute(text(TIMELINE), {"tenant": tenant, "since": since, "limit": limit})
            ).all()
        )
    await engine.dispose()

    for at, system, kind, value, secret, target, calls in reversed(rows):
        if typed and kind != "type":
            continue
        when = datetime.fromtimestamp(float(at), tz=UTC).strftime("%H:%M:%S")
        said = "«struck out»" if secret else _short(value)
        where = system.replace("https://", "")[:38]
        lines.append(
            f"  {when}  {kind or '?':9} {_short(target):{K_WIDE}}  "
            f"{said:{K_WIDE}}  {where}" + (f"  ({calls} calls)" if calls else "")
        )
    return lines


def main() -> int:
    parsing = argparse.ArgumentParser(description=__doc__)
    parsing.add_argument("--tenant", default=None)
    parsing.add_argument("--since", type=int, default=120, help="minutes back")
    parsing.add_argument("--limit", type=int, default=40)
    parsing.add_argument("--typed", action="store_true", help="only what was typed")
    args = parsing.parse_args()

    lines = asyncio.run(_timeline(args.tenant, args.since, args.limit, args.typed))
    head = f"What was done in the last {args.since} minutes — {args.tenant or 'every tenant'}"
    print(f"\n{head}\n{'─' * len(head)}")
    if not lines:
        print("\n  nothing was captured in this window.\n")
        return 0
    print("\n" + "\n".join(lines) + "\n")
    return 0


raise SystemExit(main())
