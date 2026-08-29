"""Creating a trigger, and what happens when the clock comes round.

The theme: a scheduled run has nobody to ask. Everything that could need asking
is settled at creation, and anything that changes afterwards stops the trigger
rather than guessing.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.trigger.create_trigger import CreateTrigger, NewTrigger, TriggerRefused
from sro.application.trigger.fire_trigger import FireTrigger
from sro.application.trigger.read_triggers import DeleteTrigger, SetTriggerEnabled
from sro.application.trigger.receive_inbound import InboundRefused, ReceiveInbound
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId, SkillId, TriggerId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.domain.trigger.watch import Term, TermField, ValueAt, Watch
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeDurableExecution,
    FakeIdFactory,
    FakeRunDispatcher,
    FakeScheduler,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
EVERY_WEEKDAY = "0 7 * * 1-5"


async def _skill(uow: FakeUnitOfWork, *, writes: bool, runnable: bool = True) -> SkillId:
    skill = f.skill(versions=0)
    plan = f.network_plan(method="POST" if writes else "GET", body=None)
    version = f.skill_version(steps=(f.step(network_plan=plan),))
    skill.add_version(version)
    if runnable:
        version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    return skill.id


def _create(uow: FakeUnitOfWork, scheduler: FakeScheduler) -> CreateTrigger:
    return CreateTrigger(uow, FakeClock(), FakeIdFactory(), scheduler)


async def test_a_read_on_a_weekday_morning_needs_nobody_to_authorise_it() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "12345"}),
    )

    assert trigger.enabled is True
    assert trigger.writes is False
    assert scheduler.scheduled == {trigger.id.value: EVERY_WEEKDAY}


async def test_a_scheduled_write_with_nobody_behind_it_is_refused_at_creation() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=True)

    with pytest.raises(TriggerRefused, match="authorised"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"}),
        )

    assert scheduler.scheduled == {}
    assert uow.triggers.rows == {}


async def test_a_scheduled_write_has_nowhere_to_ask_so_it_says_so() -> None:
    """The confirmation queue does not exist yet. The honest options are
    auto-approve, chosen by a named person, or start it by hand."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=True)

    with pytest.raises(TriggerRefused, match="confirmation"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                cron=EVERY_WEEKDAY,
                parameters={"shipment_id": "1"},
                authorized_by=True,
            ),
        )


async def test_auto_approve_lets_a_write_go_on_a_clock_with_a_name_on_it() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=True)

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            cron=EVERY_WEEKDAY,
            parameters={"shipment_id": "1"},
            authorized_by=True,
            auto_approve=True,
        ),
    )

    assert trigger.authorized_by == f.OPERATOR
    assert trigger.auto_approves is True


async def test_a_value_the_skill_needs_and_nobody_supplied_is_refused_now() -> None:
    # It would fail every single time it fired, at an hour when nobody is
    # reading the failures.
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)

    with pytest.raises(TriggerRefused, match="shipment_id"):
        await _create(uow, scheduler).execute(
            CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY)
        )


async def test_a_skill_that_has_never_been_rehearsed_cannot_be_put_on_a_clock() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False, runnable=False)

    with pytest.raises(TriggerRefused, match="rehearsed"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"}),
        )


async def test_a_trigger_that_could_not_be_scheduled_is_never_stored() -> None:
    """A stored trigger with no schedule is a task somebody believes is covered
    and is not."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler(available=False)
    skill_id = await _skill(uow, writes=False)

    with pytest.raises(Exception, match="switched off"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"}),
        )

    assert uow.triggers.rows == {}


async def test_firing_starts_the_run_durably_and_records_which_one() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"})
    )
    durable = FakeDurableExecution()

    fired = await FireTrigger(uow, FakeClock(), durable, ids=FakeIdFactory()).execute(trigger.id)

    assert fired.run_id is not None
    assert fired.skipped is None
    assert uow.triggers.rows[trigger.id.value].last_run_id == fired.run_id


async def test_a_network_fire_does_not_block_on_the_run_finishing() -> None:
    # wait=False alone is not fire-and-forget: the durable adapter's
    # fast-return path only takes it once a run id is already there to
    # hand back, so a fire without one blocked a worker slot regardless
    # of the flag.
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"})
    )
    durable = FakeDurableExecution()

    fired = await FireTrigger(uow, FakeClock(), durable, ids=FakeIdFactory()).execute(trigger.id)

    assert durable.waited == [False]
    assert fired.run_id is not None


async def test_a_trigger_bound_to_a_browser_is_asked_for_where_that_browser_is() -> None:
    # The channel to a Chrome is held by whichever process the extension
    # connected to, and the scheduler's worker is not that one.
    uow, scheduler, dispatcher = FakeUnitOfWork(), FakeScheduler(), FakeRunDispatcher()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            cron=EVERY_WEEKDAY,
            parameters={"shipment_id": "1"},
            device_id=DeviceId("dev-1"),
        ),
    )
    durable = FakeDurableExecution()

    fired = await FireTrigger(
        uow, FakeClock(), durable, ids=FakeIdFactory(), dispatcher=dispatcher
    ).execute(trigger.id)

    assert dispatcher.asked == [(skill_id.value, "dev-1")]
    assert fired.run_id is not None


async def test_a_closed_laptop_is_skipped_rather_than_disabling_the_trigger() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    dispatcher = FakeRunDispatcher(reachable=False)
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            cron=EVERY_WEEKDAY,
            parameters={"shipment_id": "1"},
            device_id=DeviceId("dev-1"),
        ),
    )

    fired = await FireTrigger(
        uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory(), dispatcher=dispatcher
    ).execute(trigger.id)

    assert fired.run_id is None
    assert "channel" in (fired.skipped or "")
    assert uow.triggers.rows[trigger.id.value].enabled is True


async def test_a_skill_re_induced_into_something_that_writes_stops_its_trigger() -> None:
    """The authorisation on this trigger was given for a task that did not
    write, and it does not carry over."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"})
    )

    skill = await uow.skills.get(f.TENANT, skill_id)
    writing = f.skill_version(
        version=2, steps=(f.step(network_plan=f.network_plan(method="POST", body=None)),)
    )
    skill.add_version(writing)
    writing.promote(PromotionStage.SHADOW, f.at(900), f.OPERATOR)

    fired = await FireTrigger(
        uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory()
    ).execute(trigger.id)

    assert fired.run_id is None
    assert uow.triggers.rows[trigger.id.value].enabled is False
    assert "authorise this trigger again" in (fired.skipped or "")


async def test_a_schedule_that_outlived_its_trigger_removes_itself() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    scheduler.scheduled["trg-gone"] = EVERY_WEEKDAY

    fired = await FireTrigger(
        uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory(), scheduler=scheduler
    ).execute(TriggerId("trg-gone"))

    assert fired.skipped == "no such trigger"
    assert scheduler.scheduled == {}


async def test_pausing_a_trigger_leaves_no_schedule_behind_to_fire_into_a_check() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"})
    )

    paused = await SetTriggerEnabled(uow, scheduler).execute(
        CTX, trigger_id=trigger.id, enabled=False, reason="the cutover"
    )

    assert paused.enabled is False
    assert scheduler.scheduled == {}

    resumed = await SetTriggerEnabled(uow, scheduler).execute(
        CTX, trigger_id=trigger.id, enabled=True
    )
    assert scheduler.scheduled == {trigger.id.value: EVERY_WEEKDAY}
    assert resumed.disabled_reason is None


async def test_deleting_another_tenants_trigger_is_not_found_rather_than_done() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    uow.triggers.rows["trg-theirs"] = Trigger(
        id=TriggerId("trg-theirs"),
        tenant_id=f.TenantId("other-corp"),
        skill_id=SkillId("skill-1"),
        kind=TriggerKind.SCHEDULE,
        created_by=f.OPERATOR,
        created_at=f.at(0),
        cron=EVERY_WEEKDAY,
    )

    with pytest.raises(NotFound):
        await DeleteTrigger(uow, scheduler).execute(CTX, trigger_id=TriggerId("trg-theirs"))

    assert "trg-theirs" in uow.triggers.rows


async def test_deleting_an_inbound_trigger_never_asks_the_scheduler() -> None:
    # It was never registered with Temporal in the first place -- an outage
    # there must not be able to block deleting something that never depended
    # on it, the same gate SetTriggerEnabled already applies.
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, kind=TriggerKind.INBOUND, parameters={"shipment_id": "1"}),
    )

    await DeleteTrigger(uow, scheduler).execute(CTX, trigger_id=trigger.id)

    assert scheduler.unschedule_calls == []
    assert trigger.id.value not in uow.triggers.rows


async def test_an_inbound_trigger_is_minted_with_its_own_token() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, kind=TriggerKind.INBOUND, parameters={"shipment_id": "1"}),
    )

    assert trigger.inbound_token is not None
    assert trigger.cron is None
    assert scheduler.scheduled == {}


async def test_an_inbound_write_has_nowhere_to_ask_so_it_says_so() -> None:
    # The same gap a scheduled write has: nobody is there when the message
    # arrives, so auto_approve, a named person, or waiting are the only honest
    # options -- exactly like a schedule, and unlike a manual "fire now".
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=True)

    with pytest.raises(TriggerRefused, match="confirmation"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                kind=TriggerKind.INBOUND,
                parameters={"shipment_id": "1"},
                authorized_by=True,
            ),
        )


async def test_auto_approve_lets_an_inbound_write_through() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=True)

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            kind=TriggerKind.INBOUND,
            parameters={"shipment_id": "1"},
            authorized_by=True,
            auto_approve=True,
        ),
    )

    assert trigger.auto_approves is True
    assert trigger.inbound_token is not None


async def test_receiving_an_inbound_message_with_the_right_token_fires_it() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, kind=TriggerKind.INBOUND, parameters={"shipment_id": "1"}),
    )
    assert trigger.inbound_token is not None
    fire = FireTrigger(uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory())

    fired = await ReceiveInbound(uow, fire).execute(trigger.id, token=trigger.inbound_token)

    assert fired.run_id is not None


async def test_receiving_an_inbound_message_with_the_wrong_token_is_refused() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, kind=TriggerKind.INBOUND, parameters={"shipment_id": "1"}),
    )
    fire = FireTrigger(uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory())

    with pytest.raises(InboundRefused):
        await ReceiveInbound(uow, fire).execute(trigger.id, token="not-the-token")  # noqa: S106


async def test_receiving_for_a_trigger_that_is_not_inbound_is_refused() -> None:
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX, NewTrigger(skill_id=skill_id, cron=EVERY_WEEKDAY, parameters={"shipment_id": "1"})
    )
    fire = FireTrigger(uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory())

    with pytest.raises(InboundRefused):
        await ReceiveInbound(uow, fire).execute(trigger.id, token="anything")  # noqa: S106


async def test_a_non_ascii_token_is_refused_not_a_crash() -> None:
    # hmac.compare_digest raises TypeError on a non-ASCII str, and Starlette
    # decodes every header through latin-1 -- any byte >= 0x80 becomes one.
    # A crash here would answer 500 instead of 404, telling an unauthenticated
    # caller its id was real when a wrong token alone would have said nothing.
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(skill_id=skill_id, kind=TriggerKind.INBOUND, parameters={"shipment_id": "1"}),
    )
    fire = FireTrigger(uow, FakeClock(), FakeDurableExecution(), ids=FakeIdFactory())

    with pytest.raises(InboundRefused):
        await ReceiveInbound(uow, fire).execute(trigger.id, token="caf\xe9")  # noqa: S106


async def test_whether_a_fire_may_take_the_operator_s_screen_is_the_trigger_s_answer() -> None:
    """A schedule firing at 3am has no business moving somebody's tab, and one
    the operator set up to watch may.

    The decision travels with the dispatch because the process holding that
    browser's socket is not the process that read the trigger -- and it is the
    trigger's to make, never the browser's.
    """
    for allowed in (True, False):
        uow, scheduler, dispatcher = FakeUnitOfWork(), FakeScheduler(), FakeRunDispatcher()
        skill_id = await _skill(uow, writes=False)
        trigger = await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                cron=EVERY_WEEKDAY,
                parameters={"shipment_id": "1"},
                device_id=DeviceId("dev-1"),
                may_take_focus=allowed,
            ),
        )

        await FireTrigger(
            uow,
            FakeClock(),
            FakeDurableExecution(),
            ids=FakeIdFactory(),
            dispatcher=dispatcher,
        ).execute(trigger.id)

        assert dispatcher.may_take_focus is allowed, (
            f"a trigger with may_take_focus={allowed} dispatched {dispatcher.may_take_focus}"
        )


async def _skill_needing(uow: FakeUnitOfWork, *names: str) -> SkillId:
    """A skill whose run needs each of these values supplied."""
    skill = f.skill(versions=0)
    url = "https://wms.test/api/orders?" + "&".join(f"{name}=${{{name}}}" for name in names)
    version = f.skill_version(
        steps=(f.step(network_plan=f.network_plan(method="GET", body=None, url=Template(url))),),
        parameters=tuple(f.parameter(name=name) for name in names),
    )
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    return skill.id


async def test_a_mail_supplies_the_order_it_names_and_nothing_else() -> None:
    """The whole point of an inbound trigger: the facility is settled once, at
    creation, and the order number arrives with each message."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill_needing(uow, "facility", "order_id")
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            kind=TriggerKind.INBOUND,
            parameters={"facility": "DC01"},
            from_message=("order_id",),
        ),
    )
    assert trigger.inbound_token is not None
    durable = FakeDurableExecution()
    fire = FireTrigger(uow, FakeClock(), durable, ids=FakeIdFactory())

    await ReceiveInbound(uow, fire).execute(
        trigger.id,
        token=trigger.inbound_token,
        message={"order_id": "4471", "facility": "OTHER_DC"},
    )

    assert durable.with_values == [{"facility": "DC01", "order_id": "4471"}]


async def test_a_value_a_message_will_supply_need_not_be_known_at_creation() -> None:
    """Without this the trigger could not be created at all -- nobody knows the
    order number of a mail that has not arrived."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill_needing(uow, "facility", "order_id")

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            kind=TriggerKind.INBOUND,
            parameters={"facility": "DC01"},
            from_message=("order_id",),
        ),
    )

    assert trigger.from_message == ("order_id",)


async def test_a_message_may_only_name_a_parameter_the_skill_has() -> None:
    """A typo is silent otherwise: the value is dropped for having the wrong
    name, and every mail fires a run with nothing in it."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill_needing(uow, "facility", "order_id")

    with pytest.raises(TriggerRefused, match="no order_number for a message to supply"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                kind=TriggerKind.INBOUND,
                parameters={"facility": "DC01", "order_id": "1"},
                from_message=("order_number",),
            ),
        )


async def test_a_message_that_names_no_order_is_not_a_run() -> None:
    """Every relay sends some of these -- an autoreply, a thread whose number
    is only in an attachment. Each would otherwise be a run that starts, asks
    the warehouse for nothing, and fails."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill_needing(uow, "facility", "order_id")
    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            kind=TriggerKind.INBOUND,
            parameters={"facility": "DC01"},
            from_message=("order_id",),
        ),
    )
    assert trigger.inbound_token is not None
    durable = FakeDurableExecution()
    fire = FireTrigger(uow, FakeClock(), durable, ids=FakeIdFactory())

    fired = await ReceiveInbound(uow, fire).execute(
        trigger.id, token=trigger.inbound_token, message={"order_id": "   "}
    )

    assert fired.run_id is None
    assert fired.skipped == "nothing said order_id"
    assert durable.started == []


# --- a watch is a trigger the operator's own browser evaluates --------------


def _watch(*values: ValueAt) -> Watch:
    return Watch(
        host="mail.google.com",
        terms=(Term(field=TermField.SUBJECT, contains="shipment status"),),
        values=values,
    )


async def test_a_watch_for_a_task_nobody_has_taught_is_refused() -> None:
    """Nothing untaught reaches the ladder. A watch is the one trigger that
    fires on somebody else's schedule -- a mail arriving -- so a watch for a
    skill that does not exist would be a proposal, in front of an operator,
    for a task this system has never done."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()

    with pytest.raises(NotFound):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=SkillId("skl-nobody-taught"),
                kind=TriggerKind.WATCH,
                watch=_watch(),
                device_id=DeviceId("dev-lena-laptop"),
                parameters={"shipment_id": "1"},
            ),
        )

    assert uow.triggers.rows == {}


async def test_a_watch_for_a_skill_that_has_never_been_rehearsed_is_refused() -> None:
    """The same rule one rung further in: taught is not the same as allowed to
    run, and a mail is not a person deciding it is."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False, runnable=False)

    with pytest.raises(TriggerRefused, match="rehearsed"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                kind=TriggerKind.WATCH,
                watch=_watch(),
                device_id=DeviceId("dev-lena-laptop"),
                parameters={"shipment_id": "1"},
            ),
        )


async def test_a_value_pointed_at_a_parameter_the_skill_does_not_have_is_refused() -> None:
    """Silent otherwise: the mail's value is dropped for having the wrong name
    and the trigger fires with nothing, every time, until somebody reads a run.
    """
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    misnamed = ValueAt(
        name="order_id",
        where=ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("span.ref")),
    )

    with pytest.raises(TriggerRefused, match="no order_id"):
        await _create(uow, scheduler).execute(
            CTX,
            NewTrigger(
                skill_id=skill_id,
                kind=TriggerKind.WATCH,
                watch=_watch(misnamed),
                device_id=DeviceId("dev-lena-laptop"),
                parameters={"shipment_id": "1"},
            ),
        )


async def test_the_mail_supplies_the_value_so_nobody_has_to_type_one() -> None:
    """The point of the whole thing: the trigger is created without a shipment
    id because every matching mail carries its own."""
    uow, scheduler = FakeUnitOfWork(), FakeScheduler()
    skill_id = await _skill(uow, writes=False)
    from_the_mail = ValueAt(
        name="shipment_id",
        where=ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("span.ref")),
    )

    trigger = await _create(uow, scheduler).execute(
        CTX,
        NewTrigger(
            skill_id=skill_id,
            kind=TriggerKind.WATCH,
            watch=_watch(from_the_mail),
            device_id=DeviceId("dev-lena-laptop"),
        ),
    )

    assert trigger.from_message == ("shipment_id",)
    assert trigger.inbound_token is None
    # Nothing on a clock and nothing on a relay: the browser holding it is the
    # only thing that ever evaluates it.
    assert scheduler.scheduled == {}
