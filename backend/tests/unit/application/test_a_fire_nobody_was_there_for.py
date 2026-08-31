"""A write that goes off with nobody there.

A manual trigger needs none of this: the click that fires it is the
confirmation. A schedule and an inbound message both fire into an empty room,
and until this existed the honest options were auto-approve -- chosen in
advance by a named person -- or refusing to create the trigger at all.

What the queue must never become is a thing that drains itself. Nothing here
starts a run because time passed; an item nobody answered expires, and expiring
runs nothing. A write that happened because everybody was on holiday is the
failure the whole ladder exists to prevent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.trigger.answer_confirmation import (
    AnswerConfirmation,
    ExpireConfirmations,
    ReadConfirmations,
)
from sro.application.trigger.fire_trigger import FireTrigger
from sro.domain.execution.run import Medium
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TriggerId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.trigger.confirmation import ANSWER_WITHIN, Answer
from sro.domain.trigger.trigger import Trigger, TriggerKind
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeDurableExecution,
    FakeIdFactory,
    FakeRunDispatcher,
    FakeUnitOfWork,
)

AT = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SUPERVISOR = PrincipalId("supervisor@acme.test")
BY_SUPERVISOR = RequestContext(tenant_id=f.TENANT, principal_id=SUPERVISOR)


async def _armed(uow: FakeUnitOfWork, *, requires_confirmation: bool = True) -> Trigger:
    """A skill that writes, and an inbound trigger pointed at it."""
    version = f.skill_version(steps=(f.step(index=0, network_plan=f.network_plan(method="POST")),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    trigger = Trigger(
        id=TriggerId("trg-1"),
        tenant_id=f.TENANT,
        skill_id=skill.id,
        kind=TriggerKind.INBOUND,
        created_by=f.OPERATOR,
        created_at=AT,
        parameters={"shipment_id": "SH-1"},
        writes=True,
        authorized_by=f.OPERATOR,
        requires_confirmation=requires_confirmation,
        inbound_token="a-token",  # noqa: S106 -- the trigger's own, not a credential
        medium=Medium.NETWORK,
    )
    await uow.triggers.add(trigger)
    return trigger


def _fire(uow: FakeUnitOfWork, durable: FakeDurableExecution, *, at: datetime = AT) -> FireTrigger:
    return FireTrigger(uow, FakeClock(at), durable, ids=FakeIdFactory())


def _answer(
    uow: FakeUnitOfWork, durable: FakeDurableExecution, *, at: datetime = AT
) -> AnswerConfirmation:
    return AnswerConfirmation(uow, FakeClock(at), FakeIdFactory(), durable)


async def test_a_write_that_fires_with_nobody_there_becomes_a_card() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)

    fired = await _fire(uow, durable).execute(TriggerId("trg-1"), message={"subject": "Short ship"})

    assert fired.run_id is None
    assert fired.confirmation_id is not None
    assert durable.started == []
    waiting = await ReadConfirmations(uow).execute(CTX)
    assert len(waiting) == 1
    # The one sentence somebody reads before deciding.
    assert waiting[0].because == "Short ship"


async def test_the_trigger_still_says_it_fired() -> None:
    """A schedule showing "never" while filling somebody's queue would be the
    screen disagreeing with the thing it describes."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)

    await _fire(uow, durable).execute(TriggerId("trg-1"))

    trigger = await uow.triggers.get(f.TENANT, TriggerId("trg-1"))
    assert trigger.last_fired_at == AT
    assert trigger.last_run_id is None


async def test_approving_it_starts_the_run_with_the_answerers_name_on_it() -> None:
    """Not the name of whoever created the trigger. An unattended write happens
    because somebody said so, and this is the somebody."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    answered = await _answer(uow, durable).approve(
        BY_SUPERVISOR, confirmation_id=fired.confirmation_id
    )

    assert answered.answer is Answer.APPROVED
    assert len(durable.started) == 1
    assert durable.authorised == [SUPERVISOR.value]
    assert durable.with_values == [{"shipment_id": "SH-1"}]


async def test_it_runs_with_the_values_frozen_when_it_was_asked() -> None:
    """What somebody approves has to be what is written in front of them. A
    trigger edited in between would turn a yes to one thing into a yes to
    another, under the name of the person who pressed the button."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    trigger = await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    trigger.parameters = {"shipment_id": "SOMETHING-ELSE"}
    await uow.triggers.save(trigger)
    await _answer(uow, durable).approve(BY_SUPERVISOR, confirmation_id=fired.confirmation_id)

    assert durable.with_values == [{"shipment_id": "SH-1"}]


async def test_declining_it_runs_nothing_and_says_who_said_no() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    await _answer(uow, durable).decline(
        BY_SUPERVISOR, confirmation_id=fired.confirmation_id, note="wrong dock"
    )

    assert durable.started == []
    declined = await uow.confirmations.get(f.TENANT, fired.confirmation_id)
    assert declined.answer is Answer.DECLINED
    assert declined.answered_by == SUPERVISOR
    assert declined.note == "wrong dock"


async def test_a_card_nobody_answered_in_time_can_never_be_approved() -> None:
    """Answering one that has run out is not a late yes, it is a yes to
    something nobody has looked at since. The trigger fires again if it is
    still true."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    with pytest.raises(InvariantViolation, match="expired without an answer"):
        await _answer(uow, durable, at=AT + ANSWER_WITHIN).approve(
            BY_SUPERVISOR, confirmation_id=fired.confirmation_id
        )

    assert durable.started == []


async def test_nothing_runs_because_time_passed() -> None:
    """The queue must never drain itself. Expiring is a decision to do nothing
    rather than a decision deferred."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    await _fire(uow, durable).execute(TriggerId("trg-1"))

    expired = await ExpireConfirmations(uow, FakeClock(AT + ANSWER_WITHIN)).execute(CTX)

    assert expired == 1
    assert durable.started == []
    # Recorded rather than deleted: "we chose not to" and "we never looked" are
    # different things to read a month later.
    row = next(iter(uow.confirmations.rows.values()))
    assert row.answer is Answer.EXPIRED


async def test_answering_twice_is_refused() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))
    await _answer(uow, durable).approve(BY_SUPERVISOR, confirmation_id=fired.confirmation_id)

    with pytest.raises(InvariantViolation, match="already approved"):
        await _answer(uow, durable).approve(BY_SUPERVISOR, confirmation_id=fired.confirmation_id)

    assert len(durable.started) == 1


async def test_a_trigger_switched_off_after_it_fired_cannot_be_approved() -> None:
    """Somebody decided to stop this task between the fire and the answer.
    Running it now would be running the thing they stopped."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    trigger = await _armed(uow)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    trigger.disable("the supplier changed their process")
    await uow.triggers.save(trigger)

    with pytest.raises(InvariantViolation, match="disabled after it fired"):
        await _answer(uow, durable).approve(BY_SUPERVISOR, confirmation_id=fired.confirmation_id)

    assert durable.started == []


async def test_auto_approve_still_runs_without_asking() -> None:
    """The other honest answer, unchanged: a named person saying in advance
    that this one need not be asked about."""
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow, requires_confirmation=False)

    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    assert fired.confirmation_id is None
    assert fired.run_id is not None
    assert len(durable.started) == 1


async def test_a_card_that_expired_is_no_longer_waiting() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await _armed(uow)
    await _fire(uow, durable).execute(TriggerId("trg-1"))
    await ExpireConfirmations(uow, FakeClock(AT + timedelta(days=2))).execute(CTX)

    assert await ReadConfirmations(uow).execute(CTX) == ()


async def test_approving_a_card_runs_it_in_the_browser_the_trigger_named() -> None:
    """Found by pressing the button.

    `approve` called `execute_skill` directly instead of the start a fire uses,
    which quietly dropped the trigger's `device_id`: a card for a task bound to
    the operator's own browser drove a browser this deployment owns, failed to
    attach to a CDP endpoint nobody was listening on, and left the card already
    marked approved.
    """
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    dispatcher = FakeRunDispatcher()
    trigger = await _armed(uow)
    trigger.device_id = DeviceId("dev-1")
    await uow.triggers.save(trigger)
    fired = await _fire(uow, durable).execute(TriggerId("trg-1"))

    await AnswerConfirmation(uow, FakeClock(AT), FakeIdFactory(), durable, dispatcher).approve(
        BY_SUPERVISOR, confirmation_id=fired.confirmation_id
    )

    # In the operator's browser, and nowhere else.
    assert dispatcher.with_values == [{"shipment_id": "SH-1"}]
    assert durable.started == []
