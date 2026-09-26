"""A mined job put on a clock, and what happens when the clock comes round.

Until this existed nothing could start a rig workflow except a person accepting
an offer in the panel: `Trigger` named a `SkillId` and nothing else. A job that
has earned its autonomy -- three live runs whose every write a state belt
verified -- still had to wait for somebody to be looking at the right tab.

The theme is the same one the skill half has, with one difference worth saying
out loud. The skill path checks `runnable`, `changes_the_system` and
`blank_inputs` here because nothing downstream will. The job path checks almost
nothing here on purpose: `run_workflow` is dry until somebody presses through
to live, a live write parks for a person until the job has EARNED the right,
and every step is verified before the next is sent. What these tests pin is
that the plumbing reaches that ladder rather than inventing a weaker one beside
it.
"""

from __future__ import annotations

from collections.abc import Coroutine
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.trigger.answer_confirmation import AnswerConfirmation
from sro.application.trigger.create_trigger import CreateTrigger, NewTrigger, TriggerRefused
from sro.application.trigger.fire_trigger import FireTrigger
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.template import Template
from sro.domain.skill.workflow import Step, Workflow
from sro.domain.trigger.trigger import TriggerKind
from sro.domain.trigger.watch import QUESTION, Term, TermField, ValueAt, Watch
from tests import factories as f
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeClock,
    FakeDurableExecution,
    FakeIdFactory,
    FakeRunDispatcher,
    FakeScheduler,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
LAPTOP = DeviceId("dev-1")
EVERY_WEEKDAY = "0 7 * * 1-5"
NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
WMS = "https://wms.acme.test"


class _Dropped(Pursuits):
    """Holds what was spawned instead of running it.

    Every test here is about what reaches `StartWorkflowRun.execute` -- the
    claimed row, the browser, `live` -- and awaiting `perform` would drive the
    whole loop against a fake channel to learn nothing about the trigger. The
    coroutine is closed rather than left pending, or the event loop warns about
    it at teardown and the warning is louder than the test.
    """

    def __init__(self) -> None:
        super().__init__()
        self.spawned = 0

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        self.spawned += 1
        coroutine.close()


class _Closed(FakeChannel):
    """No browser of this tenant's is connected."""

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return ()


def _job(*, workflow_id: str = "wfl_1") -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant=f.TENANT.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[Step(order=n, says=f"step {n}", system=None, cites=[f"ges-{n}"]) for n in range(2)],
        parameters=[{"name": "clientCode", "seen_values": ["NEWTESTS"]}],
    )


def _gesture(gesture_id: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=f.TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_739_314_800.0,
        url=f"{WMS}/work-areas",
        system=WMS,
        tab_id=7,
        frame_url=None,
        action=Action(
            kind="click",
            at=1_739_314_800.0,
            url=f"{WMS}/work-areas",
            target=Target(role="button", name="Save"),
        ),
    )


async def _held(job: Workflow | None = None) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    stored = job or _job()
    await uow.workflows.save(stored)
    await uow.gestures.add_gestures(
        tuple(_gesture(cited) for step in stored.steps for cited in step.cites)
    )
    return uow


def _starter(
    uow: FakeUnitOfWork,
    *,
    durable: FakeDurableExecution | None = None,
    steel_tenants: frozenset[str] = frozenset(),
) -> StartWorkflowRun:
    return StartWorkflowRun(
        uow,
        channel=FakeChannel(),
        asker=FakeAsker(),
        plan_model="gemini-3.8-flash-preview",
        rescue_model="gemini-3.1-pro-preview-rig",
        clock=FakeClock(NOW),
        cap_usd=5.0,
        stops=Stops(),
        approvals=Approvals(),
        one_time_secrets=OneTimeSecrets(),
        durable=durable,
        steel_tenants=steel_tenants,
    )


def _create(
    uow: FakeUnitOfWork,
    scheduler: FakeScheduler,
    *,
    can_gather: bool = False,
    start_run: StartWorkflowRun | None = None,
) -> CreateTrigger:
    return CreateTrigger(
        uow,
        FakeClock(NOW),
        FakeIdFactory(),
        scheduler,
        can_gather=can_gather,
        start_run=start_run,
    )


def _new(**over: object) -> NewTrigger:
    asked: dict[str, object] = {
        "workflow_id": "wfl_1",
        "cron": EVERY_WEEKDAY,
        "parameters": {"clientCode": "NEWTESTS"},
        "device_id": LAPTOP,
        "authorized_by": True,
    }
    asked.update(over)
    return NewTrigger(**asked)


def _fire(
    uow: FakeUnitOfWork,
    *,
    starter: StartWorkflowRun | None = None,
    pursuits: Pursuits | None = None,
) -> FireTrigger:
    return FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        start_run=starter,
        pursuits=pursuits,
    )


# Creating one


async def test_a_proven_job_on_a_weekday_morning_is_a_write_with_a_name_on_it() -> None:
    uow, scheduler = await _held(), FakeScheduler()

    trigger = await _create(uow, scheduler).execute(CTX, _new())

    assert trigger.workflow_id == "wfl_1"
    assert trigger.skill_id is None
    # Not computed from the steps. A standing authority to drive somebody's
    # browser through a recording of real work is a write by the honest
    # reading, whatever the recording happened to contain.
    assert trigger.writes is True
    assert trigger.authorized_by == f.OPERATOR
    assert trigger.requires_confirmation is True
    assert scheduler.scheduled == {trigger.id.value: EVERY_WEEKDAY}


async def test_a_job_with_no_browser_named_is_refused_rather_than_run_headless() -> None:
    # A workflow is a recording of somebody's own window. There is no headless
    # path for one on the extension, so a trigger without a device would fail
    # every morning.
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="browser"):
        await _create(uow, scheduler).execute(CTX, _new(device_id=None))


async def test_a_steel_tenant_s_job_trigger_names_no_browser() -> None:
    # Its runs start on the server and drive nobody's browser.
    uow, scheduler = await _held(), FakeScheduler()
    steel = _starter(uow, durable=FakeDurableExecution(), steel_tenants=frozenset({f.TENANT.value}))

    trigger = await _create(uow, scheduler, start_run=steel).execute(CTX, _new(device_id=None))

    assert trigger.device_id is None


async def test_a_job_nobody_stood_behind_is_refused() -> None:
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="authorised"):
        await _create(uow, scheduler).execute(CTX, _new(authorized_by=False))


async def test_a_value_the_job_declares_and_nobody_supplied_is_refused_now() -> None:
    # `StartWorkflowRun` refuses a press that leaves one blank, which for a
    # schedule means failing at 3am every night instead of once, here.
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="clientCode"):
        await _create(uow, scheduler).execute(CTX, _new(parameters={}))


async def test_a_message_pointed_at_a_parameter_the_job_has_not_got_is_refused() -> None:
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="shipment_id"):
        await _create(uow, scheduler).execute(CTX, _new(from_message=("shipment_id",)))


def _watching(**over: object) -> NewTrigger:
    """A watch on a mined job: the rule that recognises the mail, and the job
    it fires."""
    asked: dict[str, object] = {
        "kind": TriggerKind.WATCH,
        "cron": None,
        "watch": Watch(
            host="mail.google.com",
            terms=(Term(field=TermField.SUBJECT, contains="customer type"),),
            subject_at=SUBJECT_IS_HERE,
            values=(),
        ),
    }
    asked.update(over)
    return _new(**asked)


async def test_a_job_can_be_watched_for_where_a_run_can_go_and_find_the_rest() -> None:
    """The refusal this replaces said a watch on a job would be "a card with no
    sentence on it", because the match path read a SKILL's inputs to say what
    the mail did not name. It reads a job's parameters now, and a run reads the
    mailbox for whatever neither the trigger nor the rule supplied.
    """
    uow, scheduler = await _held(), FakeScheduler()

    trigger = await _create(uow, scheduler, can_gather=True).execute(CTX, _watching())

    assert trigger.workflow_id == "wfl_1"
    # The rule itself, on the row. Without it the trigger is a watch that
    # matches nothing, which never fires and never says why.
    assert trigger.watch is not None and trigger.watch.host == "mail.google.com"
    assert scheduler.scheduled == {}, "a watch is evaluated by a browser, not by a clock"


async def test_a_deployment_that_cannot_look_still_refuses_a_job_it_could_not_fill() -> None:
    """The relaxation is only where it can be kept. With no mailbox to read,
    a parameter neither the trigger nor the mail supplies is a run that fails
    every time it fires -- refused once, now, in front of a person."""
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="this job needs"):
        await _create(uow, scheduler).execute(CTX, _watching(parameters={}))


async def test_a_trigger_runs_one_thing_and_says_so_rather_than_raising_a_500() -> None:
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="both"):
        await _create(uow, scheduler).execute(CTX, _new(skill_id=SkillId("skill-1")))

    with pytest.raises(TriggerRefused, match="neither"):
        await _create(uow, scheduler).execute(CTX, _new(workflow_id=None))


# Firing one


async def test_firing_an_auto_approved_job_starts_a_live_run_in_that_browser() -> None:
    """Live, always, and that is not a loosening.

    A dry run of a scheduled job sends nothing and verifies nothing: it is a
    trigger that appears to work. What keeps it safe is the ladder underneath
    -- a live write parks for a person until the job has earned the right.
    """
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))
    pursuits = _Dropped()

    fired = await _fire(uow, starter=_starter(uow), pursuits=pursuits).execute(trigger.id)

    assert fired.run_id is not None
    assert fired.confirmation_id is None
    assert pursuits.spawned == 1
    run = await uow.workflow_runs.get(f.TENANT, fired.run_id.value)
    assert run.live is True
    assert run.device_id == LAPTOP.value
    assert run.values == {"clientCode": "NEWTESTS"}
    # The trigger's own default: a schedule at 3am has no business taking
    # somebody's screen.
    assert run.allow_focus is False


async def test_a_job_that_asks_first_becomes_a_card_naming_the_job() -> None:
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new())
    pursuits = _Dropped()

    fired = await _fire(uow, starter=_starter(uow), pursuits=pursuits).execute(trigger.id)

    assert fired.run_id is None
    assert fired.confirmation_id is not None
    assert pursuits.spawned == 0
    card = await uow.confirmations.get(f.TENANT, fired.confirmation_id)
    assert card.workflow_id == "wfl_1"
    assert card.skill_id is None
    assert card.values == {"clientCode": "NEWTESTS"}


async def test_approving_the_card_starts_the_run_under_the_name_that_pressed_it() -> None:
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new())
    pursuits = _Dropped()
    fired = await _fire(uow, starter=_starter(uow), pursuits=pursuits).execute(trigger.id)
    assert fired.confirmation_id is not None
    supervisor = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("supervisor-9"))

    answered = await AnswerConfirmation(
        uow,
        FakeClock(NOW),
        FakeIdFactory(),
        FakeDurableExecution(),
        start_run=_starter(uow),
        pursuits=pursuits,
    ).approve(supervisor, confirmation_id=fired.confirmation_id)

    assert answered.run_id is not None
    run = await uow.workflow_runs.get(f.TENANT, answered.run_id.value)
    assert run.live is True
    assert run.device_id == LAPTOP.value
    assert run.started_by == "supervisor-9"
    assert uow.triggers.rows[trigger.id.value].last_run_id == answered.run_id


async def test_a_process_with_no_way_to_drive_a_browser_skips_rather_than_crashes() -> None:
    # The same shape the skill half's `dispatcher` has: a worker with no
    # channel to an extension skips the fire.
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))

    fired = await _fire(uow).execute(trigger.id)

    assert fired.run_id is None
    assert fired.skipped == "this process cannot start a job"
    assert uow.triggers.rows[trigger.id.value].enabled is True


async def test_a_job_trigger_whose_browser_was_forgotten_disables_itself() -> None:
    """Refused at creation, so this is a row written before that check existed.
    A trigger that can never reach a browser is not one to retry every hour."""
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))
    stored = uow.triggers.rows[trigger.id.value]
    object.__setattr__(stored, "device_id", None)

    fired = await _fire(uow, starter=_starter(uow), pursuits=_Dropped()).execute(trigger.id)

    assert fired.run_id is None
    assert uow.triggers.rows[trigger.id.value].enabled is False
    assert "browser" in (fired.skipped or "")


async def test_a_steel_tenant_s_trigger_fires_with_no_browser() -> None:
    uow, scheduler, durable = await _held(), FakeScheduler(), FakeDurableExecution()
    starter = _starter(uow, durable=durable, steel_tenants=frozenset({f.TENANT.value}))
    trigger = await _create(uow, scheduler, start_run=starter).execute(
        CTX, _new(auto_approve=True, device_id=None)
    )

    fired = await _fire(uow, starter=starter).execute(trigger.id)

    assert fired.run_id is not None
    run = await uow.workflow_runs.get(f.TENANT, fired.run_id.value)
    assert (run.executor, run.device_id) == ("steel", "")
    assert [one for one, _ in durable.runs_started] == [fired.run_id.value]


async def test_a_steel_trigger_with_no_browser_is_dispatched_with_none() -> None:
    uow, scheduler = await _held(), FakeScheduler()
    steel = _starter(uow, durable=FakeDurableExecution(), steel_tenants=frozenset({f.TENANT.value}))
    trigger = await _create(uow, scheduler, start_run=steel).execute(
        CTX, _new(auto_approve=True, device_id=None)
    )
    elsewhere = FakeRunDispatcher()

    await FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        dispatcher=elsewhere,
        start_run=steel,
        pursuits=_Dropped(),
    ).execute(trigger.id)

    assert elsewhere.asked == [("wfl_1", None)]


async def test_another_tenants_job_is_not_found_rather_than_scheduled() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    theirs = _job()
    theirs.tenant = TenantId("other-corp").value
    await uow.workflows.save(theirs)

    with pytest.raises(NotFound):
        await _create(uow, scheduler).execute(CTX, _new())


async def test_a_closed_laptop_is_skipped_rather_than_retried_all_night() -> None:
    """A `Conflict`, not a `DispatchFailed`.

    The job path has no dispatcher -- it presses the same door the console
    does, and that door refuses an offline browser with a conflict. Raised out
    of the fire it would reach the scheduler as a failed activity and be
    retried until somebody opened the laptop.
    """
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))
    nobody_home = _starter(uow)
    object.__setattr__(nobody_home, "_channel", _Closed())

    fired = await _fire(uow, starter=nobody_home, pursuits=_Dropped()).execute(trigger.id)

    assert fired.run_id is None
    assert "not connected" in (fired.skipped or "")
    assert uow.triggers.rows[trigger.id.value].enabled is True


async def test_the_worker_asks_the_process_that_holds_the_browser() -> None:
    """The reason `start_job` exists at all.

    A schedule fires inside the Temporal worker, and the socket to that Chrome
    is held by whichever process the extension connected to. Started in-process
    there, `StartWorkflowRun` looks for the browser in its own empty register
    and skips forever with "not connected" -- the same trap the skill path
    escaped with a dispatcher, and the job path needed its own way out.
    """
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))
    elsewhere = FakeRunDispatcher()
    pursuits = _Dropped()

    fired = await FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        dispatcher=elsewhere,
        start_run=_starter(uow),
        pursuits=pursuits,
    ).execute(trigger.id)

    assert fired.run_id is not None
    assert elsewhere.asked == [("wfl_1", "dev-1")]
    assert elsewhere.with_values == [{"clientCode": "NEWTESTS"}]
    # Handed over, not started here: nothing was claimed in this process and
    # nothing was spawned in it either.
    assert pursuits.spawned == 0
    assert uow.workflow_runs.rows == {}
    assert uow.triggers.rows[trigger.id.value].last_run_id == fired.run_id


async def test_a_dispatched_job_carries_the_triggers_focus_decision() -> None:
    # The process that holds the socket is not the process that read the
    # trigger, so whether somebody's screen may be taken has to travel.
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(
        CTX, _new(auto_approve=True, may_take_focus=True)
    )
    elsewhere = FakeRunDispatcher()

    await FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        dispatcher=elsewhere,
    ).execute(trigger.id)

    assert elsewhere.may_take_focus is True


async def test_a_worker_that_cannot_reach_the_other_process_skips_the_fire() -> None:
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))

    fired = await FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        dispatcher=FakeRunDispatcher(reachable=False),
    ).execute(trigger.id)

    assert fired.run_id is None
    assert "no channel open" in (fired.skipped or "")
    assert uow.triggers.rows[trigger.id.value].enabled is True


# A watch that asks instead of running


SUBJECT_IS_HERE = ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("h2.hP"))


def _asking() -> NewTrigger:
    """A mail that carries a question, and where in it the question is."""
    return NewTrigger(
        workflow_id=None,
        cron=None,
        parameters={},
        device_id=LAPTOP,
        kind=TriggerKind.WATCH,
        asks=True,
        watch=Watch(
            host="mail.google.com",
            terms=(Term(field=TermField.SUBJECT, contains="how many"),),
            subject_at=SUBJECT_IS_HERE,
            values=(
                ValueAt(
                    name=QUESTION,
                    where=ControlLocator(
                        strategy=LocatorStrategy.CSS_PATH, query=Template("div.mail-body")
                    ),
                ),
            ),
        ),
    )


async def test_a_watch_that_asks_is_held_to_none_of_the_job_checks() -> None:
    """There is no job. What is left is the browser that reads the mail and
    the question it reads."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()

    trigger = await _create(uow, scheduler).execute(CTX, _asking())

    assert trigger.asks
    assert trigger.workflow_id is None and trigger.skill_id is None
    assert trigger.writes is False
    assert trigger.requires_confirmation is False, "a read has nothing to ask anybody about"
    assert scheduler.scheduled == {}, "a watch is evaluated by a browser, not by a clock"


async def test_a_question_with_nowhere_to_read_it_is_refused_with_a_sentence() -> None:
    # Otherwise it fires on every mail from that sender and looks up nothing.
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    without = replace(
        _asking(),
        watch=Watch(
            host="mail.google.com",
            terms=(Term(field=TermField.SUBJECT, contains="how many"),),
            subject_at=SUBJECT_IS_HERE,
            values=(),
        ),
    )

    with pytest.raises(TriggerRefused, match="where in the mail"):
        await _create(uow, scheduler).execute(CTX, without)

    assert uow.triggers.rows == {}


async def test_a_question_that_also_names_a_job_is_refused_as_a_sentence_not_a_500() -> None:
    uow, scheduler = await _held(), FakeScheduler()

    with pytest.raises(TriggerRefused, match="runs nothing"):
        await _create(uow, scheduler).execute(CTX, replace(_asking(), workflow_id="wfl_1"))

    assert uow.triggers.rows == {}


async def test_a_retired_jobs_schedule_is_taken_down_rather_than_failing_every_period() -> None:
    """Final review M-4, 2026-09-24: a retired job's schedule fired into
    NotFound every period, and nobody was told. A trigger on a retired job is
    not chosen, so the fire finds none and removes the schedule."""
    uow, scheduler = await _held(), FakeScheduler()
    trigger = await _create(uow, scheduler).execute(CTX, _new(auto_approve=True))
    await uow.workflows.retire(f.TENANT, "wfl_1", at=NOW)
    fire = FireTrigger(
        uow,
        FakeClock(NOW),
        FakeDurableExecution(),
        ids=FakeIdFactory(),
        scheduler=scheduler,
        start_run=_starter(uow),
        pursuits=_Dropped(),
    )

    fired = await fire.execute(trigger.id)

    assert (fired.run_id, fired.skipped) == (None, "no such trigger")
    assert scheduler.unschedule_calls == [trigger.id.value]
    assert await uow.triggers.list_for_tenant(f.TENANT) == ()
