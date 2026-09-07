"""The bake-off harness, without spending anything.

Every test here runs through `FakeAsker`, so what is under test is the harness:
that each model works on its own copy of the evidence, that the bill and the
latencies are the ones the calls actually produced, that a model that falls
over does not take the sweep with it, and that a ceiling on the spend is a
ceiling. The models themselves are compared by `scripts/bakeoff.py`, with real
keys and real money, and nothing here asks a vendor anything.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from rig.bakeoff import (
    Purse,
    Row,
    Timed,
    _bill,
    burst,
    copy_store,
    forget_readings,
    percentile,
    save,
    sweep,
)
from rig.models import Answer, Asker, FakeAsker
from rig.store import Store

TENANT = "acme"


def _store(path: Path) -> Store:
    store = Store(path)
    store.migrate()
    return store


def _gestures(store: Store, how_many: int, *, read_from: int = 0) -> None:
    """`how_many` gestures, the first `read_from` of them already read."""
    for index in range(how_many):
        store.execute(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, system, gesture_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"ges_{index:03d}",
                TENANT,
                "dev_one",
                "bat_one",
                1000.0 + index,
                "https://wms.example.com",
                json.dumps({"kind": "click", "target": None, "value": "", "at": 1000.0 + index}),
            ),
        )
    for index in range(read_from):
        store.execute(
            "INSERT INTO intents (gesture_id, tenant, act, created_at) VALUES (?, ?, ?, ?)",
            (f"ges_{index:03d}", TENANT, "picked", "2026-09-07T00:00:00+00:00"),
        )


class Slow:
    """An asker that takes a known amount of time, so a latency assertion is
    about the harness rather than about how fast this machine is today."""

    def __init__(self, seconds: float, answer: Answer) -> None:
        self.seconds, self.answer = seconds, answer

    async def ask(self, **_: Any) -> Answer:
        await asyncio.sleep(self.seconds)
        return self.answer


class Angry:
    """An asker that raises rather than answering: an SDK that cannot reach the
    vendor at all, which is not the same as a model that refused."""

    async def ask(self, **_: Any) -> Answer:
        raise RuntimeError("no route to the vendor")


def test_the_middle_and_the_tail_are_calls_that_actually_happened() -> None:
    assert percentile([], 0.5) == 0.0
    assert percentile([10.0], 0.95) == 10.0
    # Nearest-rank: every figure is one of the inputs, never a number between
    # two of them.
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0


async def test_a_timed_asker_records_the_bill_and_the_wait() -> None:
    timed = Timed(Slow(0.02, Answer(data={"act": "picked"}, in_tokens=10, out_tokens=4)))

    await timed.ask(model="m", instructions="", evidence="e", schema={})

    (waited, answer), *rest = timed.calls
    assert not rest
    assert answer.in_tokens == 10
    assert waited >= 20.0, "the wait is milliseconds, and it is the call's own"


async def test_each_model_reads_the_same_evidence_on_its_own_copy(tmp_path: Path) -> None:
    """The point of the copies. Two models that shared a store would race on
    the intents table and the second would find the first's readings already
    there -- and report a day that cost nothing."""
    source = tmp_path / "source.db"
    _store(source)
    _gestures(_store(source), 4)

    rows = await sweep(
        source=source,
        out=tmp_path / "out",
        models=("one", "two"),
        asker_for=lambda _: FakeAsker(*[Answer(data={"act": "picked"}) for _ in range(8)]),
        tenant=TENANT,
        gestures=4,
        doors=("read",),
    )

    assert [row.gestures for row in rows] == [4, 4], "both models read all four"
    assert {row.model for row in rows} == {"one", "two"}
    # The source is never written: it is what every later sweep starts from.
    assert not Store(source).query("SELECT gesture_id FROM intents WHERE tenant = ?", (TENANT,))


async def test_a_reading_with_no_act_is_paid_for_and_not_usable(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _gestures(_store(source), 3)

    rows = await sweep(
        source=source,
        out=tmp_path / "out",
        models=("one",),
        asker_for=lambda _: FakeAsker(
            Answer(data={"act": "picked"}, in_tokens=100, out_tokens=10),
            Answer(data={}, in_tokens=100, out_tokens=2),
            Answer(error="the model returned no text", in_tokens=100),
        ),
        tenant=TENANT,
        gestures=3,
        doors=("read",),
    )

    row = rows[0]
    assert row.gestures == 3, "three were asked"
    assert row.usable == 1, "one came back with an act a pass could use"
    assert row.refused == 1
    assert row.calls == 3


async def test_a_vendor_that_cannot_be_reached_is_one_row_not_a_dead_sweep(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    _gestures(_store(source), 2)

    rows = await sweep(
        source=source,
        out=tmp_path / "out",
        models=("angry", "fine"),
        asker_for=lambda model: (
            Angry()
            if model == "angry"
            else FakeAsker(*[Answer(data={"act": "picked"}) for _ in range(4)])
        ),
        tenant=TENANT,
        gestures=2,
        doors=("read",),
    )

    angry = [row for row in rows if row.model == "angry"]
    fine = [row for row in rows if row.model == "fine"]
    assert angry and angry[0].error and "no route to the vendor" in angry[0].error
    assert fine and fine[0].gestures == 2, "the other model still ran"


async def test_a_door_that_would_start_over_the_budget_says_so(tmp_path: Path) -> None:
    """Skipped, and visible. A sweep that quietly stopped after two models
    leaves a page comparing two models and no sign the third was meant to be
    there."""
    source = tmp_path / "source.db"
    _gestures(_store(source), 2)
    costly = Answer(data={"act": "picked"}, in_tokens=1_000_000, out_tokens=1_000_000, cost_usd=6.0)

    rows = await sweep(
        source=source,
        out=tmp_path / "out",
        models=("spendy",),
        asker_for=lambda _: FakeAsker(costly, costly),
        tenant=TENANT,
        gestures=2,
        budget_usd=5.0,
        doors=("read", "mine"),
    )

    read, mine_row = rows[0], rows[1]
    assert read.gestures == 2, "the first door runs; the budget is checked before a door"
    assert mine_row.error == "skipped: over the sweep's budget"
    assert mine_row.calls == 0


def test_the_purse_with_no_ceiling_never_closes() -> None:
    assert Purse(-1.0, spent=99.0).over() is False
    assert Purse(1.0, spent=1.0).over() is True


def test_only_the_oldest_readings_are_forgotten(tmp_path: Path) -> None:
    """The read door re-reads the same evidence for every model; the rest of
    the day keeps its readings, because the mine door needs them and paying to
    re-read a whole day per model is the read door's bill several times over."""
    store = _store(tmp_path / "rig.db")
    _gestures(store, 5, read_from=5)

    forgotten = forget_readings(store, TENANT, 2)

    left = {row["gesture_id"] for row in store.query("SELECT gesture_id FROM intents", ())}
    assert forgotten == 2
    assert left == {"ges_002", "ges_003", "ges_004"}


def test_a_copy_starts_where_the_original_is_and_goes_its_own_way(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _gestures(_store(source), 2)

    copy = copy_store(source, tmp_path / "copy.db")
    copy.execute("DELETE FROM gestures WHERE id = ?", ("ges_000",))

    assert len(Store(source).query("SELECT id FROM gestures", ())) == 2
    assert len(copy.query("SELECT id FROM gestures", ())) == 1


def test_a_sweeps_rows_are_readable_after_it_is_over(tmp_path: Path) -> None:
    store = _store(tmp_path / "rig.db")

    save(
        store,
        [
            Row("swp_1", TENANT, "one", "read", "2026-09-07T00:00:00+00:00", calls=3, p50_ms=120.0),
            Row("swp_1", TENANT, "one", "mine", "2026-09-07T00:00:01+00:00", kept=2, lopsided=True),
        ],
    )

    rows = store.query("SELECT * FROM bakeoff WHERE tenant = ? ORDER BY door", (TENANT,))
    assert [row["door"] for row in rows] == ["mine", "read"]
    assert rows[0]["kept"] == 2
    assert rows[0]["lopsided"] == 1
    assert rows[1]["p50_ms"] == 120.0
    # Every row of one sweep can be found by the id the sweep minted.
    assert {row["sweep_id"] for row in rows} == {"swp_1"}


def test_the_harness_asks_through_the_port_and_nothing_else() -> None:
    """`Timed` is what every door holds, so it has to BE an Asker. If it drifts
    from the protocol the doors stop compiling, and this says so first."""
    timed: Asker = Timed(FakeAsker())
    assert timed is not None


async def test_the_burst_door_says_how_much_the_vendor_really_did_at_once() -> None:
    """Eight calls of a tenth of a second each. Served together, the burst
    takes about a tenth of a second and the speedup is near eight; served one
    after another it takes eight tenths and the speedup is one. That number is
    the one a vendor's own latency figures never answer."""
    calls, elapsed = await burst(
        Slow(0.1, Answer(data={"word": "yes"}, in_tokens=8, out_tokens=1)), "m", calls=8
    )

    waited = sum(ms for ms, _ in calls) / 1000.0
    assert len(calls) == 8
    assert elapsed < 0.5, "eight tenths of a second means they were serialised"
    assert waited / elapsed > 4.0


def test_an_answer_cut_off_by_the_ceiling_is_counted_apart_from_a_refusal() -> None:
    """A ceiling the answer ran into says the model had more to say and the
    budget stopped it. Filed with refusals, the one number that would tell you
    to raise the ceiling is invisible."""
    billed = _bill(
        [
            (10.0, Answer(error="truncated: the answer hit the 65536 output-token ceiling")),
            (10.0, Answer(error="not json: Expecting value")),
            (10.0, Answer(data={"act": "picked"})),
        ]
    )

    assert billed["refused"] == 2
    assert billed["truncated"] == 1
    assert billed["fastest_ms"] == 10.0


async def test_a_second_pass_over_the_same_day_is_what_stability_means(
    tmp_path: Path,
) -> None:
    """The mine door reads the day twice and reports how much of what the first
    pass cited the second cited too. Both passes are on the row -- `calls` says
    two -- because a total that left the second pass's money off would be a
    total nobody could reconcile with the invoice."""
    source = tmp_path / "source.db"
    store = _store(source)
    _gestures(store, 3, read_from=3)

    rows = await sweep(
        source=source,
        out=tmp_path / "out",
        models=("one",),
        asker_for=lambda _: FakeAsker(
            Answer(data={"workflows": []}, cost_usd=0.01),
            Answer(data={"workflows": []}, cost_usd=0.01),
        ),
        tenant=TENANT,
        doors=("mine",),
        twice=True,
    )

    row = rows[0]
    assert row.calls == 2, "both passes are on the row"
    assert row.cost_usd == 0.02, "and so is both passes' money"
    assert row.second_kept == 0
    assert row.window is not None and row.left_out is not None
