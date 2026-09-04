import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from rig.api import save_batch
from rig.mine import mine
from rig.models import Answer, FakeAsker
from rig.pool import pool_ids
from rig.store import Store
from rig.wire import Batch
from rig.workflows import known_workflows
from tests.fixtures import BATCH


def _store(tmp_path: Path) -> Store:
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = Store(tmp_path / "rig.db")
    store.migrate()
    save_batch(store, Batch.model_validate(BATCH), "acme")
    return store


def _ids(store: Store) -> list[str]:
    return [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]


def _proposal(cites: list[str], **over: Any) -> dict[str, Any]:
    base = {
        "title": "create a work operation",
        "narrative": "the operator created a work operation",
        "systems": ["http://127.0.0.1:63319"],
        "steps": [
            {
                "order": 0,
                "cites": cites,
                "says": "do it",
                "system": "http://127.0.0.1:63319",
                "parameters": [],
            }
        ],
        "parameters": [],
        "same_as": None,
        "unproven": [],
    }
    return {**base, **over}


async def test_a_pass_keeps_what_it_can_prove(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(
        Answer(
            data={"workflows": [_proposal(ids[:2])]}, in_tokens=900, out_tokens=100, cost_usd=0.01
        )
    )

    result = await mine(store, tenant="acme", asker=asker, model="gemini-3.1-pro")

    assert result.kept == 1
    assert result.rejections == []
    assert len(known_workflows(store, "acme")) == 1


async def test_a_workflow_citing_evidence_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asker = FakeAsker(Answer(data={"workflows": [_proposal(["ges_invented"])]}, cost_usd=0.01))

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.kept == 0
    assert len(result.rejections) == 1
    assert result.rejections[0].reason == "unknown gesture"
    assert known_workflows(store, "acme") == []


async def test_a_workflow_naming_a_system_its_evidence_never_touched_is_refused(
    tmp_path: Path,
) -> None:
    """The one lie this architecture cannot afford: a cross-system job whose
    second system is invented. It is the reason validate() takes the system of
    every cited gesture rather than the set of ids, and the loop must hand it
    that mapping -- a set of ids passes the citation check and cannot fail
    this one."""
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(
        Answer(
            data={"workflows": [_proposal(ids[:2], systems=["http://sap.example"])]},
            cost_usd=0.01,
        )
    )

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.kept == 0
    assert result.rejections[0].reason == "system not in evidence"


async def test_everything_the_pass_did_not_cite_lands_in_the_pool(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:1])]}, cost_usd=0.01))

    await mine(store, tenant="acme", asker=asker, model="m")

    assert set(pool_ids(store, "acme")) == set(ids[1:])


async def test_the_pool_ages_once_a_pass_and_not_twice(tmp_path: Path) -> None:
    """K_POOL_AGE counts passes. An entry that entered on this pass has sat
    through exactly one of them."""
    store = _store(tmp_path)
    asker = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.01))

    await mine(store, tenant="acme", asker=asker, model="m")

    ages = {row["age"] for row in store.query("SELECT age FROM pool WHERE tenant = 'acme'")}
    assert ages == {1}


async def test_a_pooled_gesture_whose_row_is_gone_is_named_not_dropped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """pool_ids returns ids; the window takes evidence. A pooled id that joins
    to no gesture row would otherwise leave the pass through a comprehension
    filter, and the number of gestures read would simply be smaller than the
    pool said."""
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(
        Answer(data={"workflows": []}, cost_usd=0.01),
        Answer(data={"workflows": []}, cost_usd=0.01),
    )
    with caplog.at_level(logging.WARNING, logger="rig"):
        await mine(store, tenant="acme", asker=asker, model="m")
        # A pass that lost nothing says nothing. A warning every pass is a
        # warning nobody reads by the time there is something to read.
        assert caplog.text == ""

        store.execute("DELETE FROM gestures WHERE id = ?", (ids[0],))
        result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.lost_pool == [ids[0]]
    assert result.window_size == len(ids) - 1
    # The result is gone the moment the pass returns; the log is what is left.
    assert ids[0] in caplog.text


async def test_a_second_pass_over_the_same_evidence_adds_no_second_workflow(
    tmp_path: Path,
) -> None:
    """Mining re-runs over evidence it has already read."""
    store = _store(tmp_path)
    ids = _ids(store)
    proposal = _proposal(ids[:2])
    asker = FakeAsker(
        Answer(data={"workflows": [proposal]}, cost_usd=0.01),
        Answer(data={"workflows": [proposal]}, cost_usd=0.01),
    )

    await mine(store, tenant="acme", asker=asker, model="m")
    second = await mine(store, tenant="acme", asker=asker, model="m")

    assert second.resolutions[0].kind == "same_occurrence"
    assert len(known_workflows(store, "acme")) == 1


async def test_one_pass_proposing_the_same_job_twice_stores_it_once(tmp_path: Path) -> None:
    """Resolving against `known` alone -- the list read before the pass began
    -- makes self-match unreachable, and lets a pass that repeated itself save
    the same job twice. What this pass has already kept is known too."""
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(
        Answer(data={"workflows": [_proposal(ids[:2]), _proposal(ids[:2])]}, cost_usd=0.01)
    )

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.proposed == 2
    assert result.kept == 1
    assert result.resolutions[1].kind == "same_occurrence"
    assert len(known_workflows(store, "acme")) == 1


async def test_two_passes_at_once_do_not_both_read_the_same_window(tmp_path: Path) -> None:
    """Both would read an empty store before either saved, so identity has
    nothing to match on and the same job is stored -- and billed -- twice."""
    store = _store(tmp_path)
    ids = _ids(store)
    asker = FakeAsker(
        Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01),
        Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01),
    )

    await asyncio.gather(
        mine(store, tenant="acme", asker=asker, model="m"),
        mine(store, tenant="acme", asker=asker, model="m"),
    )

    assert len(known_workflows(store, "acme")) == 1


async def test_a_reading_that_cited_one_corner_of_the_window_says_so(tmp_path: Path) -> None:
    """K_MIN_COVERAGE and K_MAX_SKEW were declared for this loop to read.
    Long-context citation bias is invisible without counting, and a pass that
    does not report it is a pass nobody can measure."""
    store = _store(tmp_path)
    ids = _ids(store)
    corner = FakeAsker(Answer(data={"workflows": [_proposal(ids[:1])]}, cost_usd=0.01))
    # Its own store: gesture ids are minted per batch, so the ids the whole
    # window is cited by are not the ids of the store above.
    elsewhere = _store(tmp_path / "b")
    whole = FakeAsker(Answer(data={"workflows": [_proposal(_ids(elsewhere))]}, cost_usd=0.01))

    lopsided = await mine(store, tenant="acme", asker=corner, model="m")
    even = await mine(elsewhere, tenant="acme", asker=whole, model="m")

    assert lopsided.lopsided is True
    assert even.lopsided is False


async def test_the_cost_of_the_pass_is_recorded(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asker = FakeAsker(Answer(data={"workflows": []}, in_tokens=900, out_tokens=100, cost_usd=0.037))

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.cost_usd == 0.037


async def test_a_refusal_costs_the_pass_and_not_the_process(tmp_path: Path) -> None:
    store = _store(tmp_path)

    result = await mine(store, tenant="acme", asker=FakeAsker(Answer(error="503")), model="m")

    assert result.kept == 0
    assert result.proposed == 0


async def test_a_gesture_whose_system_is_unknown_cannot_prove_a_step_that_names_one(
    tmp_path: Path,
) -> None:
    """`Gesture.system` is None whenever the url could not be parsed into one,
    and checks.validate takes `dict[str, str]` -- so the loop substitutes "".
    An unknown system is a silence, not a second system: a step citing only
    unattributed evidence is refused under its own reason rather than being
    read as a crossing."""
    store = _store(tmp_path)
    ids = _ids(store)
    store.execute("UPDATE gestures SET system = NULL, url = NULL WHERE id = ?", (ids[0],))
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:1])]}, cost_usd=0.01))

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.kept == 0
    assert result.rejections[0].reason == "unattributed evidence"


async def test_the_bill_belongs_to_the_pass_and_is_recorded_once(tmp_path: Path) -> None:
    """One call proposes every workflow in a pass, so the pass is what has a
    cost. Copying `Answer.cost_usd` onto each workflow made the total grow with
    how well the pass did: three workflows out of this $0.04 call summed to
    $0.12, and a four-workflow pass would have said $0.16."""
    store = _store(tmp_path)
    ids = _ids(store)
    three = [
        _proposal(ids[0:2], title="create a work operation"),
        _proposal(ids[2:4], title="receive a shipment"),
        _proposal(ids[4:6], title="correct a count"),
    ]
    asker = FakeAsker(
        Answer(data={"workflows": three}, in_tokens=900, out_tokens=100, cost_usd=0.04)
    )

    result = await mine(store, tenant="acme", asker=asker, model="m")

    assert result.kept == 3
    billed = store.query("SELECT count(*) AS n, sum(cost_usd) AS c FROM passes")[0]
    # One row, at the real figure -- not 0.04 * 3.
    assert billed["n"] == 1
    assert billed["c"] == 0.04
    assert billed["c"] != 0.04 * result.kept
    # And every workflow can name the row that was billed for it.
    rows = store.query("SELECT pass_id FROM workflows")
    assert {row["pass_id"] for row in rows} == {result.pass_id}


async def test_a_pass_whose_price_is_unknown_says_so_in_its_row(tmp_path: Path) -> None:
    """A $0.00 pass and a pass whose cost could not be established are the same
    row in cost_usd alone. A total that reads the second as free understates
    the bill and says nothing about it."""
    store = _store(tmp_path)
    asker = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.0, unpriced=True))

    await mine(store, tenant="acme", asker=asker, model="m")

    row = store.query("SELECT cost_usd, unpriced FROM passes")[0]
    assert row["cost_usd"] == 0.0
    assert row["unpriced"] == 1


async def test_a_refused_pass_is_still_a_row_and_still_says_why(tmp_path: Path) -> None:
    """The call happened, may have been billed, and returned nothing. Without a
    row it is indistinguishable from a pass that was never run."""
    store = _store(tmp_path)

    result = await mine(
        store, tenant="acme", asker=FakeAsker(Answer(error="503", unpriced=True)), model="m"
    )

    assert result.error == "503"
    assert [row["error"] for row in store.query("SELECT error FROM passes")] == ["503"]


_COLUMNS = (
    "id, tenant, stream_id, batch_id, at, url, system,"
    " tab_id, frame_url, gesture_json, requests, page_events"
)


def _crowd(store: Store, strong: int, weak: int) -> tuple[list[str], list[str]]:
    """A day bigger than one window, built out of the fixture's own rows.

    A gesture carrying a write outranks a plain click in `strength`, so the
    strong ones take their places first and the K_MIN_GESTURES floor decides
    how many of the weak ones join them. The rest are what the budget leaves
    out. The fixture's seven originals go, so the arithmetic is exactly these.
    """
    rows = store.query("SELECT * FROM gestures")
    writing = next(r for r in rows if any(q["method"] != "GET" for q in json.loads(r["requests"])))
    plain = next(
        r
        for r in rows
        if not json.loads(r["requests"]) and json.loads(r["gesture_json"])["kind"] == "click"
    )

    def clone(template: Any, new_id: str, at: float) -> str:
        values = [template[column.strip()] for column in _COLUMNS.split(",")]
        values[0], values[4] = new_id, at
        placeholders = ", ".join("?" * len(values))
        store.execute(f"INSERT INTO gestures ({_COLUMNS}) VALUES ({placeholders})", tuple(values))
        return new_id

    strong_ids = [clone(writing, f"ges_strong_{i:02d}", 1000.0 + i) for i in range(strong)]
    weak_ids = [clone(plain, f"ges_weak_{i:02d}", 2000.0 + i) for i in range(weak)]
    store.execute(
        "DELETE FROM gestures WHERE id NOT LIKE 'ges_strong_%' AND id NOT LIKE 'ges_weak_%'"
    )
    return strong_ids, weak_ids


# Bigger than the window has room for once the knowledge base is subtracted
# from it, which is how a test gets `pack` to leave evidence out without
# reaching past mine()'s own arguments to set the budget.
_CROWDED_KB = "x" * 600_000


async def test_evidence_the_budget_left_out_lands_in_the_pool(tmp_path: Path) -> None:
    """`left_out` was reported and dropped. A 150K window holds about 620
    gestures and an operator day runs to a few thousand, so past one window the
    same tail lost every pass forever while the count faithfully said so."""
    store = _store(tmp_path)
    strong_ids, weak_ids = _crowd(store, strong=20, weak=10)
    read = strong_ids + weak_ids[:5]
    asker = FakeAsker(Answer(data={"workflows": [_proposal(read)]}, cost_usd=0.04))

    result = await mine(store, tenant="acme", asker=asker, model="m", kb=_CROWDED_KB)

    assert result.rejections == []
    assert result.window_size == len(read)
    assert result.left_out == len(weak_ids[5:])
    # The pass cited everything it read, so the pool holds exactly what the
    # budget refused. Before the fix it held nothing at all.
    assert set(pool_ids(store, "acme")) == set(weak_ids[5:])


async def test_a_gesture_the_budget_left_out_is_read_by_the_next_pass(tmp_path: Path) -> None:
    """Being in the pool is the point only because K_POOL_BONUS then buys it a
    place. This asserts the place, not the row: the second pass proposes a
    workflow over the tail, and a tail still outside the window is refused for
    citing gestures the pass never saw."""
    store = _store(tmp_path)
    strong_ids, weak_ids = _crowd(store, strong=20, weak=10)
    tail = weak_ids[5:]
    asker = FakeAsker(
        Answer(data={"workflows": [_proposal(strong_ids + weak_ids[:5])]}, cost_usd=0.04),
        Answer(data={"workflows": [_proposal(tail, title="the tail")]}, cost_usd=0.04),
    )

    await mine(store, tenant="acme", asker=asker, model="m", kb=_CROWDED_KB)
    second = await mine(store, tenant="acme", asker=asker, model="m", kb=_CROWDED_KB)

    assert [r.reason for r in second.rejections] == []
    assert second.kept == 1
    # The window is the same size; the bonus changed who is in it. The fresh
    # weak gestures that displaced the tail last pass are this pass's tail.
    assert second.window_size == 25
    assert second.left_out == len(tail)


async def test_a_pass_that_keeps_nothing_still_says_it_read_the_window(tmp_path: Path) -> None:
    """A proposal that resolved onto a stored workflow still read the window and
    still cited real gestures. Measured on real output: an identity re-run
    proposed three, kept none, reported coverage 0.00 with lopsided=True -- and
    re-pooled every gesture those proposals cited -- while having read the whole
    window correctly."""
    store = _store(tmp_path)
    ids = _ids(store)

    first = await mine(
        store,
        tenant="acme",
        asker=FakeAsker(Answer(data={"workflows": [_proposal(ids)]}, cost_usd=0.01)),
        model="gemini-3.1-pro",
    )
    assert first.kept == 1

    again = await mine(
        store,
        tenant="acme",
        asker=FakeAsker(Answer(data={"workflows": [_proposal(ids)]}, cost_usd=0.01)),
        model="gemini-3.1-pro",
    )

    assert again.kept == 0, "the same job again is not a new workflow"
    assert again.rejections == [], "it was not refused, it was recognised"
    assert again.coverage.coverage > 0.0, "it read the window; coverage must say so"
    assert not again.lopsided, "a correct pass that keeps nothing is not lopsided"
    assert set(ids).isdisjoint(pool_ids(store, "acme")), (
        "evidence a stored workflow already explains must not be re-pooled"
    )
