"""A mail read for what it asks, against a mailbox that answers.

The rung that replaces the substring. What these pin is not "the model said
Create a Customer Type" -- a fake says whatever the test put in it -- but the
rules around that answer: once per message, silence where it is unsure, the
operator's own mailbox and nobody else's, and an offer rather than a run.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sro.application.chat.from_the_mail import FromTheMail
from sro.application.context import RequestContext
from sro.application.ports.tools import ToolResult, ToolsUnavailable
from sro.domain.execution.gathering import Found, Gathered
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

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
