"""The chat door: what an operator said, and which job it turns out to be.

Ported from `new_agent_arch/tests/test_entry.py`, names unchanged. Eight of its
nine are here; the ninth --
`test_no_schema_in_the_package_uses_what_the_developer_api_refuses` -- already
lives in `tests/unit/domain/rig/test_planning.py`, where it walks every schema
under `sro.domain` rather than one. `UNDERSTAND_SCHEMA` is declared in
`sro.domain.chat.reading` so that walker reaches it: a second copy of that rule
over here would be a rule the next schema can be written outside of.

Everything below the ported eight is this port's own, and each one stands under
a comment in `understand.py` that records a decision: the paragraph that made
the door work, the job the model named, the order the form's fields come back
in, and the row that carries the bill and never the sentence.
"""

from dataclasses import asdict
from datetime import UTC, datetime

from sro.application.chat.understand import read_utterance, understand
from sro.domain.chat.reading import INSTRUCTIONS, UNDERSTAND_SCHEMA, ChatReading
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeAsker, FakeChatRepository, FakeUnitOfWork

TENANT = TenantId("acme")

NOW = datetime(2025, 2, 11, 23, tzinfo=UTC)
"""The rig's clock through all of this, and deliberately not today: a row
stamped by a door that read `datetime.now(UTC)` instead of its `now` would
agree with a fixture dated today by the calendar alone."""

WFS = [
    Workflow(
        id="wfl_1",
        tenant=TENANT.value,
        title="create a client",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=["g"])],
        parameters=[{"name": "clientCode", "seen_values": ["A"]}],
    )
]

SECOND = Workflow(
    id="wfl_2",
    tenant=TENANT.value,
    title="create a work area",
    narrative="n",
    steps=[Step(order=0, says="s", system=None, cites=["g"])],
    parameters=[{"name": "areaName", "seen_values": ["NEWTESTS"]}],
)


def _answer(workflow_id: str | None, values: list[dict[str, str]]) -> Answer:
    return Answer(data={"workflow_id": workflow_id, "values": values, "missing": []})


async def test_an_utterance_is_read_against_the_workflows_held_and_asks_for_what_is_missing() -> (
    None
):
    asker = FakeAsker(
        Answer(
            data={
                "workflow_id": "wfl_1",
                "values": [{"name": "clientCode", "value": "NEW9"}],
                "missing": [],
            }
        )
    )
    got = await understand("create client NEW9", WFS, asker, "m")
    assert got.workflow_id == "wfl_1" and got.values == {"clientCode": "NEW9"} and got.missing == []
    assert "create a client" in str(asker.asked[0]["evidence"]), (
        "the workflows are what it reads against"
    )


async def test_a_workflow_the_rig_does_not_hold_is_not_offered() -> None:
    got = await understand(
        "x",
        WFS,
        FakeAsker(Answer(data={"workflow_id": "wfl_nope", "values": [], "missing": []})),
        "m",
    )
    assert got.workflow_id is None


async def test_a_value_for_a_parameter_the_workflow_does_not_declare_is_dropped() -> None:
    got = await understand(
        "x",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [
                        {"name": "clientCode", "value": "A"},
                        {"name": "evil", "value": "b"},
                    ],
                    "missing": [],
                }
            )
        ),
        "m",
    )
    assert got.values == {"clientCode": "A"}


def test_the_schema_is_the_specs() -> None:
    properties = UNDERSTAND_SCHEMA["properties"]
    assert isinstance(properties, dict)
    assert set(properties) == {"workflow_id", "values", "missing"}


async def test_a_parameter_with_no_value_is_missing_whatever_the_model_says() -> None:
    """The model's own `missing` is read and ignored: it is the one field it
    can get wrong in the direction that matters, because a parameter dropped
    from `missing` is a parameter the form never asks for and the run then
    performs with whatever the recording happened to contain."""
    got = await understand(
        "make one",
        WFS,
        FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []})),
        "m",
    )
    assert got.missing == ["clientCode"]


async def test_a_value_the_model_invented_a_name_for_leaves_its_parameter_missing() -> None:
    got = await understand(
        "make one",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "evil", "value": "b"}],
                    "missing": ["nothing"],
                }
            )
        ),
        "m",
    )
    assert got.values == {} and got.missing == ["clientCode"]


async def test_the_model_that_named_nothing_still_hands_back_what_it_cost() -> None:
    """Every gesture gets a reading, and a refusal is one too: the answer is
    carried on all three ways out, so the caller can bill it."""
    both: tuple[dict[str, object] | None, ...] = (
        None,
        {"workflow_id": "wfl_nope", "values": [], "missing": []},
    )
    for data in both:
        answer = Answer(data=data, cost_usd=0.0003, in_tokens=120)
        got = await understand("x", WFS, FakeAsker(answer), "m")
        assert got.workflow_id is None
        assert got.answer is answer

    named = Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []}, cost_usd=0.0009)
    got = await understand("x", WFS, FakeAsker(named), "m")
    assert got.answer is named


async def test_the_reading_is_asked_of_the_model_it_was_given_under_the_declared_schema() -> None:
    asker = FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []}))
    await understand("x", WFS, asker, "gemini-3.8-flash")
    [asked] = asker.asked
    assert asked["model"] == "gemini-3.8-flash"
    assert asked["schema"] is UNDERSTAND_SCHEMA, "structured output, or the reading is prose"
    assert asked["instructions"], "a model told nothing answers about nothing"


def test_a_job_is_a_kind_of_work_not_the_one_time_it_was_done() -> None:
    """The paragraph that made this door work, pinned word for word.

    A mined job is named after the single demonstration it was read from,
    values and all -- "Create Work Area NEWTESTS" -- so a door told only to
    answer which job was meant compares a live sentence against the record of
    one past doing and answers null. Told nothing else, it named no job for
    five real operator sentences. Told this, five of five. Reworded away, the
    door still runs, still costs money and still offers nothing, which is why
    the sentence is a test and not a note.
    """
    assert "A job is a kind of work, not the one time it was done." in INSTRUCTIONS
    assert "Match on what the job does." in INSTRUCTIONS
    assert "Answer null only\nwhen no job here does that kind of work at all." in INSTRUCTIONS


async def test_the_job_offered_is_the_one_the_model_named() -> None:
    """Two jobs held, the second one named. The offer the form renders is a
    workflow id and that workflow's parameters, so a door that hands back
    whichever job it happened to reach first offers a real form for the wrong
    work -- and one held job is enough to hide it."""
    got = await understand(
        "create work area NEWTEST9",
        [*WFS, SECOND],
        FakeAsker(_answer("wfl_2", [{"name": "areaName", "value": "NEWTEST9"}])),
        "m",
    )
    assert got.workflow_id == "wfl_2"
    assert got.values == {"areaName": "NEWTEST9"} and got.missing == []


async def test_what_is_missing_comes_back_in_one_order() -> None:
    """`declared` is a set, so an unsorted `missing` is the interpreter's hash
    order: the same sentence asked twice reorders the fields of the form the
    operator is looking at, and nothing about that is reproducible enough to
    screenshot or to test against.

    Eight parameters rather than the two this reads as needing. Set iteration
    order is a new arrangement per interpreter, so a three-name plant agrees
    with an unsorted `missing` on roughly one PYTHONHASHSEED in six -- measured,
    not guessed: three of eight seeds passed against exactly that mutant. At
    eight names an accidental agreement is one arrangement in 40320, and the
    hash seed stops being the thing that decides whether this suite is honest.
    """
    eight = Workflow(
        id="wfl_3",
        tenant=TENANT.value,
        title="t",
        narrative="n",
        # Declared in an order that is neither the answer nor its reverse, so a
        # `missing` that kept declaration order is not satisfied by this plant
        # either.
        parameters=[
            {"name": "zone"},
            {"name": "clientCode"},
            {"name": "statusCombo"},
            {"name": "areaName"},
            {"name": "ownerCode"},
            {"name": "dockId"},
            {"name": "siteCode"},
            {"name": "lane"},
        ],
    )
    got = await understand("make one", [eight], FakeAsker(_answer("wfl_3", [])), "m")
    assert got.missing == [
        "areaName",
        "clientCode",
        "dockId",
        "lane",
        "ownerCode",
        "siteCode",
        "statusCombo",
        "zone",
    ]


async def test_the_prompt_spells_the_redaction_marker_the_way_the_rest_of_the_system_does() -> None:
    """The marker is «redacted» everywhere else, and json.dumps' default
    `ensure_ascii` would write it into this prompt -- and only this prompt --
    as \\u00abredacted\\u00bb."""
    redacted = Workflow(
        id="wfl_4", tenant=TENANT.value, title="create a client for «redacted»", narrative="n"
    )
    asker = FakeAsker(_answer(None, []))
    await understand("x", [redacted], asker, "m")
    assert "«redacted»" in str(asker.asked[0]["evidence"])


def _rows(uow: FakeUnitOfWork) -> list[ChatReading]:
    """The stored readings. `FakeUnitOfWork.chats` is annotated with the port
    it stands in for, and a port has no rows to reach into."""
    assert isinstance(uow.chats, FakeChatRepository)
    return uow.chats.rows


async def _read(*answers: Answer, workflows: list[Workflow] | None = None) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    for workflow in workflows if workflows is not None else WFS:
        await uow.workflows.save(workflow)
    for answer in answers:
        await read_utterance(
            uow,
            tenant_id=TENANT,
            utterance="create client NEWTEST9 at the Coventry dock",
            asker=FakeAsker(answer),
            model="m",
            now=NOW,
        )
    return uow


async def test_what_the_reading_cost_is_written_down() -> None:
    """The row exists for the cap and the spend line. A door whose readings
    are not billed is model money nothing sums, which is how an unattended
    week spends without limit."""
    uow = await _read(
        Answer(
            data={"workflow_id": "wfl_1", "values": [], "missing": []},
            in_tokens=120,
            out_tokens=30,
            thought_tokens=7,
            cost_usd=0.0003,
        )
    )
    [row] = _rows(uow)
    assert row.id.startswith("cht_")
    assert row.tenant == TENANT.value and row.at == NOW.isoformat()
    assert row.workflow_id == "wfl_1"
    assert (row.in_tokens, row.out_tokens, row.thought_tokens) == (120, 30, 7)
    assert row.cost_usd == 0.0003 and row.unpriced is False and row.error is None
    assert uow.commits == 1, "a bill nothing committed is a bill the next rollback loses"
    # The whole point of the row: the day's cap can see what the door spent.
    assert (await uow.spend.today(TENANT, now=NOW)).cost_usd == 0.0003


async def test_a_refusal_is_a_reading_and_gets_its_row() -> None:
    """A call that came back with nothing is the case that matters: the row is
    then the only record left of a call that cost money and returned nothing,
    and a model the price table never knew about is blind rather than free."""
    uow = await _read(Answer(data=None, in_tokens=90, unpriced=True, error="503 from the model"))
    [row] = _rows(uow)
    assert row.workflow_id is None and row.error == "503 from the model"
    assert row.unpriced is True and row.in_tokens == 90 and row.cost_usd == 0.0
    assert uow.commits == 1


async def test_the_sentence_the_door_read_is_not_written_down() -> None:
    """An operator's words about their own warehouse are not ours to keep, and
    the row exists for the cap and the spend line -- neither of which needs
    them. `ChatReading` has no field for the utterance; this is the test that
    notices one being added and filled."""
    uow = await _read(_answer("wfl_1", [{"name": "clientCode", "value": "NEWTEST9"}]))
    [row] = _rows(uow)
    written = " ".join(str(value) for value in asdict(row).values())
    for word in ("NEWTEST9", "Coventry", "dock", "create client"):
        assert word not in written, f"the door wrote down what it read: {word!r} in {written!r}"
