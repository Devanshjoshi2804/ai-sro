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


def _mail(said: str) -> str:
    return json.dumps({"id": "m-1", "subject": "Fwd: new type", "body": said})


def _reading(workflow_id: str | None, *, sure: bool = True) -> dict[str, object]:
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


def _look(uow: FakeUnitOfWork, mailbox: _Mailbox, reads: _Reads) -> FromTheMail:
    return FromTheMail(uow, mailbox, reads, model="m")


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
