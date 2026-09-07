"""One day of real evidence, put to several models, side by side.

The rig runs on Gemini and every number it has ever produced is a number about
Gemini. This asks the other question: on the SAME evidence, through the SAME
doors, what does each model cost, how long does it take, and how good is what
comes back.

Two doors, because they are the two shapes of call the rig makes and they
answer differently:

- **read** -- one small call per gesture, hundreds a day. Latency and price per
  call dominate, and the quality question is how many readings came back with
  an `act` a pass can use. A model that answers cheaply and uselessly is the
  failure a cost column alone reports as a win.
- **mine** -- one large call over a window of a day's evidence. Price per call
  is the whole bill, and the quality question is what it found: how many
  workflows it proposed, how many survived the checks, and how many stand on
  evidence from more than one system.

Every model gets its own copy of the store, so no run can see another's
writings and every run starts from byte-identical evidence. The sweep's own
rows are written to the store the API serves, which is never mined here: a
comparison must not leave workflows behind.

Money is real. `budget_usd` is a ceiling on the whole sweep, checked before
each door, and a door skipped for want of budget says so in its row rather
than being missing.
"""

import asyncio
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rig.mine import mine
from rig.models import Answer, Asker
from rig.store import Store
from rig.workflows import cited_ids, known_workflows

DOORS = ("read", "mine")

K_READ_GESTURES = 20
"""How many gestures the read door reads, by default. Small on purpose: the
per-call numbers converge quickly and the whole day is what the mine door is
for. Capped at 200 because the reading loop's own query is."""


@dataclass(frozen=True, slots=True)
class Row:
    """One door of one model. What the page draws, and what the store keeps."""

    sweep_id: str
    tenant: str
    model: str
    door: str
    at: str
    calls: int = 0
    seconds: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    slowest_ms: float = 0.0
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: int = 0
    refused: int = 0
    gestures: int | None = None
    usable: int | None = None
    proposed: int | None = None
    kept: int | None = None
    cross_system: int | None = None
    coverage: float | None = None
    skew: float | None = None
    lopsided: bool | None = None
    error: str | None = None


@dataclass
class Timed:
    """An asker that records what every call cost and how long it took.

    Wall clock per call, not per door: the read door is serialised across
    models by the rig's own process-wide reading lock, so a door's elapsed time
    is not comparable between models while a single call's always is.
    """

    inner: Asker
    calls: list[tuple[float, Answer]] = field(default_factory=list)

    async def ask(self, **asked: Any) -> Answer:
        started = time.perf_counter()
        answer = await self.inner.ask(**asked)
        self.calls.append(((time.perf_counter() - started) * 1000.0, answer))
        return answer

    def since(self, mark: int) -> list[tuple[float, Answer]]:
        return self.calls[mark:]


def percentile(values: list[float], share: float) -> float:
    """The value at `share` through the sorted list, nearest-rank.

    Nearest-rank rather than interpolated: at twenty calls an interpolated p95
    invents a number between two real ones, and every figure on this page is
    meant to be something that actually happened.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(-(-share * len(ordered) // 1))))
    return ordered[rank - 1]


def _bill(calls: list[tuple[float, Answer]]) -> dict[str, Any]:
    latencies = [ms for ms, _ in calls]
    return {
        "calls": len(calls),
        "p50_ms": round(percentile(latencies, 0.50), 1),
        "p95_ms": round(percentile(latencies, 0.95), 1),
        "slowest_ms": round(max(latencies), 1) if latencies else 0.0,
        "in_tokens": sum(a.in_tokens for _, a in calls),
        "out_tokens": sum(a.out_tokens for _, a in calls),
        "thought_tokens": sum(a.thought_tokens for _, a in calls),
        "cost_usd": round(sum(a.cost_usd for _, a in calls), 6),
        "unpriced": sum(1 for _, a in calls if a.unpriced),
        "refused": sum(1 for _, a in calls if a.error),
    }


def copy_store(source: Path, target: Path) -> Store:
    """A byte-identical starting point, WAL included -- a plain file copy takes
    the database without whatever is still sitting in its write-ahead log."""
    target.unlink(missing_ok=True)
    origin = sqlite3.connect(source)
    copy = sqlite3.connect(target)
    with copy:
        origin.backup(copy)
    origin.close()
    copy.close()
    store = Store(target)
    store.migrate()
    return store


def forget_readings(store: Store, tenant: str, gestures: int) -> int:
    """Drop the readings of the oldest `gestures` gestures, and say how many.

    So every model reads the SAME evidence rather than whatever nobody had got
    to yet. The rest of the day keeps its readings, because the mine door needs
    a day of intents to work from and re-reading all of them would be the read
    door's bill several times over.
    """
    ids = [
        str(row["id"])
        for row in store.query(
            "SELECT id FROM gestures WHERE tenant = ? ORDER BY at LIMIT ?",
            (tenant, max(0, min(gestures, 200))),
        )
    ]
    for gesture_id in ids:
        store.execute("DELETE FROM intents WHERE gesture_id = ?", (gesture_id,))
    return len(ids)


def _usable(store: Store, tenant: str, ids: Iterable[str]) -> int:
    """Readings that came back with an act. The mining prompt is built out of
    `act`; a reading without one is a row that was paid for and cannot be
    used."""
    wanted = set(ids)
    return sum(
        1
        for row in store.query(
            "SELECT gesture_id, act, error FROM intents WHERE tenant = ?", (tenant,)
        )
        if row["gesture_id"] in wanted and row["act"] and not row["error"]
    )


@dataclass
class Purse:
    """What the whole sweep may spend, and what it has.

    One event loop, so `spend` is only ever touched between awaits and needs no
    lock. A door that would start over the ceiling is skipped and says so --
    stopping a sweep silently is how a comparison ends up with three models in
    it and a fourth nobody noticed was missing.

    The ceiling is not a hard stop, and the arithmetic is worth stating: the
    models run at once, so every model's first door starts before any of them
    has recorded what it spent. A sweep of five models can therefore overshoot
    by up to five doors' worth. It is a budget, not a fuse -- the fuse is that
    a sweep is a command somebody types.
    """

    budget_usd: float
    spent: float = 0.0

    def over(self) -> bool:
        return self.budget_usd >= 0 and self.spent >= self.budget_usd


async def one_model(
    *,
    source: Path,
    out: Path,
    model: str,
    asker: Asker,
    tenant: str,
    sweep_id: str,
    gestures: int,
    purse: Purse,
    doors: tuple[str, ...] = DOORS,
) -> list[Row]:
    """Both doors, one model, on its own copy of the evidence."""
    from rig.api import read_new_gestures

    now = datetime.now(tz=UTC).isoformat()
    store = copy_store(source, out / f"{model.replace('.', '-')}.db")
    timed = Timed(asker)
    rows: list[Row] = []

    if "read" in doors:
        wanted = [
            str(row["id"])
            for row in store.query(
                "SELECT id FROM gestures WHERE tenant = ? ORDER BY at LIMIT ?",
                (tenant, max(0, min(gestures, 200))),
            )
        ]
        forget_readings(store, tenant, gestures)
        if purse.over():
            rows.append(
                Row(sweep_id, tenant, model, "read", now, error="skipped: over the sweep's budget")
            )
        else:
            mark, began = len(timed.calls), time.perf_counter()
            read = await read_new_gestures(store, timed, model, tenant)
            calls = timed.since(mark)
            purse.spent += sum(a.cost_usd for _, a in calls)
            rows.append(
                Row(
                    sweep_id,
                    tenant,
                    model,
                    "read",
                    now,
                    seconds=round(time.perf_counter() - began, 3),
                    gestures=read,
                    usable=_usable(store, tenant, wanted),
                    **_bill(calls),
                )
            )

    if "mine" in doors:
        if purse.over():
            rows.append(
                Row(sweep_id, tenant, model, "mine", now, error="skipped: over the sweep's budget")
            )
            return rows
        mark, began = len(timed.calls), time.perf_counter()
        result = await mine(store, tenant=tenant, asker=timed, model=model, kb="")
        calls = timed.since(mark)
        purse.spent += sum(a.cost_usd for _, a in calls)
        systems = {
            str(row["id"]): str(row["system"] or "")
            for row in store.query("SELECT id, system FROM gestures WHERE tenant = ?", (tenant,))
        }
        kept = [w for w in known_workflows(store, tenant) if w.pass_id == result.pass_id]
        rows.append(
            Row(
                sweep_id,
                tenant,
                model,
                "mine",
                now,
                seconds=round(time.perf_counter() - began, 3),
                proposed=result.proposed,
                kept=result.kept,
                # The one number this whole architecture was built to produce:
                # a job that stands on evidence from more than one system, which
                # a per-host pipeline structurally cannot see.
                cross_system=sum(
                    1 for w in kept if len({systems[c] for c in cited_ids(w) if systems.get(c)}) > 1
                ),
                coverage=round(result.coverage.coverage, 4),
                skew=round(result.coverage.skew, 4),
                lopsided=result.lopsided,
                error=result.error,
                **_bill(calls),
            )
        )
    return rows


async def sweep(
    *,
    source: Path,
    out: Path,
    models: tuple[str, ...],
    asker_for: Callable[[str], Asker],
    tenant: str,
    gestures: int = K_READ_GESTURES,
    budget_usd: float = 5.0,
    doors: tuple[str, ...] = DOORS,
    sweep_id: str = "",
) -> list[Row]:
    """Every model at once, each on its own copy. One model failing outright
    does not take the sweep with it: its rows carry the error instead."""
    sweep_id = sweep_id or "swp_" + secrets.token_hex(8)
    out.mkdir(parents=True, exist_ok=True)
    purse = Purse(budget_usd)
    now = datetime.now(tz=UTC).isoformat()

    async def guarded(model: str) -> list[Row]:
        try:
            return await one_model(
                source=source,
                out=out,
                model=model,
                asker=asker_for(model),
                tenant=tenant,
                sweep_id=sweep_id,
                gestures=gestures,
                purse=purse,
                doors=doors,
            )
        except Exception as problem:  # noqa: BLE001 -- one model's failure is one model's row
            return [
                Row(
                    sweep_id,
                    tenant,
                    model,
                    door,
                    now,
                    error=f"{type(problem).__name__}: {problem}",
                )
                for door in doors
            ]

    gathered = await asyncio.gather(*(guarded(model) for model in models))
    return [row for rows in gathered for row in rows]


def save(store: Store, rows: list[Row]) -> None:
    """The sweep's rows go to the store the API serves, so the page can read a
    comparison the sweep itself ran somewhere else."""
    with store.connect() as connection:
        for row in rows:
            connection.execute(
                "INSERT INTO bakeoff (id, sweep_id, tenant, model, door, at, calls, seconds,"
                " p50_ms, p95_ms, slowest_ms, in_tokens, out_tokens, thought_tokens, cost_usd,"
                " unpriced, refused, gestures, usable, proposed, kept, cross_system, coverage,"
                " skew, lopsided, error)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?)",
                (
                    "bko_" + secrets.token_hex(8),
                    row.sweep_id,
                    row.tenant,
                    row.model,
                    row.door,
                    row.at,
                    row.calls,
                    row.seconds,
                    row.p50_ms,
                    row.p95_ms,
                    row.slowest_ms,
                    row.in_tokens,
                    row.out_tokens,
                    row.thought_tokens,
                    row.cost_usd,
                    row.unpriced,
                    row.refused,
                    row.gestures,
                    row.usable,
                    row.proposed,
                    row.kept,
                    row.cross_system,
                    row.coverage,
                    row.skew,
                    None if row.lopsided is None else int(row.lopsided),
                    row.error,
                ),
            )
