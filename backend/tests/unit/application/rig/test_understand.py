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

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime

from sro.application.chat.understand import read_utterance, understand
from sro.domain.chat.reading import INSTRUCTIONS, UNDERSTAND_SCHEMA, ChatReading
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeAsker, FakeChatRepository, FakeUnitOfWork

# Every parameter in this file is marked `required`, because these tests are
# about what a sentence failed to supply for a job that needs it. Since
# 2026-09-22 a parameter is demanded only where the page said so -- see
# `sro.domain.skill.learned.demanded` -- and an unmarked fixture is a fixture
# about an optional field, which is a different test.
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
        parameters=[{"name": "clientCode", "seen_values": ["A"], "required": True}],
    )
]

SECOND = Workflow(
    id="wfl_2",
    tenant=TENANT.value,
    title="create a work area",
    narrative="n",
    steps=[Step(order=0, says="s", system=None, cites=["g"])],
    parameters=[{"name": "areaName", "seen_values": ["NEWTESTS"], "required": True}],
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
    assert set(properties) == {"workflow_id", "values", "missing", "items", "sure", "also"}


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
            {"name": "zone", "required": True},
            {"name": "clientCode", "required": True},
            {"name": "statusCombo", "required": True},
            {"name": "areaName", "required": True},
            {"name": "ownerCode", "required": True},
            {"name": "dockId", "required": True},
            {"name": "siteCode", "required": True},
            {"name": "lane", "required": True},
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
    # Length too, not only the prefix: new_chat_id's comment claims "the shape
    # every other id in the backend has", and token_hex(4) passed on the prefix
    # alone. The other four minters pin it; this was the one that did not.
    assert row.id.startswith("cht_") and len(row.id) == 36
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


# --- several things, one job -------------------------------------------------


def _said(*things: dict[str, str]) -> list[dict[str, object]]:
    return [
        {"values": [{"name": name, "value": value} for name, value in thing.items()]}
        for thing in things
    ]


async def test_three_things_in_one_sentence_are_three_things() -> None:
    """The mail that prompted this carried three equipment types. The door
    could answer one, and the other two were lost between a message and a
    browser that had just proved it could do them."""
    got = await understand(
        "add these three",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "items": _said(
                        {"clientCode": "8SITDOWN"},
                        {"clientCode": "8STANDUP"},
                        {"clientCode": "8REACHT"},
                    ),
                }
            )
        ),
        "m",
    )

    assert got.items == [
        {"clientCode": "8SITDOWN"},
        {"clientCode": "8STANDUP"},
        {"clientCode": "8REACHT"},
    ]
    assert got.missing == [], "every thing named its own code"


async def test_one_thing_names_no_items_at_all() -> None:
    """Most sentences. A job run for one item performs exactly as a job run for
    none, and the door says so by answering none."""
    got = await understand(
        "make one",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "clientCode", "value": "ONE"}],
                    "missing": [],
                }
            )
        ),
        "m",
    )

    assert got.items == []
    assert got.values == {"clientCode": "ONE"}


async def test_a_parameter_one_thing_lacks_is_missing() -> None:
    """Three equipment types of which one has no code is a form that has to ask
    for the code. Checked against every thing, not against what the job shares:
    a check against the shared values alone would say somebody supplied it."""
    got = await understand(
        "add these",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "items": _said({"clientCode": "8SITDOWN"}, {}),
                }
            )
        ),
        "m",
    )

    assert got.items == [{"clientCode": "8SITDOWN"}], "a thing naming nothing is not a thing"
    assert got.missing == ["clientCode"]


async def test_a_key_this_job_never_declared_is_dropped_from_a_thing_too() -> None:
    # The same filter `values` gets, for the same reason: a sentence a stranger
    # could have written must not put a key into a run.
    got = await understand(
        "add these",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "items": _said({"clientCode": "A", "sudo": "yes"}),
                }
            )
        ),
        "m",
    )

    assert got.items == [{"clientCode": "A"}]


# --- saying so when it is not sure -------------------------------------------


async def test_a_reading_that_is_not_sure_says_so() -> None:
    """The answer that started this.

    An operator whose tenant holds "Create a Warehouse Equipment Type" typed
    "lets create warehouse equipment type" and was told "Create a customer type
    does that" -- with no way for anything downstream to know it had guessed. A
    guess that creates one wrong record is a nuisance; the same guess against a
    list of twenty is twenty wrong records in a warehouse.
    """
    got = await understand(
        "make one of those",
        [*WFS, SECOND],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "sure": False,
                    "also": ["wfl_2"],
                }
            )
        ),
        "m",
    )

    assert got.workflow_id == "wfl_1", "it still answers its best reading"
    assert got.sure is False
    assert got.also == ["wfl_2"], "and what a person will be asked to choose between"


async def test_naming_another_job_it_might_have_meant_is_not_being_sure() -> None:
    """A reading that offers an alternative has already said it was choosing,
    whatever it then claims about itself."""
    got = await understand(
        "make one",
        [*WFS, SECOND],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "sure": True,
                    "also": ["wfl_2"],
                }
            )
        ),
        "m",
    )

    assert got.sure is False


async def test_a_job_this_tenant_does_not_hold_is_not_an_alternative() -> None:
    # The same filter `workflow_id` gets: a model naming one is a
    # hallucination, and a question offering it is a question with a wrong
    # answer in it.
    got = await understand(
        "make one",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "sure": False,
                    "also": ["wfl_nope", "wfl_1"],
                }
            )
        ),
        "m",
    )

    assert got.also == [], "an id nobody holds, and its own answer, are not alternatives"


async def test_a_plain_reading_is_sure_and_says_nothing_else() -> None:
    got = await understand(
        "create client NEW9",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "clientCode", "value": "NEW9"}],
                    "missing": [],
                    "sure": True,
                }
            )
        ),
        "m",
    )

    assert got.sure is True and got.also == []


async def test_the_mails_a_job_was_asked_for_by_reach_the_model() -> None:
    """The one signal this door was never shown.

    A watch is a substring somebody typed once and will miss "please set up a
    new client category" forever. What says what a REQUEST for a job looks like
    is the mails the operator acted on before doing it -- already in the store,
    cited by the job itself -- and the decision about which job a piece of text
    means is made here.
    """
    asker = FakeAsker(_answer("wfl_1", []))

    await understand(
        "a customer type please",
        WFS,
        asker,
        "m",
        {"wfl_1": ["a customer type :- GKB description :- leaning new SRO type 002"]},
    )

    (job,) = json.loads(str(asker.asked[0]["evidence"]))["jobs"]
    assert job["asked_by"] == ["a customer type :- GKB description :- leaning new SRO type 002"]
    # And the prompt says what to do with them. A model that answered with a
    # code out of an old request would create that record a second time.
    assert "Never take a value out of one" in INSTRUCTIONS


async def test_a_job_nobody_mailed_about_carries_no_empty_list_to_argue_with() -> None:
    """An `asked_by: []` invites "this job is never asked for by mail", which
    is a claim about the tenant's history rather than about the job."""
    asker = FakeAsker(_answer("wfl_1", []))

    await understand("a customer type please", WFS, asker, "m")

    (job,) = json.loads(str(asker.asked[0]["evidence"]))["jobs"]
    assert "asked_by" not in job


async def test_the_examples_are_read_off_the_gestures_the_jobs_cite() -> None:
    """End to end through the door an operator actually reaches: the mails are
    not passed in by a caller, they are read out of the evidence."""
    uow = FakeUnitOfWork()
    await uow.workflows.save(WFS[0])
    await uow.gestures.add_gestures(
        (
            Gesture(
                id="g",
                tenant=TENANT.value,
                stream_id="str-1",
                batch_id="bat-1",
                at=10.0,
                url="https://mail.google.com/mail/u/0/#inbox/abc",
                system="https://mail.google.com",
                tab_id=7,
                frame_url=None,
                action=Action(
                    kind="click",
                    at=10.0,
                    url="https://mail.google.com",
                    target=Target(name="please create a client for the Coventry dock"),
                ),
            ),
        )
    )
    asker = FakeAsker(_answer("wfl_1", []))

    await read_utterance(
        uow,
        tenant_id=TENANT,
        utterance="new client for Coventry",
        asker=asker,
        model="m",
        now=NOW,
    )

    (job,) = json.loads(str(asker.asked[0]["evidence"]))["jobs"]
    assert job["asked_by"] == ["please create a client for the Coventry dock"]


async def test_a_request_naming_a_field_this_job_has_no_parameter_for_says_which() -> None:
    """The dropping is right and the silence was the fault.

    A job's parameters are what two doings proved VARY, and the form has far
    more fields than that -- so `code NEW9, and put it in Inbound` is a
    perfectly reasonable request, answered here by a record with no Department
    in it and nothing anywhere saying so. The run says it after the press, and
    after the press is after the record.
    """
    got = await understand(
        "create client NEW9 in Inbound",
        WFS,
        FakeAsker(
            _answer(
                "wfl_1",
                [
                    {"name": "clientCode", "value": "NEW9"},
                    {"name": "Department", "value": "Inbound"},
                ],
            )
        ),
        "m",
    )

    # Still dropped from the values: a key the workflow never declared is a
    # value nothing asked for, arriving in a sentence a stranger could write.
    assert got.values == {"clientCode": "NEW9"}
    assert got.unasked == ["Department"]
    # And what it SAID, kept beside the name: a form posts far more fields than
    # a job varies, so where the dictionary names the slot the write can fill
    # it after all -- and it cannot fill a value this threw away.
    assert got.aside == {"Department": "Inbound"}


async def test_a_request_this_job_can_write_whole_names_nothing_extra() -> None:
    got = await understand(
        "create client NEW9",
        WFS,
        FakeAsker(_answer("wfl_1", [{"name": "clientCode", "value": "NEW9"}])),
        "m",
    )

    assert got.unasked == []


# --- and an alternative the sentence cannot fill ------------------------------


async def test_a_job_this_sentence_could_not_fill_is_not_an_alternative() -> None:
    """Measured on the deployment 2026-09-19. A mail saying `customer type :-
    GZ2 / description :- undo round two` was read as `Create a Customer Type`
    -- the only job of that name, eighty-seven runs behind it -- and the model
    named `Forward an Email` as one it might have meant. `sure` went false, the
    mail path said nothing at all, and the request sat unread in a mailbox
    while the tenant held the job it asked for.

    The sentence settles it: one job's parameters are all named and the
    other's are not, which is a fact about the two rather than a confidence.
    """
    got = await understand(
        "customer type :- GZ2, description :- undo round two",
        [*WFS, SECOND],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "clientCode", "value": "GZ2"}],
                    "missing": [],
                    "sure": False,
                    "also": ["wfl_2"],
                }
            )
        ),
        "m",
    )

    assert got.workflow_id == "wfl_1"
    assert got.also == [], "it kept an alternative this sentence names nothing for"
    assert got.sure is True


async def test_an_alternative_the_sentence_could_equally_fill_still_stands() -> None:
    """Two jobs the sentence supplies is the ambiguity this refusal is for, and
    it is left exactly as it was."""
    both = replace(
        SECOND, parameters=[{"name": "clientCode", "seen_values": ["A"], "required": True}]
    )

    got = await understand(
        "make one with clientCode A",
        [*WFS, both],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "clientCode", "value": "A"}],
                    "missing": [],
                    "sure": True,
                    "also": ["wfl_2"],
                }
            )
        ),
        "m",
    )

    assert got.also == ["wfl_2"]
    assert got.sure is False


async def test_a_sentence_that_fills_neither_stays_unsure() -> None:
    """Eliminating everything is not choosing. A sentence that names no values
    at all leaves the alternatives exactly where the model left them."""
    got = await understand(
        "make one of those",
        [*WFS, SECOND],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [],
                    "missing": [],
                    "sure": False,
                    "also": ["wfl_2"],
                }
            )
        ),
        "m",
    )

    assert got.also == ["wfl_2"]
    assert got.sure is False


async def test_a_field_the_page_never_asked_for_is_not_missing() -> None:
    """The third door, and the one the operator met first.

    Measured on the deployment 2026-09-22 at 11:35. The run's own question had
    just said "I can also set Department and Manufacturer ... or I will run
    without", and this door then asked "Department takes 10 characters. What
    should it be?" -- because `missing` here is `declared` minus what arrived,
    and `declared` is every parameter the job has learnt.

    A job learns a parameter from two doings that varied a field. That says
    the operator filled it twice, not that the form demands it.
    """
    job = replace(
        WFS[0],
        parameters=[
            {"name": "Customer Type", "names": ["Customer Type*"], "seen_values": ["GGD"]},
            {"name": "Department", "names": ["Department"], "seen_values": ["IN"]},
        ],
    )

    got = await understand(
        "create a customer type",
        [job],
        FakeAsker(Answer(data={"workflow_id": job.id, "values": [], "missing": []})),
        "m",
    )

    assert got.missing == ["Customer Type"], "a field the page never asked for was demanded"


async def test_a_job_is_still_recognised_after_it_learns_an_optional_field() -> None:
    """Measured on the deployment 2026-09-22 at 07:06.

    `Create a Customer Type` grew from two parameters to four the night
    before, as Department and Manufacturer became parameters. A mail giving
    customer type and description -- everything the form demands -- then
    failed to FILL the job, so the reading's alternative was never eliminated,
    `sure` stayed false, and the request was dropped with "asked for a job
    this tenant holds more than one of".

    Learning two fields cost the job the ability to be recognised at all. An
    optional slot nobody named says nothing about whether the sentence was
    about this job: the form does not ask for it, so a request that does not
    mention it is a complete request.
    """
    grown = replace(
        WFS[0],
        parameters=[
            {"name": "Customer Type", "names": ["Customer Type*"], "seen_values": ["GGD"]},
            {"name": "Customer Type Description", "names": ["Desc*"], "seen_values": ["x"]},
            {"name": "Department", "names": ["Department"], "seen_values": ["IN"]},
            {"name": "Manufacturer", "names": ["Manufacturer"], "seen_values": ["OUTSIDE"]},
        ],
    )
    other = replace(SECOND, id="wfl_other", title="Reply to Email")

    got = await understand(
        "customer type :- MRN1 description :- morning run",
        [grown, other],
        FakeAsker(
            Answer(
                data={
                    "workflow_id": grown.id,
                    "values": [
                        {"name": "Customer Type", "value": "MRN1"},
                        {"name": "Customer Type Description", "value": "morning run"},
                    ],
                    "missing": [],
                    # The reading hedged, exactly as it did on the deployment.
                    "also": [other.id],
                    "sure": False,
                }
            )
        ),
        "m",
    )

    assert got.sure is True, "a job whose every demanded field was given was still ambiguous"
    assert got.workflow_id == grown.id
    assert got.missing == []
