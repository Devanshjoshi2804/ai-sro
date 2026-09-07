"""One suite, two implementations: the fake and the store, on the same rules.

Plan 3 writes the mining pass and the runner against the fakes in
``tests/unit/fakes.py``. A fake that does not keep its store's rules is a suite
that passes against a lie, and the failure surfaces two plans later as a
mystery. Two divergences were found by eye -- a save counter standing in for
``created_at`` without its tiebreak, and a window sorted on ISO text where the
store compares instants -- and finding those by eye does not scale to six
repositories and twelve implementations.

So: every test body is written once, against the protocol, and runs twice. The
parameter is in the test id, so a failure says ``[fake]`` or ``[sql]`` rather
than leaving the reader to work out which half produced which list.

**When they disagree, the fake changes.** The store is what production runs.
Never the test, and never a ``Sql*`` repository.

**The SQL half cannot skip.** ``tests/integration/conftest.py`` skips itself
when Docker is unavailable, which is right for a suite that proves the SQL is
valid and wrong for one that says what the fake has to keep: a contract half
nobody ran is a contract nobody has.

What is deliberately *not* under contract, because a fake cannot honour it:

* Transactions. ``commit`` is a counter in the fake and a real one in the
  store, so nothing here proves a rollback. ``tests/integration`` does.
* Database constraints, ``FOR UPDATE``, and anything the schema enforces
  rather than the repository. The two ``Conflict`` rules below are the
  exception, because both implementations raise them by hand.
* An order whose sort key is a server clock. ``known`` and ``intents_since``
  order on a ``datetime.now()`` taken inside the write, so a tie cannot be
  planted from out here and the tiebreak cannot be pinned. Both are total on
  the store side; ``intents_since`` is total on neither, and that is named in
  the report.

Every ordering test below plants rows that **tie on the sort key**. A suite
that only ever plants distinct instants passes against a total order and a
non-total one alike, and so says nothing: ``since`` on runs was found ordering
by ``started_at`` alone on the store side and ``(started_at, id)`` on the fake,
and three runs sharing an instant came back in different orders.

One thing this cannot promise, said out loud rather than implied: both sides
read an ISO ``since`` through the same rule -- ``codec.when`` in the fake, a
line-for-line copy of it in each repository -- so "a naive ``since`` is read as
UTC" passes here vacuously. It is proved in ``tests/integration``, against the
column.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Gesture, GestureBatch, Intent
from sro.domain.observation.mining import MiningPass
from sro.domain.observation.pool import K_POOL_AGE, RETIRED_PASSES
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import Offer
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.repositories import SqlUnitOfWork

# The SQL half runs against the same Postgres the integration suite uses.
# Imported rather than re-declared: two definitions of "a disposable database"
# is one of them going stale.
from tests.integration.conftest import (  # noqa: F401  (fixtures, used by name)
    engine,
    postgres_url,
    session_factory,
)
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")
DEVICE = DeviceId("dev_1")
OTHER_DEVICE = DeviceId("dev_2")


@pytest.fixture(params=["fake", "sql"])
def store(request: pytest.FixtureRequest) -> UnitOfWork:
    """The same unit of work twice: the fake, then the real one.

    ``getfixturevalue`` rather than a parameter, so the fake half never builds
    a Docker client -- and so a skip raised by the integration fixtures is
    caught here and turned into a failure. A contract test that quietly skips
    is worse than no contract test: the suite goes green and the fake is
    unchecked.
    """
    if request.param == "fake":
        return FakeUnitOfWork()
    try:
        factory = request.getfixturevalue("session_factory")
    except pytest.skip.Exception as unavailable:
        pytest.fail(
            "the SQL half of this contract cannot be skipped -- it is the half that "
            f"says what the fake has to keep: {unavailable}",
            pytrace=False,
        )
    return SqlUnitOfWork(factory)


def _at(hour: int, *, minute: int = 0, offset: str = "+00:00") -> str:
    return f"2026-09-06T{hour:02d}:{minute:02d}:00{offset}"


def _today(hour: int = 12) -> str:
    """An instant inside the day ``spend.today`` is asked about."""
    return datetime.now(tz=UTC).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def _gesture(
    gesture_id: str, *, at: float = 1.0, tenant: TenantId = TENANT, **over: Any
) -> Gesture:
    fields: dict[str, Any] = {
        "id": gesture_id,
        "tenant": tenant.value,
        "stream_id": "dev_1",
        "batch_id": "bat_1",
        "at": at,
        "url": "https://wms.example/orders",
        "system": "https://wms.example",
        "tab_id": 7,
        "frame_url": "https://wms.example/orders",
        "action": Action(kind="click", at=at, url="https://wms.example/orders"),
    }
    fields.update(over)
    return Gesture(**fields)


def _batch(batch_id: str = "bat_1", **over: Any) -> GestureBatch:
    fields: dict[str, Any] = {
        "batch_id": batch_id,
        "device_id": DEVICE.value,
        "tenant": TENANT.value,
        "mode": "passive",
        "received_at": _at(9),
    }
    fields.update(over)
    return GestureBatch(**fields)


def _intent(gesture_id: str, *, tenant: TenantId = TENANT, **over: Any) -> Intent:
    fields: dict[str, Any] = {"gesture_id": gesture_id, "tenant": tenant.value, "act": "click"}
    fields.update(over)
    return Intent(**fields)


def _run(run_id: str, *, tenant: TenantId = TENANT, **over: Any) -> WorkflowRun:
    fields: dict[str, Any] = {
        "id": run_id,
        "tenant": tenant.value,
        "workflow_id": "wfl_1",
        "device_id": DEVICE.value,
        "values": {"workArea": "THIRD"},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": _at(10),
    }
    fields.update(over)
    return WorkflowRun(**fields)


def _workflow(workflow_id: str, *, tenant: TenantId = TENANT, **over: Any) -> Workflow:
    fields: dict[str, Any] = {
        "id": workflow_id,
        "tenant": tenant.value,
        "title": "put away a pallet",
        "narrative": "scan, place, confirm",
        "systems": ["https://wms.example"],
        "shape_key": [["click", "Save"]],
    }
    fields.update(over)
    return Workflow(**fields)


def _pass(pass_id: str, *, tenant: TenantId = TENANT, **over: Any) -> MiningPass:
    fields: dict[str, Any] = {"id": pass_id, "tenant": tenant.value, "started_at": _at(10)}
    fields.update(over)
    return MiningPass(**fields)


def _offer(offer_id: str, *, tenant: TenantId = TENANT, **over: Any) -> Offer:
    fields: dict[str, Any] = {
        "id": offer_id,
        "tenant": tenant.value,
        "workflow_id": "wfl_1",
        "device_id": DEVICE.value,
        "k": 2,
        "fate": "dismissed",
        "at": _at(10),
    }
    fields.update(over)
    return Offer(**fields)


def _chat(chat_id: str, *, tenant: TenantId = TENANT, **over: Any) -> ChatReading:
    fields: dict[str, Any] = {"id": chat_id, "tenant": tenant.value, "at": _at(10)}
    fields.update(over)
    return ChatReading(**fields)


class TestWorkflows:
    async def test_known_is_oldest_first_and_a_resave_moves_a_workflow_to_the_end(
        self, store: UnitOfWork
    ) -> None:
        """Load-bearing, not cosmetic: ``resolve`` breaks a tie at the top
        score with a strict ``>``, so the first workflow in this list wins a
        proposal that matches two of them equally well. The store rewrites
        ``created_at`` on a re-save, which is what moves one to the end."""
        async with store as work:
            for name in ("wfl_1", "wfl_2", "wfl_3"):
                await work.workflows.save(_workflow(name))
            await work.commit()

        async with store as work:
            assert [one.id for one in await work.workflows.known(TENANT)] == [
                "wfl_1",
                "wfl_2",
                "wfl_3",
            ]
            await work.workflows.save(_workflow("wfl_1", title="renamed by a merge"))
            await work.commit()

        async with store as work:
            assert [one.id for one in await work.workflows.known(TENANT)] == [
                "wfl_2",
                "wfl_3",
                "wfl_1",
            ]

    async def test_a_step_the_merge_dropped_leaves_the_store(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.workflows.save(
                _workflow(
                    "wfl_1",
                    steps=[
                        Step(order=0, says="scan", system=None),
                        Step(order=1, says="place", system=None),
                    ],
                )
            )
            await work.commit()

        async with store as work:
            await work.workflows.save(
                _workflow("wfl_1", steps=[Step(order=0, says="scan", system=None)])
            )
            await work.commit()

        async with store as work:
            kept = await work.workflows.get(TENANT, "wfl_1")
        assert [step.says for step in kept.steps] == ["scan"]

    async def test_passes_are_oldest_first_on_the_instant_and_read_back_normalised(
        self, store: UnitOfWork
    ) -> None:
        """The offsets disagree with the text: ``12:00+02:00`` is ten o'clock
        and sorts *after* ``11:00+00:00`` as a string and *before* it as an
        instant. The store compares ``timestamptz``."""
        async with store as work:
            await work.workflows.add_pass(_pass("pas_c", started_at=_at(11)))
            await work.workflows.add_pass(_pass("pas_a", started_at=_at(11)))
            await work.workflows.add_pass(_pass("pas_early", started_at=_at(12, offset="+02:00")))
            await work.commit()

        async with store as work:
            made = await work.workflows.passes(TENANT)
        assert [one.id for one in made] == ["pas_early", "pas_a", "pas_c"]
        assert made[0].started_at == "2026-09-06T10:00:00+00:00"

    async def test_a_pass_id_is_stored_once(self, store: UnitOfWork) -> None:
        """A pass id is minted per reading, so a second row under one id is one
        model call billed twice."""
        async with store as work:
            await work.workflows.add_pass(_pass("pas_1"))
            await work.commit()

        with pytest.raises(Conflict):
            async with store as work:
                await work.workflows.add_pass(_pass("pas_1"))
                await work.commit()

    async def test_a_weak_step_is_named_once_however_often_it_is_noticed(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflows.mark_stale("wfl_1", 2, matched_by="text", noticed_at=_at(10))
            await work.workflows.mark_stale("wfl_1", 2, matched_by="text", noticed_at=_at(11))
            await work.workflows.mark_stale("wfl_1", 3, matched_by=None, noticed_at=_at(11))
            await work.commit()

        async with store as work:
            assert await work.workflows.stale_count("wfl_1") == 2
            # Idempotent: clearing a step that was never weak is not an error.
            await work.workflows.clear_stale("wfl_1", 2)
            await work.workflows.clear_stale("wfl_1", 9)
            await work.commit()

        async with store as work:
            assert await work.workflows.stale_count("wfl_1") == 1

    async def test_only_a_state_belt_registers_an_effect_and_one_write_is_one_row(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflows.record_effect(
                "wfl_1", run_id="run_1", ord_=1, verified_by="screen", at=_at(10)
            )
            await work.workflows.record_effect(
                "wfl_1", run_id="run_1", ord_=1, verified_by="status", at=_at(10)
            )
            await work.workflows.record_effect(
                "wfl_1", run_id="run_1", ord_=1, verified_by="read", at=_at(11)
            )
            await work.commit()

        async with store as work:
            assert await work.workflows.forget_effects("wfl_1") == 1
            await work.commit()

        async with store as work:
            assert await work.workflows.forget_effects("wfl_1") == 0

    async def test_proofs_name_the_written_steps_of_every_live_held_run(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_held",
                    live=True,
                    outcome="held",
                    started_at=_at(10),
                    steps=[
                        RunStep(order=0, says="look", verdict="held", result={"wrote": False}),
                        RunStep(order=1, says="save", verdict="held", result={"wrote": True}),
                    ],
                )
            )
            # A dry run and a run that stopped are neither of them proof.
            await work.workflow_runs.save(
                _run(
                    "run_dry",
                    live=False,
                    outcome="held",
                    started_at=_at(11),
                    steps=[RunStep(order=0, says="save", verdict="held", result={"wrote": True})],
                )
            )
            await work.workflow_runs.save(_run("run_stopped", live=True, outcome="stopped"))
            await work.workflows.record_effect(
                "wfl_1", run_id="run_held", ord_=1, verified_by="status", at=_at(10)
            )
            await work.commit()

        async with store as work:
            proofs = await work.workflows.proofs(TENANT, "wfl_1")

        assert [one.run_id for one in proofs] == ["run_held"]
        assert proofs[0].wrote == frozenset({1})
        assert proofs[0].verified == frozenset({1})


class TestWorkflowRuns:
    async def test_for_workflow_is_oldest_first_on_the_instant_and_breaks_ties_on_the_id(
        self, store: UnitOfWork
    ) -> None:
        """Two runs of one workflow routinely share an instant -- one form
        submits them -- so the tie is planted rather than avoided: an order that
        is not total is an order that changes between reads."""
        async with store as work:
            await work.workflow_runs.save(_run("run_c", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_a", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_b", started_at=_at(11)))
            # 12:00+02:00 is ten o'clock: earlier as an instant, later as text.
            await work.workflow_runs.save(_run("run_early", started_at=_at(12, offset="+02:00")))
            await work.workflow_runs.save(_run("run_elsewhere", workflow_id="wfl_2"))
            await work.commit()

        async with store as work:
            found = await work.workflow_runs.for_workflow(TENANT, "wfl_1")
        assert [one.id for one in found] == ["run_early", "run_a", "run_b", "run_c"]

    async def test_since_is_newest_first_and_reads_the_instant_back_normalised(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(_run("run_early", started_at=_at(12, offset="+02:00")))
            await work.workflow_runs.save(_run("run_c", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_a", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_b", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_before", started_at=_at(8)))
            await work.commit()

        async with store as work:
            found = await work.workflow_runs.since(TENANT, since=_at(9))
        assert [one.id for one in found] == ["run_c", "run_b", "run_a", "run_early"]
        assert found[-1].started_at == "2026-09-06T10:00:00+00:00"

    async def test_save_replaces_a_runs_steps_rather_than_appending(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_1",
                    steps=[
                        RunStep(order=0, says="scan", verdict="held"),
                        RunStep(order=1, says="place", verdict="held"),
                    ],
                )
            )
            await work.commit()

        async with store as work:
            await work.workflow_runs.save(
                _run("run_1", steps=[RunStep(order=0, says="scan", verdict="held")])
            )
            await work.commit()

        async with store as work:
            kept = await work.workflow_runs.get(TENANT, "run_1")
        assert kept is not None
        assert [step.says for step in kept.steps] == ["scan"]

    async def test_a_step_that_sent_nothing_reads_back_as_nothing(self, store: UnitOfWork) -> None:
        """``sent IS NULL`` is the question every reader asks about a step. A
        JSON scalar ``null`` would answer it wrong."""
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_1",
                    steps=[
                        RunStep(order=0, says="wait", verdict="skipped", sent=None, result=None)
                    ],
                )
            )
            await work.commit()

        async with store as work:
            kept = await work.workflow_runs.get(TENANT, "run_1")
        assert kept is not None
        assert kept.steps[0].sent is None
        assert kept.steps[0].result is None

    async def test_awaiting_names_only_steps_of_runs_that_are_still_running(
        self, store: UnitOfWork
    ) -> None:
        """A step left ``awaiting`` on a run that was aborted is not waiting on
        anybody: without the predicate it sits in the supervisor's queue asking
        for a tap that can no longer let anything out."""
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_running",
                    started_at=_at(10),
                    outcome="running",
                    steps=[
                        RunStep(order=0, says="scan", verdict="held"),
                        RunStep(order=1, says="confirm the write", verdict="awaiting"),
                    ],
                )
            )
            await work.workflow_runs.save(
                _run(
                    "run_also_running",
                    started_at=_at(10),
                    outcome="running",
                    steps=[RunStep(order=0, says="approve the move", verdict="awaiting")],
                )
            )
            await work.workflow_runs.save(
                _run(
                    "run_aborted",
                    started_at=_at(11),
                    outcome="aborted",
                    steps=[RunStep(order=0, says="confirm the write", verdict="awaiting")],
                )
            )
            await work.commit()

        async with store as work:
            parked = await work.workflow_runs.awaiting(TENANT)
        # The two running runs share an instant, so the queue is ordered by the
        # run id between them: a supervisor's list that reshuffles on every
        # poll is a list nobody can work down.
        assert parked == (
            ("run_also_running", 0, "approve the move"),
            ("run_running", 1, "confirm the write"),
        )

    async def test_approve_is_first_tap_wins(self, store: UnitOfWork) -> None:
        """A write rescued to the second rung parks at the same step and takes
        a second tap; the first authorisation, and the first browser, stand."""
        async with store as work:
            assert (
                await work.workflow_runs.approve(
                    "run_1", 1, at=_at(12, offset="+02:00"), device_id=DEVICE.value
                )
                is True
            )
            assert (
                await work.workflow_runs.approve(
                    "run_1", 1, at=_at(11), device_id=OTHER_DEVICE.value
                )
                is False
            )
            await work.commit()

        async with store as work:
            assert await work.workflow_runs.approvals("run_1") == (
                (1, "2026-09-06T10:00:00+00:00", DEVICE.value),
            )

    async def test_in_flight_names_the_run_this_browser_is_already_driving(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(_run("run_done", outcome="held"))
            await work.workflow_runs.save(
                _run("run_other_browser", device_id=OTHER_DEVICE.value, outcome="running")
            )
            await work.commit()

        async with store as work:
            assert await work.workflow_runs.in_flight(TENANT, DEVICE) is None
            await work.workflow_runs.save(_run("run_live", outcome="running"))
            await work.commit()

        async with store as work:
            assert await work.workflow_runs.in_flight(TENANT, DEVICE) == "run_live"

    async def test_fail_orphans_sweeps_every_tenant_and_lands_the_reason_on_a_step(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_mid",
                    outcome="running",
                    steps=[RunStep(order=0, says="scan", verdict="held")],
                )
            )
            await work.workflow_runs.save(
                _run("run_nowhere", tenant=OTHER_TENANT, outcome="running")
            )
            await work.workflow_runs.save(_run("run_done", outcome="held"))
            await work.commit()

        async with store as work:
            assert await work.workflow_runs.fail_orphans("the worker restarted") == 2
            await work.commit()

        async with store as work:
            swept = await work.workflow_runs.get(TENANT, "run_mid")
            elsewhere = await work.workflow_runs.get(OTHER_TENANT, "run_nowhere")
        assert swept is not None and elsewhere is not None
        assert swept.outcome == "failed"
        assert swept.steps[-1].reason == "the worker restarted"
        # A run that died before its first step still has to say why somewhere.
        assert [step.order for step in elsewhere.steps] == [0]
        assert elsewhere.steps[0].reason == "the worker restarted"


class TestOffers:
    async def test_newest_is_at_descending_with_arrival_as_the_tiebreak(
        self, store: UnitOfWork
    ) -> None:
        """Several offers of one job routinely carry the same second, because
        the extension sends whole-second instants. The three newest decide
        whether a browser is rested, so the tie has to break on arrival."""
        async with store as work:
            for name, k in (("off_1", 1), ("off_2", 2), ("off_3", 3)):
                await work.offers.record(_offer(name, k=k, at=_at(10)))
            await work.offers.record(_offer("off_older", k=9, at=_at(9)))
            await work.commit()

        async with store as work:
            window = await work.offers.newest(TENANT, "wfl_1", limit=10)
        assert [row.k for row in window] == [3, 2, 1, 9]

    async def test_newest_orders_on_the_instant_and_reads_it_back_normalised(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.offers.record(_offer("off_early", k=1, at=_at(12, offset="+02:00")))
            await work.offers.record(_offer("off_late", k=2, at=_at(11)))
            await work.commit()

        async with store as work:
            window = await work.offers.newest(TENANT, "wfl_1", limit=10)
        assert [row.k for row in window] == [2, 1]
        assert window[1].at == "2026-09-06T10:00:00+00:00"

    async def test_the_window_excludes_nudges_and_the_tally_counts_them(
        self, store: UnitOfWork
    ) -> None:
        """``k = 0`` is an arrival: "you have been here before" with nothing
        typed is not a recognition that diverged and not an offer anyone turned
        down. Keeping it out of the window is what lets ``limit`` mean what it
        says; the panel's tally is a different question."""
        async with store as work:
            await work.offers.record(_offer("off_nudge", k=0, fate="expired", at=_at(11)))
            await work.offers.record(_offer("off_real", k=2, fate="dismissed", at=_at(10)))
            await work.commit()

        async with store as work:
            assert [row.k for row in await work.offers.newest(TENANT, "wfl_1", limit=10)] == [2]
            assert [
                row.k
                for row in await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=10)
            ] == [2]
            assert dict(await work.offers.fates(TENANT, "wfl_1")) == {
                "expired": 1,
                "dismissed": 1,
            }

    async def test_newest_for_device_is_one_browsers_window(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.offers.record(_offer("off_mine", k=1, at=_at(10)))
            await work.offers.record(
                _offer("off_theirs", k=2, device_id=OTHER_DEVICE.value, at=_at(11))
            )
            await work.commit()

        async with store as work:
            assert [
                row.k
                for row in await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=10)
            ] == [1]
            # Recognition is a property of the job, not of who was asked.
            assert [row.k for row in await work.offers.newest(TENANT, "wfl_1", limit=10)] == [2, 1]

    async def test_since_is_the_whole_offer_newest_first_with_no_window_filters(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.offers.record(_offer("off_nudge", k=0, at=_at(11)))
            await work.offers.record(_offer("off_real", k=2, at=_at(10)))
            await work.offers.record(_offer("off_before", k=2, at=_at(8)))
            await work.commit()

        async with store as work:
            audited = await work.offers.since(TENANT, since=_at(9))
        assert [one.id for one in audited] == ["off_nudge", "off_real"]
        assert audited[1].at == "2026-09-06T10:00:00+00:00"


class TestChats:
    async def test_since_is_newest_first_on_the_instant_and_reads_back_normalised(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.chats.record(_chat("cha_early", at=_at(12, offset="+02:00")))
            await work.chats.record(_chat("cha_a", at=_at(11)))
            await work.chats.record(_chat("cha_c", at=_at(11)))
            await work.chats.record(_chat("cha_before", at=_at(8)))
            await work.commit()

        async with store as work:
            read = await work.chats.since(TENANT, since=_at(9))
        # Tied on `at`, which comes off the record: there is no arrival column
        # on a chat row, so the id is the tiebreak on both sides.
        assert [one.id for one in read] == ["cha_c", "cha_a", "cha_early"]
        assert read[-1].at == "2026-09-06T10:00:00+00:00"


class TestGestures:
    async def test_a_batch_id_is_claimed_once(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.gestures.add_batch(_batch())
            await work.commit()

        with pytest.raises(Conflict):
            async with store as work:
                await work.gestures.add_batch(_batch())
                await work.commit()

    async def test_gestures_and_unread_are_oldest_first_and_a_reading_is_never_reoffered(
        self, store: UnitOfWork
    ) -> None:
        """A gesture that was read is never offered again, error or not: the
        model was asked, it answered, and it was billed."""
        async with store as work:
            # `ges_1` and `ges_2` share an instant: `at` is the browser's clock
            # in milliseconds and a burst of gestures ties on it. Under `unread`
            # a non-total order is a different *set* of 200, not a different
            # order, which is why the tie is planted here.
            await work.gestures.add_gestures(
                (_gesture("ges_2", at=1.0), _gesture("ges_1", at=1.0), _gesture("ges_3", at=3.0))
            )
            await work.commit()

        async with store as work:
            assert [one.id for one in await work.gestures.gestures_for(TENANT)] == [
                "ges_1",
                "ges_2",
                "ges_3",
            ]
            assert [one.id for one in await work.gestures.unread(TENANT, limit=2)] == [
                "ges_1",
                "ges_2",
            ]
            assert [one.id for one in await work.gestures.gestures_for(TENANT, ids=("ges_3",))] == [
                "ges_3"
            ]
            await work.gestures.save_intent(_intent("ges_1", error="the model refused"))
            await work.commit()

        async with store as work:
            assert [one.id for one in await work.gestures.unread(TENANT, limit=2)] == [
                "ges_2",
                "ges_3",
            ]
            assert await work.gestures.count(TENANT) == 3

    async def test_a_second_reading_of_one_gesture_replaces_the_first(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.gestures.save_intent(_intent("ges_1", act="click", cost_usd=0.01))
            await work.commit()

        async with store as work:
            await work.gestures.save_intent(_intent("ges_1", act="type", cost_usd=0.02))
            await work.commit()

        async with store as work:
            read = await work.gestures.intents_for(TENANT)
        assert [(one.gesture_id, one.act) for one in read] == [("ges_1", "type")]

    async def test_intents_since_reads_the_clock_the_reading_was_stored_on(
        self, store: UnitOfWork
    ) -> None:
        """Not the gesture's clock: ``created_at`` is when the reading was
        stored, which is the same column the day's spend is summed over,
        because it is the reading that was billed."""
        before = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()
        async with store as work:
            await work.gestures.save_intent(_intent("ges_1"))
            await work.gestures.save_intent(_intent("ges_2"))
            await work.commit()

        async with store as work:
            since_before = await work.gestures.intents_since(TENANT, since=before)
            later = (datetime.now(tz=UTC) + timedelta(minutes=1)).isoformat()
            since_after = await work.gestures.intents_since(TENANT, since=later)
        # Newest first.
        assert [one.gesture_id for one in since_before] == ["ges_2", "ges_1"]
        assert since_after == ()

    async def test_streams_are_newest_first(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.gestures.add_gestures(
                (
                    _gesture("ges_1", at=1.0, stream_id="old"),
                    _gesture("ges_2", at=5.0, stream_id="zebra"),
                    _gesture("ges_3", at=4.0, stream_id="old"),
                    _gesture("ges_4", at=5.0, stream_id="ant"),
                )
            )
            await work.commit()

        async with store as work:
            # Two streams whose last gesture ties: the stream id breaks it, and
            # ascending within a descending clock, as the query reads.
            assert await work.gestures.streams(TENANT) == (
                ("ant", 5.0, 1),
                ("zebra", 5.0, 1),
                ("old", 4.0, 2),
            )

    async def test_the_same_orphan_request_twice_is_one_row(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.gestures.add_orphan_request(
                TENANT, batch_id="bat_1", request_id="req_1", payload={"url": "a"}
            )
            await work.gestures.add_orphan_request(
                TENANT, batch_id="bat_1", request_id="req_1", payload={"url": "b"}
            )
            await work.commit()

        async with store as work:
            await work.gestures.add_batch(_batch())
            await work.commit()

        async with store as work:
            assert await work.gestures.batch_owner("bat_1") == DEVICE.value
            assert await work.gestures.batch_owner("bat_missing") is None


class TestPool:
    async def test_re_entering_does_not_reset_an_entrys_age(self, store: UnitOfWork) -> None:
        """A gesture that has sat unplaced through three passes keeps the age
        those passes gave it. Reset, nothing in a recurring window ever
        retires."""
        async with store as work:
            assert await work.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await work.pool.age(TENANT, shown=("ges_1",))
            await work.pool.age(TENANT, shown=("ges_1",))
            await work.commit()

        async with store as work:
            assert (
                await work.pool.add_unclaimed(
                    TENANT, window_ids=("ges_1", "ges_2"), claimed=frozenset()
                )
                == 1
            )
            await work.commit()

        async with store as work:
            waiting = await work.pool.waiting(TENANT)
        assert [(one.gesture_id, one.age) for one in waiting] == [("ges_1", 2), ("ges_2", 0)]

    async def test_a_cited_gesture_leaves_the_pool_wherever_it_was(self, store: UnitOfWork) -> None:
        """``claimed`` is cleared in full rather than only where it intersects
        the window: a pass can cite evidence that is only in the pool, and
        clearing the intersection alone would leave that citation to age out
        despite having been placed."""
        async with store as work:
            await work.pool.add_unclaimed(
                TENANT, window_ids=("ges_1", "ges_2"), claimed=frozenset()
            )
            await work.commit()

        async with store as work:
            assert (
                await work.pool.add_unclaimed(
                    TENANT, window_ids=("ges_3",), claimed=frozenset({"ges_1"})
                )
                == 1
            )
            await work.commit()

        async with store as work:
            assert await work.pool.ids(TENANT) == ("ges_2", "ges_3")

    async def test_a_pass_that_packed_nothing_still_moves_everything_waiting(
        self, store: UnitOfWork
    ) -> None:
        """An empty window is not the absence of a window. ``NOT IN ()`` under
        three-valued logic matches nothing, so the branch is spelled out on
        both sides -- a pass that packs nothing is exactly when the pool most
        needs to record that nobody was seen."""
        async with store as work:
            await work.pool.add_unclaimed(
                TENANT, window_ids=("ges_1", "ges_2"), claimed=frozenset()
            )
            await work.pool.age(TENANT, shown=())
            await work.commit()

        async with store as work:
            waiting = await work.pool.waiting(TENANT)
        assert [(one.age, one.waited) for one in waiting] == [(0, 1), (0, 1)]

    async def test_only_evidence_a_reading_saw_ages_and_waiting_starts_again(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.pool.add_unclaimed(
                TENANT, window_ids=("ges_seen", "ges_passed"), claimed=frozenset()
            )
            await work.pool.age(TENANT, shown=("ges_seen",))
            await work.commit()

        async with store as work:
            waiting = await work.pool.waiting(TENANT)
        assert [(one.gesture_id, one.age, one.waited) for one in waiting] == [
            ("ges_passed", 0, 1),
            ("ges_seen", 1, 0),
        ]

    async def test_an_entry_read_past_the_cap_retires_and_is_no_longer_waiting(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await work.commit()

        retired = 0
        for _ in range(K_POOL_AGE + 1):
            async with store as work:
                retired += await work.pool.age(TENANT, shown=("ges_1",))
                await work.commit()

        async with store as work:
            assert retired == 1
            assert await work.pool.waiting(TENANT) == ()
            gone = await work.pool.retired(TENANT)
        assert [(one.gesture_id, one.reason) for one in gone] == [("ges_1", RETIRED_PASSES)]


class TestSpend:
    async def test_the_day_is_summed_over_every_table_that_can_bill_it(
        self, store: UnitOfWork
    ) -> None:
        """A cap that summed one of the four was a cap on a quarter of the
        bill. The blind count is read beside the sum, never derived from it: a
        model the price table never heard of records $0.00 and ``unpriced``."""
        now = datetime.now(tz=UTC)
        async with store as work:
            await work.gestures.save_intent(_intent("ges_1", cost_usd=0.01))
            await work.gestures.save_intent(_intent("ges_2", cost_usd=0.0, unpriced=True))
            await work.workflows.add_pass(_pass("pas_1", started_at=_today(), cost_usd=0.02))
            await work.workflow_runs.save(
                _run("run_1", started_at=_today(), cost_usd=0.04, unpriced=True)
            )
            await work.chats.record(_chat("cha_1", at=_today(), cost_usd=0.08))
            # Errored, so nothing was billed: unpriced without being blind.
            await work.chats.record(
                _chat("cha_2", at=_today(), unpriced=True, error="the model refused")
            )
            await work.commit()

        async with store as work:
            spent = await work.spend.today(TENANT, now=now)

        assert spent.cost_usd == pytest.approx(0.15)
        # The unpriced reading, and nothing else: the run billed, and the chat
        # errored.
        assert spent.blind == 1

    async def test_a_run_that_billed_nothing_at_all_is_the_blind_one(
        self, store: UnitOfWork
    ) -> None:
        """A run carries no error column, so its blind row is the one that
        billed nothing. A run that billed its other steps and lost one to a
        503 is not that."""
        now = datetime.now(tz=UTC)
        async with store as work:
            await work.workflow_runs.save(
                _run("run_blind", started_at=_today(), cost_usd=0.0, unpriced=True)
            )
            await work.commit()

        async with store as work:
            assert (await work.spend.today(TENANT, now=now)).blind == 1


class TestTenantScoping:
    async def test_no_read_returns_another_tenants_row(self, store: UnitOfWork) -> None:
        """One planted row per read, and every read asked as ``acme``. A filter
        that is missing on one side of the port is a tenant reading another
        tenant's warehouse."""
        async with store as work:
            await work.gestures.add_gestures((_gesture("ges_theirs", tenant=OTHER_TENANT),))
            await work.gestures.save_intent(_intent("ges_theirs", tenant=OTHER_TENANT))
            await work.workflows.save(_workflow("wfl_theirs", tenant=OTHER_TENANT))
            await work.workflows.add_pass(
                _pass("pas_theirs", tenant=OTHER_TENANT, started_at=_today())
            )
            await work.workflow_runs.save(
                _run("run_theirs", tenant=OTHER_TENANT, outcome="running", started_at=_today())
            )
            await work.workflow_runs.save(
                _run(
                    "run_theirs_parked",
                    tenant=OTHER_TENANT,
                    outcome="running",
                    steps=[RunStep(order=0, says="confirm", verdict="awaiting")],
                )
            )
            await work.offers.record(_offer("off_theirs", tenant=OTHER_TENANT, at=_today()))
            await work.chats.record(_chat("cha_theirs", tenant=OTHER_TENANT, at=_today()))
            await work.pool.add_unclaimed(
                OTHER_TENANT, window_ids=("ges_theirs",), claimed=frozenset()
            )
            await work.commit()

        yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
        async with store as work:
            assert await work.gestures.gestures_for(TENANT) == ()
            assert await work.gestures.unread(TENANT, limit=10) == ()
            assert await work.gestures.intents_for(TENANT) == ()
            assert await work.gestures.intents_since(TENANT, since=yesterday) == ()
            assert await work.gestures.count(TENANT) == 0
            assert await work.gestures.streams(TENANT) == ()

            assert await work.workflows.known(TENANT) == ()
            assert await work.workflows.passes(TENANT) == ()
            assert await work.workflows.proofs(TENANT, "wfl_theirs") == ()

            assert await work.workflow_runs.get(TENANT, "run_theirs") is None
            assert await work.workflow_runs.for_workflow(TENANT, "wfl_1") == ()
            assert await work.workflow_runs.since(TENANT, since=yesterday) == ()
            assert await work.workflow_runs.in_flight(TENANT, DEVICE) is None
            assert await work.workflow_runs.awaiting(TENANT) == ()

            assert await work.offers.newest(TENANT, "wfl_1", limit=10) == ()
            assert await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=10) == ()
            assert dict(await work.offers.fates(TENANT, "wfl_1")) == {}
            assert await work.offers.since(TENANT, since=yesterday) == ()

            assert await work.chats.since(TENANT, since=yesterday) == ()

            assert await work.pool.waiting(TENANT) == ()
            assert await work.pool.ids(TENANT) == ()
            assert await work.pool.retired(TENANT) == ()

            assert (await work.spend.today(TENANT, now=datetime.now(tz=UTC))).cost_usd == 0.0
