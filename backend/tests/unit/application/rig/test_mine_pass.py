"""The door onto the miner: it refuses before it packs a window, or it asks once.

`mine` itself is proved next door in `test_mine.py`. What is here is everything
between a request and that function: which refusals happen before a database is
touched at all, whose tenant is read, whose clock decides the day, and that the
session the pass writes through is one this use case opened.

Nothing here is dated today. `NOW` is a February 2025 evening, six months from
any wall clock this will run against, so a pass that reached for
`datetime.now(UTC)` instead of its clock answers against an empty day rather
than agreeing with these fixtures by the calendar.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.chat.reading import ChatReading
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.infrastructure.db.codec import when
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeClock, FakeGestureRepository, FakeUnitOfWork

TENANT = TenantId("acme")
RIVAL = TenantId("rival")
MODEL = "gemini-3.1-pro-preview"
HOST = "http://127.0.0.1:63319"

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
"""23:00, one hour before a midnight. `over_cap` sums the day from the midnight
BEFORE `now`, so an hour's advance moves this into the next day and out of
reach of everything planted below -- which is the only way to tell a pass that
read its clock from one that read a clock."""

CAP = 5.0


def _ctx(tenant: TenantId = TENANT) -> RequestContext:
    return RequestContext(tenant_id=tenant, principal_id=PrincipalId("operator"))


def _pass(
    uow: FakeUnitOfWork,
    *,
    asker: FakeAsker | None,
    clock: FakeClock | None = None,
    model: str = MODEL,
    cap_usd: float = CAP,
    ours: frozenset[str] = frozenset(),
) -> MinePass:
    # `hand_out`, as a container hands one out: strict, and not yet entered.
    # A use case that read a repository without opening its own session would
    # be an AttributeError here rather than a green test and a 500 in
    # production.
    return MinePass(
        uow.hand_out(),
        asker=asker,
        model=model,
        clock=clock or FakeClock(NOW),
        cap_usd=cap_usd,
        ours=ours,
    )


async def _day(tenant: TenantId = TENANT) -> tuple[FakeUnitOfWork, list[str]]:
    uow = FakeUnitOfWork()
    found = _gestures(tenant.value)
    await uow.gestures.add_gestures(tuple(found))
    return uow, [g.id for g in sorted(found, key=lambda g: (g.at, g.id))]


def _proposal(cites: list[str], **over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "create a work operation",
        "narrative": "the operator created a work operation",
        "systems": [HOST],
        # Two steps: `validate` refuses a workflow shorter than
        # `identity.K_MIN_SHARED_STEPS`. Both cite the same evidence, so
        # nothing else about the fixture moves.
        "steps": [
            {"order": 0, "cites": cites, "says": "do it", "system": HOST, "parameters": []},
            {"order": 1, "cites": cites, "says": "save it", "system": HOST, "parameters": []},
        ],
        "parameters": [],
        "same_as": None,
    }
    return {**base, **over}


async def _billed(uow: FakeUnitOfWork, *, cost_usd: float, at: datetime) -> None:
    """A day with a model call on it. The chat door is one of the four billable
    tables and the cheapest to write; the cap reads the sum, not the table."""
    await uow.chats.record(
        ChatReading(id=f"cht_{cost_usd}", tenant=TENANT.value, at=at.isoformat(), cost_usd=cost_usd)
    )


def _rows(uow: FakeUnitOfWork) -> dict[str, Gesture]:
    assert isinstance(uow.gestures, FakeGestureRepository)
    return uow.gestures.rows


def test_these_fixtures_are_nowhere_near_the_wall_clock() -> None:
    """The sentence this file's docstring is written on, made to fail if it
    stops being true. Move `NOW` to today -- the natural thing to do to a test
    about *today's* spend -- and a pass reading `datetime.now(UTC)` satisfies
    every assertion below."""
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


# --- the two refusals -------------------------------------------------------


async def test_no_asker_refuses_before_anything_is_read() -> None:
    """The refusal is worth its own test because the alternative is not an
    exception, it is a pass that finds nothing -- which is what a quiet day
    looks like."""
    uow, _ = await _day()

    with pytest.raises(AskerUnavailable):
        await _pass(uow, asker=None).execute(_ctx())

    assert await uow.workflows.passes(TENANT) == (), "a refused pass wrote a row"
    assert uow.commits == 0, "a refused pass opened and committed a transaction"


class _RefusingUnitOfWork(FakeUnitOfWork):
    """A unit of work that cannot be opened.

    The only way to hold the code to the comment at the top of `execute`: a
    503 that first took a connection is a 503 that made the outage slightly
    worse, and moving `asker_or_refuse` one line down into the `async with`
    passed every other test in this file and in the integration one.
    """

    async def __aenter__(self) -> FakeUnitOfWork:
        raise AssertionError("a session was opened before the model was checked for")


async def test_the_missing_model_is_noticed_before_a_connection_is_taken() -> None:
    """`AskerUnavailable`, not the `AssertionError` above. A deployment with no
    key answers 503 for every request it gets, and taking a database connection
    on the way to saying so is how a missing setting becomes a pool
    exhaustion."""
    with pytest.raises(AskerUnavailable):
        await _pass(_RefusingUnitOfWork(), asker=None).execute(_ctx())


async def test_over_the_cap_refuses_and_says_which_number_stopped_it() -> None:
    """Both numbers, because a reader has to be able to tell a cap that wants
    raising from a cap that is working."""
    uow, _ = await _day()
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))
    asker = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.01))

    with pytest.raises(OverCap) as refused:
        await _pass(uow, asker=asker).execute(_ctx())

    assert "5.0100" in str(refused.value)
    assert "5.00" in str(refused.value)
    assert asker.asked == [], "the most expensive call in the system was made anyway"


async def test_a_refusal_at_the_door_leaves_no_row_behind() -> None:
    """`mine`'s own cap check returns a `MineResult` carrying the reason, and
    a caller hammering the door would get a table full of rows about its own
    hammering. Refusing here means the spend table records calls that were
    made, which is what it is for."""
    uow, _ = await _day()
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))

    with pytest.raises(OverCap):
        await _pass(uow, asker=FakeAsker()).execute(_ctx())

    assert await uow.workflows.passes(TENANT) == ()


async def test_ours_reaches_the_pass_this_door_opens() -> None:
    """`MinePass` takes `ours` at construction, one seam away from where a
    container reads `Settings.our_own_origins` -- and the only proof it is not
    dropped in transit is a job with nothing left once `mine` strikes it."""
    uow, ids = await _day()
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))

    result = await _pass(uow, asker=asker, ours=frozenset({"127.0.0.1:63319"})).execute(_ctx())

    assert result.kept == 0
    assert result.rejections[0].reason == "not a job"


async def test_a_negative_cap_is_no_cap_and_the_pass_runs() -> None:
    """The switch a deliberate one-off measurement wants. Planted far over the
    shipped cap, so a door that judged against a literal refuses."""
    uow, ids = await _day()
    await _billed(uow, cost_usd=500.0, at=NOW.replace(hour=10))
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))

    result = await _pass(uow, asker=asker, cap_usd=-1.0).execute(_ctx())

    assert result.kept == 1


# --- what a pass that runs answers with -------------------------------------


async def test_the_pass_that_spends_the_last_of_the_cap_still_gets_its_receipt() -> None:
    """The cap is asked BEFORE the pass and never after it.

    $4.99 is on the day and this pass bills $0.01, so the moment it finishes
    the tenant is at $5.00 and over. Asked again afterwards, the same rule
    refuses -- and the caller is handed a 429 for a call that was made,
    succeeded and was billed, with the only copy of the result thrown away.
    Nothing that reads the reason can tell that from a call that never
    happened.
    """
    uow, ids = await _day()
    await _billed(uow, cost_usd=4.99, at=NOW.replace(hour=10))

    result = await _pass(uow, asker=FakeAsker(_answer(ids[:2]))).execute(_ctx())

    assert result.kept == 1
    assert result.cost_usd == 0.01
    # And the day is now over the cap, which is what makes the ordering
    # visible: the next caller is the one that gets refused.
    with pytest.raises(OverCap):
        await _pass(uow, asker=FakeAsker(_answer(ids[:2]))).execute(_ctx())


async def test_a_pass_that_runs_returns_every_figure_the_row_records() -> None:
    """Not `is not None`. Each counter answers a different question, and every
    figure here is a different number, so a body that crossed two of them --
    `kept` for `proposed`, `in_tokens` for `out_tokens` -- fails rather than
    coincidentally agreeing.
    """
    uow, ids = await _day()
    asker = FakeAsker(
        Answer(
            data={"workflows": [_proposal(ids[:2]), _proposal(["ges_invented"])]},
            in_tokens=900,
            out_tokens=140,
            thought_tokens=40,
            cost_usd=0.01,
        )
    )

    result = await _pass(uow, asker=asker).execute(_ctx())

    assert result.proposed == 2
    assert result.kept == 1
    assert [one.workflow_title for one in result.rejections] == ["create a work operation"]
    assert [one.kind for one in result.resolutions] == ["new"]
    assert result.learned_parameters == 0, "one doing cannot name a parameter"
    assert (result.in_tokens, result.out_tokens, result.thought_tokens) == (900, 140, 40)
    assert (result.cost_usd, result.unpriced) == (0.01, False)
    assert result.error is None
    assert result.pass_id.startswith("pas_")
    assert result.window_size == len(ids)
    assert (result.left_out, result.lost_pool) == (0, [])


async def test_a_second_doing_of_a_job_is_reported_as_learning_and_not_as_nothing() -> None:
    """`learned_parameters` is the only figure that says whether parameter
    learning is getting better, and a pass that keeps nothing while widening a
    parameter reads as a wasted call without it."""
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]

    first = await _pass(uow, asker=FakeAsker(_answer(ids))).execute(_ctx())
    assert (first.kept, first.learned_parameters) == (1, 0)

    again_rows = [
        replace(
            row,
            id=f"{row.id}_again",
            at=row.at + 10_000.0,
            action=(
                replace(row.action, value="SOMETHING-ELSE")
                if row.action.kind == "type" and row.action.value
                else row.action
            ),
        )
        for row in original
    ]
    await uow.gestures.add_gestures(tuple(again_rows))

    again = await _pass(uow, asker=FakeAsker(_answer([row.id for row in again_rows]))).execute(
        _ctx()
    )

    assert again.kept == 0, "it is the same job, not a new one"
    assert again.learned_parameters >= 1, "and this time it knows what varies"


def _answer(cites: list[str]) -> Answer:
    return Answer(data={"workflows": [_proposal(cites)]}, cost_usd=0.01)


# --- whose tenant, whose clock, whose model ---------------------------------


async def test_the_day_mined_is_the_callers_and_never_the_stores() -> None:
    """Two tenants, because a pass that read the tenant off anything but `ctx`
    passes every other assertion in this file. `rival` shares the store and has
    nothing in it, so its window is empty and its proposal cites evidence it
    cannot see."""
    uow, ids = await _day()
    asker = FakeAsker(_answer(ids[:2]))

    result = await _pass(uow, asker=asker).execute(_ctx(RIVAL))

    assert result.kept == 0
    assert result.window_size == 0
    assert await uow.workflows.known(RIVAL) == ()
    assert [one.tenant for one in await uow.workflows.passes(RIVAL)] == [RIVAL.value]
    assert await uow.workflows.passes(TENANT) == ()


async def test_the_cap_is_checked_against_the_callers_clock_and_not_a_read_one() -> None:
    """Which day is being asked about is a decision no route may make, so the
    reading comes off the container's clock. Move that clock an hour, across
    the midnight the day is summed from, and the same $5.01 stops refusing --
    an answer that MOVES, which no clock of the pass's own can do."""
    uow, ids = await _day()
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))
    clock = FakeClock(NOW)

    with pytest.raises(OverCap):
        await _pass(uow, asker=FakeAsker(_answer(ids[:2])), clock=clock).execute(_ctx())

    clock.advance(3600)

    assert (await _pass(uow, asker=FakeAsker(_answer(ids[:2])), clock=clock).execute(_ctx())).kept


async def test_the_day_the_pass_is_billed_to_is_the_clocks_and_not_the_servers() -> None:
    """The row's own stamp, not just the cap's window. `mine` takes `now` and
    writes it; a pass handed the wrong reading bills February's call to today.
    """
    uow, ids = await _day()

    await _pass(uow, asker=FakeAsker(_answer(ids[:2]))).execute(_ctx())

    (row,) = await uow.workflows.passes(TENANT)
    assert when(row.started_at) == NOW


async def test_the_model_asked_is_the_one_this_deployment_configured() -> None:
    """Not the shipped default and not a literal: the pass carries the name it
    was built with, so a deployment that pinned another one is billed for the
    model it chose."""
    uow, ids = await _day()
    asker = FakeAsker(_answer(ids[:2]))

    await _pass(uow, asker=asker, model="gemini-3.1-flash-preview").execute(_ctx())

    assert [one["model"] for one in asker.asked] == ["gemini-3.1-flash-preview"]


async def test_the_day_the_cap_judges_is_the_callers_and_never_a_neighbours() -> None:
    """The cap's tenant, which nothing else in this file crosses with a spend.

    `test_the_day_mined_is_the_callers_and_never_the_stores` plants no spend and
    every cap test above uses one tenant, so `over_cap(uow, TenantId("acme"),
    ...)` -- a literal in the one argument that says whose day is being summed
    -- survives the whole suite. What it costs if it is ever wrong that way is
    not subtle: a tenant that has spent nothing is refused because a neighbour
    spent, and a tenant over its own cap keeps mining because the neighbour has
    not.

    Both directions, because the first alone is also satisfied by a pass with no
    cap in it at all. The same hole and the same test live beside `ReadChat` in
    `test_read_chat.py`: one defect wearing two file names.
    """
    uow, _ = await _day(RIVAL)
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))  # TENANT's day, not RIVAL's

    result = await _pass(uow, asker=FakeAsker(Answer(data={"workflows": []}))).execute(_ctx(RIVAL))

    assert result.pass_id, "another tenant's spending refused this one's pass"

    # And the converse: the same money on RIVAL's own day does refuse it.
    await uow.chats.record(
        ChatReading(
            id="cht_rival",
            tenant=RIVAL.value,
            at=NOW.replace(hour=10).isoformat(),
            cost_usd=5.01,
        )
    )

    with pytest.raises(OverCap):
        await _pass(uow, asker=FakeAsker(Answer(data={"workflows": []}))).execute(_ctx(RIVAL))
