"""The mail door reads Outlook mail with no Outlook branch.

`FromTheMail` is the same object that reads Gmail. Here its mailbox is the real Outlook
connector's tool functions over a fake Nango proxy answering recorded Graph JSON, so the
shapes it parses are the ones the Outlook connector produces.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import ModuleType

from sro.application.ports.tools import ToolResult
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests.unit.application.rig.test_a_mail_job_is_written_not_clicked import (
    THREAD,
    _a_run,
    _reply_job,
    _written,
)
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _Mailbox,
    _Reads,
    mail_world,
)
from tests.unit.test_the_outlook_connector import FakeNango, _mail, nango, outlook  # noqa: F401


class _OutlookMailbox(_Mailbox):
    def __init__(self, connector: ModuleType) -> None:
        super().__init__()
        self._outlook = connector

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        self.asked.append((principal_id.value, tool, dict(arguments)))
        text = await self._outlook.run_tool("acme", "sam", tool, arguments)
        return ToolResult(text=text)


async def test_a_mail_that_arrived_in_outlook_starts_its_run_like_a_gmail_one(
    outlook: ModuleType,  # noqa: F811
    nango: FakeNango,  # noqa: F811
) -> None:
    arrived = _mail(
        "m-1",
        body={"contentType": "text", "content": "please add customer type GT2"},
        bodyPreview="please add customer type GT2",
    )
    nango.on("GET", "/v1.0/me/messages", {"value": [arrived]})
    nango.on("GET", "/v1.0/me/messages/m-1", arrived)
    world = await mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)
    reads = _Reads(
        {
            "job": JOB,
            "values": [{"field": "Customer Type", "value": "GT2", "quote": "GT2"}],
            "missing": [],
            "sure": True,
        }
    )
    mailbox = _OutlookMailbox(outlook)

    looked = await world.look(mailbox, reads).execute(CTX)

    assert looked.offered[0].started
    assert len(world.durable.runs_started) == 1
    assert [tool for _who, tool, _args in mailbox.asked][:2] == ["search_threads", "get_message"]
    assert "GT2" in reads.saw[0]


async def test_a_mail_the_outlook_connector_sent_is_recorded_as_sent_and_not_retried(
    outlook: ModuleType,  # noqa: F811
    nango: FakeNango,  # noqa: F811
) -> None:
    """The connector's real send answer goes through mail_job's send path. An answer with
    no id read as 'the mailbox did not say the mail went': the run failed after the mail
    had gone, and the operator's retry mailed it twice."""
    from sro.application.execution.mail_job import draft_the_mail_job
    from tests import factories as f
    from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

    original = _mail(
        "orig",
        conversationId=THREAD,
        **{"from": {"emailAddress": {"name": "Alex R", "address": "alex.r@example.com"}}},
    )
    nango.on("GET", "/v1.0/me/messages", {"value": [original]})
    nango.on("POST", "/v1.0/me/messages/orig/createReply", {"id": "AAMk-imm-9"})
    nango.on("POST", "/v1.0/me/messages/AAMk-imm-9/send", None)
    uow, mailbox = FakeUnitOfWork(), _OutlookMailbox(outlook)

    finished = await draft_the_mail_job(
        CTX,
        await _a_run(uow),
        _reply_job(),
        {},
        uow=uow,
        tools=mailbox,
        asker=_written("alex.r@example.com"),
        clock=FakeClock(),
        ids=FakeIdFactory(),
        servers={},
    )

    assert finished.outcome == "held"
    (step,) = finished.steps
    assert (step.verdict, step.made) == ("held", {"message": "AAMk-imm-9"})
    said = (await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1))[
        0
    ].messages[-1]
    assert said.text.startswith("Sent to alex.r@example.com")
    sends = [p for m, p, *_ in nango.seen if m == "POST" and p.endswith("/send")]
    assert sends == ["/proxy/v1.0/me/messages/AAMk-imm-9/send"]  # one mail went, once
