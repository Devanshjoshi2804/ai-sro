"""What an operator actually did, in the order they did it.

    uv run python scripts/what_they_did.py --tenant greyorange
    uv run python scripts/what_they_did.py --since 90      # the last hour and a half
    uv run python scripts/what_they_did.py --typed         # only what was typed

The question this answers gets asked every time something on a screen looks
wrong: *did a run do that, or did a person?* It was answered on 2026-09-16 by
hand-written SQL against the `gestures` table, and the first three attempts
answered nothing at all -- because the query asked for `gesture->'action'->>'kind'`
and the stored JSON has no `action` key. Every column came back empty, which
reads exactly like "nothing was captured", and the conclusion drawn from it was
that capture was broken. It was not. The shape was wrong.

**The shape, once, here.** A gesture row stores the action INLINE:

    {"at": …, "url": …, "kind": "type", "value": "GDY", "secret": false,
     "target": {"name": …, "component": {"field_label": "Customer Type", …}}}

`sro.domain.observation.gesture.Gesture` puts those five under `.action`, which
is what every reader inside the backend sees -- the repository unpacks the row
on the way out. So `g.action.kind` is right in Python and `gesture->>'kind'` is
right in SQL, and the two looking different is the whole trap.

`value` is what was typed. Not `text`: a probe that asked for `action.text`
printed `null` for every gesture it read and said nothing about it, which is
the same mistake wearing the quieter face.

**Reads, and nothing else.** Raw SQL for `measure.py`'s stated reason: this
asks a question the product never asks -- "what happened, in order" -- and a
repository method added for a probe is a method the product then carries. A
secret's value is never stored (the recorder strikes it at the boundary), so
`secret` is printed as a fact and there is nothing behind it to leak.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.config import get_settings

K_WIDE = 34
"""How much of a field name or a typed value one line shows. A mail row's
accessible name is the whole subject and first line, and a timeline where one
entry wraps four times is one nobody reads."""

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
    """One line of it, however the page wrapped it."""
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
        # The absence is a measurement too, and it is the one that was misread:
        # nothing here means nothing was CAPTURED, which is a different fact
        # from nothing having happened.
        print("\n  nothing was captured in this window.\n")
        return 0
    print("\n" + "\n".join(lines) + "\n")
    return 0


raise SystemExit(main())
