"""`scripts/dry_run.py` against a real Postgres, and what it hands the matcher.

The replay file is the acceptance test for shapes and recognition from phase 4
on, and it is read by a node script in another package: nothing in the Python
suite fails when a key is renamed, so the contract itself is asserted here --
every key `new-chrome-extension/scripts/offer-replay.mjs` and
`src/background/recognise.js` read, and nothing extra pretending to be one.

Integration and not unit, for the reason `test_the_read_only_doors.py` exists:
`ServeShapes` and the evidence read both open a `SqlUnitOfWork`, which has no
repositories until `__aenter__`, and `FakeUnitOfWork` answers entered or not.
The script is the newest caller of both.

What is planted is one job that can be served and one that cannot, because the
two halves of the file are gathered by different reads: `shapes` is every
PROVEN workflow and `jobs` is every workflow at all, and a replay that quietly
dropped the unproven ones would report "8 of 8" over a corpus of nine.
"""

from __future__ import annotations

import json
from typing import Any

from scripts.dry_run import TYPED, _gestures_of, replay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.skill.serve_shapes import ServeShapes
from sro.domain.observation.gesture import Action, Gesture, GestureBatch, Target
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.fakes import FakeClock

TENANT = TenantId("acme")
CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("tests"))

SYSTEM = "https://wms.example"
TYPED_VALUE = "WA-4471"
"""The text the operator typed. It is a parameter's seen value, so the export
marks its presence -- and the text itself must not be anywhere in the file.

Deliberately not a word in the job's title. A mined title often quotes the
value it was mined from, and with the two the same the leak assertion below
passed on the title and would have gone on passing with the mark removed."""

# Every key `offer-replay.mjs` and `recognise.js` read off a served shape.
# `hosts` and `starts_on` are not read by either, and are in the file because
# the rig's `/v1/shapes` served the whole record; asserted so that dropping one
# is a decision rather than a diff nobody notices.
SHAPE_KEYS = {
    "id",
    "title",
    "starts_on",
    "hosts",
    "shape",
    "parameters",
    "held_runs",
    "offer_after",
    "quiet_until",
}
GESTURE_KEYS = {"triple", "value", "secret", "at"}


def _gesture(gesture_id: str, *, at: float, action: Action) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=TENANT.value,
        stream_id="dev_1",
        batch_id="bat_1",
        at=at,
        url=f"{SYSTEM}/work-areas",
        system=SYSTEM,
        tab_id=7,
        frame_url=f"{SYSTEM}/work-areas",
        page_url=f"{SYSTEM}/work-areas",
        action=action,
    )


def _click(gesture_id: str, name: str, *, at: float) -> Gesture:
    return _gesture(
        gesture_id,
        at=at,
        action=Action(kind="click", at=at, target=Target(tag="button", name=name)),
    )


def _corpus() -> tuple[list[Gesture], list[Workflow]]:
    """One proven job of four gestures -- a click, a scroll, a typed
    parameter, a click -- and one unproven job sharing its evidence.

    ``at`` runs BACKWARDS against the citation order, so the two orders are
    never accidentally the same and a test cannot pass by reading the wrong
    one. Both the served shape and the replayed job are built in ``at`` order,
    because that is the order a browser's tail arrives in; the citation order
    is the model's narration and no browser has ever heard of it.
    """
    gestures = [
        _click("ges_1", "Work Areas", at=400.0),
        _gesture("ges_2", at=300.0, action=Action(kind="scroll", at=300.0)),
        _gesture(
            "ges_3",
            at=200.0,
            action=Action(
                kind="type",
                at=200.0,
                value=TYPED_VALUE,
                target=Target(tag="input", name="Work Area"),
            ),
        ),
        _click("ges_4", "Save", at=100.0),
    ]
    proven = Workflow(
        id="wfl_proven",
        tenant=TENANT.value,
        title="Create Work Area NEWTESTS",
        narrative="the operator created a work area",
        systems=[SYSTEM],
        steps=[
            Step(order=0, says="open", system=SYSTEM, cites=["ges_1", "ges_2"], parameters=[]),
            Step(
                order=1,
                says="name it",
                system=SYSTEM,
                cites=["ges_3"],
                parameters=["workArea"],
            ),
            Step(order=2, says="save", system=SYSTEM, cites=["ges_4"], parameters=[]),
        ],
        parameters=[{"name": "workArea", "seen_values": [TYPED_VALUE]}],
    )
    unproven = Workflow(
        id="wfl_unproven",
        tenant=TENANT.value,
        title="Something the miner is unsure of",
        narrative="cites the same evidence and has not been proven",
        systems=[SYSTEM],
        steps=[Step(order=0, says="open", system=SYSTEM, cites=["ges_1"], parameters=[])],
        unproven=["ges_9"],
    )
    return gestures, [proven, unproven]


async def _planted(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, Any]:
    gestures, workflows = _corpus()
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.gestures.add_batch(
            GestureBatch(
                batch_id="bat_1",
                device_id="dev_1",
                tenant=TENANT.value,
                mode="passive",
                received_at="2026-09-05T10:00:00+00:00",
            )
        )
        await uow.gestures.add_gestures(tuple(gestures))
        for workflow in workflows:
            await uow.workflows.save(workflow)
        await uow.commit()

    written = await replay(
        ServeShapes(SqlUnitOfWork(session_factory), FakeClock()),
        SqlUnitOfWork(session_factory),
        CTX,
    )
    # Through the encoder the script itself uses: a float the driver handed back
    # as a Decimal, or an id that is not a str, is a file the node script cannot
    # read, and it would not fail on the dict.
    parsed: dict[str, Any] = json.loads(json.dumps(written, indent=1))
    return parsed


async def test_the_file_has_the_two_keys_the_replay_reads(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    written = await _planted(session_factory)

    assert set(written) == {"shapes", "jobs"}


async def test_a_served_shape_carries_every_key_the_matcher_reads(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    written = await _planted(session_factory)

    (shape,) = written["shapes"]
    assert set(shape) == SHAPE_KEYS
    assert shape["id"] == "wfl_proven"
    assert shape["title"] == "Create Work Area NEWTESTS"
    assert shape["offer_after"] == 2
    assert shape["quiet_until"] is None
    assert shape["parameters"] == [{"name": "workArea", "at": 1}]
    assert all(len(triple) == 3 for triple in shape["shape"])
    assert all(isinstance(part, str) for triple in shape["shape"] for part in triple)


async def test_every_workflow_is_a_job_even_the_one_no_shape_is_served_for(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """`shapes` is the proven half; `jobs` is all of it. The unproven job is
    the case the matcher must answer "never offered" to, and it can only answer
    that about a job it was given."""
    written = await _planted(session_factory)

    assert [job["id"] for job in written["jobs"]] == ["wfl_proven", "wfl_unproven"]
    assert [shape["id"] for shape in written["shapes"]] == ["wfl_proven"]


async def test_a_jobs_gestures_arrive_in_the_order_they_were_made(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A browser appends to its tail as gestures arrive. It has never heard of
    a step.

    This assertion used to read the other way round -- citation order, planted
    corpus made backwards -- and justified itself with "cite order is what the
    shape is built in, so cite order is what the tail has to arrive in". That
    reasoning is circular, and the circle was hiding the measurement: the
    replay fed the matcher the very sequence the shape was built from, so the
    matcher was being handed its own answer. Fed honestly, in the order a
    browser would send them, acme's corpus offered 3 of 7 jobs where the
    harness had been reporting 5, and tenant `new`'s two cross-system jobs
    offered 0 of 2.

    Both halves moved together: `shape.in_time_order` builds the shape in this
    order too, which is what took those numbers to 6 of 7 and 2 of 2. The
    acceptance test that both halves agree is
    `test_the_job_walks_the_very_triples_its_shape_is_made_of` below, and it
    passes either way -- which is exactly why this one has to pin the order
    against the browser rather than against its neighbour.
    """
    written = await _planted(session_factory)

    job = written["jobs"][0]
    assert set(job) == {"id", "title", "gestures"}
    assert [gesture["at"] for gesture in job["gestures"]] == [100.0, 200.0, 300.0, 400.0]
    assert [gesture["triple"][1] for gesture in job["gestures"]] == [
        "name|Save",
        "name|Work Area",
        "anon|scroll",
        "name|Work Areas",
    ]


async def test_the_scroll_is_left_in_the_job_and_out_of_the_shape(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """`recognise.js`'s `tailWith` drops the scroll. Dropping it here as well
    would hand the matcher a tail it had already cleaned and prove nothing
    about the one line that does the cleaning."""
    written = await _planted(session_factory)

    (shape,) = written["shapes"]
    job = written["jobs"][0]
    scrolls = [gesture for gesture in job["gestures"] if gesture["triple"][1] == "anon|scroll"]
    assert len(scrolls) == 1
    assert ["anon|scroll"] not in [[triple[1]] for triple in shape["shape"]]


async def test_the_job_walks_the_very_triples_its_shape_is_made_of(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The whole acceptance test in one line: strip what the tail drops and
    what is left must be the shape, exactly. A second spelling of the triple in
    either half is a job that is never offered, and the count would fall
    without anything else in the suite going red."""
    written = await _planted(session_factory)

    (shape,) = written["shapes"]
    job = written["jobs"][0]
    walked = [
        gesture["triple"] for gesture in job["gestures"] if gesture["triple"][1] != "anon|scroll"
    ]
    assert walked == shape["shape"]


async def test_a_gesture_carries_the_mark_of_a_value_and_never_the_value(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The file goes to /tmp and is read by another process. The matcher lifts
    on "a value was typed here"; the text is a customer's."""
    written = await _planted(session_factory)

    job = written["jobs"][0]
    assert all(set(gesture) == GESTURE_KEYS for gesture in job["gestures"])
    # The typed gesture is at 200.0, which is second once the job arrives in
    # the order it was made rather than in citation order.
    assert [gesture["value"] for gesture in job["gestures"]] == [None, TYPED, None, None]
    assert [gesture["secret"] for gesture in job["gestures"]] == [False, False, False, False]
    assert TYPED_VALUE not in json.dumps(written)


def test_a_password_field_exports_as_secret_by_either_half_of_the_flag() -> None:
    """`bool(action.secret or (action.target and action.target.secret))`.

    Dropping the `target.secret` half survives every other test in the Python
    suite and all seven replay tests here, because nothing planted a secret
    gesture at all. It is not cosmetic: `recognise.js` builds its tail from
    these entries, so a gesture on a password field exported as not-secret puts
    a gesture in the tail the extension would never have built -- and the
    replay would then be measuring a tail that does not exist. The rig carries
    both halves at `new_agent_arch/scripts/dry_run.py:253-255`.

    No database: `_gestures_of` is pure, and it is the function the flag lives
    in. It sits here rather than in `tests/unit` because that is where the
    import of `scripts.dry_run` already is.
    """
    marked_on_the_gesture = _gesture(
        "ges_a",
        at=1.0,
        action=Action(kind="type", at=1.0, secret=True, target=Target(tag="input", name="Token")),
    )
    marked_on_the_element = _gesture(
        "ges_b",
        at=2.0,
        action=Action(
            kind="type", at=2.0, target=Target(tag="input", name="Password", secret=True)
        ),
    )
    plain = _click("ges_c", "Save", at=3.0)
    by_id = {g.id: g for g in (marked_on_the_gesture, marked_on_the_element, plain)}
    workflow = Workflow(
        id="wfl_secret",
        tenant=TENANT.value,
        title="sign in",
        narrative="the operator signed in",
        systems=[SYSTEM],
        steps=[
            Step(
                order=0,
                says="sign in",
                system=SYSTEM,
                cites=["ges_a", "ges_b", "ges_c"],
                parameters=[],
            )
        ],
    )

    exported = _gestures_of(workflow, by_id)

    assert [entry["secret"] for entry in exported] == [True, True, False]
