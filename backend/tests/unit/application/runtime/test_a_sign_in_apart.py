"""A sign-in that outlives the turn that asked for it.

QA 2026-10-02: a chat lookup has 10 s; a cold Blue Yonder sign-in takes 24-34 s. The
turn's timeout cancelled the sign-in and left the lease READY on the sign-in page, so
the next ask began another sign-in inside another 10 s, and none could ever finish.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

import pytest

from sro.application.connection.refusals import ForgetsRefusalOnWrite
from sro.application.runtime.broker import K_FAILURE, SessionBroker, SigningIn, SignIns
from sro.application.runtime.step import Held, LaneContext, NeedsAPerson
from sro.domain.execution.account import LeaseState
from sro.domain.execution.lanes import StepResult
from sro.domain.skill.workflow import Step
from tests.unit.application.runtime.test_the_broker import (
    APP,
    CTX,
    LENA,
    PASSWORD,
    STEEL,
    WRONG,
    _broker,
    _signing_world,
)
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeBrowserPool,
    FakeClock,
    FakePageDriver,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import SigningLane


class _SlowSignIn(SigningLane):
    """A sign-in that takes as long as the test says: every step waits on `gate`."""

    def __init__(self, driver: FakePageDriver) -> None:
        super().__init__(driver)
        self.gate, self.started = asyncio.Event(), asyncio.Event()

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        self.started.set()
        await self.gate.wait()
        return await super().execute(step, values, ctx)


def _states(uow: FakeUnitOfWork) -> list[LeaseState]:
    return [lease.state for lease in uow.browser_sessions.leases.values()]


async def _apart(broker: SessionBroker, holder: str, *, patience_s: float = 0.0) -> Held:
    return await broker.acquire(
        CTX, LENA, APP, holder=holder, park=False, patience_s=patience_s, apart_s=30.0
    )


async def test_a_sign_in_cancelled_mid_way_leaves_no_lease_that_looks_usable() -> None:
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)
    asking = asyncio.create_task(broker.acquire(CTX, LENA, APP, holder="run_1"))
    await lane.started.wait()
    assert _states(uow) == [LeaseState.SIGNING_IN]

    asking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asking

    assert LeaseState.READY not in _states(uow)
    assert await uow.browser_sessions.current_lease(CTX.tenant_id, LENA) is None


async def test_a_sign_in_the_turn_stopped_waiting_for_goes_on_and_the_next_ask_is_signed_in() -> (
    None
):
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)

    with pytest.raises(SigningIn, match=r"signing in to wms\.example"):
        await _apart(broker, "lookup_1")
    lane.gate.set()
    await broker.signings.settled()
    held = await _apart(broker, "lookup_2")

    assert held.lease.state is LeaseState.READY and lane.sign_ins == 1
    assert _states(uow) == [LeaseState.READY]
    assert not await broker.signed_out(CTX, held)


async def test_a_turn_that_is_cancelled_while_it_waits_does_not_cancel_the_sign_in() -> None:
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)
    asking = asyncio.create_task(_apart(broker, "lookup_1", patience_s=60.0))
    await lane.started.wait()

    asking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asking
    lane.gate.set()
    await broker.signings.settled()

    assert _states(uow) == [LeaseState.READY] and lane.sign_ins == 1


async def test_two_asks_while_an_account_signs_in_share_that_one_sign_in() -> None:
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)
    both = asyncio.gather(
        _apart(broker, "lookup_1", patience_s=60.0), _apart(broker, "lookup_2", patience_s=60.0)
    )
    await lane.started.wait()

    lane.gate.set()
    one, two = await both

    assert lane.sign_ins == 1 and len(uow.browser_sessions.leases) == 1
    assert one.lease.id == two.lease.id and one.target_id != two.target_id


async def test_the_sign_in_that_failed_apart_is_what_the_next_ask_hears_and_it_never_loops() -> (
    None
):
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)

    with pytest.raises(SigningIn):
        await _apart(broker, "lookup_1")
    lane.gate.set()
    await broker.signings.settled()
    with pytest.raises(NeedsAPerson, match="password refused"):
        await _apart(broker, "lookup_2")

    assert lane.sign_ins == 1, "the second ask reported the first's failure and started nothing"


async def test_shutdown_cancels_a_sign_in_and_leaves_no_ready_lease() -> None:
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    broker = _broker(uow, driver, vault, lane)
    with pytest.raises(SigningIn):
        await _apart(broker, "lookup_1")
    await lane.started.wait()

    await broker.signings.close()

    assert LeaseState.READY not in _states(uow) and lane.sign_ins == 0


async def test_a_re_sign_in_cancelled_mid_way_does_not_leave_the_signed_out_lease_ready() -> None:
    uow, driver, vault = await _signing_world()
    lane = _SlowSignIn(driver)
    lane.gate.set()
    broker = _broker(uow, driver, vault, lane)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.expire_session()
    lane.gate.clear()
    lane.started.clear()
    asking = asyncio.create_task(broker.reauth(CTX, held, APP))
    await lane.started.wait()

    asking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asking

    assert LeaseState.READY not in _states(uow)


async def _failed_apart(
    clock: FakeClock,
) -> tuple[SessionBroker, ForgetsRefusalOnWrite, _SlowSignIn, FakePageDriver]:
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    lane, signings = _SlowSignIn(driver), SignIns()
    vault_seen = ForgetsRefusalOnWrite(vault, on_written=signings.forget)
    broker = SessionBroker(
        uow,
        FakeBrowserPool({STEEL: 1}),
        driver,
        FakeAccountLocks(),
        vault_seen,
        clock,
        ui=lane,
        close_s=0.05,
        signings=signings,
    )
    with pytest.raises(SigningIn):
        await _apart(broker, "lookup_1")
    lane.gate.set()
    await broker.signings.settled()
    return broker, vault_seen, lane, driver


async def test_a_sign_in_failure_nobody_asked_about_expires_after_ten_minutes() -> None:
    """R-L3: a refusal heard a day later is not news, and must not hide a sign-in that
    would work now."""
    clock = FakeClock()
    clock = FakeClock()
    broker, _, lane, _ = await _failed_apart(clock)
    clock.advance(int(K_FAILURE.total_seconds()) + 1)

    with pytest.raises(NeedsAPerson, match="no usable password"):
        await _apart(broker, "lookup_2", patience_s=60.0)

    assert lane.sign_ins == 1, "no second chain ran: a new sign-in began and met the latch"


async def test_a_failure_still_fresh_is_heard_once_by_the_next_ask() -> None:
    clock = FakeClock()
    broker, _, lane, _ = await _failed_apart(clock)
    clock.advance(int(K_FAILURE.total_seconds()) - 1)

    with pytest.raises(NeedsAPerson, match="password refused"):
        await _apart(broker, "lookup_2", patience_s=60.0)

    assert lane.sign_ins == 1


async def test_a_new_password_clears_the_failure_at_once() -> None:
    """R-L3: the person fixed what failed; the next ask signs in rather than hearing the
    old refusal."""
    broker, vault, _, driver = await _failed_apart(FakeClock())
    driver.refuses = False

    await vault.store(LENA.vault_key("password"), PASSWORD)
    held = await _apart(broker, "lookup_2", patience_s=60.0)

    assert held.lease.state is LeaseState.READY
