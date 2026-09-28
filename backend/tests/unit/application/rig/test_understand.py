"""The chat door: what an operator said, and which job it turns out to be.

Ported from `new_agent_arch/tests/test_entry.py`, and ported again to R1's
reader: candidates ranked in code, the whole request read once, and every
value quoted and checked. The rules each old test pinned still stand; where
the answer's shape changed (`job`, `values: [{field, value, quote}]`), the
fixtures changed with it. What a value must pass is pinned value by value in
`tests/unit/domain/test_reading_a_request.py`; this file is the door.
"""

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any

from sro.application.chat.understand import (
    K_A_CHORE,
    Understood,
    offer_check,
    read_utterance,
    understand,
)
from sro.application.skill.job_facts import job_facts
from sro.domain.chat.reading import ChatReading
from sro.domain.chat.request import Candidate
from sro.domain.execution.field_classes import field_classes
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.prompts.read_request import READ_REQUEST
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.test_compiling_a_job import _learned_field
from tests.unit.fakes import FakeAsker, FakeChatRepository, FakeUnitOfWork
from tests.unit.runtime_support import save_job, save_step

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
        steps=[Step(order=0, says="s", system=None, cites=["g"], parameters=["clientCode"])],
        parameters=[{"name": "clientCode", "seen_values": ["A"], "required": True}],
    )
]

SECOND = Workflow(
    id="wfl_2",
    tenant=TENANT.value,
    title="create a work area",
    narrative="n",
    steps=[Step(order=0, says="s", system=None, cites=["g"], parameters=["areaName"])],
    parameters=[{"name": "areaName", "seen_values": ["NEWTESTS"], "required": True}],
)


def _job(workflow: Workflow, asked_by: tuple[str, ...] = ()) -> Candidate:
    return Candidate(
        id=workflow.id,
        title=workflow.title,
        fields=field_classes(workflow, {}, {}),
        aliases={},
        seen={},
        asked_by=asked_by,
    )


def _jobs(*workflows: Workflow) -> list[Candidate]:
    return [_job(one) for one in workflows or WFS]


def _value(field: str, value: str, quote: str = "") -> dict[str, str]:
    return {"field": field, "value": value, "quote": quote or value}


def _answer(
    job: str | None, values: list[dict[str, str]], *, sure: bool = True, **more: object
) -> Answer:
    return Answer(data={"job": job, "sure": sure, "values": values, **more})


def _candidates(asker: FakeAsker) -> list[dict[str, Any]]:
    fence = str(asker.asked[0]["evidence"]).split('<untrusted name="candidates">\n', 1)[1]
    said = json.loads(fence.split("\n</untrusted>", 1)[0])
    assert isinstance(said, list)
    return said


async def test_an_utterance_is_read_against_its_candidates_and_asks_for_what_is_missing() -> None:
    asker = FakeAsker(_answer("wfl_1", [_value("clientCode", "NEW9")]))
    got = await understand("create client NEW9", _jobs(), asker)
    assert got.workflow_id == "wfl_1" and got.values == {"clientCode": "NEW9"} and got.missing == []
    assert "create a client" in str(asker.asked[0]["evidence"]), (
        "the candidates are what it reads against"
    )


async def test_a_workflow_that_was_not_a_candidate_is_not_offered() -> None:
    got = await understand("x", _jobs(), FakeAsker(_answer("wfl_nope", [])))
    assert got.workflow_id is None


def test_the_schema_is_the_specs() -> None:
    properties = READ_REQUEST.output_schema["properties"]
    assert isinstance(properties, dict)
    assert set(properties) == {"job", "sure", "also", "values", "items"}


async def test_a_parameter_with_no_value_is_missing_whatever_the_model_says() -> None:
    """Missing is worked out in code: a parameter dropped from it is a parameter
    the form never asks for and the run then performs with whatever the
    recording happened to contain."""
    got = await understand("make one", _jobs(), FakeAsker(_answer("wfl_1", [])))
    assert got.missing == ["clientCode"]


async def test_a_value_the_model_invented_a_name_for_leaves_its_parameter_missing() -> None:
    got = await understand(
        "make one b", _jobs(), FakeAsker(_answer("wfl_1", [_value("evil", "b")]))
    )
    assert got.values == {} and got.missing == ["clientCode"]
    assert got.aside == {"evil": "b"}, "kept under its own word, never as a parameter"


async def test_the_model_that_named_nothing_still_hands_back_what_it_cost() -> None:
    """Every reading is billed, and a refusal is one too."""
    for data in (None, {"job": "wfl_nope", "sure": True, "values": []}):
        answer = Answer(data=data, cost_usd=0.0003, in_tokens=120)
        got = await understand("x", _jobs(), FakeAsker(answer))
        assert got.workflow_id is None
        assert (got.answer.cost_usd, got.answer.in_tokens) == (0.0003, 120)

    named = Answer(data={"job": "wfl_1", "sure": True, "values": []}, cost_usd=0.0009)
    got = await understand("x", _jobs(), FakeAsker(named))
    assert got.answer is named


async def test_the_reading_is_asked_of_the_model_its_record_names_under_its_schema() -> None:
    asker = FakeAsker(_answer("wfl_1", []))
    await understand("x", _jobs(), asker)
    [asked] = asker.asked
    assert asked["model"] == READ_REQUEST.model
    assert asked["schema"] == dict(READ_REQUEST.output_schema), (
        "structured output, or the reading is prose"
    )
    assert asked["instructions"], "a model told nothing answers about nothing"


def test_a_job_is_a_kind_of_work_not_the_one_time_it_was_done() -> None:
    """The paragraph that made this door work, pinned word for word.

    A mined job is named after the single demonstration it was read from,
    values and all -- "Create Work Area NEWTESTS" -- so a door told only to
    answer which job was meant compares a live sentence against the record of
    one past doing and answers null. Reworded away, the door still runs, still
    costs money and still offers nothing, which is why the sentence is a test.
    """
    assert "Match on\nwhat the job does, not on one demonstration's values" in READ_REQUEST.task
    assert '"a work area called\nNEWTEST9" asks for "Create Work Area NEWTESTS"' in (
        READ_REQUEST.task
    )


async def test_the_job_offered_is_the_one_the_model_named() -> None:
    got = await understand(
        "create work area NEWTEST9",
        _jobs(*WFS, SECOND),
        FakeAsker(_answer("wfl_2", [_value("areaName", "NEWTEST9")])),
    )
    assert got.workflow_id == "wfl_2"
    assert got.values == {"areaName": "NEWTEST9"} and got.missing == []


async def test_what_is_missing_comes_back_in_one_order() -> None:
    """Eight parameters, declared in an order that is neither the answer nor its
    reverse: at eight names an accidental agreement with a hash order is one
    arrangement in 40320."""
    eight = Workflow(
        id="wfl_3",
        tenant=TENANT.value,
        title="t",
        narrative="n",
        parameters=[
            {"name": name, "required": True}
            for name in (
                "zone",
                "clientCode",
                "statusCombo",
                "areaName",
                "ownerCode",
                "dockId",
                "siteCode",
                "lane",
            )
        ],
    )
    got = await understand("make one", _jobs(eight), FakeAsker(_answer("wfl_3", [])))
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
    redacted = Workflow(
        id="wfl_4", tenant=TENANT.value, title="create a client for «redacted»", narrative="n"
    )
    asker = FakeAsker(_answer(None, []))
    await understand("x", _jobs(redacted), asker)
    assert "«redacted»" in str(asker.asked[0]["evidence"])


def _rows(uow: FakeUnitOfWork) -> list[ChatReading]:
    assert isinstance(uow.chats, FakeChatRepository)
    return uow.chats.rows


SAID = "create client NEWTEST9 at the Coventry dock"


async def _read(*answers: Answer, workflows: list[Workflow] | None = None) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    # A cited, proven save, so every job compiles.
    await uow.gestures.add_gestures(tuple(save_step(gid="g")[1].values()))
    for workflow in workflows if workflows is not None else WFS:
        await uow.workflows.save(workflow)
    for answer in answers:
        await read_utterance(
            uow, tenant_id=TENANT, utterance=SAID, asker=FakeAsker(answer), now=NOW
        )
    return uow


async def test_what_the_reading_cost_is_written_down() -> None:
    uow = await _read(
        Answer(
            data={"job": "wfl_1", "sure": True, "values": []},
            in_tokens=120,
            out_tokens=30,
            thought_tokens=7,
            cost_usd=0.0003,
        )
    )
    [row] = _rows(uow)
    assert row.id.startswith("cht_") and len(row.id) == 36
    assert row.tenant == TENANT.value and row.at == NOW.isoformat()
    assert row.workflow_id == "wfl_1"
    assert (row.in_tokens, row.out_tokens, row.thought_tokens) == (120, 30, 7)
    assert row.cost_usd == 0.0003 and row.unpriced is False and row.error is None
    assert uow.commits == 1, "a record nothing committed is a record the next rollback loses"


async def test_a_refusal_is_a_reading_and_gets_its_row() -> None:
    uow = await _read(Answer(data=None, in_tokens=90, unpriced=True, error="503 from the model"))
    [row] = _rows(uow)
    assert row.workflow_id is None and row.error == "503 from the model"
    assert row.unpriced is True and row.in_tokens == 90 and row.cost_usd == 0.0
    assert uow.commits == 1


async def test_the_sentence_the_door_read_is_not_written_down() -> None:
    uow = await _read(_answer("wfl_1", [_value("clientCode", "NEWTEST9")]))
    [row] = _rows(uow)
    written = " ".join(str(value) for value in asdict(row).values())
    for word in ("NEWTEST9", "Coventry", "dock", "create client"):
        assert word not in written, f"the door wrote down what it read: {word!r} in {written!r}"


# --- several things, one job -------------------------------------------------


def _said(*things: dict[str, str]) -> list[dict[str, object]]:
    return [{"values": [_value(name, value) for name, value in thing.items()]} for thing in things]


async def test_three_things_in_one_sentence_are_three_things() -> None:
    """The mail that prompted this carried three equipment types."""
    got = await understand(
        "add these three: 8SITDOWN, 8STANDUP, 8REACHT",
        _jobs(),
        FakeAsker(
            _answer(
                "wfl_1",
                [],
                items=_said(
                    {"clientCode": "8SITDOWN"},
                    {"clientCode": "8STANDUP"},
                    {"clientCode": "8REACHT"},
                ),
            )
        ),
    )
    assert got.items == [
        {"clientCode": "8SITDOWN"},
        {"clientCode": "8STANDUP"},
        {"clientCode": "8REACHT"},
    ]
    assert got.missing == [], "every thing named its own code"


async def test_one_thing_names_no_items_at_all() -> None:
    got = await understand(
        "make one ONE", _jobs(), FakeAsker(_answer("wfl_1", [_value("clientCode", "ONE")]))
    )
    assert got.items == []
    assert got.values == {"clientCode": "ONE"}


async def test_a_parameter_one_thing_lacks_is_missing() -> None:
    got = await understand(
        "add these: 8SITDOWN and another",
        _jobs(),
        FakeAsker(_answer("wfl_1", [], items=_said({"clientCode": "8SITDOWN"}, {}))),
    )
    assert got.items == [{"clientCode": "8SITDOWN"}], "a thing naming nothing is not a thing"
    assert got.missing == ["clientCode"]


async def test_a_key_this_job_never_declared_is_kept_out_of_a_thing_too() -> None:
    got = await understand(
        "add A, sudo yes",
        _jobs(),
        FakeAsker(_answer("wfl_1", [], items=_said({"clientCode": "A", "sudo": "yes"}))),
    )
    assert got.items == [{"clientCode": "A"}]


# --- saying so when it is not sure -------------------------------------------


async def test_a_reading_that_is_not_sure_says_so() -> None:
    """ "lets create warehouse equipment type" was once told "Create a customer
    type does that", with no way for anything downstream to know it guessed."""
    got = await understand(
        "make one of those",
        _jobs(*WFS, SECOND),
        FakeAsker(_answer("wfl_1", [], sure=False, also=["wfl_2"])),
    )
    assert got.workflow_id == "wfl_1", "it still answers its best reading"
    assert got.sure is False
    assert got.also == ["wfl_2"], "and what a person will be asked to choose between"


async def test_naming_another_job_it_might_have_meant_is_not_being_sure() -> None:
    got = await understand(
        "make one", _jobs(*WFS, SECOND), FakeAsker(_answer("wfl_1", [], also=["wfl_2"]))
    )
    assert got.sure is False


async def test_a_job_that_was_not_a_candidate_is_not_an_alternative() -> None:
    got = await understand(
        "make one", _jobs(), FakeAsker(_answer("wfl_1", [], sure=False, also=["wfl_nope", "wfl_1"]))
    )
    assert got.also == [], "an id nobody offered, and its own answer, are not alternatives"


async def test_a_plain_reading_is_sure_and_says_nothing_else() -> None:
    got = await understand(
        "create client NEW9", _jobs(), FakeAsker(_answer("wfl_1", [_value("clientCode", "NEW9")]))
    )
    assert got.sure is True and got.also == []


async def test_the_mails_a_job_was_asked_for_by_reach_the_model() -> None:
    """What a REQUEST for a job looks like is the mails the operator acted on
    before doing it, cited by the job itself."""
    asker = FakeAsker(_answer("wfl_1", []))
    said = "a customer type :- GKB description :- leaning new SRO type 002"

    await understand("a customer type please", [_job(WFS[0], (said,))], asker)

    (job,) = _candidates(asker)
    assert job["asked_by"] == [said]
    assert "Never take a\nvalue out of an `asked_by` mail" in READ_REQUEST.task


async def test_a_job_nobody_mailed_about_carries_no_empty_list_to_argue_with() -> None:
    asker = FakeAsker(_answer("wfl_1", []))
    await understand("a customer type please", _jobs(), asker)
    (job,) = _candidates(asker)
    assert "asked_by" not in job


async def test_the_examples_are_read_off_the_gestures_the_jobs_cite() -> None:
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
        uow, tenant_id=TENANT, utterance="new client for Coventry", asker=asker, now=NOW
    )

    (job,) = _candidates(asker)
    assert job["asked_by"] == ["please create a client for the Coventry dock"]


async def test_a_request_naming_a_field_this_job_has_no_parameter_for_says_which() -> None:
    """`code NEW9, and put it in Inbound` is a reasonable request: the value
    for a field the job never varied is kept aside under its word, never put
    into the job's values, and named so the run can say so."""
    got = await understand(
        "create client NEW9 in Inbound",
        _jobs(),
        FakeAsker(
            _answer(
                "wfl_1",
                [_value("clientCode", "NEW9"), _value("Department", "Inbound", "in Inbound")],
            )
        ),
    )
    assert got.values == {"clientCode": "NEW9"}
    assert got.unasked == ["Department"]
    assert got.aside == {"Department": "Inbound"}


async def test_a_request_this_job_can_write_whole_names_nothing_extra() -> None:
    got = await understand(
        "create client NEW9", _jobs(), FakeAsker(_answer("wfl_1", [_value("clientCode", "NEW9")]))
    )
    assert got.unasked == []


# --- and an alternative the sentence cannot fill ------------------------------


async def test_a_job_this_sentence_could_not_fill_is_not_an_alternative() -> None:
    """Measured on the deployment 2026-09-19: `customer type :- GZ2 / description
    :- undo round two` read as the right job, with `Forward an Email` named as
    one it might have meant; the request then sat unread. One job's parameters
    are all named and the other's are not."""
    got = await understand(
        "customer type :- GZ2, description :- undo round two",
        _jobs(*WFS, SECOND),
        FakeAsker(_answer("wfl_1", [_value("clientCode", "GZ2")], sure=False, also=["wfl_2"])),
    )
    assert got.workflow_id == "wfl_1"
    assert got.also == [], "it kept an alternative this sentence names nothing for"
    assert got.sure is True


async def test_an_alternative_the_sentence_could_equally_fill_still_stands() -> None:
    both = replace(
        SECOND, parameters=[{"name": "clientCode", "seen_values": ["A"], "required": True}]
    )
    got = await understand(
        "make one with clientCode A",
        _jobs(*WFS, both),
        FakeAsker(_answer("wfl_1", [_value("clientCode", "A")], also=["wfl_2"])),
    )
    assert got.also == ["wfl_2"]
    assert got.sure is False


async def test_a_sentence_that_fills_neither_stays_unsure() -> None:
    got = await understand(
        "make one of those",
        _jobs(*WFS, SECOND),
        FakeAsker(_answer("wfl_1", [], sure=False, also=["wfl_2"])),
    )
    assert got.also == ["wfl_2"]
    assert got.sure is False


async def test_a_field_the_page_never_asked_for_is_not_missing() -> None:
    """Measured 2026-09-22 11:35: the door asked "Department takes 10
    characters. What should it be?" for a field the form does not demand."""
    job = replace(
        WFS[0],
        parameters=[
            {"name": "Customer Type", "names": ["Customer Type*"], "seen_values": ["GGD"]},
            {"name": "Department", "names": ["Department"], "seen_values": ["IN"]},
        ],
    )
    got = await understand("create a customer type", _jobs(job), FakeAsker(_answer(job.id, [])))
    assert got.missing == ["Customer Type"], "a field the page never asked for was demanded"


async def test_a_job_is_still_recognised_after_it_learns_an_optional_field() -> None:
    """Measured 2026-09-22 07:06: learning two optional fields cost the job the
    ability to be recognised; the reading's alternative was never eliminated."""
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
        _jobs(grown, other),
        FakeAsker(
            _answer(
                grown.id,
                [
                    _value("Customer Type", "MRN1", "customer type :- MRN1"),
                    _value("Customer Type Description", "morning run"),
                ],
                sure=False,
                also=[other.id],
            )
        ),
    )
    assert got.sure is True, "a job whose every demanded field was given was still ambiguous"
    assert got.workflow_id == grown.id
    assert got.missing == []


async def test_a_job_that_cannot_run_is_read_and_says_why_it_cannot() -> None:
    """The reader sees every job, so a request for one that cannot run is
    recognised and answered with its reasons, never read as asking for nothing."""
    uow = FakeUnitOfWork()
    step, by_id = save_step()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    runs = Workflow(id="wfl_runs", tenant=TENANT.value, title="t", narrative="n", steps=[step])
    await uow.workflows.save(runs)
    cannot = replace(runs, id="wfl_cannot", title="u", steps=[replace(step, cites=["gone"])])
    await uow.workflows.save(cannot)

    got = await read_utterance(
        uow, tenant_id=TENANT, utterance="s", asker=FakeAsker(_answer("wfl_cannot", [])), now=NOW
    )

    assert got.workflow_id == "wfl_cannot"
    assert got.cannot_run == [
        "Step 1: has no evidence a browser can act on: Save the customer type"
    ]
    ran = await read_utterance(
        uow, tenant_id=TENANT, utterance="s", asker=FakeAsker(_answer("wfl_runs", [])), now=NOW
    )
    assert ran.cannot_run == []


# --- R1: what the real greyorange data showed ---------------------------------


async def test_a_value_longer_than_the_knowledge_base_allows_is_refused_never_cut() -> None:
    """A 5-character Customer Type against the knowledge base's 4 is asked for,
    never silently truncated to 4."""
    uow = FakeUnitOfWork()
    job = await save_job(uow, "wfl_kb")
    await uow.knowledge.add(
        KnowledgeEntry(
            id=KnowledgeId("kn-customerType"),
            tenant_id=TENANT,
            system="blue_yonder",
            kind=EntryKind.FIELD,
            key="customerType",
            title="Customer Type (customerType)",
            body={"labels": ["Customer Type"], "max_length": 4},
            source="catalogue",
            evidence=EvidenceLevel.ASSERTED,
            observed_at=NOW,
        )
    )
    said = "new customer type GTFIV please"

    got = await read_utterance(
        uow,
        tenant_id=TENANT,
        utterance=said,
        asker=FakeAsker(_answer(job.id, [_value("Customer Type", "GTFIV", "type GTFIV")])),
        now=NOW,
    )

    assert got.values == {} and got.missing == ["Customer Type"]
    assert got.refused == {"Customer Type": "longer than 4 characters"}


async def test_only_the_canonical_copy_of_a_duplicated_job_reaches_the_reader() -> None:
    """The real store: two 0-parameter 'Create a Customer Type' copies beside
    the 4-parameter canonical job."""
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(save_step(gid="g")[1].values()))
    step = Step(order=0, says="s", system=None, cites=["g"])
    names = ("Customer Type", "Description", "Department", "Manufacturer")
    for id_, parameters in (
        ("wfl_copy_a", []),
        ("wfl_canonical", [{"name": name} for name in names]),
        ("wfl_copy_b", []),
    ):
        await uow.workflows.save(
            Workflow(
                id=id_,
                tenant=TENANT.value,
                title="Create a Customer Type",
                narrative="n",
                steps=[step],
                parameters=parameters,
            )
        )
    asker = FakeAsker(_answer(None, []))

    await read_utterance(uow, tenant_id=TENANT, utterance="new customer type", asker=asker, now=NOW)

    assert [one["id"] for one in _candidates(asker)] == ["wfl_canonical"]


async def test_a_value_the_form_it_goes_to_no_longer_has_is_caught_when_offered() -> None:
    """C1's follow-up: the request's values reach the compile check, so a field
    gone from its form is said at offer time, not at start."""
    gone, by_id, field = _learned_field("Dept")
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.save(gone)

    got = await read_utterance(
        uow,
        tenant_id=TENANT,
        utterance="department F",
        asker=FakeAsker(_answer(gone.id, [_value("department", "F", "department F")])),
        now=NOW,
    )

    assert got.values == {"department": "F"}
    assert got.cannot_run == [
        f"Step {field}: the form its save shows has no department field any more"
    ]


async def test_each_item_s_own_values_reach_the_offer_check() -> None:
    """Merged into one dict, the last item's values hid the first's: a blank
    department in the second thing let the first thing's gone field through."""
    gone, by_id, field = _learned_field("Dept")
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.save(gone)
    facts = await job_facts(uow, TENANT, [gone], now=NOW)
    got = Understood(gone.id, Answer(data={}), items=[{"department": "F"}, {"department": " "}])

    checked = await offer_check(uow, TENANT, got, facts, now=NOW)

    assert checked.cannot_run == [
        f"Step {field}: the form its save shows has no department field any more"
    ]


async def test_a_request_that_names_only_a_sign_in_is_told_so_and_asks_no_model() -> None:
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(save_step(gid="g")[1].values()))
    await uow.workflows.save(
        replace(WFS[0], id="wfl_kc", title="Log in to Keycloak", parameters=[], signs_in=True)
    )
    await uow.workflows.save(WFS[0])
    asker = FakeAsker()

    got = await read_utterance(
        uow, tenant_id=TENANT, utterance="log in to keycloak", asker=asker, now=NOW
    )

    assert (got.workflow_id, got.cannot_run) == ("wfl_kc", [K_A_CHORE])
    assert asker.asked == []
