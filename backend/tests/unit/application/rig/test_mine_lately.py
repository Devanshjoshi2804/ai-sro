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
from sro.domain.observation.gesture import Action, Gesture, GestureBatch
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.whose import about, whose
from tests.unit.fakes import FakeUnitOfWork

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


class _Reads:
    """A reader that answers a fixed run of counts, then nothing."""

    def __init__(self, *counts: int) -> None:
        self.counts = list(counts)
        self.asked: list[str] = []

    async def execute(self, ctx: RequestContext) -> int:
        self.asked.append(ctx.tenant_id.value)
        return self.counts.pop(0) if self.counts else 0


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


SETTLED = NOW - timedelta(minutes=5)
"""When the evidence in most of these tests arrived: long enough ago that the
operator has stopped. The sweep leaves a tenant that is still uploading alone,
so evidence stamped `NOW` would be skipped by every test here for a reason none
of them is about."""


async def _recorded(uow: FakeUnitOfWork, *tenants: str, taken: datetime = SETTLED) -> None:
    """A batch that carried something, which is the only kind the store counts.

    The gesture is not decoration. `tenants_since` and `newest_arrival` both
    ask for batches with evidence in them, because a watching extension
    uploads on its timer whether or not anybody did anything -- and an empty
    heartbeat answering "this tenant is busy" is how mining once stopped
    running altogether while the product was in use. A fixture with no gesture
    in it is a batch the real store would not count.
    """
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
        await uow.gestures.add_gestures(
            (
                Gesture(
                    id=f"ges_{tenant}",
                    tenant=tenant,
                    stream_id=f"str_{tenant}",
                    batch_id=f"bat_{tenant}",
                    at=taken.timestamp(),
                    url="https://wms.example/receiving",
                    system="https://wms.example",
                    tab_id=1,
                    frame_url=None,
                    action=Action(kind="click", at=taken.timestamp()),
                ),
            )
        )


async def _swept(
    uow: FakeUnitOfWork,
    passes: _Passes,
    reads: _Reads | None = None,
    *,
    max_reads: int = 25,
) -> dict[str, MineResult]:
    lately = MineLately(
        uow,
        passes,
        reads or _Reads(),
        window_hours=24,
        max_reads=max_reads,
    )
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


async def test_a_tenant_is_read_before_it_is_mined() -> None:
    """Not arranged for tidiness. A mining pass packs its window out of
    gestures and their READINGS, so mining ahead of the reader spends the most
    expensive call in the system on evidence nobody has understood yet."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme")
    order: list[str] = []

    class _Noting(_Reads):
        async def execute(self, ctx: RequestContext) -> int:
            order.append("read")
            return 0

    class _Mining(_Passes):
        async def execute(self, ctx: RequestContext) -> MineResult:
            order.append("mine")
            return MineResult()

    await _swept(uow, _Mining(), _Noting())

    assert order == ["read", "mine"]


async def test_reading_repeats_until_a_pass_finds_nothing_left() -> None:
    """One `ReadGestures` call reads at most 200 gestures, so a sweep that made
    one pass would leave a busy tenant falling further behind every hour with
    nothing anywhere saying so."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme")
    reads = _Reads(200, 200, 43, 0, 200)

    mined = await _swept(uow, _Passes(), reads)

    assert reads.asked == ["acme"] * 4, "it stopped at the pass that found nothing"
    assert mined["acme"].read == 443


async def test_a_reader_that_never_finishes_costs_one_sweep_and_not_every_one() -> None:
    """A stop against a pass that keeps reporting progress it is not making.
    `daily_usd_cap` is the budget; this is the broken-reader bound."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme")
    reads = _Reads(*([200] * 100))

    mined = await _swept(uow, _Passes(), reads, max_reads=3)

    assert reads.asked == ["acme"] * 3
    assert mined["acme"].read == 600


async def test_a_tenant_whose_reading_is_refused_is_not_then_mined() -> None:
    """The cap stops the cycle where it is reached. Mining a tenant whose
    reading was refused for cost is spending the expensive half of the budget
    it just said was gone."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new")
    passes = _Passes()

    class _Capped(_Reads):
        async def execute(self, ctx: RequestContext) -> int:
            if ctx.tenant_id.value == "acme":
                raise OverCap("the day's cap of $5.00 is spent")
            return 0

    mined = await _swept(uow, passes, _Capped())

    assert passes.asked == ["new"], "acme was never mined"
    assert mined["acme"].error and "cap" in mined["acme"].error
    assert mined["new"].kept == 1


async def _mined(
    uow: FakeUnitOfWork,
    tenant: str,
    *,
    left_out: int,
    at: datetime,
    window_size: int = 0,
) -> None:
    await uow.workflows.add_pass(
        MiningPass(
            id=f"pas_{tenant}_{at.isoformat()}",
            tenant=tenant,
            started_at=at.isoformat(),
            left_out=left_out,
            window_size=window_size,
        )
    )


async def test_a_tenant_whose_evidence_has_not_changed_is_not_read_again() -> None:
    """A pass re-reads the tenant's whole history, so on unchanged evidence it
    asks the same question and pays for the same answer. One measured pass over
    tenant `new` cost $0.34, proposed the two jobs it already knew and kept
    nothing -- on an hourly sweep that is $8 a day to learn nothing."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    await _mined(uow, "acme", left_out=0, at=NOW - timedelta(hours=1))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == []
    assert mined == {}


async def test_evidence_that_arrived_since_the_last_pass_is_worth_paying_for() -> None:
    uow = FakeUnitOfWork()
    await _mined(uow, "acme", left_out=0, at=NOW - timedelta(hours=2))
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=1))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == ["acme"]
    assert mined["acme"].kept == 1


async def test_a_pass_that_could_not_hold_the_day_is_worth_another_one() -> None:
    """A day too big for one window is read across several passes, and the
    carry-over pool rotates which part: ten simulated passes went 81% then 96%
    coverage, with nineteen gestures never shown. So a pass with evidence it
    could not hold has more to say about a day nobody added to."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    await _mined(uow, "acme", left_out=1_204, at=NOW - timedelta(hours=1))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == ["acme"]
    assert mined["acme"].kept == 1


async def test_the_day_too_big_for_one_window_is_swept_once_and_then_left_alone() -> None:
    """The loop this branch became, measured on the deployment 2026-09-21.

    A store bigger than one window leaves evidence out of EVERY pass -- 1,981
    of 2,066 there, an average of 444 gestures against a window of 154 -- so
    `left_out` was permanently true, the "has anything new arrived" question
    below it was never reached, and the sweep paid for a pass a minute over
    evidence nobody had added to. 463 passes on a day that captured 56
    gestures, $220.95 of them, every captured gesture read about 352 times.

    Enough passes to sweep the store once is what "more to say" is worth. The
    pool rotates which part of a day gets read; after it has been round once,
    a further pass sees what an earlier one already saw.
    """
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    # A window that holds a tenth of what there is: ten passes to sweep it.
    for nth in range(9):
        await _mined(
            uow,
            "acme",
            left_out=90,
            window_size=10,
            at=NOW - timedelta(minutes=50 - nth),
        )
    passes = _Passes()

    assert (await _swept(uow, passes))["acme"].kept == 1, "it stopped before one sweep"

    # And the tenth closes it. Nothing has arrived since, so there is nothing
    # left for an eleventh to see.
    await _mined(uow, "acme", left_out=90, window_size=10, at=NOW - timedelta(minutes=40))
    quiet = _Passes()

    assert await _swept(uow, quiet) == {}
    assert quiet.asked == [], "it went on paying for a day nobody added to"


async def test_evidence_arriving_starts_the_sweep_again() -> None:
    """The counter is "passes since anybody worked", not a lifetime quota: a
    tenant that has been swept out and then does something is a tenant with
    something new to read."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    for nth in range(12):
        await _mined(uow, "acme", left_out=90, window_size=10, at=NOW - timedelta(minutes=50 - nth))
    assert await _swept(uow, _Passes()) == {}, "the fixture was not swept out to begin with"

    # Somebody works. The batch is newer than every pass above it.
    await uow.gestures.add_batch(
        GestureBatch(
            batch_id="bat_acme_2",
            tenant="acme",
            device_id="dev_1",
            mode="watch",
            received_at=(NOW - timedelta(minutes=6)).isoformat(),
        )
    )
    await uow.gestures.add_gestures(
        (
            Gesture(
                id="ges_acme_2",
                tenant="acme",
                stream_id="str_acme",
                batch_id="bat_acme_2",
                at=(NOW - timedelta(minutes=6)).timestamp(),
                url="https://wms.example/receiving",
                system="https://wms.example",
                tab_id=1,
                frame_url=None,
                action=Action(kind="click", at=(NOW - timedelta(minutes=6)).timestamp()),
            ),
        )
    )
    passes = _Passes()

    assert (await _swept(uow, passes))["acme"].kept == 1
    assert passes.asked == ["acme"]


async def test_a_tenant_nobody_has_ever_mined_is_always_worth_a_pass() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    passes = _Passes()

    assert (await _swept(uow, passes))["acme"].kept == 1
    assert passes.asked == ["acme"]


async def test_one_tenants_quiet_day_does_not_skip_the_tenant_beside_it() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new", taken=NOW - timedelta(hours=2))
    await _mined(uow, "acme", left_out=0, at=NOW - timedelta(hours=1))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == ["new"]
    assert sorted(mined) == ["new"]


async def test_a_tenant_still_working_is_left_to_finish() -> None:
    """The failure a minute-by-minute sweep introduces, and the reason it can
    run that often.

    An operator halfway through creating a supplier has filled two fields. Mine
    them now and the half they have done is proposed, kept, and offered back
    forever as though it were the job. Waiting costs one interval, and nothing
    is lost by waiting: the evidence does not go anywhere.
    """
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(seconds=20))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert mined == {}
    assert passes.asked == [], "somebody was mined in the middle of their task"


async def test_a_tenant_that_has_gone_quiet_is_mined_on_the_next_sweep() -> None:
    # The other side of the same rule: two minutes of silence is a person who
    # stopped, measured against doings of 35 to 180 seconds and uploads that
    # land a median 27 seconds after the moment they cover.
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(seconds=150))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == ["acme"]
    assert mined["acme"].kept == 1


async def test_tenant_as_new_gestures_do_not_make_tenant_b_worth_a_pass() -> None:
    """`tenants_since` answers for every tenant with new evidence, not just
    this one -- so a global read of it made any tenant's new gestures worth a
    pass for all of them. `b`'s own evidence predates its last pass; only
    `a`'s does not."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "b", taken=NOW - timedelta(hours=3))
    await _mined(uow, "b", left_out=0, at=NOW - timedelta(hours=2))
    await _recorded(uow, "a", taken=NOW - timedelta(hours=1))
    passes = _Passes()

    mined = await _swept(uow, passes)

    assert passes.asked == ["a"], "b's own evidence has not changed since its last pass"
    assert sorted(mined) == ["a"]


async def test_one_tenant_working_does_not_hold_up_another_who_has_stopped() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(seconds=10))
    await _recorded(uow, "new", taken=NOW - timedelta(minutes=10))
    passes = _Passes()

    await _swept(uow, passes)

    assert passes.asked == ["new"]


async def test_each_tenant_s_reading_and_pass_are_billed_to_that_tenant() -> None:
    """The sweep runs outside any request, so nothing names the tenant but the
    sweep itself: the metered client bills whoever is named while that
    tenant's reading and pass run, and nobody once the sweep moves on."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", "new")
    seen: list[tuple[str, str]] = []

    class _Noting(_Reads):
        async def execute(self, ctx: RequestContext) -> int:
            seen.append(("read", str(whose().get("tenant"))))
            return 0

    class _Mining(_Passes):
        async def execute(self, ctx: RequestContext) -> MineResult:
            seen.append(("mine", str(whose().get("tenant"))))
            assert whose().get("tenant") == ctx.tenant_id.value
            return MineResult()

    with about():
        await _swept(uow, _Mining(), _Noting())
        assert "tenant" not in whose()

    assert sorted(seen) == sorted(
        [("read", "acme"), ("mine", "acme"), ("read", "new"), ("mine", "new")]
    )


def _job_citing(tenant: str, *, signs_in: bool | None) -> Workflow:
    return Workflow(
        id=f"wfl_{tenant}",
        tenant=tenant,
        title="receive",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=[f"ges_{tenant}"])],
        signs_in=signs_in,
    )


async def test_a_quiet_sweep_decides_every_job_nobody_has_judged() -> None:
    """QA's 23 jobs came out of the 0069 migration as `signs_in = false`,
    and the flag was only ever decided when new gestures arrived. On a quiet
    system that never happened, so the vault migration found no sign-in job to
    move. An undecided job is decided on the next sweep, new gestures or not --
    and a tenant quiet for longer than the mining window is still swept."""
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(days=30))
    await _mined(uow, "acme", left_out=0, at=NOW - timedelta(days=29))
    await uow.workflows.save(_job_citing("acme", signs_in=None))

    await _swept(uow, _Passes())

    assert (await uow.workflows.get(TenantId("acme"), "wfl_acme")).signs_in is False


async def test_a_decided_job_is_not_decided_again_without_new_evidence() -> None:
    uow = FakeUnitOfWork()
    await _recorded(uow, "acme", taken=NOW - timedelta(hours=2))
    await _mined(uow, "acme", left_out=0, at=NOW - timedelta(hours=1))
    await uow.workflows.save(_job_citing("acme", signs_in=True))

    await _swept(uow, _Passes())

    assert (await uow.workflows.get(TenantId("acme"), "wfl_acme")).signs_in is True
