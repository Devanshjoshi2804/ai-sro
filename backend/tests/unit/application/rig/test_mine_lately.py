"""The rig's miner on a loop, and what one tenant's bad day costs the others.

`MinePass` had one caller in `src/` and it was a door, so a deployment learned
exactly as often as somebody remembered to press it. Every mining result this
project has measured came from a person running a script.

No worker and no Temporal: `MineLately` takes the pass it calls, so a stub that
counts, refuses or explodes is the whole fixture. The loop that calls this on
an interval is `worker.mine_the_rig_lately`, which has its own tests beside the
pre-rig sweep's.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mining_pass import MineResult
from sro.application.shared.refusals import OverCap
from sro.domain.observation.gesture import GestureBatch
from tests.unit.fakes import FakeUnitOfWork

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


class _Passes:
    """A mining pass that records who it was asked about, and may refuse."""

    def __init__(self, refuse: dict[str, Exception] | None = None) -> None:
        self.asked: list[str] = []
        self._refuse = refuse or {}

    async def execute(self, ctx: RequestContext) -> MineResult:
        self.asked.append(ctx.tenant_id.value)
        problem = self._refuse.get(ctx.tenant_id.value)
        if problem is not None:
            raise problem
        return MineResult(pass_id=f"pas_{ctx.tenant_id.value}", kept=1)


async def _recorded(uow: FakeUnitOfWork, *tenants: str, taken: datetime = NOW) -> None:
    for tenant in tenants:
        await uow.gestures.add_batch(
            GestureBatch(
                batch_id=f"bat_{tenant}",
                tenant=tenant,
                device_id="dev_1",
                mode="watch",
                received_at=taken.isoformat(),
            )
        )


async def _swept(uow: FakeUnitOfWork, passes: _Passes) -> dict[str, MineResult]:
    lately = MineLately(uow, passes, window_hours=24)  # type: ignore[arg-type]
    return await lately.execute(now=NOW)


async def test_every_recorded_tenant_is_mined_without_anybody_asking() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new")
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert sorted(passes.asked) == ["acme", "new"]
    assert sorted(mined) == ["acme", "new"]
    assert mined["acme"].kept == 1


async def test_a_tenant_over_its_cap_does_not_decide_whether_anybody_else_learns() -> None:
    """The cap is the deployment saying what a day of learning may cost, so it
    is a result rather than an error -- and it is one tenant's result. A sweep
    that stopped at the first refusal would let the tenant whose name sorts
    first silence the rest."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new")
    passes = _Passes({"acme": OverCap("the day's cap of $5.00 is spent")})

    mined = await _swept(uow, passes)

    assert sorted(passes.asked) == ["acme", "new"], "the second tenant was still asked"
    assert mined["acme"].error and "cap" in mined["acme"].error
    assert mined["acme"].kept == 0
    assert mined["new"].kept == 1


async def test_a_pass_that_explodes_is_one_tenants_bad_day() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new")
    passes = _Passes({"acme": RuntimeError("the model hung up")})

    mined = await _swept(uow, passes)

    assert sorted(passes.asked) == ["acme", "new"]
    assert mined["acme"].error == "the model hung up"
    assert mined["new"].kept == 1


async def test_a_tenant_that_recorded_nothing_lately_is_not_mined() -> None:
    """The window bounds which tenants are mined, and a pass is the most
    expensive call this system makes: asking it about a tenant whose browsers
    have uploaded nothing for a month is paying to re-read a month of evidence
    that nothing has been added to."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(days=30))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == []
    assert mined == {}


async def test_a_tenant_with_no_evidence_at_all_is_not_mined() -> None:
    passes = _Passes()

    assert await _swept(FakeUnitOfWork(), passes) == {}
    assert passes.asked == []
