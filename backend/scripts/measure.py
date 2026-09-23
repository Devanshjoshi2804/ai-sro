from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from sro.application.context import RequestContext
from sro.config import get_settings
from sro.container import build_container
from sro.domain.lookup.address import address_for
from sro.domain.shared.identifiers import PrincipalId, TenantId

ROOT = Path(__file__).resolve().parents[2]

WAREHOUSE = "jdadelivers.com"

MAIL_HOSTS = ("mail.google.com", "outlook.office.com")
LOCAL_HOSTS = ("localhost", "127.0.0.1")


@dataclass
class Line:
    label: str
    value: object
    of: object | None = None
    standing: str = "recorded"
    note: str = ""

    def rendered(self) -> str:
        shown = f"{self.value:,}" if isinstance(self.value, int) else str(self.value)
        if self.of is not None:
            shown = (
                f"{shown} of {self.of:,}" if isinstance(self.of, int) else f"{shown} of {self.of}"
            )
        tail = f"   {self.note}" if self.note else ""
        return f"  {self.label:<44} {shown:>22}   [{self.standing}]{tail}"

    def as_json(self) -> dict[str, object]:
        return {
            "label": self.label,
            "value": self.value,
            "of": self.of,
            "standing": self.standing,
            "note": self.note,
        }


@dataclass
class Section:
    title: str
    why: str
    lines: list[Line] = field(default_factory=list)

    def add(self, *lines: Line) -> None:
        self.lines.extend(lines)

    def rendered(self) -> str:
        head = f"\n{self.title}\n{'─' * len(self.title)}\n  {self.why}\n"
        if not self.lines:
            return head + "\n  nothing measured here.\n"
        return head + "\n" + "\n".join(line.rendered() for line in self.lines) + "\n"


async def _rows(db: AsyncConnection, sql: str, **args: object) -> list[Any]:
    return list((await db.execute(text(sql), args)).all())


async def _one(db: AsyncConnection, sql: str, **args: object) -> Any:
    rows = await _rows(db, sql, **args)
    return rows[0][0] if rows and rows[0] else 0


MINE = "(cast(:tenant as text) is null or tenant_id = cast(:tenant as text))"


def _host(url: str | None) -> str:
    if not url:
        return "none"
    bare = url.split("//", 1)[-1].split("/", 1)[0].split("?", 1)[0]
    return bare.split(":")[0] if not bare.startswith("localhost:") else "localhost"


def _standing_for(host: str) -> str:
    if WAREHOUSE in host:
        return "warehouse"
    if host in MAIL_HOSTS:
        return "mail"
    if any(host.startswith(local) for local in LOCAL_HOSTS):
        return "local"
    return "other"


async def evidence(db: AsyncConnection, tenant: str | None) -> Section:
    into = Section(
        "1. Evidence",
        "What was watched. Everything downstream stands on this, so it is measured by HOST:"
        " a day of fixtures and a day in a warehouse are not the same day.",
    )
    batches = await _one(db, f"select count(*) from gesture_batches where {MINE}", tenant=tenant)
    gestures = await _rows(
        db, f"select url, requests, at from gestures where {MINE}", tenant=tenant
    )
    if not gestures:
        into.add(Line("gestures stored", 0, standing="none", note="nothing has been captured"))
        return into

    hosts = Counter(_standing_for(_host(url)) for url, _, _ in gestures)
    stamps = [at for _, _, at in gestures if at]
    calls = [call for _, requests, _ in gestures for call in (requests or [])]
    writes = [
        call
        for call in calls
        if str(call.get("method", "")).upper() in ("POST", "PUT", "PATCH", "DELETE")
    ]
    worked = [
        call
        for call in writes
        if isinstance(call.get("status"), int) and 200 <= int(call["status"]) < 300
    ]
    warehouse_writes = [call for call in worked if WAREHOUSE in _host(call.get("url"))]

    into.add(
        Line("batches uploaded", batches, standing="recorded"),
        Line("gestures stored", len(gestures), standing="recorded"),
        Line(
            "span",
            f"{_when(min(stamps))} → {_when(max(stamps))}" if stamps else "none",
            standing="recorded",
        ),
        Line("gestures on the warehouse", hosts.get("warehouse", 0), len(gestures), "warehouse"),
        Line("gestures in a mailbox", hosts.get("mail", 0), len(gestures), "mail"),
        Line("gestures on a local page", hosts.get("local", 0), len(gestures), "local"),
        Line("calls captured beside them", len(calls), standing="recorded"),
        Line("writes seen succeed", len(worked), len(writes), "recorded"),
        Line(
            "…of those, in the warehouse",
            len(warehouse_writes),
            len(worked),
            "warehouse" if warehouse_writes else "none",
            note="" if warehouse_writes else "no write to a real warehouse was ever captured",
        ),
    )

    orphan_requests = await _one(
        db, f"select count(*) from orphan_requests where {MINE}", tenant=tenant
    )
    orphan_pages = await _one(db, f"select count(*) from orphan_pages where {MINE}", tenant=tenant)
    into.add(
        Line(
            "requests that reached no gesture",
            orphan_requests,
            len(calls) + orphan_requests,
            "recorded",
            note="background traffic AND evidence the correlator lost; this does not separate them",
        ),
        Line("page events that reached no gesture", orphan_pages, standing="recorded"),
    )
    return into


def _when(stamp: object) -> str:
    if isinstance(stamp, int | float):
        return datetime.fromtimestamp(float(stamp), tz=UTC).strftime("%Y-%m-%d")
    return str(stamp)[:10]


async def mining(db: AsyncConnection, tenant: str | None) -> Section:
    into = Section(
        "2. Mining",
        "What the model read out of that evidence, and what refused it. The uncited steps"
        " are the number that matters: a step citing nothing is the failure `validate`"
        " exists to stop.",
    )
    passes = await _rows(
        db,
        "select count(*), coalesce(sum(cost_usd),0), coalesce(sum(proposed),0),"
        " coalesce(sum(kept),0), coalesce(sum(rejected),0),"
        f" coalesce(sum(unplaced),0) from mining_passes where {MINE}",
        tenant=tenant,
    )
    count, cost, proposed, kept, rejected, unplaced = passes[0] if passes else (0, 0, 0, 0, 0, 0)
    failed = await _one(
        db,
        f"select count(*) from mining_passes where error is not null and {MINE}",
        tenant=tenant,
    )

    workflows = await _rows(db, f"select id from workflows where {MINE}", tenant=tenant)
    mine = f"workflow_id in (select id from workflows where {MINE})"
    steps = await _one(db, f"select count(*) from workflow_steps where {mine}", tenant=tenant)
    uncited = await _one(
        db,
        "select count(*) from workflow_steps where"
        f" (cites is null or jsonb_array_length(cites) = 0) and {mine}",
        tenant=tenant,
    )
    into.add(
        Line("mining passes run", count, standing="recorded"),
        Line("passes that failed outright", failed, count, "recorded"),
        Line("model spend on mining", f"${float(cost):.2f}", standing="recorded"),
        Line("workflows proposed", proposed, standing="recorded"),
        Line("kept", kept, proposed or None, "recorded"),
        Line("rejected by validate", rejected, proposed or None, "recorded"),
        Line("workflows now stored", len(workflows), standing="recorded"),
        Line(
            "gestures the passes could not place",
            unplaced,
            standing="recorded",
            note="the model's own claim about its window, not about any job",
        ),
        Line("steps stored", steps, standing="recorded"),
        Line(
            "…citing no gesture at all",
            uncited,
            steps or None,
            "recorded",
            note="should be 0: validate refuses these",
        ),
    )

    candidates = await _rows(
        db,
        f"select status, count(*) from task_candidates where {MINE} group by status",
        tenant=tenant,
    )
    for status, number in sorted(candidates, key=lambda row: -row[1]):
        into.add(Line(f"candidates {status}", number, standing="recorded"))

    open_joins = await _one(
        db,
        f"select count(*) from task_candidates where {MINE}"
        " and joins is not null and jsonb_array_length(joins) > 0",
        tenant=tenant,
    )
    into.add(
        Line(
            "candidates carrying a join",
            open_joins,
            standing="recorded",
            note="`make open-joins` shows the ones still asking a person",
        )
    )
    return into


async def running(db: AsyncConnection, tenant: str | None) -> Section:
    into = Section(
        "3. Running",
        "What was driven back through a browser, and WHICH BELT said it worked. The belt is"
        " the whole argument: a step held by a status code and one held by a picture are"
        " different claims about reality.",
    )
    runs = await _rows(
        db,
        f"select outcome, live, count(*) from workflow_runs where {MINE} group by outcome, live",
        tenant=tenant,
    )
    if not runs:
        into.add(Line("workflow runs", 0, standing="none", note="nothing has ever been run"))
    for outcome, live, number in sorted(runs, key=lambda row: -row[2]):
        into.add(
            Line(
                f"runs {outcome} ({'live' if live else 'dry'})",
                number,
                standing="local" if live else "recorded",
            )
        )

    verdicts = await _rows(
        db,
        "select verdict, verdict_by, count(*) from workflow_run_steps where run_id in"
        f" (select id from workflow_runs where {MINE}) group by verdict, verdict_by",
        tenant=tenant,
    )
    by_belt: Counter[tuple[str, str]] = Counter()
    for verdict, verdict_by, number in verdicts:
        by_belt[(verdict or "none", verdict_by or "none")] += number
    total_steps = sum(by_belt.values())
    for (verdict, belt), number in sorted(by_belt.items(), key=lambda item: -item[1]):
        into.add(Line(f"steps {verdict} by {belt}", number, total_steps or None, "recorded"))

    for belt in ("status", "read", "screen"):
        seen = sum(number for (_, name), number in by_belt.items() if name == belt)
        into.add(
            Line(
                f"rung {belt!r} has verified",
                seen,
                total_steps or None,
                "recorded" if seen else "none",
                note="" if seen else "never, in this selection",
            )
        )

    skill_runs = await _rows(
        db, f"select status, count(*) from runs where {MINE} group by status", tenant=tenant
    )
    for status, number in sorted(skill_runs, key=lambda row: -row[1]):
        into.add(Line(f"skill runs {status}", number, standing="recorded"))
    return into


async def asking(db: AsyncConnection, tenant: str | None, asked: tuple[str, ...]) -> Section:
    into = Section(
        "4. Asking",
        "The read half. A lookup stores nothing by design, so this measures on demand: it"
        " plans each question and resolves the address, and sends NOTHING.",
    )
    entries = await _rows(
        db,
        f"select kind, count(*) from knowledge_entries where {MINE} group by kind",
        tenant=tenant,
    )
    for kind, number in sorted(entries, key=lambda row: -row[1]):
        into.add(Line(f"knowledge: {kind}", number, standing="recorded"))

    if not asked:
        into.add(
            Line(
                "questions planned",
                0,
                standing="none",
                note="pass --questions FILE (one question per line)",
            )
        )
        return into
    if not tenant:
        into.add(Line("questions planned", 0, standing="none", note="--questions needs --tenant"))
        return into

    container = build_container()
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("measure"))

    planned = addressed = stopped = refused = 0
    async with container.unit_of_work() as uow:
        gestures = list(await uow.gestures.gestures_for(TenantId(tenant)))
    for question in asked:
        answer = await container.plan_lookups().execute(ctx, question=question)
        if answer.plan.asks is not None:
            stopped += 1
            continue
        if answer.refused or not answer.plan.lookups:
            refused += 1
            continue
        planned += 1
        if all(address_for(one, gestures) is not None for one in answer.plan.lookups):
            addressed += 1

    into.add(
        Line("questions asked", len(asked), standing="recorded"),
        Line("planned a lookup", planned, len(asked), "recorded"),
        Line(
            "…every target addressable",
            addressed,
            planned or None,
            "recorded",
            note="a plan whose address does not resolve cannot be sent",
        ),
        Line("stopped on an open question", stopped, len(asked), "recorded"),
        Line("refused outright", refused, len(asked), "recorded"),
        Line(
            "answers actually fetched",
            0,
            standing="none",
            note="sending needs the API up and a connected browser; this script sends nothing",
        ),
    )
    return into


async def spending(db: AsyncConnection, tenant: str | None) -> Section:
    into = Section(
        "5. What it cost",
        "Model spend by purpose, and how much of it failed. A loop that improves a number"
        " while doubling the bill has not improved anything.",
    )
    calls = await _rows(
        db,
        "select purpose, count(*), sum(case when failed then 1 else 0 end) from model_calls"
        f" where {MINE} group by purpose",
        tenant=tenant,
    )
    for purpose, number, failures in sorted(calls, key=lambda row: -row[1]):
        into.add(
            Line(f"model calls: {purpose}", number, standing="recorded", note=f"{failures} failed")
        )
    if not calls:
        into.add(Line("model calls recorded", 0, standing="none"))

    for table, label in (("mining_passes", "mining"), ("workflow_runs", "runs"), ("chats", "chat")):
        spent = await _one(
            db, f"select coalesce(sum(cost_usd),0) from {table} where {MINE}", tenant=tenant
        )
        into.add(Line(f"spend on {label}", f"${float(spent):.2f}", standing="recorded"))
    return into


def unmeasured() -> Section:
    into = Section(
        "6. Not measured by anything here",
        "What no number above stands on. This list shrinking is the actual progress metric.",
    )
    into.add(
        Line(
            "a write THIS SYSTEM made in the warehouse",
            "never",
            standing="none",
            note="§1's warehouse writes are the operator's own; APITEST1 is still not created",
        ),
        Line(
            "a lookup that really fetched",
            "never",
            standing="none",
            note="needs API + connected extension; --send has not been run",
        ),
        Line(
            "tab.open against a real Chrome",
            "never",
            standing="none",
            note="node tests only",
        ),
        Line(
            "the panel's answer card, drawn",
            "never",
            standing="none",
            note="rendered in a fake document only",
        ),
        Line(
            "a watch created by a person",
            "never",
            standing="none",
            note="no UI marks a mail; watches exist only as hand-posted JSON",
        ),
        Line(
            "a full day on the real warehouse",
            "never",
            standing="none",
            note="operator-only; everything downstream of it is theory",
        ),
        Line(
            "offers, as the browser really makes them",
            "see replay",
            standing="recorded",
            note="`make offer-replay` scores the matcher over stored walks",
        ),
    )
    return into


def revision() -> str:
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - git is on PATH or it is not
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip() or "unknown"


async def _measure(tenant: str | None, asked: tuple[str, ...]) -> dict[str, object]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as db:
        sections = [
            await evidence(db, tenant),
            await mining(db, tenant),
            await running(db, tenant),
            await asking(db, tenant, asked),
            await spending(db, tenant),
            unmeasured(),
        ]
    await engine.dispose()

    head = f"What this system has done — {tenant or 'every tenant'} — {revision()}"
    print(f"\n{head}\n{'═' * len(head)}")
    print(f"  measured {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    print(
        "  standings: warehouse = a real Blue Yonder host answered · mail = a real mailbox ·"
        "\n             local = a page we serve ourselves · recorded = replayed from stored"
        " evidence\n             none = nothing has ever run this"
    )
    for section in sections:
        print(section.rendered())

    return {
        "revision": revision(),
        "tenant": tenant,
        "measured_at": datetime.now(UTC).isoformat(),
        "sections": [
            {
                "title": section.title,
                "why": section.why,
                "lines": [line.as_json() for line in section.lines],
            }
            for section in sections
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default=None, help="one tenant; every tenant by default")
    parser.add_argument("--questions", type=Path, default=None, help="one question per line")
    parser.add_argument("--json", dest="out", type=Path, default=None, help="write the report too")
    args = parser.parse_args()
    asked = (
        tuple(
            line.strip()
            for line in args.questions.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        )
        if args.questions is not None and args.questions.is_file()
        else ()
    )
    report = asyncio.run(_measure(args.tenant, asked))
    if args.out is not None:
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"  written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
