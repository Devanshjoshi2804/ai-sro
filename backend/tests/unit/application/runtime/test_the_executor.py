from dataclasses import replace

from sro.application.runtime.executor import StepExecutor
from sro.domain.execution.lanes import Broken, Lane, StepResult
from sro.domain.observation.gesture import Target
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
