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
from typing import Any

import pytest

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.application.skill.serve_shapes import shapes_for
from sro.domain.execution.compose import Composed, with_field
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.driving import WAS_OUR_OWN_DRIVING
from sro.domain.observation.gesture import Gesture, Intent, PageMark
from sro.domain.prompts.mine import MINE
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer, ModelSpend
from sro.domain.skill.workflow import field_key
from sro.infrastructure.db.codec import when
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeAsker,
    FakeClock,
    FakeGestureRepository,
    FakeUnitOfWork,
)

TENANT = TenantId("acme")
RIVAL = TenantId("rival")
HOST = "http://127.0.0.1:63319"
APP = "https://app.example"

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
        locks=FakeAccountLocks(),
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
    }
    return {**base, **over}


async def _did_it_again(uow: FakeUnitOfWork, ids: list[str]) -> list[str]:
    """The same controls touched again, on evidence of their own.

    Cited ids are per-occurrence: two independent doings of one job cite
    disjoint sets, and that is what lets the resolver tell "the same job again"
    from "this window read twice". A copy with a new id and a later clock is
    the smallest honest version of that.
    """
    rows = _rows(uow)
    made = []
    for nth, one in enumerate(ids):
        copy = replace(rows[one], id=f"{one}_again", at=rows[one].at + 3600 + nth)
        await uow.gestures.add_gestures((copy,))
        made.append(copy.id)
    return made


async def _billed(uow: FakeUnitOfWork, *, cost_usd: float, at: datetime) -> None:
    """A day with a model call on it, as the metered client bills one."""
    await uow.spend.record(
        ModelSpend(id=f"cht_{cost_usd}", tenant=TENANT.value, model="m", at=at, cost_usd=cost_usd)
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


async def test_a_replay_of_our_own_is_not_evidence_this_pass_can_mine() -> None:
    """The other half of the second check.

    The reading loop MARKS a gesture this browser made while driving a run of
    its own -- it does not hide it, because `unread` means "has no intent row"
    and a gesture merely skipped would come back forever. So mining is where
    the mark has to be acted on, and a gesture the model was never asked about
    still packs, still scores and can still end up in a candidate.

    What it costs to be missing is not a stray row: it is a task mined from a
    robot imitating a person, and offered back as worth automating.
    """
    uow, ids = await _day()
    for gesture_id in ids:
        await uow.gestures.save_intent(
            Intent(gesture_id=gesture_id, tenant=TENANT.value, why=WAS_OUR_OWN_DRIVING)
        )
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))

    result = await _pass(uow, asker=asker).execute(_ctx())

    assert result.kept == 0, "a job was mined from this system driving itself"
    # The pass itself still runs and still asks: a window with nothing in it is
    # not this rule's business, and a tenant whose whole day was replays is the
    # same case as one who did nothing at all. What it must not do is propose a
    # job from that evidence, which is what `kept` says.
    assert [one.id for one in await uow.workflows.known(TENANT)] == []


async def test_a_job_stored_under_an_older_shape_rule_is_not_mined_again() -> None:
    """A stored shape is a cache of a rule, and the rule can change.

    `shape_key` gained the screen on 2026-09-21. Every job mined before that
    carries a shape computed without one, and compared as they stood a
    proposal's screen-aware shape would match none of them: every known job
    would come back `new` and one pass would save a second copy of all 22.

    So the known set is re-shaped from its own cited evidence before anything
    is compared, by the same function the proposal uses. Here the stored job
    carries deliberate nonsense -- a shape from no rule this system has ever
    had -- and is still recognised, which is only possible if it was re-shaped.
    """
    uow, ids = await _day()
    asker = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))
    kept = (await _pass(uow, asker=asker).execute(_ctx())).kept
    assert kept == 1, "the fixture did not mine a job to store"
    [stored] = await uow.workflows.known(TENANT)
    stored.shape_key = [["a shape", "from a rule", "nobody has"]]
    await uow.workflows.save(stored)

    # A SECOND doing of the same job: the same screens and the same controls,
    # on evidence of its own. Cited ids are per-occurrence, so this cannot be
    # waved away as "read before" -- the only thing that can recognise it is
    # the shape, which is the thing under test.
    first = {one.id: one for one in await uow.gestures.gestures_for(TENANT)}
    again_ids = []
    for nth, was in enumerate(first[one] for one in ids[:2]):
        copy = replace(was, id=f"{was.id}_again", at=was.at + 600 + nth)
        await uow.gestures.add_gestures((copy,))
        again_ids.append(copy.id)

    again = await _pass(
        uow,
        asker=FakeAsker(Answer(data={"workflows": [_proposal(again_ids)]}, cost_usd=0.01)),
    ).execute(_ctx())

    assert again.kept == 0, "one job was stored twice under two shape rules"
    assert len(await uow.workflows.known(TENANT)) == 1


async def test_a_doing_that_contains_the_job_grows_it() -> None:
    """The half that could not be finished without this.

    Measured on the deployment 2026-09-21: an operator did `Create a Customer
    Type` twice, filling `Department` and `Manufacturer` both times with
    different values -- two doings varying a control, which is this system's
    whole bar for a parameter. The job learnt neither, and could not ever:
    `learn_parameters` compares the stored job against the proposal, and the
    stored job was a doing that had never reached those controls. Stored steps
    never grew.

    `Resolution.contains` has been computed since identity was written and
    read by nothing, and its own note names this caller: *"Mine contains
    theirs" is the case for replacing*.
    """
    uow, ids = await _day()
    first = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))
    assert (await _pass(uow, asker=first).execute(_ctx())).kept == 1
    [stored] = await uow.workflows.known(TENANT)
    assert len(stored.steps) == 2

    # A SECOND doing: its own evidence, doing everything the first did and one
    # thing more. Its own, because cited ids are per-occurrence -- a proposal
    # citing the first doing's gestures is the same evidence read twice, which
    # the resolver settles before it ever asks whether one contains the other.
    again = await _did_it_again(uow, ids[:3])
    wider = _proposal(again[:2])
    wider["steps"] = [
        *wider["steps"],  # type: ignore[misc]
        {
            "order": 2,
            "cites": [again[2]],
            "says": "and the extra field",
            "system": HOST,
            "parameters": [],
        },
    ]
    await _pass(uow, asker=FakeAsker(Answer(data={"workflows": [wider]}, cost_usd=0.01))).execute(
        _ctx()
    )

    [grown] = await uow.workflows.known(TENANT)
    assert grown.id == stored.id, "it stored a second copy instead of growing the first"
    assert len(grown.steps) == 3, "the job did not take the step it had just watched"


async def test_a_doing_that_grows_the_job_keeps_the_field_a_run_learned_into_it() -> None:
    """A learned field step cites nothing a doing shows, so a re-derived shape
    never has it. Dropped, its parameter would stay declared with its key and
    nothing would fill it: every later run would leave the field out and hold."""
    uow, ids = await _day()
    first = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))
    await _pass(uow, asker=first).execute(_ctx())
    [stored] = await uow.workflows.known(TENANT)
    write = sorted(stored.steps, key=lambda one: one.order)[1]
    learned, moved = with_field(
        stored,
        Composed("department", "Department", "combobox", write.order),
        key="department",
        value="Finance",
    )
    await uow.workflows.grew(learned, moved=moved)
    await uow.workflows.remember_locator(
        stored.id, LearnedStep(write.order, "role_and_name", "combobox|Department", "composed")
    )

    again = await _did_it_again(uow, ids[:3])
    wider = _proposal(again[:2])
    wider["steps"] = [
        *wider["steps"],  # type: ignore[misc]
        {
            "order": 2,
            "cites": [again[2]],
            "says": "and the extra field",
            "system": HOST,
            "parameters": [],
        },
    ]
    await _pass(uow, asker=FakeAsker(Answer(data={"workflows": [wider]}, cost_usd=0.01))).execute(
        _ctx()
    )

    [grown] = await uow.workflows.known(TENANT)
    says = [one.says for one in sorted(grown.steps, key=lambda one: one.order)]
    assert len(says) == 4 and says[1] == "Fill Department" and says[3] == "and the extra field"
    fill = sorted(grown.steps, key=lambda one: one.order)[1]
    assert field_key(grown, fill) == "department"
    assert [(one.ord, one.query) for one in await uow.workflows.learned_for(grown.id)] == [
        (1, "combobox|Department")
    ]


async def test_a_doing_that_adds_a_password_does_not_grow_the_job() -> None:
    """Growth takes the doing's steps wholesale, and a step typing a secret
    the stored job never had would turn a job into a job that signs in first
    -- every run of it then asking for a credential it never needed. Such a
    doing still teaches the job its parameters; it does not become it."""
    uow, ids = await _day()
    first = FakeAsker(Answer(data={"workflows": [_proposal(ids[:2])]}, cost_usd=0.01))
    assert (await _pass(uow, asker=first).execute(_ctx())).kept == 1
    [stored] = await uow.workflows.known(TENANT)

    again = await _did_it_again(uow, ids[:3])
    rows = _rows(uow)
    rows[again[2]] = replace(
        rows[again[2]], action=replace(rows[again[2]].action, kind="type", secret=True)
    )
    wider = _proposal(again[:2])
    wider["steps"] = [
        *wider["steps"],  # type: ignore[misc]
        {"order": 2, "cites": [again[2]], "says": "type the password", "system": HOST},
    ]
    result = await _pass(
        uow, asker=FakeAsker(Answer(data={"workflows": [wider]}, cost_usd=0.01))
    ).execute(_ctx())

    assert [one.kind for one in result.resolutions] == ["same_job"]
    [held] = await uow.workflows.known(TENANT)
    assert held.id == stored.id
    assert len(held.steps) == 2, "the job grew a credential step it never had"


def _sign_in_kit() -> tuple[Any, Any, Any, Any]:
    base = replace(_gestures(TENANT.value)[0], requests=[], page_events=[])

    def typed(gesture_id: str, at: float, *, secret: bool = False) -> Gesture:
        return replace(
            base,
            id=gesture_id,
            at=at,
            action=replace(
                base.action,
                kind="type",
                at=at,
                secret=secret,
                target=None if secret else base.action.target,
            ),
        )

    def clicked(gesture_id: str, at: float) -> Gesture:
        return replace(base, id=gesture_id, at=at, action=replace(base.action, kind="click", at=at))

    def left_for(gesture_id: str, at: float, app: str) -> Gesture:
        """The submit, uncited: the model summarises a sign-in as the typing,
        and the leave is read off the doing after it."""
        return replace(
            clicked(gesture_id, at),
            page_events=[PageMark(at=at, page_kind="navigated", url=f"{app}/home")],
        )

    def login(title: str, *cites: str) -> dict[str, object]:
        return {
            "title": title,
            "narrative": "signed in",
            "systems": [HOST],
            "steps": [
                {"order": n, "cites": [one], "says": f"step {n}", "system": HOST}
                for n, one in enumerate(cites)
            ],
        }

    return typed, clicked, left_for, login


async def test_a_second_way_of_signing_in_to_one_system_is_the_same_job() -> None:
    """Two doings that both sign in to one application through one identity
    provider, one through a chooser and one straight to the password box,
    share almost no shape and were given different names. They are one job:
    the deployment held three `Log in using Azure B2C SSO` for want of this."""
    uow = FakeUnitOfWork()
    typed, clicked, left_for, login = _sign_in_kit()
    await uow.gestures.add_gestures(
        (typed("user", 10.0), typed("pw", 11.0, secret=True), left_for("go", 12.0, APP))
    )
    first = FakeAsker(Answer(data={"workflows": [login("Log in", "user", "pw")]}, cost_usd=0.01))
    assert (await _pass(uow, asker=first).execute(_ctx())).kept == 1
    [stored] = await uow.workflows.known(TENANT)
    assert stored.signs_in

    await uow.gestures.add_gestures(
        (
            clicked("choose", 5000.0),
            typed("pw2", 5001.0, secret=True),
            left_for("go2", 5002.0, APP),
        )
    )
    other = login("Sign in through the chooser", "choose", "pw2")
    result = await _pass(
        uow, asker=FakeAsker(Answer(data={"workflows": [other]}, cost_usd=0.01))
    ).execute(_ctx())

    assert [(one.kind, one.workflow_id) for one in result.resolutions] == [("same_job", stored.id)]
    assert len(await uow.workflows.known(TENANT)) == 1


async def test_two_applications_behind_one_identity_provider_are_two_sign_ins() -> None:
    """One identity provider in front of two applications is two sign-ins:
    folding them would leave the second application with no way back in."""
    uow = FakeUnitOfWork()
    typed, clicked, left_for, login = _sign_in_kit()
    await uow.gestures.add_gestures(
        (typed("user", 10.0), typed("pw", 11.0, secret=True), left_for("go", 12.0, APP))
    )
    first = FakeAsker(Answer(data={"workflows": [login("Log in", "user", "pw")]}, cost_usd=0.01))
    assert (await _pass(uow, asker=first).execute(_ctx())).kept == 1

    await uow.gestures.add_gestures(
        (
            clicked("choose", 5000.0),
            typed("pw2", 5001.0, secret=True),
            left_for("go2", 5002.0, "https://other-app.example"),
        )
    )
    other = login("Sign in to the other app", "choose", "pw2")
    result = await _pass(
        uow, asker=FakeAsker(Answer(data={"workflows": [other]}, cost_usd=0.01))
    ).execute(_ctx())

    assert [one.kind for one in result.resolutions] == ["new"]
    assert len(await uow.workflows.known(TENANT)) == 2


async def test_a_doing_that_types_a_second_credential_does_not_grow_the_job() -> None:
    """Per credential, not per job: a job that already types one password
    must not take a doing's steps that type a different one as well."""
    uow = FakeUnitOfWork()
    typed, clicked, _, _ = _sign_in_kit()
    mfa = "https://second-factor.example"
    await uow.gestures.add_gestures(
        (typed("pw", 10.0, secret=True), clicked("save", 11.0), clicked("done", 12.0))
    )
    job = _proposal(["pw", "save"])
    job["steps"] = [
        {"order": 0, "cites": ["pw"], "says": "password", "system": HOST},
        {"order": 1, "cites": ["save"], "says": "save", "system": HOST},
        {"order": 2, "cites": ["done"], "says": "done", "system": HOST},
    ]
    assert (
        await _pass(uow, asker=FakeAsker(Answer(data={"workflows": [job]}, cost_usd=0.01))).execute(
            _ctx()
        )
    ).kept == 1
    [stored] = await uow.workflows.known(TENANT)

    second = replace(
        typed("pw-b", 5001.5, secret=True), page_url=f"{mfa}/", url=f"{mfa}/", system=mfa
    )
    await uow.gestures.add_gestures(
        (
            typed("pw2", 5000.0, secret=True),
            clicked("save2", 5001.0),
            second,
            clicked("done2", 5002.0),
        )
    )
    wider = {
        **job,
        "systems": [HOST, mfa],
        "steps": [
            {"order": 0, "cites": ["pw2"], "says": "password", "system": HOST},
            {"order": 1, "cites": ["save2"], "says": "save", "system": HOST},
            {"order": 2, "cites": ["pw-b"], "says": "second password", "system": mfa},
            {"order": 3, "cites": ["done2"], "says": "done", "system": HOST},
        ],
    }
    result = await _pass(
        uow, asker=FakeAsker(Answer(data={"workflows": [wider]}, cost_usd=0.01))
    ).execute(_ctx())

    assert [(one.kind, one.contains) for one in result.resolutions] == [("same_job", True)]
    [held] = await uow.workflows.known(TENANT)
    assert held.id == stored.id
    assert len(held.steps) == 3, "the job grew a second credential it never typed"


async def test_a_doing_the_job_contains_does_not_shrink_it() -> None:
    """Only ever the other way. A shorter doing is the operator taking a route
    that skipped something, and a job that dropped a step every time somebody
    took a shortcut would forget itself one doing at a time."""
    uow, ids = await _day()
    wide = _proposal(ids[:2])
    wide["steps"] = [
        *wide["steps"],  # type: ignore[misc]
        {
            "order": 2,
            "cites": [ids[2]],
            "says": "and the extra field",
            "system": HOST,
            "parameters": [],
        },
    ]
    narrower = await _did_it_again(uow, ids[:2])
    assert (
        await _pass(
            uow, asker=FakeAsker(Answer(data={"workflows": [wide]}, cost_usd=0.01))
        ).execute(_ctx())
    ).kept == 1

    await _pass(
        uow, asker=FakeAsker(Answer(data={"workflows": [_proposal(narrower)]}, cost_usd=0.01))
    ).execute(_ctx())

    [held] = await uow.workflows.known(TENANT)
    assert len(held.steps) == 3, "a shorter doing took a step away from the job"


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
    # And the day is now over the cap once the client's bill for it lands,
    # which is what makes the ordering visible: the next caller is the one
    # that gets refused.
    await _billed(uow, cost_usd=0.01, at=NOW.replace(hour=11))
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


async def test_the_model_asked_is_the_one_the_record_names() -> None:
    """A model change is a prompt change, so the pass asks the model its
    record names and nothing a deployment configures can move it."""
    uow, ids = await _day()
    asker = FakeAsker(_answer(ids[:2]))

    await _pass(uow, asker=asker).execute(_ctx())

    assert [one["model"] for one in asker.asked] == [MINE.model]


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
    await uow.spend.record(
        ModelSpend(
            id="cht_rival", tenant=RIVAL.value, model="m", at=NOW.replace(hour=10), cost_usd=5.01
        )
    )

    with pytest.raises(OverCap):
        await _pass(uow, asker=FakeAsker(Answer(data={"workflows": []}))).execute(_ctx(RIVAL))


# --- a pass reads only work nothing has placed ------------------------------


def _shown(asker: FakeAsker) -> str:
    [asked] = asker.asked
    return str(asked["evidence"])


async def test_what_a_stored_job_cites_is_not_read_again() -> None:
    """Every pass used to re-send the gestures stored jobs already cite, so
    the model re-read and re-proposed known jobs at the price of a call every
    time. What a job cites is placed; a pass is for what is not."""
    uow, ids = await _day()
    assert (await _pass(uow, asker=FakeAsker(_answer(ids[:2]))).execute(_ctx())).kept == 1

    second = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.01))
    result = await _pass(uow, asker=second).execute(_ctx())

    assert result.window_size == len(ids) - 2
    assert not any(f'"{one}"' in _shown(second) for one in ids[:2])
    assert all(f'"{one}"' in _shown(second) for one in ids[2:])


async def test_a_new_doing_of_a_stored_job_still_teaches_it_without_the_old_one() -> None:
    """The earlier doing is not in the window any more, and learning does not
    need it there: `learn_parameters` reads the stored job's own citations from
    the gesture store, not from what this pass was shown."""
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]
    assert (await _pass(uow, asker=FakeAsker(_answer(ids))).execute(_ctx())).kept == 1

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
    asker = FakeAsker(_answer([row.id for row in again_rows]))

    again = await _pass(uow, asker=asker).execute(_ctx())

    assert not any(f'"{one}"' in _shown(asker) for one in ids), "the first doing was sent again"
    assert (again.kept, again.window_size) == (0, len(again_rows))
    assert again.learned_parameters >= 1


async def test_a_doing_folded_into_a_job_is_not_read_again() -> None:
    """A second doing recognised as a stored job is not saved as a job of its
    own, so nothing in the job's steps cites it -- and the pass after that used
    to send all of it again, every pass, for good."""
    uow, ids = await _day()
    original = [_rows(uow)[gesture_id] for gesture_id in ids]
    assert (await _pass(uow, asker=FakeAsker(_answer(ids))).execute(_ctx())).kept == 1
    again = [replace(row, id=f"{row.id}_again", at=row.at + 10_000.0) for row in original]
    await uow.gestures.add_gestures(tuple(again))
    folded = await _pass(uow, asker=FakeAsker(_answer([row.id for row in again]))).execute(_ctx())
    assert [one.kind for one in folded.resolutions] == ["same_job"]

    third = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.01))
    result = await _pass(uow, asker=third).execute(_ctx())

    assert result.window_size == 0
    assert not any(f'"{row.id}"' in _shown(third) for row in again)


async def test_a_retired_job_is_not_mined_back_and_not_offered() -> None:
    """Retired is for good: the job leaves the menu and the shapes, and its
    gestures stay placed, so no pass can read them into a fresh copy."""
    uow, ids = await _day()
    assert (await _pass(uow, asker=FakeAsker(_answer(ids[:2]))).execute(_ctx())).kept == 1
    [job] = await uow.workflows.known(TENANT)
    await uow.workflows.retire(TENANT, job.id, at=NOW)

    asker = FakeAsker(_answer(ids[:2]))
    result = await _pass(uow, asker=asker).execute(_ctx())

    assert not any(f'"{one}"' in _shown(asker) for one in ids[:2])
    assert result.kept == 0
    assert [one.reason for one in result.rejections] == ["unknown gesture"]
    assert await uow.workflows.known(TENANT) == ()
    assert await shapes_for(uow, tenant_id=TENANT, now=NOW) == []
