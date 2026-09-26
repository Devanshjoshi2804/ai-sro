"""The door onto the chat reader: it refuses before it asks, or it asks once.

`read_utterance` itself is proved next door in `test_understand.py`. What is
here is everything between a request and that function: which refusals happen
before a database is touched at all, whose sentence is read, whose jobs it is
read against, whose clock stamps the bill, and that the session the reading
writes through is one this use case opened.

Beside `test_mine_pass.py` and deliberately not sharing a base class with it.
The two use cases have the same two refusals and nothing else: this one takes a
sentence from the caller and that one takes nothing, and a base class holding
two refusals would be an abstraction over a coincidence.

Nothing here is dated today. `NOW` is a February 2025 evening, six months from
any wall clock this will run against, so a reading that reached for
`datetime.now(UTC)` instead of its clock bills a day nothing below planted.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.chat.read_chat import ReadChat
from sro.application.context import RequestContext
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.chat.reading import ChatReading
from sro.domain.prompts.read_request import READ_REQUEST
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer, ModelSpend
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.codec import when
from tests.unit.fakes import FakeAsker, FakeChatRepository, FakeClock, FakeUnitOfWork
from tests.unit.runtime_support import save_step

TENANT = TenantId("acme")
RIVAL = TenantId("rival")
NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
"""23:00, one hour before a midnight. `over_cap` sums the day from the midnight
BEFORE `now`, so an hour's advance moves this into the next day and out of
reach of everything planted below -- which is the only way to tell a reading
that read its clock from one that read a clock."""

CAP = 5.0

SAID = "create a work area for zone 4"
"""The operator's words about their own warehouse. Nothing this file asserts
ever finds them in a row, which is the promise `ChatReading` is shaped around.
"""


def _ctx(tenant: TenantId = TENANT) -> RequestContext:
    return RequestContext(tenant_id=tenant, principal_id=PrincipalId("operator"))


def _workflow(tenant: TenantId = TENANT) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant=tenant.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[Step(order=0, says="s", system=None, cites=["ges_1"], parameters=["areaName"])],
        parameters=[{"name": "areaName", "seen_values": ["NEWTESTS"], "required": True}],
    )


def _read(
    uow: FakeUnitOfWork,
    *,
    asker: FakeAsker | None,
    clock: FakeClock | None = None,
    cap_usd: float = CAP,
) -> ReadChat:
    # `hand_out`, as a container hands one out: strict, and not yet entered. A
    # use case that read a repository without opening its own session would be
    # an AttributeError here rather than a green test and a 500 in production.
    return ReadChat(
        uow.hand_out(),
        asker=asker,
        clock=clock or FakeClock(NOW),
        cap_usd=cap_usd,
    )


async def _held(tenant: TenantId = TENANT) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.workflows.save(_workflow(tenant))
    # A cited, proven save, so the job compiles: only a runnable job is offered.
    _, by_id = save_step(gid="ges_1")
    await uow.gestures.add_gestures(
        tuple(replace(one, tenant=tenant.value) for one in by_id.values())
    )
    return uow


def _answer(workflow_id: str | None, values: list[dict[str, str]], **over: object) -> Answer:
    return Answer(
        data={"workflow_id": workflow_id, "values": values, "missing": [], "sure": True},
        **over,
    )


def _billed_rows(uow: FakeUnitOfWork) -> list[ChatReading]:
    """The bills this store holds, typed.

    `FakeUnitOfWork.chats` is annotated as the `ChatRepository` port and the
    port has no `rows`: the narrowing is an assertion rather than an ignore so
    that a fake swapped for one without a row list fails here instead of at
    the read.
    """
    assert isinstance(uow.chats, FakeChatRepository)
    return uow.chats.rows


async def _billed(uow: FakeUnitOfWork, *, cost_usd: float, at: datetime) -> None:
    """A day with a model call on it, as the metered client bills one."""
    await uow.spend.record(
        ModelSpend(id=f"cht_{cost_usd}", tenant=TENANT.value, model="m", at=at, cost_usd=cost_usd)
    )


def test_these_fixtures_are_nowhere_near_the_wall_clock() -> None:
    """The sentence this file's docstring is written on, made to fail if it
    stops being true."""
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


# --- the two refusals -------------------------------------------------------


async def test_no_asker_refuses_before_anything_is_read() -> None:
    """503 and not an offer of nothing. A door with no model to ask that
    answered `workflow_id: null` reads exactly like a sentence naming no job
    the tenant holds, and the operator is told to rephrase a sentence that was
    never read."""
    uow = await _held()

    with pytest.raises(AskerUnavailable):
        await _read(uow, asker=None).execute(_ctx(), utterance=SAID)

    assert _billed_rows(uow) == [], "a refused reading billed a row"
    assert uow.commits == 0, "a refused reading opened and committed a transaction"


class _RefusingUnitOfWork(FakeUnitOfWork):
    """A unit of work that cannot be opened.

    The only way to hold the code to the comment at the top of `execute`: a 503
    that first took a connection is a 503 that made the outage slightly worse.
    """

    async def __aenter__(self) -> FakeUnitOfWork:
        raise AssertionError("a session was opened before the model was checked for")


async def test_the_missing_model_is_noticed_before_a_connection_is_taken() -> None:
    """`AskerUnavailable`, not the `AssertionError` above. A deployment with no
    key answers 503 for every sentence typed at it, and taking a database
    connection on the way to saying so is how a missing setting becomes a pool
    exhaustion."""
    with pytest.raises(AskerUnavailable):
        await _read(_RefusingUnitOfWork(), asker=None).execute(_ctx(), utterance=SAID)


async def test_over_the_cap_refuses_and_says_which_number_stopped_it() -> None:
    """Both numbers, because a reader has to be able to tell a cap that wants
    raising from a cap that is working."""
    uow = await _held()
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))
    asker = FakeAsker(_answer("wfl_1", []))

    with pytest.raises(OverCap) as refused:
        await _read(uow, asker=asker).execute(_ctx(), utterance=SAID)

    assert "5.0100" in str(refused.value)
    assert "5.00" in str(refused.value)
    assert asker.asked == [], "the model was asked anyway, and the cap paid for it"


async def test_a_refusal_at_the_door_leaves_no_row_behind() -> None:
    """`read_utterance` writes a row for every reading it makes, refusal
    included. A cap checked after it would therefore bill a row for a call the
    tenant was told it could not make, and a caller hammering the door would
    fill the very table the cap is summed from."""
    uow = await _held()
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))

    with pytest.raises(OverCap):
        await _read(uow, asker=FakeAsker()).execute(_ctx(), utterance=SAID)

    assert _billed_rows(uow) == [], "the refusal billed a row"


async def test_a_negative_cap_is_no_cap_and_the_sentence_is_read() -> None:
    """The switch a deliberate one-off measurement wants. Planted far over the
    shipped cap, so a door that judged against a literal refuses."""
    uow = await _held()
    await _billed(uow, cost_usd=500.0, at=NOW.replace(hour=10))

    got = await _read(uow, asker=FakeAsker(_answer("wfl_1", [])), cap_usd=-1.0).execute(
        _ctx(), utterance=SAID
    )

    assert got.workflow_id == "wfl_1"


async def test_the_reading_that_spends_the_last_of_the_cap_still_gets_its_offer() -> None:
    """The cap is asked BEFORE the reading and never after it.

    $4.99 is on the day and this reading bills $0.01, so the moment it finishes
    the tenant is at $5.00 and over. Asked again afterwards, the same rule
    refuses -- and the operator is handed a 429 for a call that was made,
    succeeded and was billed, with the only copy of the offer thrown away.
    """
    uow = await _held()
    await _billed(uow, cost_usd=4.99, at=NOW.replace(hour=10))

    got = await _read(uow, asker=FakeAsker(_answer("wfl_1", [], cost_usd=0.01))).execute(
        _ctx(), utterance=SAID
    )

    assert got.workflow_id == "wfl_1"
    await _billed(uow, cost_usd=0.01, at=NOW.replace(hour=11))
    with pytest.raises(OverCap):
        await _read(uow, asker=FakeAsker(_answer("wfl_1", []))).execute(_ctx(), utterance=SAID)


# --- what a reading that runs answers with ----------------------------------


async def test_the_sentence_read_is_the_one_the_operator_typed() -> None:
    """The one argument this use case takes from its caller. A door that read a
    constant, or read the empty string the rig's `body.get` fell back to, still
    answers, still bills and offers whatever the model makes of nothing."""
    uow = await _held()
    asker = FakeAsker(_answer("wfl_1", [{"name": "areaName", "value": "ZONE4"}]))

    await _read(uow, asker=asker).execute(_ctx(), utterance=SAID)

    assert SAID in str(asker.asked[0]["evidence"])


async def test_the_jobs_it_is_read_against_are_the_ones_this_tenant_holds() -> None:
    """Two tenants, because a door that read the tenant off anything but `ctx`
    passes every other assertion in this file. `rival` shares the store and
    holds nothing, so the job the model names is one nobody holds -- which is a
    hallucination and not an offer."""
    uow = await _held()
    asker = FakeAsker(_answer("wfl_1", [{"name": "areaName", "value": "ZONE4"}]))

    got = await _read(uow, asker=asker).execute(_ctx(RIVAL), utterance=SAID)

    assert got.workflow_id is None
    assert "wfl_1" not in str(asker.asked[0]["evidence"]), (
        "it read the store's jobs, not this tenant's"
    )
    assert [row.tenant for row in _billed_rows(uow)] == ["rival"], "billed to the wrong tenant"


async def test_the_model_asked_is_the_one_the_record_names() -> None:
    """A model change is a prompt change, so the record names it and nothing
    a deployment configures can move it."""
    uow = await _held()
    asker = FakeAsker(_answer("wfl_1", []))

    await _read(uow, asker=asker).execute(_ctx(), utterance=SAID)

    assert [one["model"] for one in asker.asked] == [READ_REQUEST.model]
    assert asker.asked[0]["schema"] == dict(READ_REQUEST.output_schema), (
        "structured output, or it is prose"
    )


async def test_the_bill_is_stamped_with_the_containers_clock() -> None:
    """The use case reads no clock of its own and the route reads none at all.
    Which day a reading is billed to comes off the container's, and every plant
    here is six months from the wall clock."""
    uow = await _held()

    await _read(uow, asker=FakeAsker(_answer("wfl_1", []))).execute(_ctx(), utterance=SAID)

    (row,) = _billed_rows(uow)
    assert when(row.at) == NOW


async def test_a_sentence_naming_no_job_still_writes_the_bill() -> None:
    """`read_utterance`'s docstring: a row is written on every reading, a
    refusal included -- that is the case that matters, because it is then the
    only record left of a call that cost money and returned nothing.

    Three ways out, and all three billed: the model answered nothing at all,
    the model named a job nobody holds, and the model named a job that exists.
    The first two are the ones a door could plausibly skip, and skipping them
    means today's cap is summed without them.
    """
    both: tuple[dict[str, object] | None, ...] = (
        None,
        {"workflow_id": "wfl_nope", "values": [], "missing": [], "sure": True},
    )
    for data in both:
        uow = await _held()
        answer = Answer(data=data, cost_usd=0.0007, in_tokens=120)

        got = await _read(uow, asker=FakeAsker(answer)).execute(_ctx(), utterance=SAID)

        assert got.workflow_id is None
        (row,) = _billed_rows(uow)
        assert (row.workflow_id, row.cost_usd, row.in_tokens) == (None, 0.0007, 120)
        assert uow.commits == 1, "the bill was written and never committed"


async def test_a_reading_whose_model_call_failed_is_billed_and_not_answered_as_no_job() -> None:
    """`error` and `unpriced` both carrying something other than their default.

    A model name the price table never knew about records $0.0000 with the flag
    set, and a day summed on `cost_usd` alone reads as free while it spends.
    The row is the only place either fact survives -- the operator is told
    "no job matched" and goes and rephrases a sentence that was never read.
    """
    uow = await _held()
    answer = Answer(error="truncated: the answer hit the output-token ceiling", unpriced=True)

    got = await _read(uow, asker=FakeAsker(answer)).execute(_ctx(), utterance=SAID)

    assert got.answer.error == "truncated: the answer hit the output-token ceiling"
    (row,) = _billed_rows(uow)
    assert row.error == "truncated: the answer hit the output-token ceiling"
    assert row.unpriced is True


async def test_the_sentence_itself_is_not_stored() -> None:
    """`ChatReading` has no field for it and that is deliberate: there is no
    column for an operator's words about their own warehouse. The row exists
    for the cap and the spend line, and neither of those needs them.

    Asserted over the whole row rather than over a field list, because a door
    that smuggled the sentence into `workflow_id` -- or into `error`, which is
    free text -- would satisfy any check that only counted fields.
    """
    uow = await _held()
    said = "create a work area for zone 4 for ACME-99, ask Priya"

    await _read(uow, asker=FakeAsker(_answer("wfl_1", []))).execute(_ctx(), utterance=said)

    (row,) = _billed_rows(uow)
    assert {one.name for one in fields(ChatReading)} == {
        "id",
        "tenant",
        "at",
        "workflow_id",
        "in_tokens",
        "out_tokens",
        "thought_tokens",
        "cost_usd",
        "unpriced",
        "error",
    }, "a field was added to the row that an operator's sentence could be put in"
    for word in ("zone", "ACME-99", "Priya", said):
        assert word not in str(row), f"{word!r} reached the row"


_ORDER_UNDER_ONE_SEED = """
import asyncio

from sro.application.chat.understand import understand
from sro.domain.shared.prices import Answer, ModelSpend
from sro.domain.skill.workflow import Workflow

NAMES = [
    "zone",
    "clientCode",
    "statusCombo",
    "areaName",
    "ownerCode",
    "dockId",
    "siteCode",
    "lane",
]


class _Asker:
    async def ask(self, **_: object) -> Answer:
        return Answer(data={"workflow_id": "wfl_8", "values": [], "missing": [], "sure": True})


held = Workflow(
    id="wfl_8",
    tenant="acme",
    title="t",
    narrative="n",
    parameters=[{"name": name, "required": True} for name in NAMES],
)
print(",".join(asyncio.run(understand("x", [held], _Asker())).missing))
"""
"""One reading, in a fresh interpreter, printing the order its fields came back
in. Runs `understand` rather than `ReadChat` because that is where the set is
-- the use case and the route hand the list on untouched, which their own tests
above and next door hold separately."""


@pytest.mark.parametrize("seed", ["0", "1", "42", "31337"])
def test_what_is_missing_comes_back_in_one_order_whatever_the_hash_seed_is(seed: str) -> None:
    """`declared` is a set in `understand`, so an unsorted `missing` is the
    interpreter's hash order: the same sentence asked twice reorders the fields
    of the form the operator is looking at, and nothing about that is
    reproducible enough to screenshot or to test against.

    A subprocess and not a `monkeypatch.setenv`, because `PYTHONHASHSEED` is
    read once when the interpreter starts and setting it inside a running one
    changes nothing -- a parameterised test that only set the variable would be
    the same arrangement asserted four times. There is no random-ordering
    pytest plugin in this repo; this is the knob.

    Eight parameters, declared in an order that is neither the answer nor its
    reverse. At three names an unsorted `missing` agrees with the answer on
    roughly one seed in six; at eight it is one arrangement in 40320, so a
    green sweep here is the sort and not luck.
    """
    ran = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _ORDER_UNDER_ONE_SEED],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONHASHSEED": seed},
    )

    assert ran.stdout.strip() == (
        "areaName,clientCode,dockId,lane,ownerCode,siteCode,statusCombo,zone"
    )


async def test_the_day_the_cap_judges_is_the_callers_and_never_a_neighbours() -> None:
    """The cap's tenant, which nothing else in this file crosses with a spend.

    The two-tenant tests above plant no spend and every cap test above uses one
    tenant, so `over_cap(uow, TenantId("acme"), ...)` -- a literal in the one
    argument that says whose day is being summed -- survives all of them. What
    it costs if it is ever wrong that way is not subtle: a tenant that has spent
    nothing is refused because a neighbour spent, and a tenant over its own cap
    keeps spending because the neighbour has not.

    Both directions, because the first alone is also satisfied by a door with
    no cap in it at all.
    """
    uow = await _held(RIVAL)
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))  # TENANT's day, not RIVAL's

    got = await _read(uow, asker=FakeAsker(_answer("wfl_1", []))).execute(
        _ctx(RIVAL), utterance=SAID
    )

    assert got.workflow_id == "wfl_1", "another tenant's spending refused this one's reading"

    # And the converse: the same money on RIVAL's own day does refuse it.
    await uow.spend.record(
        ModelSpend(
            id="cht_rival", tenant=RIVAL.value, model="m", at=NOW.replace(hour=10), cost_usd=5.01
        )
    )

    with pytest.raises(OverCap):
        await _read(uow, asker=FakeAsker(_answer("wfl_1", []))).execute(_ctx(RIVAL), utterance=SAID)
