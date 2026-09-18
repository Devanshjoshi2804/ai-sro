"""Chat: what was asked, what it was taken to mean, and what was not done."""

from __future__ import annotations

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.understand import Understood
from sro.application.context import RequestContext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import NEEDS
from sro.domain.chat.thread import Message, MessageId, Speaker, ThreadId
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import SkillId
from sro.domain.shared.prices import Answer
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _taught(uow: FakeUnitOfWork) -> None:
    skill = f.skill(
        id=SkillId("skill-adjust"),
        name="Inventory Adjust",
        objective_key=f.objective(objective_type="adjust", entity_type="inventory", facility="SG"),
        versions=0,
    )
    version = f.skill_version()
    version.describe(summary="Adjust inventory at SG.", when_to_use="After a stock check.")
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
    await uow.skills.add(skill)


def _chat(uow: FakeUnitOfWork) -> tuple[StartThread, Converse]:
    ids, clock = FakeIdFactory(), FakeClock()
    resolver = ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())))
    return StartThread(uow, clock, ids), Converse(uow, resolver, clock, ids)


async def test_a_thread_keeps_what_was_asked_and_what_was_decided() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(
        CTX, thread_id=thread.id, text="adjust inventory at SG", parameters={"shipment_id": "1"}
    )

    operator, assistant = thread.messages
    assert operator.speaker is Speaker.OPERATOR and operator.text == "adjust inventory at SG"
    assert assistant.speaker is Speaker.ASSISTANT
    assert "Inventory Adjust" in assistant.text
    assert assistant.decision["matched_skill_id"] == "skill-adjust"
    assert assistant.decision["why"], "the audit trail reads the decision, not the prose"


async def test_saying_something_performs_nothing() -> None:
    """A match is an offer. Starting it is the operator's next request, which is
    what makes their confirmation the authorisation an assisted run records."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert uow.runs.rows == {}


async def test_what_is_still_needed_is_asked_for_in_the_reply() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert "I need shipment_id" in thread.messages[-1].text
    assert thread.messages[-1].decision["missing_parameters"] == ["shipment_id"]


async def test_an_unknown_task_is_answered_with_a_way_forward() -> None:
    uow = FakeUnitOfWork()
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="do something else entirely")

    assert "Teach me" in thread.messages[-1].text
    assert thread.messages[-1].decision["matched_skill_id"] is None


async def test_a_thread_is_titled_by_what_was_asked_first() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")
    thread = await converse.execute(CTX, thread_id=thread.id, text="and again tomorrow")

    assert thread.title == "adjust inventory at SG"
    assert len(thread.messages) == 4, "nothing is edited; everything is appended"


def test_a_read_is_answered_from_the_system_not_from_the_recording() -> None:
    """What the demonstration saw is a description of that afternoon.

    Showing it as though it were current is how a console says there are sixteen
    when there are twenty-three.
    """
    from sro.application.intent.match import writes

    reading = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="GET", url=Template("https://wms.test/data/x"), body=None
                ),
            ),
        ),
        parameters=(),
    )

    assert not writes(reading)


def test_a_write_still_waits_to_be_told_to_go() -> None:
    """Running it because somebody described it would make the confirmation an
    assisted run records meaningless."""
    from sro.application.intent.match import writes

    writing = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="POST", url=Template("https://wms.test/data/x"), body=None
                ),
            ),
        ),
        parameters=(),
    )

    assert writes(writing)


async def test_a_run_message_says_it_is_a_run_and_its_result_says_it_is_a_result() -> None:
    """Two surfaces draw these -- the panel and the console -- and they draw
    different shapes for a run in progress and the record of what it made. The
    kind is what tells them apart; without it each has to infer it from which
    fields happen to be present, and they infer differently."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)
    skill = await uow.skills.get(f.TENANT, SkillId("skill-adjust"))

    thread = await converse.started(CTX, thread_id=thread.id, run_id=RunId("run-1"), skill=skill)

    assert thread.messages[-1].decision["kind"] == "run"


async def test_a_note_to_a_run_is_kept_and_resolves_nothing() -> None:
    """Saying something to a run that is happening is not asking for a task.
    Resolving it would match some other skill and offer to run that instead,
    which is the opposite of what somebody watching a run means by typing."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(
        CTX, thread_id=thread.id, text="use the north yard address", run_id=RunId("run-1")
    )

    [only] = thread.messages
    assert only.speaker is Speaker.OPERATOR
    assert only.text == "use the north yard address"
    assert only.decision == {"kind": "note", "run_id": "run-1"}


# --- the rig's jobs, asked before the taught skills ---------------------------


class _PlacesTheJob(ReadChat):
    """The rig's reader, answering about one job and never spending a model.

    A subclass rather than a fake handed in: what is under test is that
    `Converse` asks THIS door first and, where it answers, stops -- and a
    stand-in of a different type would pass even if the wiring had it the wrong
    way round.
    """

    def __init__(self, placed: Understood | None, *, raises: bool = False) -> None:
        self.placed = placed
        self.raises = raises
        self.asked: list[str] = []

    async def execute(self, ctx: RequestContext, *, utterance: str) -> Understood:
        self.asked.append(utterance)
        if self.raises:
            raise RuntimeError("no model configured")
        assert self.placed is not None
        return self.placed


def _understood(
    workflow_id: str | None,
    *,
    values: dict[str, str] | None = None,
    missing: list[str] | None = None,
    items: list[dict[str, str]] | None = None,
    sure: bool = True,
    also: list[str] | None = None,
) -> Understood:
    return Understood(
        workflow_id=workflow_id,
        answer=Answer(data={}),
        values=dict(values or {}),
        missing=list(missing or []),
        sure=sure,
        also=list(also or []),
        items=[dict(one) for one in (items or [])],
    )


async def _with_a_job(
    uow: FakeUnitOfWork,
    placed: Understood | None,
    *,
    raises: bool = False,
    can_gather: bool = False,
) -> Converse:
    await uow.workflows.save(
        Workflow(
            id="wfl_1",
            tenant=f.TENANT.value,
            title="Create a Warehouse Equipment Type",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=["g"])],
        )
    )
    ids, clock = FakeIdFactory(), FakeClock()
    resolver = ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())))
    reads = _PlacesTheJob(placed, raises=raises)
    return Converse(uow, resolver, clock, ids, reads_jobs=reads, can_gather=can_gather)


async def test_a_sentence_about_a_mined_job_is_answered_by_the_rig() -> None:
    """The wrong answer this exists to end.

    An operator typed "lets create warehouse equipment type" at a browser whose
    rig holds exactly that job, and was told "Create a customer type does that.
    I still need long_description." The resolver ranks the tenant's taught
    SKILLS -- seven of them, none about equipment types -- so it answered with
    the nearest thing it had, and the right job was in the rig all along.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse = await _with_a_job(uow, _understood("wfl_1", missing=["Voice Code"]))
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="create equipment type")

    last = said.messages[-1]
    assert "Create a Warehouse Equipment Type" in last.text
    assert "Voice Code" in last.text, "what it still needs is what the operator has to answer"
    assert last.decision is not None
    assert last.decision["kind"] == "job" and last.decision["workflow_id"] == "wfl_1"


async def test_what_a_press_needs_is_in_the_decision() -> None:
    """The browser builds its offer from this rather than reading the sentence
    a second time: two readings are two model calls and two chances to
    disagree."""
    uow = FakeUnitOfWork()
    converse = await _with_a_job(
        uow,
        _understood("wfl_1", values={"site": "SG"}, items=[{"code": "A"}, {"code": "B"}]),
    )
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="add these two")

    decision = said.messages[-1].decision
    assert decision is not None
    assert decision["values"] == {"site": "SG"}
    assert decision["items"] == [{"code": "A"}, {"code": "B"}]
    assert "for 2 things" in said.messages[-1].text


async def test_a_sentence_the_rig_cannot_place_still_reaches_the_skills() -> None:
    """The conversation the console has always had. A job the rig does not hold
    is not a sentence nobody can answer."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse = await _with_a_job(uow, _understood(None))
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert said.messages[-1].decision is not None
    assert "kind" not in said.messages[-1].decision, "the skills' own decision, not the rig's"


async def test_a_rig_that_refuses_is_not_a_conversation_that_stops() -> None:
    """No model configured, the day's cap spent, a door that raised. The
    conversation happens the way it did before the rig was asked at all."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse = await _with_a_job(uow, None, raises=True)
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert said.messages[-1].speaker is Speaker.ASSISTANT
    assert said.messages[-1].text


async def test_a_reading_that_is_not_sure_asks_which_job_rather_than_starting_one() -> None:
    """One wrong record is a nuisance; the same guess against a list of twenty
    is twenty wrong records in a warehouse, and the cost of asking is one
    sentence."""
    uow = FakeUnitOfWork()
    await uow.workflows.save(
        Workflow(
            id="wfl_2",
            tenant=f.TENANT.value,
            title="Create a Customer Type",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=["g"])],
        )
    )
    converse = await _with_a_job(uow, _understood("wfl_1", sure=False, also=["wfl_2"]))
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="make one of those")

    last = said.messages[-1]
    assert "Did you mean" in last.text
    assert "Create a Warehouse Equipment Type" in last.text
    assert "Create a Customer Type" in last.text, "the other one it was choosing between"
    assert last.decision is not None
    assert last.decision["kind"] == "which_job", (
        "a decision the browser cannot act on must not look like one it can"
    )
    assert "workflow_id" not in last.decision, "there is nothing here to press"


async def test_a_value_nobody_typed_is_offered_as_a_look_rather_than_a_demand() -> None:
    """What the card says when the run can go and find it.

    Seen on the deployment 2026-09-16: the panel offered `Create a Customer
    Type` with four empty boxes -- two of them `customertype-customerType` and
    `customertype-longDescription`, the body keys a form posts, which nobody
    has ever typed -- for values sitting in the mail that asked for the job.
    The run could read that mail by then; the sentence in front of the person
    still demanded they type it.
    """
    uow = FakeUnitOfWork()
    converse = await _with_a_job(
        uow, _understood("wfl_1", missing=["Customer Type"]), can_gather=True
    )
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="create a customer type")

    last = said.messages[-1]
    assert "look in your mail for Customer Type" in last.text
    # Still sayable: a person who types one has said what they want, and the
    # run merges what it finds UNDER what it was given.
    assert "type them here" in last.text
    assert last.decision is not None and last.decision["can_find"] is True


async def test_a_deployment_that_cannot_look_still_asks_for_the_value() -> None:
    """The promise is only made where it can be kept. A deployment with no
    connector -- or no model -- would otherwise say it will read a mailbox it
    cannot reach, and the run would refuse a step later with nobody watching."""
    uow = FakeUnitOfWork()
    converse = await _with_a_job(uow, _understood("wfl_1", missing=["Customer Type"]))
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)

    said = await converse.execute(CTX, thread_id=thread.id, text="create a customer type")

    assert "I still need Customer Type" in said.messages[-1].text
    assert said.messages[-1].decision["can_find"] is False


# --- a run that came up short asks, and the answer is the next thing said -----


async def _asked(uow: FakeUnitOfWork, missing: list[str]) -> tuple[Converse, ThreadId]:
    """A thread where a run has asked for what it could not find.

    Written the way `StartWorkflowRun._ask_for_values` writes it -- the run is
    over by then, and what it left behind is this message.
    """
    converse = await _with_a_job(uow, None)
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)
    thread.say(
        Message(
            id=MessageId("msg_asked"),
            speaker=Speaker.ASSISTANT,
            text="I could not find them. What should Customer Type be?",
            said_at=FakeClock().now(),
            decision={
                "kind": NEEDS,
                "workflow_id": "wfl_1",
                "title": "Create a Customer Type",
                "values": {},
                "missing": missing,
                "items": [],
                "watched": True,
            },
        )
    )
    await uow.threads.save(thread)
    return converse, thread.id


async def test_the_answer_to_a_question_is_taken_as_the_answer() -> None:
    """ "GPP" placed against the jobs is a sentence about nothing. Against the
    question that was actually asked it is the value, and reading it any other
    way is a system that asks somebody something and then ignores what they
    say."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type", "longDescription"])

    said = await converse.execute(CTX, thread_id=thread_id, text="GPP")

    last = said.messages[-1]
    assert last.text == "What should longDescription be?", "it did not ask the next question"
    assert last.decision == {
        "kind": NEEDS,
        "workflow_id": "wfl_1",
        "title": "Create a Customer Type",
        # What is established so far rides along, so the answer survives a
        # restart and a second browser reading the thread sees the same state.
        "values": {"Customer Type": "GPP"},
        "items": [],
        "missing": ["longDescription"],
        # What each box holds, so the next question can say why it is asking
        # and an answer that still will not fit can be refused rather than
        # carried into the form. Empty here: nothing has measured these.
        "limits": {},
        # Where the run that asked had got to. Zero here: this question was
        # asked before any step ran.
        "from_step": 0,
        "watched": True,
    }


async def test_the_last_answer_runs_the_job_without_asking_again() -> None:
    """They pressed yes before any of this. Asking for the same permission a
    second time is how a system teaches somebody to stop reading what it
    asks."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])

    said = await converse.execute(CTX, thread_id=thread_id, text="GPP")

    last = said.messages[-1]
    assert last.decision is not None
    assert last.decision["kind"] == "job", last.decision
    assert last.decision["missing"] == []
    assert last.decision["values"] == {"Customer Type": "GPP"}
    assert last.decision["resume"] is True, "the panel would have asked for a second press"


async def test_calling_it_off_is_not_a_value() -> None:
    """Without this, "no" becomes the customer type."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])

    said = await converse.execute(CTX, thread_id=thread_id, text="no")

    last = said.messages[-1]
    assert "Dropped" in last.text
    assert last.decision is not None and last.decision["kind"] != NEEDS, (
        "the conversation went on waiting for a value it had been told to forget"
    )


# --- "say the word", and the word -------------------------------------------


async def _offered(
    uow: FakeUnitOfWork, *, can_gather: bool, missing: list[str]
) -> tuple[Converse, ThreadId]:
    """A thread where the rig has offered a job and said it would run it."""
    converse = await _with_a_job(uow, None, can_gather=can_gather)
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)
    thread.say(
        Message(
            id=MessageId("msg_offer"),
            speaker=Speaker.ASSISTANT,
            text="Create a Customer Type does that — say the word and I will run it.",
            said_at=FakeClock().now(),
            decision={
                "kind": "job",
                "workflow_id": "wfl_1",
                "title": "Create a Customer Type",
                "values": {},
                "items": [],
                "missing": missing,
                "can_find": can_gather,
            },
        )
    )
    await uow.threads.save(thread)
    return converse, thread.id


async def test_saying_the_word_starts_the_job_that_was_just_offered() -> None:
    """Measured on the deployment, 2026-09-17 at 03:17.

    The assistant said "say the word and I will run it", the operator said
    "pls do", and the reply was "Nothing has been taught for that" -- the
    sentence went to the resolver, which ranks this tenant's taught SKILLS and
    had never heard of it, because nothing was holding on to what had just been
    offered. A system that asks for a word and then does not know the word is
    the same fault as the boxes on the card: it asks, and ignores the answer.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _offered(uow, can_gather=True, missing=["Customer Type"])

    said = await converse.execute(CTX, thread_id=thread_id, text="pls do")

    last = said.messages[-1]
    assert last.decision is not None
    assert last.decision["kind"] == "job", last.decision
    assert last.decision["resume"] is True, "the panel would have drawn another offer to press"
    # The run goes and looks, which is what the card's own Yes does. A
    # conversation that demanded the values the card would not is two answers
    # to one question.
    assert last.decision["missing"] == []


async def test_a_yes_where_nothing_can_go_looking_asks_for_the_value() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _offered(uow, can_gather=False, missing=["Customer Type"])

    said = await converse.execute(CTX, thread_id=thread_id, text="go ahead")

    last = said.messages[-1]
    assert last.decision is not None
    assert last.decision["kind"] == NEEDS
    assert last.text == "What should Customer Type be?"


async def test_a_sentence_that_is_not_a_yes_is_still_a_sentence() -> None:
    """ "do it for the red ones instead" is a new request, not agreement. The
    match is the whole answer, lowercased, the way `let_go` is -- a system that
    took any sentence containing "do it" as a yes would start the job it was
    just asked to change."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _offered(uow, can_gather=True, missing=[])

    said = await converse.execute(CTX, thread_id=thread_id, text="do it for the other site instead")

    last = said.messages[-1]
    assert not (last.decision or {}).get("resume"), last.decision


async def _asked_with_limits(
    uow: FakeUnitOfWork, missing: list[str], limits: dict[str, int]
) -> tuple[Converse, ThreadId]:
    """A thread where the question knows what the box holds."""
    converse = await _with_a_job(uow, None)
    thread = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)
    thread.say(
        Message(
            id=MessageId("msg_asked"),
            speaker=Speaker.ASSISTANT,
            text="Customer Type takes 4 characters. What should it be?",
            said_at=FakeClock().now(),
            decision={
                "kind": NEEDS,
                "workflow_id": "wfl_1",
                "title": "Create a Customer Type",
                "values": {},
                "missing": missing,
                "items": [],
                "limits": limits,
                "watched": True,
            },
        )
    )
    await uow.threads.save(thread)
    return converse, thread.id


async def test_an_answer_the_box_will_not_hold_is_asked_about_again() -> None:
    """The loop the card's box used to be.

    A person answers with ten characters for a field that takes four. Accepting
    it means a run that stops in front of the form, which is the whole of what
    asking here replaces -- they are at the keyboard NOW, and one more sentence
    is cheaper than the job.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked_with_limits(uow, ["Customer Type"], {"Customer Type": 4})

    said = await converse.execute(CTX, thread_id=thread_id, text="NEWSROTEST")

    last = said.messages[-1]
    # It says what was wrong, rather than repeating itself: a question asked
    # twice in the same words reads as a system that ignored them.
    assert "10 characters" in last.text, last.text
    assert "takes 4" in last.text, last.text
    assert last.decision is not None
    # Nothing was accepted, so the same value is still wanted.
    assert last.decision["missing"] == ["Customer Type"]
    assert last.decision["values"] == {}
    assert last.decision["limits"] == {"Customer Type": 4}


async def test_an_answer_that_fits_ends_the_asking_and_starts_the_job() -> None:
    """And the run starts on the press they already gave, which is the point of
    doing this in the conversation rather than on the card."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked_with_limits(uow, ["Customer Type"], {"Customer Type": 4})

    said = await converse.execute(CTX, thread_id=thread_id, text="NSRO")

    last = said.messages[-1]
    assert last.decision is not None
    assert last.decision["kind"] == "job", last.text
    assert last.decision["values"] == {"Customer Type": "NSRO"}
    # The press arriving late, not a second one to ask for.
    assert last.decision["resume"] is True


async def test_the_question_says_what_the_box_holds_when_anything_knows() -> None:
    """Asked without it, a person sends the same value back -- nothing has told
    them the field takes four, because the browser truncates in silence."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked_with_limits(
        uow, ["Customer Type", "longDescription"], {"longDescription": 28}
    )

    said = await converse.execute(CTX, thread_id=thread_id, text="GPP")

    assert said.messages[-1].text == "longDescription takes 28 characters. What should it be?"
