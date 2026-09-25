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
  rather than the repository. The three ``Conflict`` rules below are the
  exception, because both implementations raise them by hand.
* An order whose sort key is a server clock. ``known`` and ``intents_since``
  order on a ``datetime.now()`` taken inside the write, so a tie cannot be
  planted from out here and the tiebreak cannot be pinned. Both are total on
  the store side; ``intents_since`` is total on neither, and that is named in
  the report.

**Writing an ordering test here: two rules, and the second is the one that
bites.**

1. Plant rows that **tie on the sort key**. A suite that only ever plants
   distinct instants passes against a total order and a non-total one alike,
   and so says nothing. ``since`` on runs was ordering by ``started_at`` alone
   on the store side and ``(started_at, id)`` on the fake, and three runs
   sharing an instant came back in different orders.
2. Plant them in an order that **disagrees with the answer you assert**.
   Postgres's tie order at these row counts is whatever the plan happens to
   yield, and what it yields is usually the plant order or its reverse -- so a
   test that asserts the order it planted is satisfied by the bug it is meant
   to catch. This is not fixed by planting more rows: twenty tied rows stayed
   green. ``chats.since`` planted ``cha_a`` then ``cha_c`` and asserted
   ``cha_c, cha_a``; it passed with ``ChatRow.id.desc()`` deleted. Swapping the
   two plants is what made it fail.

Every ordering assertion below was mutation-tested by deleting its tiebreak
from the ``Sql*`` query and re-running. Seven bite. Five do not, and the reason
differs per case -- they are named in the task report rather than left for the
next reader to discover, because an assertion that cannot fail is a comment.

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
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Gesture, GestureBatch, Intent
from sro.domain.observation.mining import MiningPass
from sro.domain.observation.pool import K_POOL_AGE, RETIRED_PASSES
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import (
    ConfirmationId,
    DeviceId,
    PrincipalId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.shared.prices import ModelSpend
from sro.domain.skill import PromotionStage
from sro.domain.skill.offers import Offer
from sro.domain.skill.workflow import Step, Workflow
from sro.domain.trigger.confirmation import Answer, Confirmation
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


def _when(hour: int, *, minute: int = 0) -> datetime:
    """An aware instant, which is what `tool_calls.remember` takes -- the
    ledger compares it against a `timestamptz` and a naive one would be read
    in the server's zone on one side of the comparison and not the other."""
    return datetime(2026, 9, 6, hour, minute, tzinfo=UTC)


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
        # Finished, where the record's own default is `running`. Since migration
        # 0043 a browser may hold at most one RUNNING run -- a unique partial
        # index, because reading "is this browser busy" and then claiming it are
        # two statements and two presses both read free between them. So a
        # fixture that plants several runs for one browser is planting a state
        # the store refuses unless it says which one is in flight, and every
        # test below that cares says `outcome="running"` itself.
        "outcome": "held",
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
        "shape_key": [["click", "Save", "wms"]],
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


def _skill_run(run_id: str, **overrides: Any) -> Run:
    """One run of the older, skill path -- the table `runs`, not
    `workflow_runs`."""
    fields: dict[str, Any] = {
        "id": RunId(run_id),
        "tenant_id": TENANT,
        "skill_id": SkillId("skl_1"),
        "skill_version": 1,
        "stage": PromotionStage.SHADOW,
        "parameters": {},
        "requested_by": PrincipalId("operator"),
        "started_at": _when(10),
        "device_id": DEVICE,
    }
    fields.update(overrides)
    return Run(**fields)


class TestWorkflows:
    async def test_known_is_oldest_first_and_a_resave_keeps_its_place(
        self, store: UnitOfWork
    ) -> None:
        """Load-bearing, not cosmetic: ``resolve`` breaks a tie at the top
        score with a strict ``>``, so the first workflow in this list wins a
        proposal that matches two of them equally well. A re-save is not a
        new job, so it does not move one: ``created_at`` is when it was made."""
        async with store as work:
            for name in ("wfl_1", "wfl_2", "wfl_3"):
                await work.workflows.save(_workflow(name))
            await work.commit()

        async with store as work:
            await work.workflows.save(_workflow("wfl_1", title="renamed by a merge"))
            await work.commit()

        async with store as work:
            assert [one.id for one in await work.workflows.known(TENANT)] == [
                "wfl_1",
                "wfl_2",
                "wfl_3",
            ]

    async def test_a_re_saved_job_is_not_noticed_again(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.workflows.save(_workflow("wfl_1"))
            await work.commit()
        after_it_was_made = datetime.now(tz=UTC)

        async with store as work:
            await work.workflows.save(_workflow("wfl_1", title="a parameter learnt"))
            await work.commit()

        async with store as work:
            assert await work.workflows.noticed_since(TENANT, since=after_it_was_made) == ()

    async def test_noticed_since_is_newest_first_and_leaves_out_the_retired_and_the_old(
        self, store: UnitOfWork
    ) -> None:
        before = datetime.now(tz=UTC) - timedelta(seconds=1)
        async with store as work:
            for name in ("wfl_1", "wfl_2", "wfl_3"):
                await work.workflows.save(
                    _workflow(name, steps=[Step(order=0, says="open", system=None)])
                )
            await work.workflows.save(_workflow("wfl_other", tenant=OTHER_TENANT))
            await work.commit()
        async with store as work:
            await work.workflows.retire(TENANT, "wfl_2", at=_when(12))
            await work.commit()

        async with store as work:
            noticed = await work.workflows.noticed_since(TENANT, since=before)
            assert [(one.id, one.steps) for one in noticed] == [("wfl_3", 1), ("wfl_1", 1)]
            assert noticed[0].title == "put away a pallet"
            assert noticed[0].systems == ("https://wms.example",)
            later = datetime.now(tz=UTC) + timedelta(minutes=1)
            assert await work.workflows.noticed_since(TENANT, since=later) == ()

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

    async def test_a_pass_carries_back_every_figure_it_was_written_with(
        self, store: UnitOfWork
    ) -> None:
        """Both stores, every counter, round trip.

        `learned_parameters` is the reason this exists. It was computed by every
        pass since the miner was ported and had no column, so the figure died at
        the persistence layer -- and no unit test could notice, because the fake
        keeps the domain object whole and never goes through a mapper at all. A
        column added to one store and not the other, or a mapper that reads a
        neighbouring field, is invisible until here.
        """
        async with store as work:
            await work.workflows.add_pass(
                _pass(
                    "pas_full",
                    in_tokens=101,
                    out_tokens=202,
                    thought_tokens=303,
                    cost_usd=0.404,
                    unpriced=True,
                    proposed=5,
                    kept=4,
                    rejected=3,
                    learned_parameters=2,
                    coverage=0.9,
                    skew=-0.5,
                    lopsided=True,
                    error="the model would not answer",
                )
            )
            await work.commit()

        async with store as work:
            (made,) = await work.workflows.passes(TENANT)
        # Every value distinct, so a mapper reading the wrong field is caught
        # rather than agreeing by coincidence.
        assert (made.in_tokens, made.out_tokens, made.thought_tokens) == (101, 202, 303)
        assert (made.cost_usd, made.unpriced) == (0.404, True)
        assert (made.proposed, made.kept, made.rejected) == (5, 4, 3)
        assert made.learned_parameters == 2
        assert (made.coverage, made.skew, made.lopsided) == (0.9, -0.5, True)
        assert made.error == "the model would not answer"

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

    async def test_rekey_replaces_the_shape_resolution_compares_against(
        self, store: UnitOfWork
    ) -> None:
        """Run at startup when the rule that makes a key has changed: keys
        mined before the change no longer match keys mined after, and a job
        already held could be proposed again as a new one."""
        async with store as work:
            await work.workflows.save(_workflow("wfl_1"))
            await work.commit()

        async with store as work:
            await work.workflows.rekey(
                TENANT, "wfl_1", (("type", "code", "wms"), ("click", "Save", "wms"))
            )
            # Another tenant's word for the same id is not a key to rewrite.
            await work.workflows.rekey(OTHER_TENANT, "wfl_1", (("nothing", "at", "all"),))
            await work.commit()

        async with store as work:
            assert (await work.workflows.get(TENANT, "wfl_1")).shape_key == [
                ["type", "code", "wms"],
                ["click", "Save", "wms"],
            ]

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
            # Tied with `run_held` on the instant, and planted after it while
            # sorting before it: `proofs` orders `(started_at, id)`.
            await work.workflow_runs.save(
                _run(
                    "run_also_held",
                    live=True,
                    outcome="held",
                    started_at=_at(10),
                    steps=[RunStep(order=0, says="save", verdict="held", result={"wrote": True})],
                )
            )
            await work.workflows.record_effect(
                "wfl_1", run_id="run_held", ord_=1, verified_by="status", at=_at(10)
            )
            await work.commit()

        async with store as work:
            proofs = await work.workflows.proofs(TENANT, "wfl_1")

        assert [one.run_id for one in proofs] == ["run_also_held", "run_held"]
        assert proofs[1].wrote == frozenset({1})
        assert proofs[1].verified == frozenset({1})
        # A written step nobody verified is still a written step.
        assert proofs[0].wrote == frozenset({0})
        assert proofs[0].verified == frozenset()


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

    async def test_recent_is_newest_first_capped_and_filtered_as_the_rig_listed_them(
        self, store: UnitOfWork
    ) -> None:
        """The other order, on purpose: ``for_workflow`` is oldest first for
        ``proofs`` and this is the rig's own list query -- newest first, with
        the cap applied after every predicate rather than before them.

        Three rows for the ordering, because a reversed pair agrees with a
        two-element assertion once in two. The tie is planted as well: an order
        that is not total changes between reads, and a page boundary that moves
        is a row a caller never sees.
        """
        async with store as work:
            # Planted `run_a` first and asserted second: the tie has to
            # disagree with insertion order, or the assertion is satisfied by
            # the tie-break and by its absence equally -- Postgres hands back
            # heap order, and heap order here WAS the answer.
            await work.workflow_runs.save(_run("run_a", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_b", started_at=_at(11)))
            await work.workflow_runs.save(_run("run_oldest", started_at=_at(9)))
            await work.workflow_runs.save(_run("run_elsewhere", workflow_id="wfl_2"))
            await work.workflow_runs.save(_run("run_theirs", tenant=OTHER_TENANT))
            await work.commit()

        async with store as work:
            newest_first = await work.workflow_runs.recent(TENANT, limit=20)
            capped = await work.workflow_runs.recent(TENANT, limit=2)
            one_job = await work.workflow_runs.recent(TENANT, limit=20, workflow_id="wfl_2")

        assert [one.id for one in newest_first] == [
            "run_b",
            "run_a",
            "run_elsewhere",
            "run_oldest",
        ]
        # The cap is the query's, and it keeps the newest rather than whichever
        # the store handed back first.
        assert [one.id for one in capped] == ["run_b", "run_a"]
        assert [one.id for one in one_job] == ["run_elsewhere"]

    async def test_recent_narrows_to_named_ids_and_an_empty_set_matches_nothing(
        self, store: UnitOfWork
    ) -> None:
        """How ``awaiting=true`` is served: the parked runs are a set of ids,
        and an empty set is "nothing matches" rather than "no filter" -- the
        difference between a supervisor's empty queue and every run of the
        tenant presented as work waiting on them."""
        async with store as work:
            await work.workflow_runs.save(_run("run_parked", started_at=_at(9)))
            await work.workflow_runs.save(_run("run_going", started_at=_at(11)))
            await work.commit()

        async with store as work:
            named = await work.workflow_runs.recent(TENANT, limit=20, ids=frozenset({"run_parked"}))
            # Named and capped: the ids narrow first, so a run outside the cap
            # is still found by the queue that asked for it by name.
            narrowed_then_capped = await work.workflow_runs.recent(
                TENANT, limit=1, ids=frozenset({"run_parked"})
            )
            nothing = await work.workflow_runs.recent(TENANT, limit=20, ids=frozenset())

        assert [one.id for one in named] == ["run_parked"]
        assert [one.id for one in narrowed_then_capped] == ["run_parked"]
        assert nothing == ()

    async def test_recent_carries_the_steps_of_every_row_it_returns(
        self, store: UnitOfWork
    ) -> None:
        """The list answers with whole rows, which is what puts every parked
        step on the wire. A read that returned bare run rows would serve a panel
        that cannot tell a parked run from a finished one."""
        async with store as work:
            await work.workflow_runs.save(
                _run(
                    "run_parked",
                    outcome="running",
                    steps=[
                        RunStep(order=1, says="confirm the write", verdict="awaiting"),
                        RunStep(order=3, says="and the second", verdict="awaiting"),
                    ],
                )
            )
            await work.commit()

        async with store as work:
            (found,) = await work.workflow_runs.recent(TENANT, limit=20)

        assert [(step.order, step.says) for step in found.steps] == [
            (1, "confirm the write"),
            (3, "and the second"),
        ]

    async def test_tallies_count_runs_and_holds_per_workflow_for_one_tenant(
        self, store: UnitOfWork
    ) -> None:
        """The two integers ``shapes_for`` gates on, for the whole tenant at
        once. Both halves count rows rather than summing a boolean, so a
        workflow that has run and never held is ``(n, 0)`` and not ``(n,
        None)``; and a workflow with runs in another tenant's warehouse is
        not this tenant's evidence in either direction.
        """
        async with store as work:
            await work.workflow_runs.save(_run("run_held", outcome="held"))
            await work.workflow_runs.save(_run("run_failed", outcome="failed"))
            await work.workflow_runs.save(_run("run_going", outcome="running"))
            # Run, never held: the workflow the gate withdraws.
            await work.workflow_runs.save(_run("run_flop", workflow_id="wfl_2", outcome="failed"))
            # Known, never run. It has no row in the runs index, so it has no
            # key here -- the caller is what turns absent into (0, 0), and an
            # implementation that reached for the workflows table to invent a
            # zero pair would answer differently.
            await work.workflows.save(_workflow("wfl_never_run"))
            # The same workflow id, somebody else's warehouse.
            await work.workflow_runs.save(_run("run_theirs", tenant=OTHER_TENANT, outcome="held"))
            await work.commit()

        async with store as work:
            counted = await work.workflow_runs.tallies(TENANT)

        assert dict(counted) == {"wfl_1": (3, 1), "wfl_2": (1, 0)}

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

    async def test_outcomes_since_counts_by_outcome_and_live_in_the_window(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.workflow_runs.save(_run("run_a", started_at=_at(10), live=True))
            await work.workflow_runs.save(_run("run_b", started_at=_at(11), live=True))
            await work.workflow_runs.save(_run("run_dry", started_at=_at(11)))
            await work.workflow_runs.save(
                _run("run_stopped", started_at=_at(12, offset="+02:00"), outcome="stopped")
            )
            await work.workflow_runs.save(_run("run_before", started_at=_at(8), live=True))
            await work.workflow_runs.save(
                _run("run_theirs", tenant=OTHER_TENANT, started_at=_at(11), live=True)
            )
            await work.commit()

        async with store as work:
            found = await work.workflow_runs.outcomes_since(TENANT, since=_at(9))
        assert sorted(found) == [("held", False, 1), ("held", True, 2), ("stopped", False, 1)]

    async def test_save_upserts_a_runs_steps_and_never_deletes_the_rest(
        self, store: UnitOfWork
    ) -> None:
        """D1: `save` upserts the steps it carries by `order`, changing a step
        already there and adding a step that is new, but never deletes a step
        it does not carry -- a stale save (fewer steps than the row already
        has) must not erase a step another writer has since added."""
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
                _run("run_1", steps=[RunStep(order=0, says="scanned", verdict="read")])
            )
            await work.commit()

        async with store as work:
            kept = await work.workflow_runs.get(TENANT, "run_1")
        assert kept is not None
        by_order = {step.order: step for step in kept.steps}
        assert by_order[0].says == "scanned"
        assert by_order[0].verdict == "read"
        assert by_order[1].says == "place"

    async def test_a_run_carries_back_the_step_it_was_saved_at(self, store: UnitOfWork) -> None:
        """Both repositories, one assertion. The fake keeps a dataclass and the
        SQL mapper copies column by column, so a field the mapper forgets round
        trips as its default through every unit test and loses the operator's
        progress only against real Postgres.

        Non-default on purpose: ``from_step=0`` is what a dropped column
        returns, so an assertion written against the default cannot fail.
        """
        async with store as work:
            await work.workflow_runs.save(_run("run_resumed", from_step=4))
            await work.commit()

        async with store as work:
            read = await work.workflow_runs.get(TENANT, "run_resumed")
        assert read is not None
        assert read.from_step == 4

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
                        # Two parked steps, and the deeper one planted FIRST.
                        # The rig reported only the deepest of these and this
                        # port returns every one, `ord` ascending -- plan 4b's
                        # ruling, and until this second step existed nothing
                        # anywhere held either half of it: a store flipped to
                        # `ord DESC` passed 2710 tests. Planted out of order
                        # because an assertion that agrees with insertion order
                        # agrees with the sort and with its absence equally.
                        RunStep(order=3, says="and let the second out", verdict="awaiting"),
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
                    # A second browser, because one browser may hold one
                    # running run since 0043 -- and because that is what this
                    # read is FOR: the parked steps across browsers, so a
                    # supervisor can answer a run they are not sitting in
                    # front of.
                    device_id=OTHER_DEVICE.value,
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
            ("run_running", 3, "and let the second out"),
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
            await work.workflow_runs.save(_run("run_ant", outcome="running", started_at=_at(10)))
            await work.commit()

        async with store as work:
            assert await work.workflow_runs.in_flight(TENANT, DEVICE) == "run_ant"
            # Per browser, and the other one is unaffected: this read answers
            # "may I put a hand on THIS window", not "is anything happening".
            assert await work.workflow_runs.in_flight(TENANT, OTHER_DEVICE) == "run_other_browser"

    async def test_a_browser_cannot_hold_two_running_runs_at_once(self, store: UnitOfWork) -> None:
        """What `in_flight` used to have to break a tie about.

        This test previously planted TWO running runs for one browser, tied on
        the instant, and asserted `in_flight` named the same one every time --
        because an order that is not total is an order that changes between
        reads. Migration 0043 makes that state unreachable: a unique partial
        index on `(tenant_id, device_id) WHERE outcome = 'running'`, because
        reading "is this browser busy" and then claiming it are two statements
        with awaits between them, and two presses both read free.

        So the tie is gone and what replaces it is the refusal. The `ORDER BY`
        in both implementations stays -- it costs nothing and it is the answer
        if the index is ever dropped -- but it is no longer what stops a second
        hand reaching the same window.
        """
        async with store as work:
            await work.workflow_runs.save(_run("run_first", outcome="running"))
            await work.commit()

        async with store as work:
            with pytest.raises(Conflict) as refused:
                await work.workflow_runs.save(_run("run_second", outcome="running"))
        assert DEVICE.value in str(refused.value)

        async with store as work:
            assert await work.workflow_runs.in_flight(TENANT, DEVICE) == "run_first"

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
            # Five tied, not two: at three the planner handed back the answer
            # the tiebreak wanted anyway and the assertion was satisfied by the
            # bug. A tie big enough to sort is a tie the plan cannot flatter.
            for k in range(1, 6):
                await work.offers.record(_offer(f"off_{k}", k=k, at=_at(10)))
            await work.offers.record(_offer("off_older", k=9, at=_at(9)))
            await work.commit()

        async with store as work:
            window = await work.offers.newest(TENANT, "wfl_1", limit=10)
            # A limit inside the tie, which is the case the rule is for: the
            # tiebreak decides the *set* of three the counsel reads, not only
            # their order, and `K_WINDOW` cuts a real day's offers mid-second.
            narrow = await work.offers.newest(TENANT, "wfl_1", limit=3)
        assert [row.k for row in window] == [5, 4, 3, 2, 1, 9]
        assert [row.k for row in narrow] == [5, 4, 3]

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
            for k in (1, 3, 5, 7, 9):
                await work.offers.record(_offer(f"off_mine_{k}", k=k, at=_at(10)))
            await work.offers.record(
                _offer("off_theirs", k=2, device_id=OTHER_DEVICE.value, at=_at(11))
            )
            await work.commit()

        async with store as work:
            # Two of this browser's, tied on the instant: the same window as
            # `newest`, so the same arrival tiebreak.
            assert [
                row.k
                for row in await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=10)
            ] == [9, 7, 5, 3, 1]
            assert [
                row.k
                for row in await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=3)
            ] == [9, 7, 5]
            # Recognition is a property of the job, not of who was asked.
            assert [row.k for row in await work.offers.newest(TENANT, "wfl_1", limit=10)] == [
                2,
                9,
                7,
                5,
                3,
                1,
            ]

    async def test_since_is_the_whole_offer_newest_first_with_no_window_filters(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.offers.record(_offer("off_nudge", k=0, at=_at(11)))
            await work.offers.record(_offer("off_real", k=2, at=_at(10)))
            # Tied with `off_real`, and later, so `seq DESC` puts it first.
            await work.offers.record(_offer("off_also_real", k=2, at=_at(10)))
            await work.offers.record(_offer("off_before", k=2, at=_at(8)))
            await work.commit()

        async with store as work:
            audited = await work.offers.since(TENANT, since=_at(9))
        assert [one.id for one in audited] == ["off_nudge", "off_also_real", "off_real"]
        assert audited[-1].at == "2026-09-06T10:00:00+00:00"


class TestChats:
    async def test_since_is_newest_first_on_the_instant_and_reads_back_normalised(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.chats.record(_chat("cha_early", at=_at(12, offset="+02:00")))
            # Planted c-then-a while the answer is c-then-a-by-id: the plant
            # order has to disagree with the answer, or the heap satisfies the
            # assertion for free.
            await work.chats.record(_chat("cha_c", at=_at(11)))
            await work.chats.record(_chat("cha_a", at=_at(11)))
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

    async def test_a_gesture_id_is_stored_once(self, store: UnitOfWork) -> None:
        """``add_batch`` raises one method over precisely so a retried upload
        cannot double its gestures, and the id is unique in the store. A fake
        that writes into a dict swallowed the second copy instead -- so every
        suite built on it would prove a doubling the store refuses."""
        async with store as work:
            await work.gestures.add_gestures((_gesture("ges_1"),))
            await work.commit()

        with pytest.raises(Conflict):
            async with store as work:
                await work.gestures.add_gestures((_gesture("ges_1"),))
                await work.commit()

    async def test_no_ids_asked_for_is_nothing_and_never_everything(
        self, store: UnitOfWork
    ) -> None:
        """`ids=()` is "these none"; `ids=None` is "all of them".

        Both readers of this guard the call -- `shapes_for` and `ReadEvidence`
        skip it for a workflow that cites nothing, to keep `IN ()` off
        Postgres -- and their comments say the guard is an optimisation and
        not a null check. That sentence is only true if the two arguments are
        told apart down here. A repository reading empty as absent serves a
        cite-less workflow the tenant's entire store, and it reads as a very
        well-evidenced job.
        """
        async with store as work:
            await work.gestures.add_gestures((_gesture("ges_1"), _gesture("ges_2")))
            await work.commit()

        async with store as work:
            assert await work.gestures.gestures_for(TENANT, ids=()) == ()
            assert len(await work.gestures.gestures_for(TENANT, ids=None)) == 2

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

    async def test_ageing_one_tenant_does_not_age_another(self, store: UnitOfWork) -> None:
        """Retiring on a tenant filter while counting passes without one is the
        sibling mistake: the eviction looks scoped and the clock is not. The
        retirement caps are asked per tenant, so a clock that is not would stay
        silent until the other tenant is next mined -- and then retire its
        whole pool at once. All three shapes of call, because each bumps on a
        predicate of its own."""
        async with store as work:
            await work.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await work.pool.add_unclaimed(OTHER_TENANT, window_ids=("ges_2",), claimed=frozenset())
            await work.pool.age(TENANT)
            await work.pool.age(TENANT, shown=())
            await work.pool.age(TENANT, shown=("ges_1",))
            await work.commit()

        async with store as work:
            theirs = await work.pool.waiting(OTHER_TENANT)
        assert [(one.gesture_id, one.age, one.waited) for one in theirs] == [("ges_2", 0, 0)]


class TestSpend:
    async def test_the_day_is_the_ledger_the_metered_client_writes(self, store: UnitOfWork) -> None:
        """Every model call is one row, whichever door made it. The blind count
        is read beside the sum, never derived from it: a model the price table
        never heard of records $0.00 and ``unpriced``."""
        now = datetime.now(tz=UTC)
        today = now.replace(hour=0, minute=0, second=1, microsecond=0)
        async with store as work:
            await work.spend.record(_spent("spd_1", at=today, cost_usd=0.01))
            await work.spend.record(_spent("spd_2", at=today, unpriced=True))
            await work.spend.record(_spent("spd_3", at=today, cost_usd=0.04))
            await work.spend.record(
                _spent("spd_4", at=today, cost_usd=9.0, tenant=OTHER_TENANT.value)
            )
            await work.spend.record(_spent("spd_5", at=today - timedelta(seconds=2), cost_usd=7.0))
            await work.commit()

        async with store as work:
            spent = await work.spend.today(TENANT, now=now)

        assert spent.cost_usd == pytest.approx(0.05)
        assert spent.blind == 1


def _spent(spent_id: str, *, at: datetime, tenant: str = TENANT.value, **over: Any) -> ModelSpend:
    return ModelSpend(id=spent_id, tenant=tenant, model="gemini-3-flash", at=at, **over)


class TestSinceWindows:
    async def test_a_row_stamped_exactly_at_since_is_inside_the_window(
        self, store: UnitOfWork
    ) -> None:
        """``>=``, not ``>``. An audit that walks forward by asking for
        everything since the last instant it saw drops exactly one row per call
        if the boundary is exclusive, and drops it silently -- the three reads
        that take a `since` all have to agree on which side of the edge it
        falls."""
        edge = _at(9)
        async with store as work:
            await work.offers.record(_offer("off_edge", at=edge))
            await work.chats.record(_chat("cha_edge", at=edge))
            await work.workflow_runs.save(_run("run_edge", started_at=edge))
            await work.commit()

        async with store as work:
            offers = await work.offers.since(TENANT, since=edge)
            chats = await work.chats.since(TENANT, since=edge)
            runs = await work.workflow_runs.since(TENANT, since=edge)

        assert [one.id for one in offers] == ["off_edge"]
        assert [one.id for one in chats] == ["cha_edge"]
        assert [one.id for one in runs] == ["run_edge"]


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
                    # Their second browser: one browser holds one running run.
                    device_id=OTHER_DEVICE.value,
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
            assert dict(await work.workflow_runs.tallies(TENANT)) == {}

            assert await work.offers.newest(TENANT, "wfl_1", limit=10) == ()
            assert await work.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=10) == ()
            assert dict(await work.offers.fates(TENANT, "wfl_1")) == {}
            assert await work.offers.since(TENANT, since=yesterday) == ()

            assert await work.chats.since(TENANT, since=yesterday) == ()

            assert await work.pool.waiting(TENANT) == ()
            assert await work.pool.ids(TENANT) == ()
            assert await work.pool.retired(TENANT) == ()

            assert (await work.spend.today(TENANT, now=datetime.now(tz=UTC))).cost_usd == 0.0


class TestToolCalls:
    """The ledger that stops one job writing the same thing twice.

    Untested against Postgres until now, on either half. `remember` is one
    statement with two shapes -- `ON CONFLICT DO NOTHING`, and with a window
    `ON CONFLICT DO UPDATE ... WHERE claimed_at < at - stale_after RETURNING` --
    and every rule it keeps is expressed in SQL the fake re-states in Python.
    A lost `RETURNING`, a flipped comparison, or `DO NOTHING` where `DO UPDATE`
    belongs was caught by nothing: the fake would keep answering correctly
    while the deployment let a second warehouse record through, or refused the
    same job forever.
    """

    async def test_the_first_claim_is_the_one_that_writes(self, store: UnitOfWork) -> None:
        async with store as work:
            first = await work.tool_calls.remember(TENANT, "wfl_1:1:abc", tool="save", at=_when(9))
            second = await work.tool_calls.remember(TENANT, "wfl_1:1:abc", tool="save", at=_when(9))
            await work.commit()

        assert (first, second) == (True, False)

    async def test_another_key_is_another_write(self, store: UnitOfWork) -> None:
        # The values are in the key, so the same job and step with a different
        # client code is a different record and must not be refused.
        async with store as work:
            assert await work.tool_calls.remember(TENANT, "wfl_1:1:abc", tool="s", at=_when(9))
            assert await work.tool_calls.remember(TENANT, "wfl_1:1:xyz", tool="s", at=_when(9))
            await work.commit()

    async def test_another_tenant_holding_the_same_key_is_not_this_one(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            assert await work.tool_calls.remember(TENANT, "wfl_1:1:abc", tool="s", at=_when(9))
            assert await work.tool_calls.remember(
                OTHER_TENANT, "wfl_1:1:abc", tool="s", at=_when(9)
            )
            await work.commit()

    async def test_a_claim_inside_the_window_still_refuses(self, store: UnitOfWork) -> None:
        window = timedelta(minutes=30)
        async with store as work:
            assert await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(9), stale_after=window
            )
            assert not await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(9, minute=20), stale_after=window
            )
            await work.commit()

    async def test_a_claim_older_than_the_window_is_taken_over(self, store: UnitOfWork) -> None:
        """What lets the same job be done again tomorrow with the same values,
        and the half `RETURNING` carries: the row is updated in place and the
        update is the answer."""
        window = timedelta(minutes=30)
        async with store as work:
            assert await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(9), stale_after=window
            )
            assert await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(10), stale_after=window
            )
            await work.commit()

    async def test_the_window_moves_with_the_claim_that_took_it_over(
        self, store: UnitOfWork
    ) -> None:
        """A taken-over claim is a new claim, so the next one is measured from
        it. Without this the key would be free forever once it had aged once."""
        window = timedelta(minutes=30)
        async with store as work:
            await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(9), stale_after=window
            )
            await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(10), stale_after=window
            )
            assert not await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(10, minute=20), stale_after=window
            )
            await work.commit()

    async def test_no_window_means_the_key_is_claimed_for_good(self, store: UnitOfWork) -> None:
        # `stale_after=None` is the caller saying this write must never be made
        # twice, and a day later is still twice.
        async with store as work:
            assert await work.tool_calls.remember(TENANT, "wfl_1:1:abc", tool="s", at=_when(9))
            assert not await work.tool_calls.remember(
                TENANT, "wfl_1:1:abc", tool="s", at=_when(9) + timedelta(days=1)
            )
            await work.commit()


class TestSkillRunsInFlight:
    """`runs.in_flight`, on both stores, because the fake and the SQL answer it
    from different shapes: a `DeviceId` against a `DeviceId` in Python, and a
    column against `device_id.value` in SQL. The first version of the fake
    compared the identifier to the string and answered `None` for a browser
    that really was busy -- green, and the guard switched off."""

    async def test_the_run_driving_this_browser_is_named(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.runs.add(_skill_run("run_now"))
            await work.commit()

        async with store as work:
            assert await work.runs.in_flight(TENANT, DEVICE) == "run_now"

    async def test_a_finished_run_is_not_driving_anything(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.runs.add(_skill_run("run_done", ended_at=_when(11)))
            await work.commit()

        async with store as work:
            assert await work.runs.in_flight(TENANT, DEVICE) is None

    async def test_another_browser_and_another_tenant_are_not_this_one(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.runs.add(_skill_run("run_theirs", device_id=OTHER_DEVICE))
            await work.runs.add(_skill_run("run_other_tenant", tenant_id=OTHER_TENANT))
            await work.commit()

        async with store as work:
            assert await work.runs.in_flight(TENANT, DEVICE) is None
            assert await work.runs.in_flight(TENANT, OTHER_DEVICE) == "run_theirs"

    async def test_a_run_in_a_browser_of_ours_names_no_device(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.runs.add(_skill_run("run_steel", device_id=None))
            await work.commit()

        async with store as work:
            assert await work.runs.in_flight(TENANT, DEVICE) is None


def _confirmation(
    confirmation_id: str, *, tenant: TenantId = TENANT, answer: Answer = Answer.WAITING
) -> Confirmation:
    return Confirmation(
        id=ConfirmationId(confirmation_id),
        tenant_id=tenant,
        trigger_id=TriggerId("trg_1"),
        asked_at=_when(9),
        expires_at=_when(10),
        workflow_id="wfl_1",
        answer=answer,
    )


class TestTenantsWaiting:
    async def test_each_tenant_with_a_card_still_waiting_once(self, store: UnitOfWork) -> None:
        async with store as work:
            await work.confirmations.add(_confirmation("cnf_1"))
            await work.confirmations.add(_confirmation("cnf_2"))
            await work.confirmations.add(_confirmation("cnf_3", tenant=OTHER_TENANT))
            await work.commit()

        async with store as work:
            assert sorted(t.value for t in await work.confirmations.tenants_waiting()) == [
                "acme",
                "other-corp",
            ]

    async def test_a_tenant_whose_cards_were_all_answered_is_not_waiting(
        self, store: UnitOfWork
    ) -> None:
        async with store as work:
            await work.confirmations.add(_confirmation("cnf_1", answer=Answer.APPROVED))
            await work.confirmations.add(_confirmation("cnf_2", answer=Answer.EXPIRED))
            await work.commit()

        async with store as work:
            assert await work.confirmations.tenants_waiting() == ()


def _lease(lease_id: str, **over: Any) -> Lease:
    fields: dict[str, Any] = {
        "id": lease_id,
        "account": Account.of("acme", "https://wms.example", "lena"),
        "container_url": "http://steel:3000",
        "steel_session_id": f"s-{lease_id}",
        "context_id": f"ctx-{lease_id}",
        "holder": "run_1",
        "heartbeat_at": _when(9),
        "expires_at": _when(9) + K_LEASE_TTL,
        "state": LeaseState.SIGNING_IN,
    }
    fields.update(over)
    return Lease(**fields)


class TestLeases:
    async def test_a_beat_on_a_waiting_lease_never_moves_its_deadline(
        self, store: UnitOfWork
    ) -> None:
        until = _when(9) + timedelta(minutes=10)
        async with store as work:
            await work.browser_sessions.lease(TENANT, _lease("lse_a"))
            await work.browser_sessions.settle(
                TENANT, "lse_a", state=LeaseState.WAITING, until=until
            )
            await work.commit()

        async with store as work:
            # A sibling beats well past the WAITING deadline -- the beat is
            # accepted (it still holds the lease as the caller's), but it
            # must never push a WAITING lease's expiry out.
            assert await work.browser_sessions.beat(
                TENANT, "lse_a", now=until + timedelta(minutes=20)
            )
            await work.commit()

        async with store as work:
            waiting = await work.browser_sessions.get_lease(TENANT, "lse_a")
            assert waiting is not None
            assert waiting.state is LeaseState.WAITING
            assert waiting.expires_at == until
