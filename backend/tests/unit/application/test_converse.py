"""Chat: what was asked, what it was taken to mean, and what was not done."""

from __future__ import annotations

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.reading_an_answer import Read
from sro.application.chat.understand import Understood
from sro.application.context import RequestContext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import NEEDS, pending_job
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


class _Reads:
    """A reading of whether a sentence answers the standing question.

    Takes the verdict rather than computing one: what is under test is what
    this door DOES with each verdict, and a fake that decided for itself would
    be a second implementation of the thing being tested.
    """

    def __init__(self, answers: bool, value: str = "", about: str = "the_wait") -> None:
        self._answers = answers
        self._value = value
        self._about = about
        self.asked: list[str] = []

    async def execute(self, _ctx: object, _pending: object, said: str) -> Read:
        self.asked.append(said)
        return Read(
            answers=self._answers,
            value=self._value or said,
            why="a fake",
            about="" if self._answers else self._about,
        )


async def test_a_sentence_that_is_not_an_answer_does_not_become_the_value() -> None:
    """The one this was built for.

    Measured on the deployment 2026-09-18. A question stood asking for
    `Customer Type`. The operator had already sent the answer by MAIL and was
    watching for it to land, so they typed `has reply arrived` into the panel
    to ask this system a question. It was taken as the value, a run started one
    millisecond later, and `HAS REPLY ARRIVED` was typed into a four-character
    box in a live warehouse system.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    converse._answers = _Reads(answers=False)  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="has reply arrived")

    last = said.messages[-1]
    assert last.decision is None or last.decision.get("kind") != "job", (
        "a sentence nobody meant as an answer started a run"
    )
    assert "has reply arrived" not in str(last.decision or {}), (
        "it was written down as the value anyway"
    )
    # And the question is still standing, because nothing consumed it: the
    # answer, when it comes, has something to land in.
    assert pending_job(said.messages) is not None, "the question was swallowed"


async def test_a_question_about_the_waiting_is_answered_about_the_waiting() -> None:
    """ "check now" went to the task RESOLVER -- a door for "what work do you
    want done" -- so it planned some, and answered two words about a mailbox
    with a wall of text about Check In and Check Out screens nobody had
    mentioned. Seen on the deployment 2026-09-18 at 16:42.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    # A mail went out about this one, which is what is being waited on.
    async with uow as opened:
        thread = await opened.threads.get(f.TENANT, thread_id)
        thread.say(
            Message(
                id=MessageId("msg_sent"),
                speaker=Speaker.SYSTEM,
                text="Asked asker@example.com. I will carry on when they reply.",
                said_at=FakeClock().now(),
                decision={"kind": "mail_sent", "to": "asker@example.com", "sent": True},
            )
        )
        await opened.threads.save(thread)
        before = len(thread.messages)
    converse._answers = _Reads(answers=False, about="the_wait")  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="check now")

    last = said.messages[-1]
    # What they actually asked about, and then the question again.
    assert last.text == (
        "Nothing back from asker@example.com yet. Customer Type takes 4 characters. "
        "What should it be?"
    ) or last.text.startswith("Nothing back from asker@example.com yet."), last.text
    # And what they said is in the thread, because they said it.
    assert any(m.speaker == Speaker.OPERATOR and m.text == "check now" for m in said.messages)
    # Two messages and no more: what they said, and the answer. A third would
    # be the resolver's -- the door that planned a Check In screen out of two
    # words about a mailbox.
    assert len(said.messages) - before == 2, [m.text for m in said.messages[before:]]
    # The question is still there to answer.
    assert pending_job(said.messages) is not None


async def test_asking_for_a_different_job_is_still_heard() -> None:
    """The gate is about answers, not about the person. Somebody who says
    "create an equipment type instead" has asked for work, and a door that
    replied "I am still waiting on Customer Type" to that would be the old
    swallowing with better manners."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    converse._answers = _Reads(answers=False, about="another_task")  # type: ignore[assignment]

    said = await converse.execute(
        CTX, thread_id=thread_id, text="create a warehouse equipment type instead"
    )

    # Handled as the request it is -- and the question is still standing under
    # it, because nothing answered it.
    assert len(said.messages) >= 3
    assert pending_job(said.messages) is not None


async def test_a_refused_sentence_is_told_how_to_be_taken_at_its_word() -> None:
    """A reading told to refuse when it is unsure is the right default and it
    leaves a loop nobody can get out of: the operator types a real value, is
    told "I am still waiting on this one", types it again and is refused
    again. `question` already names that loop as the thing this must not be,
    for the length case. This is the same exit for the reading case.

    Measured on the deployment 2026-09-19, thread thr_163bf91b: asked what
    Address should be, the operator typed `testing for new purpose` and was
    told only that the wait continued.
    """
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    converse._answers = _Reads(answers=False)  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="testing for new purpose")

    assert 'say "Customer Type: ..." and I will take it' in said.messages[-1].text, said.messages[
        -1
    ].text


async def test_a_value_the_person_named_themselves_is_taken_without_a_reading() -> None:
    """And the exit has to work, which means going nowhere near the thing that
    refused them. A way out that is itself read by the reading is not one."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    reads = _Reads(answers=False)
    converse._answers = reads  # type: ignore[assignment]

    said = await converse.execute(
        CTX, thread_id=thread_id, text="Customer Type: testing for new purpose"
    )

    assert reads.asked == [], "the way out of the loop went through the thing being got out of"
    last = said.messages[-1]
    assert last.decision is not None and last.decision["kind"] == "job"
    # The value, not the sentence that named it.
    assert last.decision["values"] == {"Customer Type": "testing for new purpose"}


async def test_a_sentence_that_is_an_answer_still_is() -> None:
    """The reading is a gate, not a wall. What it says answers, answers."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    reads = _Reads(answers=True, value="S057")
    converse._answers = reads  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="the code is S057")

    last = said.messages[-1]
    assert last.decision is not None and last.decision["kind"] == "job"
    # The VALUE the reading pulled out, not the sentence around it. A form
    # typed with "the code is S057" is a wrong record with a reason.
    assert last.decision["values"] == {"Customer Type": "S057"}


async def test_letting_go_is_never_handed_to_a_reading() -> None:
    """ "No" ends the question. A reading asked whether "no" answers "what
    should Customer Type be" has been given a question with no good answer,
    and the one word a person uses to get out of a loop must not depend on how
    it is read."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, ["Customer Type"])
    reads = _Reads(answers=False)
    converse._answers = reads  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="no")

    assert reads.asked == [], "the way out of the loop went through a model"
    assert said.messages[-1].text == "Dropped Create a Customer Type."


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
        # And which outside conversation it answers to, so the run an answer
        # starts is findable by a reply. Empty: nothing asked for this by mail.
        "mail_thread": "",
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


class _Plans:
    """A lookup planner that answers with one ready plan, or none."""

    def __init__(self, ready: bool = True) -> None:
        self._ready = ready
        self.asked: list[str] = []

    async def execute(self, _ctx: object, *, question: str, system: str | None = None) -> object:
        from sro.application.lookup.plan_lookups import Planned
        from sro.domain.lookup.plan import Lookup, Plan

        self.asked.append(question)
        looks = (
            (Lookup(system="WM", how="call", target="/data/WM/wm/customerTypes"),)
            if self._ready
            else ()
        )
        return Planned(Plan(question=question, lookups=looks))


class _Runs:
    """A browser that answers the plan, or does not."""

    def __init__(self, ok: bool = True, detail: str = "") -> None:
        self.focus: list[bool] = []
        self.within: list[float] = []
        self._ok = ok
        self._detail = detail

    async def execute(
        self,
        _ctx: object,
        *,
        plan: object,
        allow_focus: bool = False,
        within: float = 45.0,
        **_rest: object,
    ) -> object:
        import json as _json

        from sro.application.lookup.run_lookups import Answers, Looked

        self.focus.append(allow_focus)
        self.within.append(within)
        if not self._ok:
            return Answers(
                plan=plan,
                looked=(
                    Looked(
                        lookup=plan.lookups[0],
                        ok=False,
                        detail=self._detail,
                    ),
                ),
            )
        body = _json.dumps(
            {"data": [{"customerType": "KKYT", "longDescription": "my sro is best"}]}
        )
        return Answers(
            plan=plan,
            looked=(
                Looked(
                    lookup=plan.lookups[0],
                    ok=True,
                    url="https://wms.example/data/WM/wm/customerTypes",
                    answer={"status": 200, "body": body},
                ),
            ),
        )


async def test_a_question_nothing_was_taught_for_goes_to_the_lookup_door() -> None:
    """Measured on the deployment 2026-09-21. Asked "is there a customer type
    called KKYT", three doors answered one sentence:

        18:30:26  POST /v1/lookups             3601ms
        18:30:35  POST /v1/threads/../messages 7691ms  <- the screen walk
        18:30:43  POST /v1/ask                 6567ms  <- the answer

    and the wrong one arrived first. This door replied "Nobody has
    demonstrated reading that, so I will work it out on the screen" with five
    screens to open, while the lookup door planned
    `call /data/WM/wm/customerTypes`, got 200, and found KKYT.
    """
    uow = FakeUnitOfWork()
    converse, thread_id = await _asked(uow, [])
    plans, runs = _Plans(), _Runs()
    converse._plan_lookups = plans  # type: ignore[assignment]
    converse._run_lookups = runs  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="is there a customer type KKYT")

    assert plans.asked == ["is there a customer type KKYT"]
    last = said.messages[-1]
    assert last.decision is not None and last.decision["kind"] == "looked"
    answers = last.decision["answers"]
    assert isinstance(answers, list)
    [answer] = answers
    assert answer["target"] == "/data/WM/wm/customerTypes"
    assert "KKYT" in str(answer["body"])
    assert "screen" not in last.text.lower(), last.text


async def test_a_question_never_takes_the_screen_somebody_is_working_on() -> None:
    """`focus_not_permitted` is the refusal this path exists to stop meeting.
    A question is not a reason to navigate the tab in front of an operator."""
    uow = FakeUnitOfWork()
    converse, thread_id = await _asked(uow, [])
    runs = _Runs()
    converse._plan_lookups = _Plans()  # type: ignore[assignment]
    converse._run_lookups = runs  # type: ignore[assignment]

    await converse.execute(CTX, thread_id=thread_id, text="is there a customer type KKYT")

    assert runs.focus == [False]


async def test_a_conversation_does_not_wait_on_a_browser_for_a_minute() -> None:
    """A reply in a panel is a turn in a conversation, and a turn that takes a
    minute has stopped being one.

    Measured on the deployment 2026-09-21, request `req_10d3ff9b`: the
    browser's socket dropped twice inside one request, a command waited out
    the lookup door's full 45 seconds, and the reply took 67459ms. Routing the
    conversation through that door is what made a thread reply wait on a
    browser at all.
    """
    from sro.application.lookup.run_lookups import K_DEADLINE_S, K_WHILE_TALKING

    uow = FakeUnitOfWork()
    converse, thread_id = await _asked(uow, [])
    runs = _Runs()
    converse._plan_lookups = _Plans()  # type: ignore[assignment]
    converse._run_lookups = runs  # type: ignore[assignment]

    await converse.execute(CTX, thread_id=thread_id, text="is there a customer type KKYT")

    assert runs.within == [K_WHILE_TALKING]
    assert K_WHILE_TALKING < K_DEADLINE_S, "a conversation waits as long as a lookup does"


async def test_a_browser_that_never_answered_is_said_in_words_a_person_can_act_on() -> None:
    """ "I could not read that. timeout" is a sentence about this system's
    plumbing. The person reading it can see their own browser."""
    uow = FakeUnitOfWork()
    converse, thread_id = await _asked(uow, [])
    converse._plan_lookups = _Plans()  # type: ignore[assignment]
    converse._run_lookups = _Runs(ok=False, detail="timeout after 10000ms")  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="is there a customer type KKYT")

    assert "could not reach your browser" in said.messages[-1].text
    assert "timeout" not in said.messages[-1].text


async def test_a_browser_that_refused_still_says_what_it_refused_with() -> None:
    """A browser that said no is a different problem from one that said
    nothing, and flattening them throws away the one thing that says which."""
    uow = FakeUnitOfWork()
    converse, thread_id = await _asked(uow, [])
    converse._plan_lookups = _Plans()  # type: ignore[assignment]
    converse._run_lookups = _Runs(ok=False, detail="no tab is open on that system")  # type: ignore[assignment]

    said = await converse.execute(CTX, thread_id=thread_id, text="is there a customer type KKYT")

    assert "no tab is open on that system" in said.messages[-1].text


async def test_a_sentence_that_asks_for_work_is_not_looked_up() -> None:
    """The gate is `is_a_question`, the same word rule `/v1/ask` decides by --
    so the two doors cannot disagree about what a question is."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    converse, thread_id = await _asked(uow, [])
    plans = _Plans()
    converse._plan_lookups = plans  # type: ignore[assignment]
    converse._run_lookups = _Runs()  # type: ignore[assignment]

    await converse.execute(CTX, thread_id=thread_id, text="create a customer type called GPP")

    assert plans.asked == [], "a sentence asking for work was sent to the lookup door"
