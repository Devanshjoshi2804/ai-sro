"""A mail read for what it asks, against a mailbox that answers.

The rung that replaces the substring. What these pin is not "the model said
Create a Customer Type" -- a fake says whatever the test put in it -- but the
rules around that answer: once per message, silence where it is unsure, the
operator's own mailbox and nobody else's, and an offer rather than a run.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.context import RequestContext
from sro.application.ports.tools import ToolResult, ToolsUnavailable
from sro.domain.chat.asking import NEEDS, Pending, pending_job
from sro.domain.execution.gathering import Found, Gathered
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.knowledge.entry import (
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
JOB = "wfl_1"


class _Mailbox:
    """A connector that answers whatever the test put in it, per operator."""

    def __init__(self, **answers: str) -> None:
        self._answers = answers
        self.asked: list[tuple[str, str, dict[str, str]]] = []

    @property
    def available(self) -> bool:
        return True

    async def list_tools(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> Any:
        return ()

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        self.asked.append((principal_id.value, tool, dict(arguments)))
        if tool == "search_threads":
            return ToolResult(text=self._answers.get("search", json.dumps({"messages": []})))
        return ToolResult(text=self._answers.get(arguments.get("id", ""), "{}"))


class _Reads:
    """The model, one scripted reading per message."""

    def __init__(self, *answers: dict[str, object]) -> None:
        self._answers = list(answers)
        self.saw: list[str] = []

    async def ask(self, *, evidence: str, **_: object) -> Answer:
        self.saw.append(evidence)
        if not self._answers:
            return Answer(data={"workflow_id": None, "values": [], "missing": [], "sure": True})
        return Answer(data=self._answers.pop(0), cost_usd=0.001)


def _found(*ids: str) -> str:
    return json.dumps({"messages": [{"id": one} for one in ids]})


def _mail(said: str, thread: str = "") -> str:
    return json.dumps({"id": "m-1", "subject": "Fwd: new type", "body": said, "thread_id": thread})


def _conversation(*said: str) -> str:
    """A whole thread, oldest first, as `get_thread` answers it."""
    return json.dumps(
        {
            "id": "t-1",
            "messages": [
                {"id": f"m-{n}", "subject": "Customer type", "body": one}
                for n, one in enumerate(said)
            ],
        }
    )


def _reading(
    workflow_id: str | None,
    *,
    sure: bool = True,
    bare: bool = False,
) -> dict[str, object]:
    """What the model read out of one mail.

    `bare` is the request that carries no values of its own -- "please create
    the customer type as discussed" -- which is what most requests actually
    look like and what the gather exists for.
    """
    if bare:
        return {
            "workflow_id": workflow_id,
            "values": [],
            "missing": ["Customer Type", "Customer Type Description"],
            "sure": sure,
        }
    return {
        "workflow_id": workflow_id,
        "values": [{"name": "Customer Type", "value": "GPX"}],
        "missing": ["Customer Type Description"],
        "sure": sure,
    }


async def _held() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.workflows.save(
        Workflow(
            id=JOB,
            tenant=f.TENANT.value,
            title="Create a Customer Type",
            narrative="open the screen, type the code, save",
            steps=[Step(order=0, says="type the code", system=None, cites=["g"])],
            parameters=[
                {"name": "Customer Type", "seen_values": ["GGD"]},
                {"name": "Customer Type Description", "seen_values": ["leaning new SRO type 01"]},
            ],
        )
    )
    return uow


def _look(uow: FakeUnitOfWork, mailbox: _Mailbox, reads: _Reads, gather: Any = None) -> FromTheMail:
    return FromTheMail(uow, mailbox, reads, model="m", gather=gather)


class _Gathers:
    """A mailbox that has the values the request did not carry."""

    def __init__(self, **values: str) -> None:
        self.values = values
        self.asked: list[tuple[str, tuple[str, ...]]] = []

    async def execute(self, _ctx: Any, *, job: str, wanted: Any, **_rest: Any) -> Gathered:
        self.asked.append((job, tuple(wanted)))
        found = {
            name: Found(value=self.values[name], from_message="m-0")
            for name in wanted
            if name in self.values
        }
        return Gathered(values=found, missing=tuple(n for n in wanted if n not in found))


async def _thread(uow: FakeUnitOfWork) -> Any:
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=CTX.principal_id, limit=1)
    return threads[0] if threads else None


async def test_a_mail_that_asks_for_a_job_becomes_the_same_offer_a_typed_request_does() -> None:
    """Deliberately the same decision `_say_the_job` writes. The panel already
    draws a card from `kind: "job"` and the press already starts the run; a
    second card shape for "this came from a mail" would be a second press to
    keep working."""
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please add customer type GPX")})
    reads = _Reads(_reading(JOB))

    looked = await _look(uow, mailbox, reads).execute(CTX)

    (one,) = looked.offered
    assert one.title == "Create a Customer Type"
    assert one.values == {"Customer Type": "GPX"}
    assert one.missing == ["Customer Type Description"]
    # Which mail, so a person can open it and check the reading. The id, never
    # the words.
    assert one.message == "m-1"
    # And nothing is said into the conversation. The card the browser draws
    # from this ends when it is pressed, when the operator does the job
    # themselves, or when their day does -- a thread line would outlive all
    # three and be history of a question nobody answered.
    assert await _thread(uow) is None


async def test_a_mail_is_offered_once_however_often_the_mailbox_is_read() -> None:
    """A look every few minutes over the same inbox would otherwise offer the
    same mail forty times."""
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please add customer type GPX")})
    reads = _Reads(_reading(JOB), _reading(JOB))
    look = _look(uow, mailbox, reads)

    first = await look.execute(CTX)
    second = await look.execute(CTX)

    assert len(first.offered) == 1
    assert second.offered == ()
    assert second.read == 0, "the second look read the mail again to decide it was the same one"


async def test_a_reading_that_is_not_sure_says_nothing() -> None:
    """Silence beats a wrong card. A mail nobody was asking about is the common
    case in any mailbox, and a card per delivery notice is a panel nobody reads
    by the fourth."""
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("here is your delivery note")})
    reads = _Reads(_reading(JOB, sure=False))

    looked = await _look(uow, mailbox, reads).execute(CTX)

    assert looked.offered == ()
    assert looked.read == 1, "it read the mail and decided, rather than never looking"
    # Silent to the panel, and NOT silent about why.
    #
    # "none of them asks for a job this tenant holds" was what a look said
    # here, and it is false: one of them asked, and the reading could not tell
    # which job it meant. Measured on the deployment, 2026-09-17: the tenant
    # held two workflows called `Create a Customer Type` -- one with six steps
    # and sixty-one runs, one with two steps and none -- so every mail asking
    # for one named both, `sure` went false, and the mail path was silent about
    # a job the rig had otherwise learned to do. A look that reports the wrong
    # absence is a look nobody investigates.
    assert "none of them asks for a job" not in looked.why, looked.why
    assert "more than one" in looked.why, looked.why


async def test_a_mail_that_asks_for_nothing_this_tenant_does_is_not_forced_onto_a_job() -> None:
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("lunch at one?")})
    reads = _Reads(_reading(None))

    looked = await _look(uow, mailbox, reads).execute(CTX)

    assert looked.offered == ()
    assert "none of them asks for a job" in looked.why


async def test_the_mailbox_is_read_as_the_operator_and_no_one_else() -> None:
    """Each reads their own mail. The port takes the principal and this passes
    it down; a look that reached another operator's mailbox would be the
    boundary undone one layer up."""
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("customer type GPX")})

    await _look(uow, mailbox, _Reads(_reading(JOB))).execute(CTX)

    assert {who for who, _, _ in mailbox.asked} == {"devansh"}
    assert [tool for _, tool, _ in mailbox.asked] == ["search_threads", "get_message"]


async def test_a_mailbox_that_cannot_be_reached_is_a_sentence_and_not_a_failure() -> None:
    class _Gone(_Mailbox):
        async def call(self, *args: object, **kw: object) -> ToolResult:
            raise ToolsUnavailable("gmail did not answer")

    looked = await _look(await _held(), _Gone(), _Reads()).execute(CTX)

    assert looked.offered == () and "could not be reached" in looked.why


async def test_a_tenant_with_no_mined_jobs_reads_no_mail_at_all() -> None:
    """Nothing to recognise, so nothing is read. A look that fetched somebody's
    mail to compare it against an empty list would be reading a mailbox for no
    reason at all."""
    mailbox = _Mailbox(search=_found("m-1"))

    looked = await _look(FakeUnitOfWork(), mailbox, _Reads()).execute(CTX)

    assert looked.offered == () and "no mined jobs" in looked.why
    assert mailbox.asked == []


async def test_an_offer_names_the_values_it_is_about() -> None:
    """A request rarely carries them.

    "Please create the customer type as discussed" is the whole of it, and what
    to create is in the mail before it. So the reading came back with the job
    and two missing values, and the card said "Create a Customer Type -- want
    me to do it?" with nothing to tell one from another. Four of them stacked
    up on the deployment, 2026-09-18, and they were the same sentence four
    times.

    Nobody can consent to a write they cannot see. The run gathers these
    anyway, a moment after the press; this is the same work moved to where the
    decision is actually made.
    """
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    reads = _Reads(_reading(JOB, bare=True))
    gather = _Gathers(
        **{"Customer Type": "GU3", "Customer Type Description": "leaning new SRO type 038"}
    )

    looked = await _look(uow, mailbox, reads, gather).execute(CTX)

    (one,) = looked.offered
    assert one.values == {
        "Customer Type": "GU3",
        "Customer Type Description": "leaning new SRO type 038",
    }
    assert one.missing == [], one.missing
    # Asked for the job by name and for exactly what was missing.
    assert gather.asked == [
        ("Create a Customer Type", ("Customer Type", "Customer Type Description"))
    ]


async def test_an_offer_whose_values_are_not_in_the_mail_still_offers() -> None:
    """What the gather could not find stays missing, and the card asks for it.

    The alternative -- refusing to offer at all -- would lose a request the
    operator can answer in two words, which is the whole reason the boxes on
    the card exist.
    """
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    reads = _Reads(_reading(JOB, bare=True))

    looked = await _look(uow, mailbox, reads, _Gathers()).execute(CTX)

    (one,) = looked.offered
    assert one.values == {}
    assert one.missing == ["Customer Type", "Customer Type Description"]


async def test_a_look_with_no_gather_offers_what_the_mail_itself_said() -> None:
    """A deployment with no connector, or none configured: the offer is still
    made from the request alone rather than not made."""
    uow = await _held()
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please add customer type GPX")})
    reads = _Reads(_reading(JOB))

    looked = await _look(uow, mailbox, reads).execute(CTX)

    (one,) = looked.offered
    assert one.values == {"Customer Type": "GPX"}


async def test_a_request_that_refers_to_an_earlier_mail_reads_the_conversation() -> None:
    """ "As discussed" was discussed in the mail above it.

    A reply names no values and the mail it replies to holds them, and which
    mail that is, is a fact Gmail already knows: it is the same thread. The
    gather searched the whole mailbox for it instead, with a query a model
    writes, and on a mailbox holding seventeen near-identical threads came back
    "the mailbox holds none of the values this job needs" about a value sitting
    one mail away. Measured on the deployment, 2026-09-17 at 21:26.
    """
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{
            "m-1": _mail("please create the customer type in WMS as discussed", thread="t-1"),
            "t-1": _conversation(
                'the code is GU5 and the description should read "leaning new SRO type 040"',
                "please create the customer type in WMS as discussed",
            ),
        },
    )
    # The request alone says nothing; the conversation says both.
    reads = _Reads(_reading(JOB, bare=True), _reading(JOB))

    looked = await _look(uow, mailbox, reads).execute(CTX)

    (one,) = looked.offered
    assert one.values == {"Customer Type": "GPX"}, one.values
    assert one.missing == ["Customer Type Description"]
    # The conversation was read, and by id rather than by searching for it.
    assert [one for one in mailbox.asked if one[1:] == ("get_thread", {"id": "t-1"})], mailbox.asked


async def test_a_request_in_no_conversation_does_not_ask_for_one() -> None:
    """A mail with no thread is a mail with nothing above it. Asking Gmail for
    thread "" is a call that can only fail."""
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    looked = await _look(uow, mailbox, _Reads(_reading(JOB, bare=True))).execute(CTX)

    assert looked.offered, "it refused to offer at all"
    assert not [one for one in mailbox.asked if one[1] == "get_thread"], mailbox.asked


async def test_an_offer_says_which_of_its_values_the_job_s_own_boxes_will_not_hold() -> None:
    """Asked before the press, because it is known before the press.

    The run already refuses a value that will not fit -- it types, the browser
    silently keeps a prefix, and the run stops rather than write a record that
    does not say what was asked for. It can only refuse standing in front of
    the box, which means somebody pressed, watched half a form fill, and got a
    question back. An earlier run found the limit and wrote it down; there is
    no reason to spend a person's press rediscovering it.
    """
    uow = await _held()
    await uow.workflows.save(
        Workflow(
            id=JOB,
            tenant=f.TENANT.value,
            title="Create a Customer Type",
            narrative="open the screen, type the code, save",
            steps=[
                Step(
                    order=0,
                    says="type the description",
                    system=None,
                    cites=["g"],
                    parameters=["Customer Type Description"],
                )
            ],
            parameters=[
                {"name": "Customer Type", "seen_values": ["GGD"]},
                {"name": "Customer Type Description", "seen_values": ["leaning new SRO type 01"]},
            ],
        )
    )
    await uow.workflows.remember_limit(JOB, 0, 28)
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    gather = _Gathers(
        **{
            "Customer Type": "GU9",
            "Customer Type Description": "leaning new SRO type 044 for the north dock",
        }
    )

    looked = await _look(uow, mailbox, _Reads(_reading(JOB, bare=True)), gather).execute(CTX)

    (one,) = looked.offered
    # The one that will not fit, and what the box takes. Not the one that will.
    assert one.too_long == {"Customer Type Description": 28}
    # Still offered, with the value on it: the card asks for a shorter one, and
    # a person who can answer in four words should not have to start again.
    assert one.values["Customer Type Description"].startswith("leaning new SRO type 044")


async def test_an_offer_for_a_job_nothing_has_hit_a_limit_on_says_nothing_about_limits() -> None:
    """Which is most of them. A limit exists only where a run has found one,
    and inventing one from silence would ask somebody to shorten a value that
    was never too long."""
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    gather = _Gathers(
        **{
            "Customer Type": "GU9",
            "Customer Type Description": "leaning new SRO type 044 for the north dock",
        }
    )

    looked = await _look(uow, mailbox, _Reads(_reading(JOB, bare=True)), gather).execute(CTX)

    (one,) = looked.offered
    assert one.too_long == {}


async def test_a_card_can_ask_about_a_limit_no_run_has_ever_hit() -> None:
    """The whole point of a job declaring its fields.

    `workflow_learned.holds` costs a wrong record to fill: a run types, the
    browser silently keeps a prefix, and the run writes the number down for
    next time. The vendor documented the same number years ago and it has been
    in the store since the knowledge base was first ingested. So the FIRST
    request too long for a field is asked about, rather than being the one that
    teaches the job what it should already have known.
    """
    uow = await _held()
    await uow.knowledge.add(
        KnowledgeEntry(
            id=KnowledgeId("kb-1"),
            tenant_id=f.TENANT,
            system="blue_yonder",
            kind=EntryKind.FIELD,
            key="longDescription",
            title="Customer Type Description (longDescription)",
            body={"labels": ["Customer Type Description"], "max_length": 20},
            source="index/field-dictionary.json",
            evidence=EvidenceLevel.ASSERTED,
            observed_at=datetime.now(tz=UTC),
        )
    )
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type in WMS as discussed")},
    )
    gather = _Gathers(
        **{
            "Customer Type": "GU9",
            "Customer Type Description": "leaning new SRO type 044 for the north dock",
        }
    )

    looked = await _look(uow, mailbox, _Reads(_reading(JOB, bare=True)), gather).execute(CTX)

    (one,) = looked.offered
    # Nothing was learnt; everything was already written down.
    assert await uow.workflows.learned_for(JOB) == ()
    assert one.too_long == {"Customer Type Description": 20}


def _short(thread: str, *, needs: list[str], values: dict[str, str]) -> WorkflowRun:
    """A run of this job that came up short and is waiting on that thread."""
    return WorkflowRun(
        id="run_1",
        tenant=f.TENANT.value,
        workflow_id=JOB,
        device_id="dev-1",
        values=values,
        started_by="devansh",
        live=True,
        allow_focus=True,
        started_at=datetime.now(tz=UTC).isoformat(),
        outcome="failed",
        needs=needs,
        awaiting=as_said(waiting_on("gmail", thread, now=datetime.now(tz=UTC))),
    )


async def test_a_reply_carries_on_the_run_that_was_waiting_for_it() -> None:
    """The one address the panel does not have.

    A run came up short of the customer type. The person who knows it is
    whoever sent the request, and they are not sitting in front of the panel --
    so the question goes to their mailbox, and the answer comes back there.
    Read as a fresh request it is two words that name no job at all, `sure`
    goes false, and the arrival is dropped for good: the message id is claimed
    before it is read.
    """
    uow = await _held()
    await uow.workflow_runs.save(
        _short("t-9", needs=["Customer Type"], values={"Customer Type Description": "north dock"})
    )
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("GU9", thread="t-9")})
    gather = _Gathers(**{"Customer Type": "GU9"})
    # A reading that would have thrown this away, to prove nothing consults it.
    reads = _Reads(_reading(None))

    looked = await _look(uow, mailbox, reads, gather).execute(CTX)

    (one,) = looked.offered
    assert one.workflow_id == JOB
    # What the earlier run established rides along: the operator pressed once.
    assert one.values == {"Customer Type Description": "north dock", "Customer Type": "GU9"}
    assert one.missing == []
    assert one.thread == "t-9"
    # And the model was never asked to read the reply.
    assert reads.saw == []


async def test_a_reply_to_a_wait_that_ran_out_is_an_ordinary_new_request() -> None:
    """A pause with no end to it is an abandonment. Past the deadline nobody is
    holding the question open, and reading a reply into it would start a write
    somebody asked for a week ago and has long since done by hand."""
    uow = await _held()
    stale = _short("t-9", needs=["Customer Type"], values={})
    stale.awaiting = {"server": "gmail", "thread": "t-9", "until": "2001-01-01T00:00:00+00:00"}
    await uow.workflow_runs.save(stale)
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type as discussed", thread="t-9")},
    )
    reads = _Reads(_reading(JOB, bare=True))

    looked = await _look(uow, mailbox, reads, _Gathers()).execute(CTX)

    (one,) = looked.offered
    # The ordinary path: read, and asked about from scratch.
    assert reads.saw
    assert one.missing == ["Customer Type", "Customer Type Description"]


async def test_a_mail_on_a_thread_nothing_is_waiting_on_is_read_as_it_always_was() -> None:
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type as discussed", thread="t-other")},
    )
    reads = _Reads(_reading(JOB, bare=True))

    looked = await _look(uow, mailbox, reads, _Gathers()).execute(CTX)

    assert reads.saw
    (one,) = looked.offered
    assert one.thread == "t-other"


async def test_an_offer_names_the_conversation_it_was_read_out_of() -> None:
    """So the run started from it can be found again by a reply. An id and
    never a word of anybody's mail."""
    uow = await _held()
    mailbox = _Mailbox(
        search=_found("m-1"),
        **{"m-1": _mail("please create the customer type as discussed", thread="t-7")},
    )

    looked = await _look(uow, mailbox, _Reads(_reading(JOB, bare=True)), _Gathers()).execute(CTX)

    assert looked.offered[0].thread == "t-7"


async def test_an_offer_is_turned_into_a_question_in_the_operators_own_thread() -> None:
    """The card's way into the loop the run path has always used.

    Until this, the only way to reach `_answer_the_question` was to type a yes
    in the chat. The card -- which is where people actually press -- drew boxes
    instead, and `asking.py` spends four paragraphs on why that is wrong.
    """
    uow = FakeUnitOfWork()
    pending = Pending(
        workflow_id=JOB,
        title="Create a Customer Type",
        values={"Customer Type Description": "north dock"},
        missing=("Customer Type",),
        limits={"Customer Type": 4},
    )

    asked = await AskAboutTheOffer(uow, FakeClock(), FakeIdFactory()).execute(
        CTX, pending, about="Customer type for the SRO pilot, round twenty-six"
    )

    # Which job, which request, and what is already established -- the whole of
    # what the card said, carried into a conversation that was not beside it.
    assert asked.startswith(
        "Create a Customer Type — Customer type for the SRO pilot, round twenty-six."
    ), asked
    assert "I have Customer Type Description: north dock." in asked, asked
    # And the question says what the box holds, so the same value does not come
    # straight back.
    assert asked.endswith("Customer Type takes 4 characters. What should it be?"), asked
    thread = await _thread(uow)
    assert thread is not None
    last = thread.messages[-1]
    assert last.text == asked
    assert last.decision is not None
    assert last.decision["kind"] == NEEDS
    # Everything established rides along, so the answer resumes rather than
    # starting the job over.
    assert last.decision["values"] == {"Customer Type Description": "north dock"}
    assert last.decision["missing"] == ["Customer Type"]
    assert last.decision["limits"] == {"Customer Type": 4}


async def test_an_offer_that_needs_nothing_asks_nothing() -> None:
    """A caller that got here about a job which turned out to be ready should
    start it. An error would make the ordinary path an exceptional one."""
    uow = FakeUnitOfWork()
    pending = Pending(workflow_id=JOB, title="Create a Customer Type", values={}, missing=())

    assert await AskAboutTheOffer(uow, FakeClock(), FakeIdFactory()).execute(CTX, pending) == ""
    assert await _thread(uow) is None


async def test_an_offer_whose_only_fault_is_a_value_that_will_not_fit_is_asked_about() -> None:
    """The press this door exists for, and the one it first got wrong.

    Measured on the deployment 2026-09-18: a mail carrying a ten-character code
    for a four-character field has nothing MISSING -- it supplied both values --
    so the offer read as ready and the door answered `nothing to ask` on the
    one press it was built to answer. A value the box will not take is as
    outstanding as one nobody gave; more so, because the person believes they
    have already answered it.
    """
    uow = FakeUnitOfWork()
    pending = Pending(
        workflow_id=JOB,
        title="Create a Customer Type",
        values={
            "Customer Type": "NEWSROTEST",
            "Customer Type Description": "Leaning new SRO type 048",
        },
        missing=(),
        limits={"Customer Type": 4},
    )

    asked = await AskAboutTheOffer(uow, FakeClock(), FakeIdFactory()).execute(CTX, pending)

    # What the request asked for and why it will not do, rather than a bare
    # demand for a value they believe they already gave.
    assert "The request said Customer Type NEWSROTEST, which is 10 characters." in asked, asked
    assert asked.endswith("Customer Type takes 4 characters. What should it be?"), asked
    thread = await _thread(uow)
    assert thread is not None
    decision = thread.messages[-1].decision
    assert decision is not None
    assert decision["missing"] == ["Customer Type"]
    # The value that will not fit rides along rather than being cleared: the
    # person is answering about it, and the run needs everything else intact.
    assert decision["values"]["Customer Type Description"] == "Leaning new SRO type 048"


async def test_a_name_both_unsupplied_and_capped_is_asked_about_once() -> None:
    """Asking twice for one word is the form this replaces."""
    uow = FakeUnitOfWork()
    pending = Pending(
        workflow_id=JOB,
        title="Create a Customer Type",
        values={"Customer Type": "NEWSROTEST"},
        missing=("Customer Type",),
        limits={"Customer Type": 4},
    )

    await AskAboutTheOffer(uow, FakeClock(), FakeIdFactory()).execute(CTX, pending)

    thread = await _thread(uow)
    assert thread is not None
    decision = thread.messages[-1].decision
    assert decision is not None
    assert decision["missing"] == ["Customer Type"]


async def test_a_question_this_door_asks_is_one_the_answering_door_can_find() -> None:
    """The writer and the reader, against each other rather than a fixture.

    Every test of the answering path built its own question by hand, with
    `Speaker.ASSISTANT` on it, because that is what `pending_job` reads. What
    actually WROTE questions used `Speaker.SYSTEM`, so no question this system
    has ever asked was findable -- the run path's included, since `5a2d10b1`.

    Measured on the deployment 2026-09-18: three questions standing in the
    thread, an operator's sentence going past all three to the skill resolver,
    and `Nobody has demonstrated that` as the answer to `What should Customer
    Type be?`.

    A fixture agreeing with the reader proves the reader agrees with itself.
    """
    uow = FakeUnitOfWork()
    pending = Pending(
        workflow_id=JOB,
        title="Create a Customer Type",
        values={},
        missing=("Customer Type",),
        limits={"Customer Type": 4},
    )

    await AskAboutTheOffer(uow, FakeClock(), FakeIdFactory()).execute(CTX, pending)

    thread = await _thread(uow)
    assert thread is not None
    waiting = pending_job(thread.messages)
    assert waiting is not None, (
        "the question this door asked cannot be found by the door that answers it"
    )
    assert waiting.asking_for == "Customer Type"
    assert waiting.limits == {"Customer Type": 4}
