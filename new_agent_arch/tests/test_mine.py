import asyncio
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
