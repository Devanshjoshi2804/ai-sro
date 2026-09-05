import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from rig.api import save_batch
from rig.mine import mine
from rig.models import Answer, FakeAsker
from rig.pool import K_POOL_AGE, add_unclaimed, age_pool, pool_ids, retired_entries
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


def _link(store: Store, gesture_ids: list[str], value: str, system: str) -> None:
    """One value carried by two gestures on two systems -- a crossing.

    The second of the pair is moved to `system` because values.shared_values
    needs two systems to call anything a crossing, and _crowd clones every
    gesture off one template.
    """
    from rig.api import save_intent
    from rig.records import Intent, ValueSeen

    store.execute("UPDATE gestures SET system = ? WHERE id = ?", (system, gesture_ids[1]))
    for gesture_id in gesture_ids:
        save_intent(
            store,
            Intent(
                gesture_id=gesture_id,
                tenant="acme",
                act="typed it",
                values_seen=[ValueSeen(field="supplier", value=value)],
            ),
        )


async def test_the_prompt_never_names_a_crossing_the_window_left_out(tmp_path: Path) -> None:
    """crossings are computed over the whole tenant; checks.validate refuses any
    workflow citing an id outside the window. Named anyway, a crossing whose
    partner the budget dropped is an instruction to produce a workflow that is
    then discarded in full -- and it is the cross-system class this rig exists
    to find. Proved at a 25-item window over 60 real pairs: 95 ids named, none
    citable."""
    store = _store(tmp_path)
    strong_ids, weak_ids = _crowd(store, strong=25, weak=5)
    # Both ends inside: the block must still render, or this test would pass on
    # a prompt with no crossings section at all.
    _link(store, strong_ids[:2], "WHOLLY-IN-WINDOW", "https://sap.example")
    # One end outside: the weak partner is 26th by strength even with the
    # `linked` bonus, and the window holds 25.
    straddler = [strong_ids[2], weak_ids[-1]]
    _link(store, straddler, "STRADDLES-THE-EDGE", "https://sap.example")
    asker = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.04))

    result = await mine(store, tenant="acme", asker=asker, model="m", kb=_CROWDED_KB)
    prompt = asker.asked[0]["evidence"]
    # json.dumps(indent=1) never writes a blank line, so the blank line after
    # the block is where it ends. Both values also appear in the evidence of
    # the gestures carrying them, which is what makes the block the only place
    # this can be read.
    block = prompt.split("## Values appearing in more than one system\n")[1].split("\n\n")[0]

    assert result.window_size == 25
    assert result.left_out == 5, "the window must be smaller than the evidence"
    assert "WHOLLY-IN-WINDOW" in block, "a crossing both of whose ends are citable is a hint"
    assert weak_ids[-1] not in prompt, "the prompt named evidence the model may not cite"
    assert "STRADDLES-THE-EDGE" not in block, "one id left is not a crossing"


async def test_a_retired_gesture_loses_its_bonus_and_not_its_place(tmp_path: Path) -> None:
    """The decision K_POOL_AGE records, asserted from the window's side.

    Retirement takes K_POOL_BONUS away and nothing else: the gesture is packed
    again as ordinary evidence. So a retired entry loses a contested place to
    fresh evidence of equal strength (it no longer outranks it), and takes its
    place in a window with room (it was never removed from the running).
    """
    store = _store(tmp_path)
    strong_ids, weak_ids = _crowd(store, strong=24, weak=5)
    retiree = weak_ids[-1]
    add_unclaimed(store, "acme", [retiree], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")
    assert [entry.gesture_id for entry in retired_entries(store, "acme")] == [retiree]

    asker = FakeAsker(
        Answer(data={"workflows": []}, cost_usd=0.01),
        Answer(data={"workflows": []}, cost_usd=0.01),
    )
    tight = await mine(store, tenant="acme", asker=asker, model="m", kb=_CROWDED_KB)
    roomy = await mine(store, tenant="acme", asker=asker, model="m")

    # 24 strong and one weak, and the weak place goes to the earliest of them
    # rather than to the retiree, which would have taken it at 1.5.
    assert tight.window_size == 25
    assert retiree not in asker.asked[0]["evidence"], "a retired entry competes without its bonus"
    assert weak_ids[0] in asker.asked[0]["evidence"], "the place it lost went to fresh evidence"
    # Same store, a budget with room for everything: it is still evidence.
    assert roomy.window_size == len(strong_ids) + len(weak_ids)
    assert retiree in asker.asked[1]["evidence"], "retirement is not removal from the window"


async def test_a_day_of_refused_calls_does_not_retire_the_pool(tmp_path: Path) -> None:
    """K_POOL_AGE is six readings, not six attempts. An expired key, a model
    name the API 404s, or a day of 503s ages nothing: the pool was never read,
    so its patience was never spent."""
    store = _store(tmp_path)
    ids = _ids(store)
    add_unclaimed(store, "acme", ids, set())
    refused = FakeAsker(*[Answer(error="ServerError: 503 UNAVAILABLE") for _ in range(8)])

    for _ in range(8):
        result = await mine(store, tenant="acme", asker=refused, model="m")
        assert result.error == "ServerError: 503 UNAVAILABLE"

    assert retired_entries(store, "acme") == []
    assert set(pool_ids(store, "acme")) == set(ids)
    assert {row["age"] for row in store.query("SELECT age FROM pool")} == {0}


async def test_a_refused_pass_is_not_recorded_as_lopsided(tmp_path: Path) -> None:
    """`lopsided` says a model's citations fell in one corner of the window.
    A refused call cited nothing at all, so coverage is 0.0 and the flag fired
    on every 503 -- the `passes` table, which is what a person reads, blaming
    citation bias for a reading that never happened."""
    store = _store(tmp_path)

    result = await mine(
        store, tenant="acme", asker=FakeAsker(Answer(error="ServerError: 503")), model="m"
    )

    assert result.lopsided is False
    row = store.query("SELECT lopsided, coverage, error FROM passes")[0]
    assert row["lopsided"] == 0
    assert row["coverage"] == 0.0
    assert row["error"] == "ServerError: 503"


async def test_the_pass_row_is_written_even_when_the_work_after_the_call_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The row is the only record of a call that cost money. Written last, an
    exception anywhere after the model answered lost the bill -- and left any
    workflow already saved pointing at a pass_id with no row behind it."""
    import rig.mine

    store = _store(tmp_path)
    ids = _ids(store)

    def boom(*_: Any, **__: Any) -> None:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(rig.mine, "save_workflow", boom)
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.04))

    with pytest.raises(sqlite3.OperationalError):
        await mine(store, tenant="acme", asker=asker, model="m")

    row = store.query("SELECT id, cost_usd FROM passes")[0]
    assert row["cost_usd"] == 0.04, "the call was billed and nothing recorded it"


async def test_a_pass_that_recognises_a_job_learns_what_varies_in_it(tmp_path: Path) -> None:
    """A pass that keeps nothing has still learnt something if it recognised a
    job and found out what changes in it. That is the difference between
    watching the same work twice and understanding it, and two doings are the
    only evidence that can tell a parameter from a constant.

    A second doing means NEW gestures -- that is why identity matches on shape
    rather than on cited ids, and why a diff has two values to compare.
    """
    store = _store(tmp_path)
    ids = _ids(store)

    first = await mine(
        store,
        tenant="acme",
        asker=FakeAsker(Answer(data={"workflows": [_proposal(ids)]}, cost_usd=0.01)),
        model="gemini-3.1-pro",
    )
    assert first.kept == 1
    assert first.learned_parameters == 0, "one doing cannot name a parameter"

    # The job done again: its own gestures, and the operator typed something
    # else into the same control.
    again_ids = []
    for gesture_id in ids:
        row = store.query("SELECT * FROM gestures WHERE id = ?", (gesture_id,))[0]
        gesture = json.loads(row["gesture_json"])
        if gesture.get("kind") == "type" and gesture.get("value"):
            gesture["value"] = "SOMETHING-ELSE"
        fresh = f"{gesture_id}_again"
        store.execute(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, url, system, tab_id,"
            " frame_url, page_url, gesture_json, requests, page_events)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fresh,
                row["tenant"],
                row["stream_id"],
                row["batch_id"],
                row["at"] + 10_000.0,
                row["url"],
                row["system"],
                row["tab_id"],
                row["frame_url"],
                row["page_url"],
                json.dumps(gesture),
                row["requests"],
                row["page_events"],
            ),
        )
        again_ids.append(fresh)

    again = await mine(
        store,
        tenant="acme",
        asker=FakeAsker(Answer(data={"workflows": [_proposal(again_ids)]}, cost_usd=0.01)),
        model="gemini-3.1-pro",
    )

    assert again.kept == 0, "it is the same job, not a new one"
    assert again.learned_parameters >= 1, "and this time it knows what varies"
    stored = known_workflows(store, "acme")[0]
    assert any("SOMETHING-ELSE" in (p.get("seen_values") or []) for p in stored.parameters)


async def test_a_third_doing_widens_a_parameter_it_does_not_discard_it(tmp_path: Path) -> None:
    """`Parameter.seen` promises "every value observed" and delivered two.

    _learn_parameters always diffs the STORED steps -- doing #1 -- against the
    proposal, and a name already present was skipped outright, so a parameter's
    range froze at the first pair however many times the job was done again. A
    range is the useful part of a parameter: a runner asked for `$clientCode`
    wants to know it has been TEST1, SOMETHING-ELSE and A-THIRD-ONE.
    """
    store = _store(tmp_path)
    ids = _ids(store)

    await mine(
        store,
        tenant="acme",
        asker=FakeAsker(Answer(data={"workflows": [_proposal(ids)]}, cost_usd=0.01)),
        model="gemini-3.1-pro",
    )

    def _redo(value: str, suffix: str, offset: float) -> list[str]:
        fresh_ids = []
        for gesture_id in ids:
            row = store.query("SELECT * FROM gestures WHERE id = ?", (gesture_id,))[0]
            gesture = json.loads(row["gesture_json"])
            if gesture.get("kind") == "type" and gesture.get("value"):
                gesture["value"] = value
            fresh = f"{gesture_id}_{suffix}"
            store.execute(
                "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, url, system, tab_id,"
                " frame_url, page_url, gesture_json, requests, page_events)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fresh,
                    row["tenant"],
                    row["stream_id"],
                    row["batch_id"],
                    row["at"] + offset,
                    row["url"],
                    row["system"],
                    row["tab_id"],
                    row["frame_url"],
                    row["page_url"],
                    json.dumps(gesture),
                    row["requests"],
                    row["page_events"],
                ),
            )
            fresh_ids.append(fresh)
        return fresh_ids

    for value, suffix, offset in (
        ("SOMETHING-ELSE", "again", 10_000.0),
        ("A-THIRD-ONE", "thrice", 20_000.0),
    ):
        await mine(
            store,
            tenant="acme",
            asker=FakeAsker(
                Answer(data={"workflows": [_proposal(_redo(value, suffix, offset))]}, cost_usd=0.01)
            ),
            model="gemini-3.1-pro",
        )

    stored = known_workflows(store, "acme")[0]
    seen = [p.get("seen_values") for p in stored.parameters if p.get("name") == "clientCode"]
    assert seen, "the parameter is still there"
    assert "A-THIRD-ONE" in seen[0], "and the third doing widened it"
    assert "SOMETHING-ELSE" in seen[0], "without losing the second"
    assert len(stored.parameters) == 1, "one control, not one parameter per doing"
