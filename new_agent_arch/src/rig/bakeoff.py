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

DOORS = ("read", "mine", "burst")

K_BURST = 8
"""How many calls the burst door fires at once. Eight because that is the shape
the rig actually makes: a run plans one step at a time, but a reading loop over
a busy morning and a page full of parked runs both put several small calls in
flight together, and a vendor that serialises them or starts refusing is a
vendor whose per-call latency was never the whole story."""

K_READ_GESTURES = 0
"""How many gestures the read door reads. Zero means the whole day, which is
the comparison worth having: every model reads every gesture, so what they made
of the same evidence can be put side by side. A number reads that many of the
oldest, for a cheaper look at the same shape."""


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
    fastest_ms: float = 0.0
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: int = 0
    refused: int = 0
    truncated: int = 0
    gestures: int | None = None
    usable: int | None = None
    window: int | None = None
    left_out: int | None = None
    proposed: int | None = None
    kept: int | None = None
    rejected: int | None = None
    cross_system: int | None = None
    speedup: float | None = None
    coverage: float | None = None
    skew: float | None = None
    gini: float | None = None
    lopsided: bool | None = None
    stability: float | None = None
    """Two passes over the same evidence, and how much of what the first one
    cited the second one cited too (Jaccard). A model that finds a different
    day every time it reads the same day is not a model anyone can build a
    schedule on, and no single pass can show it."""
    second_kept: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Reading:
    """What one model made of one gesture. The row a disagreement is found in."""

    sweep_id: str
    tenant: str
    model: str
    gesture_id: str
    act: str | None = None
    object: str | None = None
    page: str | None = None
    confidence: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
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
        "fastest_ms": round(min(latencies), 1) if latencies else 0.0,
        "in_tokens": sum(a.in_tokens for _, a in calls),
        "out_tokens": sum(a.out_tokens for _, a in calls),
        "thought_tokens": sum(a.thought_tokens for _, a in calls),
        "cost_usd": round(sum(a.cost_usd for _, a in calls), 6),
        "unpriced": sum(1 for _, a in calls if a.unpriced),
        "refused": sum(1 for _, a in calls if a.error),
        # A ceiling the answer ran into is not the same failure as a refusal
        # or a malformed one: it says the model had more to say and the
        # budget stopped it, which is a different decision to make.
        "truncated": sum(1 for _, a in calls if a.error and "truncated" in a.error),
    }


BURST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"word": {"type": "string"}},
    "required": ["word"],
}

BURST_EVIDENCE = "Answer with the single word: yes."


async def burst(
    asker: Asker, model: str, *, calls: int
) -> tuple[list[tuple[float, Answer]], float]:
    """`calls` of the smallest possible call, all in flight at once.

    The smallest call on purpose: what is being measured is the vendor's
    behaviour under concurrency, not the model's reasoning, and a large prompt
    would hide the queueing behind its own generation time.
    """
    timed = Timed(asker)

    async def one() -> None:
        await timed.ask(model=model, instructions="", evidence=BURST_EVIDENCE, schema=BURST_SCHEMA)

    began = time.perf_counter()
    await asyncio.gather(*(one() for _ in range(calls)))
    return timed.calls, time.perf_counter() - began


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


def _oldest(store: Store, tenant: str, gestures: int) -> list[str]:
    """The oldest `gestures` gesture ids, or all of them when it is zero."""
    sql = "SELECT id FROM gestures WHERE tenant = ? ORDER BY at"
    rows = (
        store.query(sql, (tenant,))
        if gestures <= 0
        else store.query(sql + " LIMIT ?", (tenant, gestures))
    )
    return [str(row["id"]) for row in rows]


def forget_readings(store: Store, tenant: str, gestures: int) -> int:
    """Drop the readings of the oldest `gestures` gestures, and say how many.

    So every model reads the SAME evidence rather than whatever nobody had got
    to yet. The rest of the day keeps its readings, because the mine door needs
    a day of intents to work from and re-reading all of them would be the read
    door's bill several times over.
    """
    ids = _oldest(store, tenant, gestures)
    for gesture_id in ids:
        store.execute("DELETE FROM intents WHERE gesture_id = ?", (gesture_id,))
    return len(ids)


def _readings(
    store: Store, sweep_id: str, tenant: str, model: str, ids: list[str]
) -> list[Reading]:
    """Every reading this model just made, as rows a comparison can be run over.

    Read back out of the copy's own `intents` table rather than held in memory
    from the loop: what is compared has to be what was stored, and the reading
    loop's own rules about a malformed answer -- an `act` of the wrong type is
    nulled, an error is kept -- are applied on the way in.
    """
    wanted = set(ids)
    return [
        Reading(
            sweep_id=sweep_id,
            tenant=tenant,
            model=model,
            gesture_id=str(row["gesture_id"]),
            act=row["act"],
            object=row["object"],
            page=row["page"],
            confidence=row["confidence"],
            in_tokens=row["in_tokens"],
            out_tokens=row["out_tokens"],
            thought_tokens=row["thought_tokens"],
            cost_usd=row["cost_usd"],
            error=row["error"],
        )
        for row in store.query(
            "SELECT gesture_id, act, object, page, confidence, in_tokens, out_tokens,"
            " thought_tokens, cost_usd, error FROM intents WHERE tenant = ?",
            (tenant,),
        )
        if str(row["gesture_id"]) in wanted
    ]


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
    bursts: int = K_BURST,
    twice: bool = True,
    doors: tuple[str, ...] = DOORS,
) -> tuple[list[Row], list[Reading]]:
    """Every door, one model, on its own copy of the evidence."""
    from rig.api import read_new_gestures

    now = datetime.now(tz=UTC).isoformat()
    store = copy_store(source, out / f"{model.replace('.', '-')}.db")
    timed = Timed(asker)
    rows: list[Row] = []
    readings: list[Reading] = []

    if "read" in doors:
        wanted = _oldest(store, tenant, gestures)
        forget_readings(store, tenant, gestures)
        if purse.over():
            rows.append(
                Row(sweep_id, tenant, model, "read", now, error="skipped: over the sweep's budget")
            )
        else:
            mark, began = len(timed.calls), time.perf_counter()
            # The reading loop takes 200 at a time, which is its own query's
            # limit and not a budget. A day is bigger than that, and a door
            # that stopped at 200 would compare the models on the morning.
            read = 0
            while True:
                this_pass = await read_new_gestures(store, timed, model, tenant)
                read += this_pass
                if this_pass == 0 or (gestures > 0 and read >= gestures):
                    break
            calls = timed.since(mark)
            purse.spent += sum(a.cost_usd for _, a in calls)
            readings.extend(_readings(store, sweep_id, tenant, model, wanted))
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

    if "burst" in doors:
        if purse.over():
            rows.append(
                Row(sweep_id, tenant, model, "burst", now, error="skipped: over the sweep's budget")
            )
        else:
            calls, elapsed = await burst(asker, model, calls=bursts)
            purse.spent += sum(a.cost_usd for _, a in calls)
            waited = sum(ms for ms, _ in calls) / 1000.0
            rows.append(
                Row(
                    sweep_id,
                    tenant,
                    model,
                    "burst",
                    now,
                    seconds=round(elapsed, 3),
                    # Time the calls spent waiting, over the time the burst
                    # took: 8.0 means eight calls truly ran at once, 1.0 means
                    # the vendor served them one after another however they
                    # were sent. The number the vendor's own docs never say.
                    speedup=round(waited / elapsed, 2) if elapsed > 0 else None,
                    **_bill(calls),
                )
            )

    if "mine" in doors:
        if purse.over():
            rows.append(
                Row(sweep_id, tenant, model, "mine", now, error="skipped: over the sweep's budget")
            )
            return rows, readings
        mark, began = len(timed.calls), time.perf_counter()
        result = await mine(store, tenant=tenant, asker=timed, model=model, kb="")
        calls = timed.since(mark)
        purse.spent += sum(a.cost_usd for _, a in calls)
        systems = {
            str(row["id"]): str(row["system"] or "")
            for row in store.query("SELECT id, system FROM gestures WHERE tenant = ?", (tenant,))
        }
        kept = [w for w in known_workflows(store, tenant) if w.pass_id == result.pass_id]
        cited = {c for w in kept for c in cited_ids(w)}

        # The same evidence, a second time. Whether a model finds the same day
        # twice is a property no single pass can report, and it decides whether
        # anything downstream can be scheduled on it.
        stability: float | None = None
        second_kept: int | None = None
        if twice and not result.error:
            second_mark = len(timed.calls)
            again = await mine(store, tenant=tenant, asker=timed, model=model, kb="")
            second = [w for w in known_workflows(store, tenant) if w.pass_id == again.pass_id]
            twice_cited = {c for w in second for c in cited_ids(w)}
            both = cited | twice_cited
            stability = round(len(cited & twice_cited) / len(both), 4) if both else None
            second_kept = again.kept
            purse.spent += sum(a.cost_usd for _, a in timed.since(second_mark))
            # The row covers the whole door, both passes: `calls` says 2, and a
            # per-pass figure is that divided by it. Reporting only the first
            # pass would leave the second one's money off every total.
            calls = timed.since(mark)

        rows.append(
            Row(
                sweep_id,
                tenant,
                model,
                "mine",
                now,
                seconds=round(time.perf_counter() - began, 3),
                window=result.window_size,
                left_out=result.left_out,
                proposed=result.proposed,
                kept=result.kept,
                rejected=len(result.rejections),
                # The one number this whole architecture was built to produce:
                # a job that stands on evidence from more than one system, which
                # a per-host pipeline structurally cannot see.
                cross_system=sum(
                    1 for w in kept if len({systems[c] for c in cited_ids(w) if systems.get(c)}) > 1
                ),
                coverage=round(result.coverage.coverage, 4),
                skew=round(result.coverage.skew, 4),
                gini=round(result.coverage.gini, 4),
                lopsided=result.lopsided,
                stability=stability,
                second_kept=second_kept,
                error=result.error,
                **_bill(calls),
            )
        )
    return rows, readings


async def sweep(
    *,
    source: Path,
    out: Path,
    models: tuple[str, ...],
    asker_for: Callable[[str], Asker],
    tenant: str,
    gestures: int = K_READ_GESTURES,
    bursts: int = K_BURST,
    twice: bool = True,
    budget_usd: float = 5.0,
    doors: tuple[str, ...] = DOORS,
    sweep_id: str = "",
) -> tuple[list[Row], list[Reading]]:
    """Every model at once, each on its own copy. One model failing outright
    does not take the sweep with it: its rows carry the error instead."""
    sweep_id = sweep_id or "swp_" + secrets.token_hex(8)
    out.mkdir(parents=True, exist_ok=True)
    purse = Purse(budget_usd)
    now = datetime.now(tz=UTC).isoformat()

    async def guarded(model: str) -> tuple[list[Row], list[Reading]]:
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
                bursts=bursts,
                twice=twice,
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
            ], []

    gathered = await asyncio.gather(*(guarded(model) for model in models))
    return (
        [row for rows, _ in gathered for row in rows],
        [reading for _, readings in gathered for reading in readings],
    )


def save_readings(store: Store, readings: list[Reading]) -> None:
    """Every model's reading of every gesture, so the page can show where two
    models saw the same gesture differently."""
    with store.connect() as connection:
        for reading in readings:
            connection.execute(
                "INSERT OR REPLACE INTO bakeoff_readings (sweep_id, tenant, model, gesture_id,"
                " act, object, page, confidence, in_tokens, out_tokens, thought_tokens,"
                " cost_usd, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    reading.sweep_id,
                    reading.tenant,
                    reading.model,
                    reading.gesture_id,
                    reading.act,
                    reading.object,
                    reading.page,
                    reading.confidence,
                    reading.in_tokens,
                    reading.out_tokens,
                    reading.thought_tokens,
                    reading.cost_usd,
                    reading.error,
                ),
            )


def save(store: Store, rows: list[Row]) -> None:
    """The sweep's rows go to the store the API serves, so the page can read a
    comparison the sweep itself ran somewhere else."""
    with store.connect() as connection:
        for row in rows:
            connection.execute(
                "INSERT INTO bakeoff (id, sweep_id, tenant, model, door, at, calls, seconds,"
                " p50_ms, p95_ms, slowest_ms, fastest_ms, in_tokens, out_tokens, thought_tokens,"
                " cost_usd, unpriced, refused, truncated, gestures, usable, speedup, window,"
                " left_out, proposed, kept, rejected, cross_system, coverage, skew, gini,"
                " lopsided, stability, second_kept, error)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    row.fastest_ms,
                    row.in_tokens,
                    row.out_tokens,
                    row.thought_tokens,
                    row.cost_usd,
                    row.unpriced,
                    row.refused,
                    row.truncated,
                    row.gestures,
                    row.usable,
                    row.speedup,
                    row.window,
                    row.left_out,
                    row.proposed,
                    row.kept,
                    row.rejected,
                    row.cross_system,
                    row.coverage,
                    row.skew,
                    row.gini,
                    None if row.lopsided is None else int(row.lopsided),
                    row.stability,
                    row.second_kept,
                    row.error,
                ),
            )
