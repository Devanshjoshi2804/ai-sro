import asyncio
from dataclasses import replace

import pytest

from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.locks import AccountBusy
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.step import NeedsAPerson, Stopped
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Broken, Lane, StepResult
from sro.domain.observation.gesture import Target
from sro.domain.skill.workflow import Step
from tests.unit.runtime_support import (
    APP,
    FakeBroker,
    RecordingLane,
    lane_context,
    mail_send_step,
    never,
    no_api,
    no_tool,
    proven_write_step,
    save_step,
)

VALUES = {"Customer Type": "GT2"}


async def test_the_first_trusted_lane_goes_first_and_the_first_success_ends_it() -> None:
    api = RecordingLane(Lane.API, StepResult("failed", Lane.API, fingerprint="f"))
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    sight = RecordingLane(Lane.SIGHT, StepResult("done", Lane.SIGHT))
    step, by_id, ledger = proven_write_step(read_back="/api/x/GT2")

    tried = await StepExecutor(no_tool(), api, ui, sight, FakeBroker()).run(
        step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
    )

    assert [one.lane for one in tried] == [Lane.API, Lane.UI]
    assert sight.calls == 0


async def test_a_write_that_carries_a_new_field_is_never_offered_the_api_lane() -> None:
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    step, by_id, ledger = proven_write_step(read_back="/api/x/GT2")
    adding = {step.order: Adding(fresh={"department": "Finance"})}

    tried = await StepExecutor(no_tool(), no_api(), ui, never(), FakeBroker()).run(
        step, VALUES, lane_context(by_id, ledger=ledger, adding=adding), broken=(), start_url=APP
    )

    assert [one.lane for one in tried] == [Lane.UI]


async def test_an_expired_session_is_signed_back_in_and_the_lane_retried_once() -> None:
    ui = RecordingLane(
        Lane.UI, StepResult("failed", Lane.UI, expired=True), StepResult("done", Lane.UI)
    )
    broker = FakeBroker()
    step, by_id = save_step(status=201)

    tried = await StepExecutor(no_tool(), no_api(), ui, never(), broker).run(
        step, {}, lane_context(by_id), broken=(), start_url=APP
    )

    assert tried[-1].verdict == "done" and broker.reauths == 1
    assert [one.reauthed for one in ui.contexts] == [False, True]


async def test_a_lane_still_expired_after_signing_back_in_stops_the_walk() -> None:
    expired = StepResult("failed", Lane.UI, expired=True)
    ui = RecordingLane(Lane.UI, expired, expired)
    broker = FakeBroker()
    step, by_id = save_step(status=201)

    tried = await StepExecutor(no_tool(), no_api(), ui, never(), broker).run(
        step, {}, lane_context(by_id), broken=(), start_url=APP
    )

    assert tried == (expired,) and broker.reauths == 1


async def test_an_expired_lane_with_no_held_page_is_not_signed_in_and_stops() -> None:
    expired = StepResult("failed", Lane.UI, expired=True)
    broker = FakeBroker()
    step, by_id = save_step(status=201)

    tried = await StepExecutor(
        no_tool(), no_api(), RecordingLane(Lane.UI, expired), never(), broker
    ).run(step, {}, lane_context(by_id, held=None), broken=(), start_url=APP)

    assert tried == (expired,) and broker.reauths == 0


async def test_an_unknown_write_on_an_expired_session_is_never_sent_again_only_read_back() -> None:
    lost = StepResult("unknown", Lane.API, "sent to sign in", expired=True)
    api = RecordingLane(Lane.API, lost, settles="done")
    step, by_id, ledger = proven_write_step(read_back="/api/x/{name}")
    broker = FakeBroker()

    tried = await StepExecutor(no_tool(), api, never(), never(), broker).run(
        step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
    )

    assert [one.verdict for one in tried] == ["done"]
    assert (api.calls, api.read_backs, broker.reauths) == (1, 1, 1)
    assert api.contexts[-1].reauthed is True


async def test_an_unknown_write_no_read_back_settles_stays_unknown_for_the_operator() -> None:
    lost = StepResult("unknown", Lane.API, "sent to sign in", expired=True)
    api = RecordingLane(Lane.API, lost)
    step, by_id, ledger = proven_write_step(read_back="/api/x/{name}")

    tried = await StepExecutor(no_tool(), api, never(), never(), FakeBroker()).run(
        step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
    )

    assert tried == (lost,) and (api.calls, api.read_backs) == (1, 1)


async def test_a_known_broken_lane_is_skipped() -> None:
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    sight = RecordingLane(Lane.SIGHT, StepResult("done", Lane.SIGHT))
    step, by_id = save_step(status=201)

    await StepExecutor(no_tool(), no_api(), ui, sight, FakeBroker()).run(
        step,
        {},
        lane_context(by_id),
        broken=(Broken(step.order, Lane.UI, "f"),),
        start_url=APP,
    )

    assert (ui.calls, sight.calls) == (0, 1)


async def test_a_mail_send_goes_to_the_tool_lane_alone() -> None:
    tool = RecordingLane(Lane.TOOL, StepResult("failed", Lane.TOOL))
    step, by_id = mail_send_step()

    tried = await StepExecutor(tool, no_api(), never(), never(), FakeBroker()).run(
        step, {}, lane_context(by_id), broken=(), start_url=APP
    )

    assert [one.lane for one in tried] == [Lane.TOOL]


async def test_a_step_that_only_reads_the_mail_is_read_without_a_lane() -> None:
    step, by_id = mail_send_step()
    opened = by_id["g-send"]
    by_id = {
        "g-send": replace(
            opened,
            action=replace(opened.action, target=Target(tag="a", role="link", name="Inbox")),
        )
    }

    tried = await StepExecutor(no_tool(), no_api(), never(), never(), FakeBroker()).run(
        step, {}, lane_context(by_id), broken=(), start_url=APP
    )

    assert [one.verdict for one in tried] == ["read"]


START = "https://wms.example/start"


async def test_a_step_no_lane_can_act_on_tries_nothing() -> None:
    _, by_id = save_step(status=201)

    tried = await StepExecutor(no_tool(), no_api(), never(), never(), FakeBroker()).run(
        Step(order=1, says="nothing cited", system=None, cites=[]),
        {},
        lane_context(by_id),
        broken=(),
        start_url=APP,
    )

    assert tried == ()


async def test_an_unknown_write_ends_the_walk_before_any_other_lane_can_send_it() -> None:
    lost = StepResult("unknown", Lane.API, "the call may have arrived")
    api = RecordingLane(Lane.API, lost, settles="done")
    step, by_id, ledger = proven_write_step(read_back="/api/x/{name}")

    tried = await StepExecutor(no_tool(), api, never(), never(), FakeBroker()).run(
        step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
    )

    assert tried == (lost,) and api.read_backs == 0


async def test_a_ui_retry_goes_back_to_the_step_s_page_and_an_api_retry_goes_nowhere() -> None:
    ui = RecordingLane(
        Lane.UI, StepResult("failed", Lane.UI, expired=True), StepResult("done", Lane.UI)
    )
    api = RecordingLane(
        Lane.API, StepResult("failed", Lane.API, expired=True), StepResult("done", Lane.API)
    )
    saved, by_saved = save_step(status=201)
    proven, by_proven, ledger = proven_write_step(read_back="/api/x/{name}")
    broker = FakeBroker()

    await StepExecutor(no_tool(), no_api(), ui, never(), broker).run(
        saved, {}, lane_context(by_saved), broken=(), start_url=START
    )
    await StepExecutor(no_tool(), api, never(), never(), broker).run(
        proven, VALUES, lane_context(by_proven, ledger=ledger), broken=(), start_url=START
    )

    assert broker.back_tos == [by_saved["ges_save"].url, None]


async def test_a_sign_in_that_needs_a_person_still_carries_what_the_lane_answered() -> None:
    expired = StepResult("failed", Lane.UI, "the page asked to sign in", expired=True)
    step, by_id = save_step(status=201)
    broker = FakeBroker(refuses=NeedsAPerson("no usable password", kind="password"))

    with pytest.raises(NeedsAPerson) as asked:
        await StepExecutor(
            no_tool(), no_api(), RecordingLane(Lane.UI, expired), never(), broker
        ).run(step, {}, lane_context(by_id), broken=(), start_url=APP)

    assert asked.value.kind == "password"
    assert [(one.verdict, one.expired) for one in asked.value.tried] == [("failed", True)]
    assert "no usable password" in asked.value.tried[0].reason


async def test_an_unknown_write_whose_sign_in_is_busy_stays_unknown_on_the_way_out() -> None:
    lost = StepResult("unknown", Lane.API, "sent to sign in", expired=True)
    api = RecordingLane(Lane.API, lost, settles="done")
    step, by_id, ledger = proven_write_step(read_back="/api/x/{name}")
    broker = FakeBroker(refuses=AccountBusy("waiting for a person"))

    with pytest.raises(AccountBusy) as busy:
        await StepExecutor(no_tool(), api, never(), never(), broker).run(
            step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
        )

    assert [one.verdict for one in busy.value.tried] == ["unknown"]
    assert api.read_backs == 0


async def test_a_browser_lost_while_signing_back_in_keeps_the_unknown_and_sends_nothing() -> None:
    lost = StepResult("unknown", Lane.API, "sent to sign in", expired=True)
    api = RecordingLane(Lane.API, lost, settles="done")
    step, by_id, ledger = proven_write_step(read_back="/api/x/{name}")
    broker = FakeBroker(refuses=BrowserUnavailable("steel said: secret-ish detail"))

    tried = await StepExecutor(no_tool(), api, never(), never(), broker).run(
        step, VALUES, lane_context(by_id, ledger=ledger), broken=(), start_url=APP
    )

    assert tried == (replace(lost, reason="sign-in failed: BrowserUnavailable"),)
    assert (api.calls, api.read_backs) == (1, 0)


async def test_a_cancellation_while_signing_back_in_still_propagates() -> None:
    expired = StepResult("failed", Lane.UI, expired=True)
    step, by_id = save_step(status=201)
    broker = FakeBroker(refuses=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await StepExecutor(
            no_tool(), no_api(), RecordingLane(Lane.UI, expired), never(), broker
        ).run(step, {}, lane_context(by_id), broken=(), start_url=APP)


async def test_a_stop_while_signing_back_in_still_propagates() -> None:
    expired = StepResult("failed", Lane.UI, expired=True)
    step, by_id = save_step(status=201)
    broker = FakeBroker(refuses=Stopped("the operator stopped the run"))

    with pytest.raises(Stopped):
        await StepExecutor(
            no_tool(), no_api(), RecordingLane(Lane.UI, expired), never(), broker
        ).run(step, {}, lane_context(by_id), broken=(), start_url=APP)
