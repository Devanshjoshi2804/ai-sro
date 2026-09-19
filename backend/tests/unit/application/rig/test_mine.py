"""One pass, end to end -- and the six tests of `propose` that need a model.

Ported from `new_agent_arch/tests/test_mine.py` in full, names unchanged, plus
the seven tests `new_agent_arch/tests/test_umbrella.py` could only run through
a model call or a store. The eight that turned out to be `workflow_from` tests
wearing a `propose` costume went to `tests/unit/domain/rig/test_umbrella.py`,
against `workflow_from` itself.

Nothing here reaches Postgres. Two things every fixture below is arranged
against, both of them bugs that have already shipped on this branch:

* **The clock is the caller's.** `NOW` is a day in February 2025 and never
  today. The cap this pass is held to is summed since ITS midnight, so a pass
  that reads `datetime.now(UTC)` instead of its `now` cannot agree with these
  fixtures by the calendar.
* **A tie is planted against the answer.** Where the window's contents are
  asserted, the strong evidence is timed EARLIER than the weak, so a pack that
  ordered on `at` alone -- or that Postgres handed back in reverse insertion
  order -- is not satisfied by the plant.
"""

import asyncio
import logging
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sro.application.observation.mining_pass import (
    MineResult,
    fill_in_passwords,
    mine,
    propose,
    rekey_workflows,
)
from sro.domain.observation.gesture import Gesture, Intent, ValueSeen
from sro.domain.observation.pool import K_POOL_AGE
from sro.domain.observation.trim import is_secret
from sro.domain.observation.window import K_WINDOW_TOKENS, Packed, Window
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.umbrella import INSTRUCTIONS, K_EFFORT, K_SAMPLES
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeGestureRepository, FakeUnitOfWork

TENANT = TenantId("acme")
MODEL = "gemini-3.1-pro"
HOST = "http://127.0.0.1:63319"

NOW = datetime(2025, 2, 11, 23, tzinfo=UTC)
"""The rig's clock through all of this, and deliberately not today.

`over_cap` sums the day from the midnight before `now`, and every pass here
writes a `mining_passes` row stamped with it. Dated today, a fixture lets a
pass that ignores its `now` and reads `datetime.now(UTC)` agree by coincidence.
"""

CAP = 100.0
"""Far above anything these passes spend, so the cap is out of the way
everywhere except the one test that is about it."""


async def _day(tenant: TenantId = TENANT) -> tuple[FakeUnitOfWork, list[str]]:
    """One measured batch, stored, and its gesture ids in time order.

    Gesture ids are minted per correlation, so two calls give two disjoint
    days -- which is what the rig got from two stores.
    """
    uow = FakeUnitOfWork()
    found = _gestures(tenant.value)
    await uow.gestures.add_gestures(tuple(found))
    return uow, [g.id for g in sorted(found, key=lambda g: (g.at, g.id))]


async def _mine(
    uow: FakeUnitOfWork,
    asker: FakeAsker,
    *,
    kb: str = "",
    model: str = MODEL,
    cap_usd: float = CAP,
    tenant: TenantId = TENANT,
    ours: frozenset[str] = frozenset(),
) -> MineResult:
    return await mine(
        uow, tenant_id=tenant, asker=asker, model=model, now=NOW, cap_usd=cap_usd, kb=kb, ours=ours
    )


def _proposal(cites: list[str], **over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "create a work operation",
        "narrative": "the operator created a work operation",
        "systems": [HOST],
        # Two steps, not one: `validate` refuses a workflow shorter than
        # `identity.K_MIN_SHARED_STEPS`, because `resolve` can never match one
        # against a later doing and every pass would mint another copy. Both
        # steps cite the same evidence, so nothing else about these fixtures
        # moves -- `cited_ids` and the system checks read exactly as before.
        "steps": [
            {"order": 0, "cites": cites, "says": "do it", "system": HOST, "parameters": []},
            {"order": 1, "cites": cites, "says": "save it", "system": HOST, "parameters": []},
        ],
        "parameters": [],
        "same_as": None,
    }
    return {**base, **over}


def _found(*workflows: object) -> Answer:
    """An answer the model actually produced, at the rig's own $0.01."""
    return Answer(data={"workflows": list(workflows)}, cost_usd=0.01)


async def _pool_ids(uow: FakeUnitOfWork) -> set[str]:
    return set(await uow.pool.ids(TENANT))


def _rows(uow: FakeUnitOfWork) -> dict[str, Gesture]:
    """The stored gestures, editable. `FakeUnitOfWork.gestures` is annotated
    with the port it stands in for, and a port has no rows to reach into."""
    assert isinstance(uow.gestures, FakeGestureRepository)
    return uow.gestures.rows


def _seen(parameters: list[dict[str, object]], name: str) -> list[str]:
    """Every value one stored parameter has been given, as strings.

    By ANY of the control's names. A field is `Client Code` on its label and
    `clientCode` on the input, and which of those a parameter is called is a
    fact about the recording it was learnt from -- looking it up by one name
    only is how a test would go on passing while the job grew a second entry
    for the same field.
    """
    for parameter in parameters:
        listed = parameter.get("names")
        known = {str(one) for one in listed} if isinstance(listed, list) else set()
        if parameter.get("name") == name or name in known:
            values = parameter.get("seen_values")
            return [str(value) for value in values] if isinstance(values, list) else []
    return []


# --------------------------------------------------------------------------
# a day bigger than one window


def _crowd(strong: int, weak: int) -> tuple[list[Gesture], list[str], list[str]]:
    """A day bigger than one window, built out of the fixture's own rows.

    A gesture carrying a write outranks a plain click in `strength`, so the
    strong ones take their places first and the K_MIN_GESTURES floor decides
    how many of the weak ones join them. The rest are what the budget leaves
    out. The fixture's seven originals go, so the arithmetic is exactly these
    -- and the strong ones are timed FIRST, so a window that ordered on `at`
    rather than on strength would pack a different set.
    """
    found = _gestures(TENANT.value)
    writing = next(g for g in found if any(call.method != "GET" for call in g.requests))
    plain = next(g for g in found if not g.requests and g.action.kind == "click")
    strong_rows = [replace(writing, id=f"ges_strong_{i:02d}", at=1000.0 + i) for i in range(strong)]
    # Close behind the strong ones, not a thousand seconds later. `checks`
    # narrows a proposal to one sitting -- gestures more than K_SITTING_GAP_S
    # apart are two doings -- so a fixture that spaced these beyond that bound
    # had every weak gesture struck off the proposal and land in the pool as
    # unexplained. The strong ones still come FIRST, which is the plant this
    # fixture exists to make: a window that ordered on `at` rather than on
    # strength would pack a different set.
    weak_rows = [replace(plain, id=f"ges_weak_{i:02d}", at=1100.0 + i) for i in range(weak)]
    return (
        [*strong_rows, *weak_rows],
        [row.id for row in strong_rows],
        [row.id for row in weak_rows],
    )


async def _crowded_day(strong: int, weak: int) -> tuple[FakeUnitOfWork, list[str], list[str]]:
    uow = FakeUnitOfWork()
    rows, strong_ids, weak_ids = _crowd(strong, weak)
    await uow.gestures.add_gestures(tuple(rows))
    return uow, strong_ids, weak_ids


CROWDED_KB = "x" * 600_000
"""Bigger than the window has room for, which is how a test gets `pack` to
leave evidence out without reaching past `mine`'s own arguments to set the
budget. Under it the budget holds nothing and K_MIN_GESTURES decides how many
are packed, so strength decides which."""

NEARLY_FULL_KB = "x" * ((K_WINDOW_TOKENS - 10_000) * 4)
"""Most of the budget, and not all of it: what is left is ten thousand tokens
of room, so what else is subtracted from it is visible in how many gestures
fit. Under CROWDED_KB the floor decides and nothing else shows.

Derived from `K_WINDOW_TOKENS` rather than written as the 140,000 it used to
be. When the budget was lowered to keep the prompt under the 200K price
boundary, a literal sized against the old one left NEGATIVE room -- so the
floor decided, both halves of the comparison packed exactly
`K_MIN_GESTURES`, and a test about the budget passed on nothing to do with
it."""


# --------------------------------------------------------------------------
# what a pass keeps


async def test_a_pass_keeps_what_it_can_prove() -> None:
    uow, ids = await _day()
    asker = FakeAsker(
        Answer(
            data={"workflows": [_proposal(ids[:2])]}, in_tokens=900, out_tokens=100, cost_usd=0.01
        )
    )

    result = await _mine(uow, asker)

    assert result.kept == 1
    assert result.rejections == []
    assert len(await uow.workflows.known(TENANT)) == 1


async def test_a_workflow_citing_evidence_that_does_not_exist_is_refused() -> None:
    uow, _ = await _day()

    result = await _mine(uow, FakeAsker(_found(_proposal(["ges_invented"]))))

    assert result.kept == 0
    assert len(result.rejections) == 1
    assert result.rejections[0].reason == "unknown gesture"
    assert await uow.workflows.known(TENANT) == ()


async def test_a_workflow_naming_a_system_its_evidence_never_touched_is_refused() -> None:
    """The one lie this architecture cannot afford: a cross-system job whose
    second system is invented. It is the reason `validate` takes the system of
    every cited gesture rather than the set of ids, and the loop must hand it
    that mapping -- a set of ids passes the citation check and cannot fail
    this one."""
    uow, ids = await _day()
    asker = FakeAsker(_found(_proposal(ids[:2], systems=["http://sap.example"])))

    result = await _mine(uow, asker)

    assert result.kept == 0
    assert result.rejections[0].reason == "system not in evidence"


async def test_a_job_that_is_only_this_deployments_own_console_is_refused() -> None:
    """`checks.work_only`, wired into the loop rather than left unreachable:
    `validate` has already asked whether the evidence is honest, and this asks
    whether anybody wanted it mined. A proposal naming no system but ours has
    none left once `ours` strikes it."""
    uow, ids = await _day()
    asker = FakeAsker(_found(_proposal(ids[:2])))

    result = await _mine(uow, asker, ours=frozenset({"127.0.0.1:63319"}))

    assert result.kept == 0
    assert result.rejections[0].reason == "not a job"
    assert await uow.workflows.known(TENANT) == ()


async def test_a_job_on_a_host_that_is_not_ours_survives_the_strike() -> None:
    """The other side of the same guard: `ours` naming a host this proposal
    never touches strikes nothing, and the job is kept as it always was."""
    uow, ids = await _day()
    asker = FakeAsker(_found(_proposal(ids[:2])))

    result = await _mine(uow, asker, ours=frozenset({"console.example:3000"}))

    assert result.kept == 1
    assert result.rejections == []


async def test_a_gesture_whose_system_is_unknown_cannot_prove_a_step_that_names_one() -> None:
    """`Gesture.system` is None whenever the url could not be parsed into one,
    and `validate` takes `dict[str, str]` -- so the loop substitutes "". An
    unknown system is a silence, not a second system: a step citing only
    unattributed evidence is refused under its own reason rather than being
    read as a crossing."""
    uow, ids = await _day()
    _rows(uow)[ids[0]].system = None
    _rows(uow)[ids[0]].url = None

    result = await _mine(uow, FakeAsker(_found(_proposal(ids[:1]))))

    assert result.kept == 0
    assert result.rejections[0].reason == "unattributed evidence"


async def test_a_second_pass_over_the_same_evidence_adds_no_second_workflow() -> None:
    """Mining re-runs over evidence it has already read."""
    uow, ids = await _day()
    proposal = _proposal(ids[:2])
    asker = FakeAsker(_found(proposal), _found(proposal))

    await _mine(uow, asker)
    second = await _mine(uow, asker)

    assert second.resolutions[0].kind == "same_occurrence"
    assert len(await uow.workflows.known(TENANT)) == 1


async def test_one_pass_proposing_the_same_job_twice_stores_it_once() -> None:
    """Resolving against the workflows read before the pass began makes
    self-match unreachable, and lets a pass that repeated itself save the same
    job twice. What this pass has already kept is known too."""
    uow, ids = await _day()

    result = await _mine(uow, FakeAsker(_found(_proposal(ids[:2]), _proposal(ids[:2]))))

    assert result.proposed == 2
    assert result.kept == 1
    assert result.resolutions[1].kind == "same_occurrence"
    assert len(await uow.workflows.known(TENANT)) == 1


async def test_two_passes_at_once_do_not_both_read_the_same_window() -> None:
    """Both would read an empty store before either saved, so identity has
    nothing to match on and the same job is stored -- and billed -- twice."""
    uow, ids = await _day()
    asker = FakeAsker(_found(_proposal(ids[:2])), _found(_proposal(ids[:2])))

    await asyncio.gather(_mine(uow, asker), _mine(uow, asker))

    assert len(await uow.workflows.known(TENANT)) == 1


async def test_two_tenants_mine_at_the_same_time_rather_than_in_turn() -> None:
    """Keyed by tenant, not by the bare word "mining". A single global name
    makes two DIFFERENT tenants take turns, which is nothing but a queue --
    commit 7fc2b99 fixed exactly that for the reading loop, after the bake-off
    ran five models over five copies of one day and a global lock turned an
    hour of parallel work into five hours of serial work.

    Deadlocks under one lock and completes under two, with no sleep in it:
    the first tenant's asker will not answer until the second's has been
    asked, which can never happen while the second is waiting for the first's
    lock.
    """
    uow, _ = await _day()
    await uow.gestures.add_gestures(tuple(_gestures("other-corp")))
    second_asked = asyncio.Event()

    class Gated:
        """An asker that answers only once its partner has been asked."""

        def __init__(self, *, waits: bool) -> None:
            self._waits = waits

        async def ask(self, **_: object) -> Answer:
            if self._waits:
                await second_asked.wait()
            else:
                second_asked.set()
            return _found()

    await asyncio.wait_for(
        asyncio.gather(
            mine(
                uow,
                tenant_id=TENANT,
                asker=Gated(waits=True),
                model=MODEL,
                now=NOW,
                cap_usd=CAP,
            ),
            mine(
                uow,
                tenant_id=TenantId("other-corp"),
                asker=Gated(waits=False),
                model=MODEL,
                now=NOW,
                cap_usd=CAP,
            ),
        ),
        timeout=1,
    )


async def test_a_reading_that_cited_one_corner_of_the_window_says_so() -> None:
    """K_MIN_COVERAGE and K_MAX_SKEW were declared for this loop to read.
    Long-context citation bias is invisible without counting, and a pass that
    does not report it is a pass nobody can measure."""
    uow, ids = await _day()
    # Its own day: gesture ids are minted per batch, so the ids the whole
    # window is cited by are not the ids of the day above.
    elsewhere, others = await _day()

    lopsided = await _mine(uow, FakeAsker(_found(_proposal(ids[:1]))))
    even = await _mine(elsewhere, FakeAsker(_found(_proposal(others))))

    assert lopsided.lopsided is True
    assert even.lopsided is False


async def test_a_pass_that_keeps_nothing_still_says_it_read_the_window() -> None:
    """A proposal that resolved onto a stored workflow still read the window and
    still cited real gestures. Measured on real output: an identity re-run
    proposed three, kept none, reported coverage 0.00 with lopsided=True -- and
    re-pooled every gesture those proposals cited -- while having read the whole
    window correctly."""
    uow, ids = await _day()

    first = await _mine(uow, FakeAsker(_found(_proposal(ids))))
    assert first.kept == 1

    again = await _mine(uow, FakeAsker(_found(_proposal(ids))))

    assert again.kept == 0, "the same job again is not a new workflow"
    assert again.rejections == [], "it was not refused, it was recognised"
    assert again.coverage.coverage > 0.0, "it read the window; coverage must say so"
    assert not again.lopsided, "a correct pass that keeps nothing is not lopsided"
    assert set(ids).isdisjoint(await _pool_ids(uow)), (
        "evidence a stored workflow already explains must not be re-pooled"
    )


async def test_the_key_a_pass_mints_is_a_sequence_and_not_a_set() -> None:
    """The key `identity.resolve` compares proposals on, minted here.

    `rekey_workflows` recomputes it at startup from the same evidence through
    the same `ordered_cites`, and a pass that minted it any other way means
    every workflow mined is silently rewritten on the next boot -- and, until
    that boot, resolved against a key nothing else agrees with.

    A gesture two steps both stand on is two rungs of the shape, and
    `cited_ids` -- the set -- collapses it to one. That is what makes this
    deterministic where an order plant is not: the set survives every hash
    seed when the assertion is only about order, and none of them when a rung
    goes missing. The steps are also LISTED backwards, though that half cannot
    be made to fail HERE and the reason is worth writing down: `workflow_from`
    has already sorted a proposal's steps by the time the pass sees one, so
    dropping `ordered_cites`' own sort at this call site is an equivalent
    mutant. It is not one in `rekey_workflows`, where the steps come off the
    store -- which is where the sort is pinned.
    """
    uow, ids = await _day()
    typed, saved = ids[0], ids[-1]
    proposal = _proposal(
        [],
        steps=[
            {"order": 2, "cites": [saved], "says": "check it saved", "system": HOST},
            {"order": 1, "cites": [saved], "says": "save", "system": HOST},
            {"order": 0, "cites": [typed], "says": "type the code", "system": HOST},
        ],
    )

    result = await _mine(uow, FakeAsker(_found(proposal)))

    assert result.kept == 1
    key = (await uow.workflows.known(TENANT))[0].shape_key
    # Four rungs and not three: this day's evidence includes a type into a
    # field the recorder marked secret, on the same host and inside the doing,
    # and `with_passwords` adds the step for it that no model can cite. The
    # property under test is unchanged -- the key is the order the steps run in
    # and not a set -- and the password is typed second, where the operator
    # typed it.
    assert [triple[2] for triple in key] == ["type", "type", "click", "click"]


async def test_the_jobs_already_proven_are_paid_for_out_of_the_window() -> None:
    """`summary` goes to `build_prompt`, so it is billed as input, AND to
    `pack`, so it comes off the budget. `pack`'s subtraction is guarded in the
    domain; the caller handing it over was not, and a caller that passed `[]`
    measured the prompt smaller than it ships.

    That is the same failure as the `evidence_tokens` under-count this module
    was built on: a window filled to a budget that left out the fixed cost of
    the prompt it is budgeting went over the 200K boundary where Gemini 3.1
    Pro's input price doubles -- silently, at double the price.

    Same evidence both times, so the only thing that moved is what the tenant
    already knows.
    """
    plain, _, _ = _crowd(strong=0, weak=200)
    proven = [
        Workflow(
            id=f"wfl_{i:03d}",
            tenant=TENANT.value,
            # Long enough to matter, because that is the case: a tenant with a
            # year of mining behind it has a long "jobs already proven" block.
            title="create a work operation in the western yard " * 5,
            narrative="",
            systems=[HOST],
            shape_key=[[HOST, "clientCode", "type"]],
        )
        for i in range(40)
    ]

    sizes = []
    for known in ([], proven):
        uow = FakeUnitOfWork()
        await uow.gestures.add_gestures(tuple(plain))
        for workflow in known:
            await uow.workflows.save(workflow)
        sizes.append((await _mine(uow, FakeAsker(_found()), kb=NEARLY_FULL_KB)).window_size)

    blind, paid = sizes
    assert blind > paid, "the known-jobs block has to come out of the same budget"


async def test_a_gesture_linked_across_two_systems_earns_its_place() -> None:
    """`linked` is `strength`'s cross-system bonus, and the pool's docstring
    calls that "the whole mechanism by which one operator's Blue Yonder half
    meets another operator's SAP half". `strength` is guarded in the domain;
    the caller handing it the set was not.

    What hid it: `_packed` applies `linked` to POOLED entries too, so a caller
    that stopped passing it to `pack` still bonused everything carried over,
    and every pool test stayed green while fresh evidence quietly lost it.
    This pass has an empty pool.

    Planted against `at`: the linked pair is the EARLIEST evidence of the day,
    so a window ordered on time alone -- `pack` breaks ties newest-first --
    leaves it out. Sizes do not enter into
    it -- the budget here cannot hold anything, so K_MIN_GESTURES decides who
    is in and strength decides which.
    """
    uow, _, weak_ids = await _crowded_day(strong=0, weak=30)
    await _link(uow, weak_ids[:2], "CROSSES-TWO-SYSTEMS", "https://sap.example")
    asker = FakeAsker(_found())

    result = await _mine(uow, asker, kb=CROWDED_KB)
    # Before the crossings block, so a linked id is read where it was PACKED
    # rather than where it was hinted at.
    day = str(asker.asked[0]["evidence"]).split("## Values appearing in more than one system")[0]

    assert result.window_size == 25
    assert weak_ids[0] in day and weak_ids[1] in day, "a crossing is what pulls evidence in"
    assert weak_ids[5] not in day, "and it displaced an unlinked peer to do it"


# --------------------------------------------------------------------------
# the pool


async def test_everything_the_pass_did_not_cite_lands_in_the_pool() -> None:
    uow, ids = await _day()

    await _mine(uow, FakeAsker(_found(_proposal(ids[:1]))))

    assert await _pool_ids(uow) == set(ids[1:])


async def test_the_pool_ages_once_a_pass_and_not_twice() -> None:
    """K_POOL_AGE counts passes. An entry that entered on this pass has sat
    through exactly one of them."""
    uow, _ = await _day()

    await _mine(uow, FakeAsker(_found()))

    assert {entry.age for entry in await uow.pool.waiting(TENANT)} == {1}


async def test_a_pooled_gesture_the_pass_cited_leaves_the_pool() -> None:
    """`claimed` is every cited id and is never narrowed to this pass's own
    fresh evidence. A pooled gesture is packed into the window beside the fresh
    ones, so a pass can cite evidence that is only in the pool -- and a
    citation left in the pool goes on ageing and retires having been placed."""
    uow, ids = await _day()

    await _mine(uow, FakeAsker(_found()))
    assert await _pool_ids(uow) == set(ids), "nothing was cited, so everything waits"

    await _mine(uow, FakeAsker(_found(_proposal(ids[:2]))))

    assert await _pool_ids(uow) == set(ids[2:])


async def test_a_pooled_gesture_whose_row_is_gone_is_named_not_dropped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The pool holds ids; the window takes evidence. A pooled id that joins to
    no gesture row would otherwise leave the pass through a comprehension
    filter, and the number of gestures read would simply be smaller than the
    pool said."""
    uow, ids = await _day()
    logger = "sro.application.observation.mining_pass"
    with caplog.at_level(logging.WARNING, logger=logger):
        await _mine(uow, FakeAsker(_found()))
        # A pass that lost nothing says nothing. A warning every pass is a
        # warning nobody reads by the time there is something to read.
        assert caplog.text == ""

        del _rows(uow)[ids[0]]
        result = await _mine(uow, FakeAsker(_found()))

    assert result.lost_pool == [ids[0]]
    assert result.window_size == len(ids) - 1
    # The result is gone the moment the pass returns; the log is what is left.
    assert ids[0] in caplog.text


async def test_evidence_the_budget_left_out_lands_in_the_pool() -> None:
    """`left_out` was reported and dropped. A 150K window holds about 620
    gestures and an operator day runs to a few thousand, so past one window the
    same tail lost every pass forever while the count faithfully said so."""
    uow, strong_ids, weak_ids = await _crowded_day(strong=20, weak=10)
    read = strong_ids + weak_ids[-5:]

    result = await _mine(uow, FakeAsker(_found(_proposal(read))), kb=CROWDED_KB)

    assert result.rejections == []
    assert result.window_size == len(read)
    assert result.left_out == len(weak_ids[:5])
    # The pass cited everything it read, so the pool holds exactly what the
    # budget refused. Before the fix it held nothing at all.
    assert await _pool_ids(uow) == set(weak_ids[:5])


async def test_evidence_the_window_never_showed_does_not_spend_its_patience() -> None:
    """K_POOL_AGE is six READINGS, and an entry the budget left out was not
    read. Ageing the whole pool on every pass retired 2,630 of a
    3,240-gesture day unread -- evidence that had never once been in a
    prompt, retired for having been passed over by it."""
    uow, strong_ids, weak_ids = await _crowded_day(strong=20, weak=10)

    await _mine(uow, FakeAsker(_found()), kb=CROWDED_KB)

    ages = {entry.gesture_id: (entry.age, entry.waited) for entry in await uow.pool.waiting(TENANT)}
    assert ages[strong_ids[0]] == (1, 0), "shown and not cited: one reading of patience spent"
    assert ages[weak_ids[0]] == (0, 1), "never shown: it waited, it did not read"


async def test_an_entry_that_has_waited_longer_outranks_one_that_has_not() -> None:
    """K_POOL_WAIT is what rotates the day through the window. A flat carry-over
    bonus reorders nothing: every pooled entry gains the same 0.5, the ranking
    is what it was, and the window shows the same strongest items every pass.
    Measured on a synthetic all-tabs day of 3,240 gestures, passes two through
    ten packed the identical 468 and ten passes had shown 19% of the day.

    The tie is planted against the answer: the entry that has waited is the
    LATER of the two, so a pack that broke the tie on `at` -- or that dropped
    the per-pass bonus and left the two equal -- would take the other one.
    """
    uow, _strong, weak_ids = await _crowded_day(strong=24, weak=2)
    # The EARLIER of the two is the patient one: `pack` breaks a tie
    # newest-first, so without its waiting bonus this is the one that loses.
    patient, hasty = weak_ids[0], weak_ids[1]
    await uow.pool.add_unclaimed(TENANT, window_ids=(patient,), claimed=frozenset())
    # An empty window: a pass that packed nothing passed everything over.
    await uow.pool.age(TENANT, shown=())
    await uow.pool.add_unclaimed(TENANT, window_ids=(hasty,), claimed=frozenset())
    asker = FakeAsker(_found())

    result = await _mine(uow, asker, kb=CROWDED_KB)
    prompt = str(asker.asked[0]["evidence"])

    assert result.window_size == 25, "24 strong and exactly one weak place"
    assert patient in prompt, "one pass of waiting is what bought the place"
    assert hasty not in prompt


async def test_a_gesture_the_budget_left_out_is_read_by_the_next_pass() -> None:
    """Being in the pool is the point only because K_POOL_BONUS then buys it a
    place. This asserts the place, not the row: the second pass proposes a
    workflow over the tail, and a tail still outside the window is refused for
    citing gestures the pass never saw."""
    uow, strong_ids, weak_ids = await _crowded_day(strong=20, weak=10)
    tail = weak_ids[:5]
    asker = FakeAsker(
        _found(_proposal(strong_ids + weak_ids[-5:])),
        _found(_proposal(tail, title="the tail")),
    )

    await _mine(uow, asker, kb=CROWDED_KB)
    second = await _mine(uow, asker, kb=CROWDED_KB)

    assert [r.reason for r in second.rejections] == []
    assert second.kept == 1
    # The window is the same size; the bonus changed who is in it. The fresh
    # weak gestures that displaced the tail last pass are this pass's tail.
    assert second.window_size == 25
    assert second.left_out == len(tail)


async def test_a_retired_gesture_loses_its_bonus_and_not_its_place() -> None:
    """The decision K_POOL_AGE records, asserted from the window's side.

    Retirement takes K_POOL_BONUS away and nothing else: the gesture is packed
    again as ordinary evidence. So a retired entry loses a contested place to
    fresh evidence of equal strength (it no longer outranks it), and takes its
    place in a window with room (it was never removed from the running).
    """
    uow, strong_ids, weak_ids = await _crowded_day(strong=24, weak=5)
    # The earliest weak gesture: `pack` breaks a tie newest-first, so once the
    # bonus is gone this is the one fresh evidence beats.
    retiree = weak_ids[0]
    await uow.pool.add_unclaimed(TENANT, window_ids=(retiree,), claimed=frozenset())
    for _ in range(K_POOL_AGE + 1):
        await uow.pool.age(TENANT)
    assert [entry.gesture_id for entry in await uow.pool.retired(TENANT)] == [retiree]

    asker = FakeAsker(_found(), _found())
    tight = await _mine(uow, asker, kb=CROWDED_KB)
    roomy = await _mine(uow, asker)

    # 24 strong and one weak, and the weak place goes to the latest of them
    # rather than to the retiree, which would have taken it at 1.5.
    assert tight.window_size == 25
    assert retiree not in str(asker.asked[0]["evidence"]), (
        "a retired entry competes without its bonus"
    )
    assert weak_ids[-1] in str(asker.asked[0]["evidence"]), (
        "the place it lost went to fresh evidence"
    )
    # Same day, a budget with room for everything: it is still evidence.
    assert roomy.window_size == len(strong_ids) + len(weak_ids)
    assert retiree in str(asker.asked[1]["evidence"]), "retirement is not removal from the window"


async def test_a_day_of_refused_calls_does_not_retire_the_pool() -> None:
    """K_POOL_AGE is six readings, not six attempts. An expired key, a model
    name the API 404s, or a day of 503s ages nothing: the pool was never read,
    so its patience was never spent."""
    uow, ids = await _day()
    await uow.pool.add_unclaimed(TENANT, window_ids=tuple(ids), claimed=frozenset())
    refused = FakeAsker(*[Answer(error="ServerError: 503 UNAVAILABLE") for _ in range(8)])

    for _ in range(8):
        result = await _mine(uow, refused)
        assert result.error == "ServerError: 503 UNAVAILABLE"

    assert await uow.pool.retired(TENANT) == ()
    assert await _pool_ids(uow) == set(ids)
    assert {entry.age for entry in await uow.pool.waiting(TENANT)} == {0}


# --------------------------------------------------------------------------
# the bill


async def test_the_cost_of_the_pass_is_recorded() -> None:
    uow, _ = await _day()
    asker = FakeAsker(
        Answer(
            data={"workflows": []},
            in_tokens=900,
            out_tokens=100,
            thought_tokens=40,
            cost_usd=0.037,
        )
    )

    result = await _mine(uow, asker)

    assert result.cost_usd == 0.037
    billed = await uow.workflows.passes(TENANT)
    assert [one.cost_usd for one in billed] == [0.037]
    # The tokens as well, and `thought_tokens` above all: K_EFFORT
    # exists to spend those, and a row that reports the dollars without them
    # cannot say what the pass was thinking with.
    assert (billed[0].in_tokens, billed[0].out_tokens, billed[0].thought_tokens) == (900, 100, 40)
    # Stamped with the caller's clock and not the server's, so the day a pass
    # is billed to is the day its caller meant -- and so a cap summed from
    # that day's midnight is summing the same day.
    assert billed[0].started_at == NOW.isoformat()
    # A pass nobody committed is a pass nobody was billed for.
    assert uow.commits == 1


async def test_the_bill_belongs_to_the_pass_and_is_recorded_once() -> None:
    """One call proposes every workflow in a pass, so the pass is what has a
    cost. Copying `Answer.cost_usd` onto each workflow made the total grow with
    how well the pass did: three workflows out of this $0.04 call summed to
    $0.12, and a four-workflow pass would have said $0.16."""
    uow, ids = await _day()
    three = [
        _proposal(ids[0:2], title="create a work operation"),
        _proposal(ids[2:4], title="receive a shipment"),
        _proposal(ids[4:6], title="correct a count"),
    ]
    asker = FakeAsker(
        Answer(data={"workflows": three}, in_tokens=900, out_tokens=100, cost_usd=0.04)
    )

    result = await _mine(uow, asker)

    assert result.kept == 3
    billed = await uow.workflows.passes(TENANT)
    # One row, at the real figure -- not 0.04 * 3.
    assert len(billed) == 1
    assert sum(one.cost_usd for one in billed) == 0.04
    assert sum(one.cost_usd for one in billed) != 0.04 * result.kept
    # And every workflow can name the row that was billed for it.
    assert {w.pass_id for w in await uow.workflows.known(TENANT)} == {result.pass_id}


async def test_a_pass_whose_price_is_unknown_says_so_in_its_row() -> None:
    """A $0.00 pass and a pass whose cost could not be established are the same
    row in cost_usd alone. A total that reads the second as free understates
    the bill and says nothing about it."""
    uow, _ = await _day()

    await _mine(uow, FakeAsker(Answer(data={"workflows": []}, cost_usd=0.0, unpriced=True)))

    row = (await uow.workflows.passes(TENANT))[0]
    assert row.cost_usd == 0.0
    assert row.unpriced is True


async def test_a_refusal_costs_the_pass_and_not_the_process() -> None:
    uow, _ = await _day()

    result = await _mine(uow, FakeAsker(Answer(error="503")))

    assert result.kept == 0
    assert result.proposed == 0


async def test_a_refused_pass_is_still_a_row_and_still_says_why() -> None:
    """The call happened, may have been billed, and returned nothing. Without a
    row it is indistinguishable from a pass that was never run."""
    uow, _ = await _day()

    result = await _mine(uow, FakeAsker(Answer(error="503", unpriced=True)))

    assert result.error == "503"
    assert [one.error for one in await uow.workflows.passes(TENANT)] == ["503"]


async def test_a_refused_pass_is_not_recorded_as_lopsided() -> None:
    """`lopsided` says a model's citations fell in one corner of the window.
    A refused call cited nothing at all, so coverage is 0.0 and the flag fired
    on every 503 -- the passes table, which is what a person reads, blaming
    citation bias for a reading that never happened."""
    uow, _ = await _day()

    result = await _mine(uow, FakeAsker(Answer(error="ServerError: 503")))

    assert result.lopsided is False
    row = (await uow.workflows.passes(TENANT))[0]
    assert row.lopsided is False
    assert row.coverage == 0.0
    assert row.error == "ServerError: 503"


async def test_the_pass_row_is_written_even_when_the_work_after_the_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The row is the only record of a call that cost money. Written last, an
    exception anywhere after the model answered lost the bill -- and left any
    workflow already saved pointing at a pass_id with no row behind it."""
    uow, ids = await _day()

    async def boom(workflow: object) -> None:
        raise RuntimeError("database is locked")

    monkeypatch.setattr(uow.workflows, "save", boom)
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.04))

    with pytest.raises(RuntimeError):
        await _mine(uow, asker)

    billed = await uow.workflows.passes(TENANT)
    assert [one.cost_usd for one in billed] == [0.04], "the call was billed and nothing recorded it"


async def test_the_bill_is_written_on_a_session_the_save_killed() -> None:
    """The sibling above plants a Python error, where the session is fine. A
    REAL store failure kills the transaction: Postgres refuses every further
    statement on it -- InFailedSQLTransactionError -- so the bill written in
    the `finally` failed too, its DBAPIError replaced the exception that
    caused it, and the row that is the only record of a paid-for call was
    lost. Measured against the suite's own Postgres: `passes: 0`.

    The rig never met this. Its `store.execute` opened a connection per
    statement, so `save_workflow` and the pass insert were separate committed
    transactions and the bill after a failed save simply landed. One session
    is this port's shape, so the rollback-and-retry is what restores the rig's
    guarantee. The workflow itself is gone either way -- Postgres discarded it
    when the statement failed -- which is not something this fake models, and
    is why the integration test beside it exists.
    """
    uow, ids = await _day()
    uow._workflows.poisoned = True
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.04))

    with pytest.raises(RuntimeError):
        await _mine(uow, asker)

    assert uow.rollbacks == 1, "the session had to be revived before it could be written to"
    assert [one.cost_usd for one in await uow.workflows.passes(TENANT)] == [0.04]
    assert uow.commits == 1


async def test_a_day_over_its_cap_is_not_mined_and_is_not_billed() -> None:
    """The cap stops the ASKING, and it is read before the pass asks anything.
    This is the most expensive call in the system: a cap checked after the
    window is packed is a cap that has already paid for the pass it stops. And
    no `mining_passes` row -- that row exists to record a call that cost money,
    and this pass never made one."""
    uow, ids = await _day()
    asker = FakeAsker(_found(_proposal(ids[:2])))

    result = await _mine(uow, asker, cap_usd=0.0)

    assert asker.asked == [], "the model was never asked"
    assert result.error is not None and "daily cap" in result.error
    assert await uow.workflows.passes(TENANT) == (), "nothing was billed, so nothing is recorded"
    assert await uow.workflows.known(TENANT) == ()
    assert await _pool_ids(uow) == set()
    assert uow.commits == 0, "a pass that wrote nothing must not commit the caller's session"


# --------------------------------------------------------------------------
# what a second doing teaches


def _redone(rows: list[Gesture], value: str, suffix: str, offset: float) -> list[Gesture]:
    """The same job done again: its own gestures, and the operator typed
    something else into the same control.

    A second doing means NEW gestures -- that is why identity matches on shape
    rather than on cited ids, and why a diff has two values to compare.
    """
    fresh = []
    for row in rows:
        action = row.action
        if action.kind == "type" and action.value:
            action = replace(action, value=value)
        fresh.append(replace(row, id=f"{row.id}_{suffix}", at=row.at + offset, action=action))
    return fresh


async def test_a_pass_that_recognises_a_job_learns_what_varies_in_it() -> None:
    """A pass that keeps nothing has still learnt something if it recognised a
    job and found out what changes in it. That is the difference between
    watching the same work twice and understanding it, and two doings are the
    only evidence that can tell a parameter from a constant."""
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]

    first = await _mine(uow, FakeAsker(_found(_proposal(ids))))
    assert first.kept == 1
    assert first.learned_parameters == 0, "one doing cannot name a parameter"

    again_rows = _redone(original, "SOMETHING-ELSE", "again", 10_000.0)
    await uow.gestures.add_gestures(tuple(again_rows))

    again = await _mine(uow, FakeAsker(_found(_proposal([g.id for g in again_rows]))))

    assert again.kept == 0, "it is the same job, not a new one"
    assert again.learned_parameters >= 1, "and this time it knows what varies"
    stored = (await uow.workflows.known(TENANT))[0]
    assert "SOMETHING-ELSE" in _seen(stored.parameters, "clientCode")

    # And the ROW says so, not only the result. Until 0041 there was no column
    # for it: `MineResult` counted what the pass learnt and the persistence
    # layer dropped it, so a pass that learnt three left no record it had --
    # measured on the real store, where the only place the figure appeared was
    # a return value in a terminal. This test asserted the result and never the
    # row, which is exactly how that survived being ported.
    #
    # Asserted as a multiset and not in order, deliberately: `FakeClock` gives
    # every pass the same instant, so `passes()` orders on `(started_at, id)`
    # and the tie is broken by an id nobody planted. Sorting on `started_at`
    # here read [1, 0] and expected [0, 1] -- an ordering assertion the data
    # cannot support, which is this project's fourth instance of exactly that.
    learnt = sorted(one.learned_parameters for one in await uow.workflows.passes(TENANT))
    assert learnt == [0, again.learned_parameters]
    kept = {one.kept for one in await uow.workflows.passes(TENANT)}
    assert kept == {0, 1}, "a pass that learnt without keeping still reads as a pass"


async def test_the_job_stops_being_named_after_the_first_doing_of_it() -> None:
    """A title is written by a model reading ONE occurrence, so it names that
    occurrence -- and the store holds "Create Customer Type DSS" over a
    customer type since observed as DSS, DPP, CCD and CCF. The second doing is
    the first moment anything knows that value varies, and it is where the job
    gets its own name back: the title is what the offer card shows, and one
    run's value in it makes every later demonstration look like other work.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]

    named_after_one = _proposal(ids, title="create a work operation ACME-4471")
    await _mine(uow, FakeAsker(_found(named_after_one)))
    first = (await uow.workflows.known(TENANT))[0]
    assert first.title == "create a work operation ACME-4471", "one doing proves nothing yet"

    again_rows = _redone(original, "SOMETHING-ELSE", "again", 10_000.0)
    await uow.gestures.add_gestures(tuple(again_rows))
    again = await _mine(uow, FakeAsker(_found(_proposal([g.id for g in again_rows]))))

    assert again.kept == 0, "it is the same job, not a new one"
    stored = (await uow.workflows.known(TENANT))[0]
    assert stored.title == "create a work operation", "and it is the job's name now"
    assert "ACME-4471" in _seen(stored.parameters, "clientCode"), "the value is kept where it goes"


async def test_a_third_doing_widens_a_parameter_it_does_not_discard_it() -> None:
    """`seen_values` promises "every value observed" and delivered two.

    `learn_parameters` always diffs the STORED steps -- doing #1 -- against the
    proposal, and a name already present was skipped outright, so a parameter's
    range froze at the first pair however many times the job was done again. A
    range is the useful part of a parameter: a runner asked for `$clientCode`
    wants to know it has been ACME-4471, SOMETHING-ELSE and A-THIRD-ONE.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]

    await _mine(uow, FakeAsker(_found(_proposal(ids))))

    passes = []
    for value, suffix, offset in (
        ("SOMETHING-ELSE", "again", 10_000.0),
        ("A-THIRD-ONE", "thrice", 20_000.0),
    ):
        rows = _redone(original, value, suffix, offset)
        await uow.gestures.add_gestures(tuple(rows))
        passes.append(await _mine(uow, FakeAsker(_found(_proposal([g.id for g in rows])))))

    # The third doing NAMES nothing -- `clientCode` was already a parameter --
    # so `fresh` is empty and the only work it did was widen. The count is what
    # the pass TOUCHED, not what it named: counting names reported this pass as
    # having learnt nothing while it wrote a third value to the store, which is
    # the reading `mining_passes.learned_parameters` published on the live
    # database. Asserted on the wire's own figure and not only on the store,
    # because asserting the store is exactly how it survived.
    assert passes[1].kept == 0, "the third doing is still the same job"
    assert passes[1].learned_parameters == 1, "and widening one parameter is learning one"

    stored = (await uow.workflows.known(TENANT))[0]
    seen = _seen(stored.parameters, "clientCode")
    assert seen, "the parameter is still there"
    assert "A-THIRD-ONE" in seen, "and the third doing widened it"
    assert "SOMETHING-ELSE" in seen, "without losing the second"
    assert len(stored.parameters) == 1, "one control, not one parameter per doing"


async def test_a_control_the_model_already_named_does_not_gain_a_second_parameter() -> None:
    """The model names a control by the label the operator reads; `_by_control`
    names the same control by its `item_id`. Neither is wrong and they never
    match as strings.

    So a job the model declared parameters for grew a SECOND parameter per
    control on its second doing. The real acme store carried `Create a Work
    Operation` with `Operation` beside `operationCode`, `Description` beside
    `longDescription` and `Base Priority` beside `basePriority` -- six inputs a
    runner would demand for three fields, half of them under a machine name no
    operator has seen.

    The values are the evidence and the two names are two opinions about it, so
    a learned parameter whose every observed value is already recorded against
    a stored one was read off the same typing. The operator-facing label is the
    one that survives, because it is the one a person is asked to fill in.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]
    labelled = _proposal(
        ids,
        parameters=[{"name": "Client Code", "seen_values": ["ACME-4471", "SOMETHING-ELSE"]}],
    )

    assert (await _mine(uow, FakeAsker(_found(labelled)))).kept == 1

    again = _redone(original, "SOMETHING-ELSE", "again", 10_000.0)
    await uow.gestures.add_gestures(tuple(again))
    second = await _mine(uow, FakeAsker(_found(_proposal([g.id for g in again]))))

    stored = (await uow.workflows.known(TENANT))[0]
    names = [parameter.get("name") for parameter in stored.parameters]
    assert names == ["Client Code"], f"one control, one parameter; got {names}"
    assert "clientCode" not in names, "not the same field again under its item_id"
    assert second.learned_parameters == 0, "recognising a control is not learning a new one"


async def test_a_job_already_holding_two_entries_for_one_field_is_folded() -> None:
    """The repair, for the jobs this defect has already been written into.

    The deployment's `Create a Customer Type` carried four parameters for two
    fields -- `Customer Type` beside `customertype-customerType`, and the same
    again for the description -- because the page names a field twice and its
    two recordings carried different names. The fix above stops a second entry
    being written; this is what clears the ones already stored, on the next
    pass that touches the job.

    Both entries' values survive the fold. `seen_values` promises every value
    observed and the two halves observed different doings, so throwing one
    away would narrow a parameter to make a list tidy.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]
    await _mine(uow, FakeAsker(_found(_proposal(ids))))

    # The job as the defect left it: one control, two entries, one of them
    # under the name the form posts it by.
    stored = (await uow.workflows.known(TENANT))[0]
    stored.parameters = [
        {"name": "Client Code", "seen_values": ["ACME-4471"]},
        {"name": "clientCode", "seen_values": ["FROM-THE-OTHER-ENTRY"]},
    ]
    await uow.workflows.save(stored)

    again = _redone(original, "SOMETHING-ELSE", "again", 10_000.0)
    await uow.gestures.add_gestures(tuple(again))
    await _mine(uow, FakeAsker(_found(_proposal([g.id for g in again]))))

    stored = (await uow.workflows.known(TENANT))[0]
    names = [parameter.get("name") for parameter in stored.parameters]
    assert names == ["Client Code"], f"one control, one parameter; got {names}"
    seen = _seen(stored.parameters, "clientCode")
    assert "FROM-THE-OTHER-ENTRY" in seen, "the folded entry's values were thrown away"
    assert "SOMETHING-ELSE" in seen, "and this doing still widened it"


async def test_a_pass_that_learns_nothing_still_folds_what_is_already_wrong() -> None:
    """The repair must not depend on the job being done differently again.

    A job whose values have settled -- the same customer type every time --
    learns nothing on any further pass, and under a fold that ran only on the
    learning path it would carry its duplicate parameters forever. The
    operator's four boxes are not waiting for a new value.

    It reports nothing learnt, because nothing was: noticing that two of a
    job's parameters were always one is not a value it did not have before.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]
    await _mine(uow, FakeAsker(_found(_proposal(ids))))

    settled = _redone(original, "SOMETHING-ELSE", "again", 10_000.0)
    await uow.gestures.add_gestures(tuple(settled))
    await _mine(uow, FakeAsker(_found(_proposal([g.id for g in settled]))))

    # The job as the defect left it, and a doing that teaches nothing new.
    stored = (await uow.workflows.known(TENANT))[0]
    stored.parameters = [
        {"name": "Client Code", "seen_values": ["ACME-4471", "SOMETHING-ELSE"]},
        {"name": "clientCode", "seen_values": ["ACME-4471", "SOMETHING-ELSE"]},
    ]
    await uow.workflows.save(stored)

    same = _redone(original, "SOMETHING-ELSE", "thrice", 20_000.0)
    await uow.gestures.add_gestures(tuple(same))
    pass_ = await _mine(uow, FakeAsker(_found(_proposal([g.id for g in same]))))

    assert pass_.learned_parameters == 0, "a fold is not something learnt"
    stored = (await uow.workflows.known(TENANT))[0]
    names = [parameter.get("name") for parameter in stored.parameters]
    assert names == ["Client Code"], f"one control, one parameter; got {names}"


def _redone_both(rows: list[Gesture], value: str, suffix: str, offset: float) -> list[Gesture]:
    """The same job done again with BOTH filled-in controls changed.

    `_redone` touches only the typed one, which is why every test above it
    learns exactly one parameter. The upload beside it is a second control the
    operator filled in, and holding it constant is what makes it part of the
    job rather than an input to it.
    """
    fresh = []
    for row in rows:
        action = row.action
        if action.kind in ("type", "upload") and action.value:
            action = replace(action, value=f"{value}-{action.kind}")
        fresh.append(replace(row, id=f"{row.id}_{suffix}", at=row.at + offset, action=action))
    return fresh


async def test_a_pass_that_widens_two_parameters_says_two_and_not_one() -> None:
    """The sentence `MinePassResponse.learned_parameters` ships with, as a test:
    "a pass that recognises nothing new and widens TWO parameters did real
    work".

    One widening and two are the same reading if the counter is a flag. It was
    a `bool` -- so a pass that widened everything it knew reported nothing --
    and a counter that saturates at one is the same defect one value further
    along. Nothing else here can see the difference: every other doing in this
    file varies a single control.
    """
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]

    await _mine(uow, FakeAsker(_found(_proposal(ids))))

    passes = []
    for value, suffix, offset in (
        ("SECOND", "again", 10_000.0),
        ("THIRD", "thrice", 20_000.0),
    ):
        rows = _redone_both(original, value, suffix, offset)
        await uow.gestures.add_gestures(tuple(rows))
        passes.append(await _mine(uow, FakeAsker(_found(_proposal([g.id for g in rows])))))

    stored = (await uow.workflows.known(TENANT))[0]
    assert len(stored.parameters) == 2, "two controls varied, so two parameters"
    assert passes[0].learned_parameters == 2, "the second doing named both"
    assert passes[1].kept == 0, "the third doing is the same job again"
    assert passes[1].learned_parameters == 2, "and widening both is learning two"


# --------------------------------------------------------------------------
# the prompt this pass sends


async def _link(uow: FakeUnitOfWork, gesture_ids: list[str], value: str, system: str) -> None:
    """One value carried by two gestures on two systems -- a crossing.

    The second of the pair is moved to `system` because `shared_values` needs
    two systems to call anything a crossing, and `_crowd` clones every gesture
    off one template.
    """
    _rows(uow)[gesture_ids[1]].system = system
    for gesture_id in gesture_ids:
        await uow.gestures.save_intent(
            Intent(
                gesture_id=gesture_id,
                tenant=TENANT.value,
                act="typed it",
                values_seen=[ValueSeen(field="supplier", value=value)],
            )
        )


async def test_the_prompt_never_names_a_crossing_the_window_left_out() -> None:
    """Crossings are computed over the whole tenant; `validate` refuses any
    workflow citing an id outside the window. Named anyway, a crossing whose
    partner the budget dropped is an instruction to produce a workflow that is
    then discarded in full -- and it is the cross-system class this rig exists
    to find. Proved at a 25-item window over 60 real pairs: 95 ids named, none
    citable."""
    uow, strong_ids, weak_ids = await _crowded_day(strong=25, weak=5)
    # Both ends inside: the block must still render, or this test would pass on
    # a prompt with no crossings section at all.
    await _link(uow, strong_ids[:2], "WHOLLY-IN-WINDOW", "https://sap.example")
    # One end outside: the weak partner is 26th by strength even with the
    # `linked` bonus, and the window holds 25.
    await _link(uow, [strong_ids[2], weak_ids[-1]], "STRADDLES-THE-EDGE", "https://sap.example")
    asker = FakeAsker(_found())

    result = await _mine(uow, asker, kb=CROWDED_KB)
    prompt = str(asker.asked[0]["evidence"])
    # json.dumps(indent=1) never writes a blank line, so the blank line after
    # the block is where it ends. Both values also appear in the evidence of
    # the gestures carrying them, which is what makes the block the only place
    # this can be read.
    block = prompt.split("## Values appearing in more than one system\n")[1].split("\n\n")[0]

    assert result.window_size == 25
    assert result.left_out == 5, "the window must be smaller than the evidence"
    assert "WHOLLY-IN-WINDOW" in block, "a crossing both of whose ends are citable is a hint"
    assert weak_ids[-1] not in prompt, "the prompt named evidence the model may not cite"
    assert "STRADDLES-THE-EDGE" not in block, "one id left is not a crossing"


# --------------------------------------------------------------------------
# propose -- the umbrella tests that need a model call or a store


def _window() -> Window:
    items = [
        Packed("ges_1", 1.0, {"id": "ges_1", "gesture": {"kind": "type"}}, 2.0, 10),
        Packed("ges_2", 2.0, {"id": "ges_2", "gesture": {"kind": "click"}}, 1.0, 10),
    ]
    return Window(items=items, spent=20, left_out=[])


def _answer(**over: object) -> Answer:
    base: dict[str, object] = {
        "workflows": [
            {
                "title": "create a supplier",
                "narrative": "the operator created a supplier",
                "systems": ["https://wms.example"],
                "steps": [
                    {
                        "order": 0,
                        "cites": ["ges_1"],
                        "says": "type the code",
                        "system": "https://wms.example",
                        "parameters": ["code"],
                    }
                ],
                "parameters": [{"name": "code", "seen_values": ["ACME"]}],
                "same_as": None,
            }
        ]
    }
    return Answer(data={**base, **over}, in_tokens=1000, out_tokens=200, cost_usd=0.004)


async def _proposed(asker: FakeAsker) -> tuple[list[object], Answer]:
    workflows, answer = await propose(
        _window(), {}, [], "", asker=asker, model=MODEL, tenant=TENANT.value
    )
    return list(workflows), answer


async def test_a_proposal_becomes_a_workflow() -> None:
    workflows, answer = await propose(
        _window(), {}, [], "", asker=FakeAsker(_answer()), model=MODEL, tenant=TENANT.value
    )

    assert len(workflows) == 1
    assert workflows[0].title == "create a supplier"
    assert workflows[0].steps[0].cites == ["ges_1"]
    assert answer.cost_usd == 0.004


async def test_a_refusal_proposes_nothing_and_says_why() -> None:
    workflows, answer = await _proposed(FakeAsker(Answer(error="503")))

    assert workflows == []
    assert answer.error == "503"


async def test_a_malformed_answer_does_not_take_the_pass_down() -> None:
    """The schema is advisory. A model returning workflows as a string, or a
    step as a number, must cost the pass -- not the process. This one is
    `propose`'s own guard rather than `workflow_from`'s: nothing below it ever
    sees a `workflows` that is not a list."""
    for junk in ("not a list", {"a": "dict"}, 7, None):
        workflows, _ = await _proposed(FakeAsker(_answer(workflows=junk)))

        assert workflows == []


async def test_one_sample_by_default() -> None:
    asker = FakeAsker(_answer())

    await _proposed(asker)

    assert len(asker.asked) == 1
    assert K_SAMPLES == 1


async def test_the_task_is_not_repeated_outside_the_prompt() -> None:
    """`build_prompt` states the task at both ends, which is the measured
    decision. Sending it as the instruction too put it in three times, twice
    adjacently, on the most expensive call in the system."""
    asker = FakeAsker(_answer())

    await _proposed(asker)

    assert asker.asked[0]["instructions"] == ""
    assert str(asker.asked[0]["evidence"]).count(INSTRUCTIONS.strip()) == 2


async def test_the_pass_asks_for_the_effort_it_names() -> None:
    """K_SAMPLES is 1 because self-consistency bought 0.4% for 20x the cost.
    Effort is the knob that replaced it, so it has to reach the API."""
    asker = FakeAsker(_answer())

    await _proposed(asker)

    assert asker.asked[0]["effort"] == K_EFFORT
    # And the value, not only the constant. Comparing a call against the
    # constant it was made from passes whatever the constant says, so it cannot
    # fail when the value changes -- and this value cost $2.00 to establish: at
    # "high" the first real pass over 507 real gestures truncated after 2,610
    # tokens of answer and kept nothing, where "medium" kept 2 of 3.
    assert asker.asked[0]["effort"] == "medium"


async def test_two_steps_claiming_the_same_order_can_still_be_stored() -> None:
    """The workflow-step table declares PRIMARY KEY (workflow_id, ord).
    "order": 1 twice is schema-valid, so a model that repeats itself produced a
    workflow that raised on the way into the store."""
    answer = _answer(
        workflows=[
            {
                "title": "t",
                "narrative": "n",
                "steps": [
                    {"order": 1, "cites": ["ges_1"], "says": "first"},
                    {"order": 1, "cites": ["ges_2"], "says": "second"},
                ],
            }
        ]
    )
    workflows, _ = await propose(
        _window(), {}, [], "", asker=FakeAsker(answer), model=MODEL, tenant=TENANT.value
    )
    uow = FakeUnitOfWork()

    await uow.workflows.save(workflows[0])
    back = await uow.workflows.known(TENANT)

    assert [step.order for step in workflows[0].steps] == [0, 1]
    assert len(back[0].steps) == 2


# --------------------------------------------------------------------------
# rekeying
#
# Moved here with `rekey_workflows` itself, names unchanged: it is the other
# question about a shape key, and unlike `shapes_for` it writes.


STALE = [["https://old", "text|a paragraph of page copy that no longer names anything", "click"]]
"""A shape key written under a rule that has since changed."""


def _evidence() -> dict[str, Gesture]:
    return {g.id: deepcopy(g) for g in _gestures(TENANT.value)}


def _typed(by_id: dict[str, Gesture]) -> Gesture:
    return next(
        g for g in by_id.values() if g.action.kind == "type" and g.action.value == "ACME-4471"
    )


def _saver(by_id: dict[str, Gesture]) -> Gesture:
    """The click on Save, by its control and not by position."""
    return next(
        g
        for g in by_id.values()
        if g.action.target
        and g.action.target.component
        and g.action.target.component.item_id == "saveButton"
    )


def _keyed(by_id: dict[str, Gesture], wid: str = "wfl_1") -> Workflow:
    """A two-step job whose steps are LISTED in reverse of the order they run in.

    Deliberate, and the only fixture in either suite that is. `ordered_cites`
    sorts the steps before it walks them, and every fixture that builds them
    ascending already leaves that sort unguarded -- the walk agrees with the
    list by construction, so removing the sort changes nothing and no test
    notices. The key it mints is what `identity.resolve` compares a proposal
    against, so a key in the wrong order silently resolves jobs onto each
    other.

    A set is not enough either: `list(cited_ids(workflow))` happens to come out
    in step order under most hash seeds, so a mutation that swaps the ordered
    walk for a set survives on some seeds and dies on others. Two steps listed
    backwards is the plant that does not depend on the seed.
    """
    return Workflow(
        id=wid,
        tenant=TENANT.value,
        title="create a client",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(order=1, says="save", system=None, cites=[_saver(by_id).id]),
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[_typed(by_id).id],
                parameters=["clientCode"],
            ),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
    )


async def _plant(uow: FakeUnitOfWork, by_id: dict[str, Gesture], *workflows: Workflow) -> None:
    await uow.gestures.add_gestures(tuple(by_id.values()))
    for workflow in workflows:
        await uow.workflows.save(workflow)


async def test_a_stored_key_from_an_older_rule_is_recomputed_once() -> None:
    uow = FakeUnitOfWork()
    by_id = _evidence()
    workflow = _keyed(by_id)
    workflow.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, workflow)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 1
    key = (await uow.workflows.get(TENANT, "wfl_1")).shape_key
    # One triple per cited gesture, in step order: the typed code, then the
    # save -- the key the cited gestures make now, not the one written before.
    assert key != STALE and len(key) == 2 and [t[2] for t in key] == ["type", "click"]
    assert await rekey_workflows(uow, tenant_id=TENANT) == 0, "a key that agrees is left alone"


async def test_a_gesture_two_steps_both_stand_on_is_two_rungs_of_the_key() -> None:
    """The key is a SEQUENCE, and `cited_ids` is a set.

    A gesture two steps both stand on -- the same Save proving the write and
    proving the confirmation -- is two rungs of the job's shape, and a set
    collapses it to one. A key one rung short of the job is contained by jobs
    it is not, which is `identity.resolve` merging two jobs into one.

    Deterministic, where an order plant is not: a set of ids comes out in step
    order on some `PYTHONHASHSEED` values and not others, so a mutation that
    swaps the ordered walk for `list(cited_ids(...))` was measured surviving
    2 of 5 seeds against the ordering assertions alone. It survives none of
    them against a lost duplicate.
    """
    uow = FakeUnitOfWork()
    by_id = _evidence()
    workflow = _keyed(by_id)
    workflow.steps.append(Step(order=2, says="save again", system=None, cites=[_saver(by_id).id]))
    workflow.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, workflow)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 1
    key = (await uow.workflows.get(TENANT, "wfl_1")).shape_key
    assert [triple[2] for triple in key] == ["type", "click", "click"]


async def test_a_workflow_whose_evidence_is_partly_gone_keeps_its_key() -> None:
    uow = FakeUnitOfWork()
    by_id = _evidence()
    workflow = _keyed(by_id)
    workflow.steps[0].cites.append("ges_gone_with_its_batch")
    workflow.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, workflow)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 0
    assert (await uow.workflows.get(TENANT, "wfl_1")).shape_key == STALE, (
        "not rekeyed over the survivors"
    )


async def test_a_workflow_that_cites_nothing_keeps_the_key_it_has() -> None:
    """`if not wanted: continue`, which nothing was watching.

    A workflow with no citations has no evidence to make a key out of, and the
    key `shape_key([])` returns is empty. Written over a stored one, that is a
    row whose shape matches nothing -- and `containment` returns 0.0 for an
    empty set, so `identity.resolve` can never recognise the job again and the
    next pass proposes it as new. Which is the duplicate this pass exists to
    prevent.
    """
    uow = FakeUnitOfWork()
    by_id = _evidence()
    uncited = Workflow(id="wfl_1", tenant=TENANT.value, title="cites nothing", narrative="n")
    uncited.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, uncited)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 0
    assert (await uow.workflows.get(TENANT, "wfl_1")).shape_key == STALE
    assert uow.commits == 0


async def test_a_workflow_that_cannot_be_rekeyed_does_not_stop_the_others() -> None:
    uow = FakeUnitOfWork()
    by_id = _evidence()
    broken = _keyed(by_id, "wfl_1")
    broken.steps[0].cites.append("ges_gone_with_its_batch")
    broken.shape_key = [["https://old", "text|gone", "click"]]
    empty = Workflow(id="wfl_3", tenant=TENANT.value, title="cites nothing", narrative="n")
    stale = _keyed(by_id, "wfl_2")
    stale.shape_key = [["https://old", "text|stale", "click"]]
    # Visited in the order saved -- which the ids disagree with, so a pass
    # that walked them by id would meet the stale one first and never prove
    # that a skip is per workflow rather than the end of the pass.
    await _plant(uow, by_id, broken, empty, stale)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 1
    key = (await uow.workflows.get(TENANT, "wfl_2")).shape_key
    assert [t[2] for t in key] == ["type", "click"]


async def test_rekeying_leaves_another_tenant_s_stale_keys_where_they_are() -> None:
    uow = FakeUnitOfWork()
    by_id = _evidence()
    theirs = _keyed(by_id, "wfl_theirs")
    theirs.tenant = "other-corp"
    theirs.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, theirs)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 0
    assert (await uow.workflows.get(TenantId("other-corp"), "wfl_theirs")).shape_key == STALE


async def test_a_pass_that_changed_nothing_commits_nothing() -> None:
    """The rekey is a write and commits; a startup pass over a store that is
    already current should not be one."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    workflow = _keyed(by_id)
    workflow.shape_key = [list(triple) for triple in STALE]
    await _plant(uow, by_id, workflow)

    assert await rekey_workflows(uow, tenant_id=TENANT) == 1
    assert uow.commits == 1
    assert await rekey_workflows(uow, tenant_id=TENANT) == 0
    assert uow.commits == 1


async def test_a_job_already_stored_gets_the_credential_step_too() -> None:
    """The half that only showed up against the real store.

    The rule that adds a password step reached PROPOSALS the moment it was
    written -- and a job the rig already holds is re-proposed as `same_job` and
    dropped, so its stored steps, the ones a run actually performs, never
    changed. An operator whose sign-in job was mined last week would have
    waited forever for a step that is only ever added to something thrown away.
    """
    uow, ids = await _day()
    secret = next(g for g in await uow.gestures.gestures_for(TENANT) if is_secret(g))
    stored = Workflow(
        id="wfl_stored",
        tenant=TENANT.value,
        title="Sign in",
        narrative="the operator signed in",
        systems=[HOST],
        steps=[
            Step(order=0, says="type the code", system=HOST, cites=[ids[0]]),
            Step(order=1, says="save", system=HOST, cites=[ids[-1]]),
        ],
        parameters=[],
    )
    await uow.workflows.save(stored)

    filled = await fill_in_passwords(uow, tenant_id=TENANT)

    assert filled == 1
    back = await uow.workflows.get(TENANT, "wfl_stored")
    assert [step.cites for step in back.steps].count([secret.id]) == 1


async def test_filling_the_same_job_twice_changes_nothing_the_second_time() -> None:
    # Run every pass, so it has to be free when there is nothing to do.
    uow, ids = await _day()
    await uow.workflows.save(
        Workflow(
            id="wfl_stored",
            tenant=TENANT.value,
            title="Sign in",
            narrative="n",
            systems=[HOST],
            steps=[
                Step(order=0, says="type the code", system=HOST, cites=[ids[0]]),
                Step(order=1, says="save", system=HOST, cites=[ids[-1]]),
            ],
            parameters=[],
        )
    )

    assert await fill_in_passwords(uow, tenant_id=TENANT) == 1
    assert await fill_in_passwords(uow, tenant_id=TENANT) == 0
