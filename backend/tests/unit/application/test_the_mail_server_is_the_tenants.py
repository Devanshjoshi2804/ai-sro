"""The mail server is the tenant's setting, gmail unless it is set.

An Outlook connector plugs in by being named for a tenant, not by a branch in
the mail door: every call to the mailbox, the draft's send, and the record of
which thread a run waits on name the server the tenant has.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from sro.application.chat.ask_the_asker import DraftForTheAsker, SendTheDraft
from sro.application.chat.converse import Converse
from sro.application.chat.mailbox import SERVER, send_as_this_system, server_for
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.execution.gather import GatherContext
from sro.application.execution.mail_job import Written, redraft_the_mail_job, send_the_mail
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.ports.tools import ToolResult
from sro.domain.execution.progress import Progress
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.plan import ToolPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.application.rig.test_a_mail_job_is_written_not_clicked import (
    _asked_who,
    _reply_job,
    _written,
)
from tests.unit.application.rig.test_a_mail_job_is_written_not_clicked import _Mailbox as _Sent
from tests.unit.application.rig.test_asking_the_asker import (
    THREAD,
    _a_run,
    _asked,
    _Mailbox,
    _pending,
)
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    EVERY_VALUE,
    JOB,
    OPERATOR,
    _addressed,
    _look,
    _should_we,
    _sure,
    _thread,
    mail_world,
)
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeEmbedder,
    FakeHttpCaller,
    FakeIdFactory,
    FakeToolCaller,
    FakeUnitOfWork,
)

OUTLOOK: Mapping[str, str] = MappingProxyType({f.TENANT.value: "outlook"})


class _Seen:
    """Whichever mailbox, remembering the server each call named."""

    servers: list[str]

    def __init__(self, inner: Any) -> None:
        self.inner, self.servers = inner, []

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
        self.servers.append(server)
        return await self.inner.call(tenant_id, principal_id, server, tool, arguments)


def test_a_tenant_not_listed_has_gmail() -> None:
    assert server_for("beta", OUTLOOK) == SERVER == "gmail"
    assert server_for(f.TENANT.value, OUTLOOK) == "outlook"


async def test_a_look_in_an_outlook_tenant_s_mail_asks_outlook() -> None:
    world = await mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)
    seen = _Seen(world.mailbox)
    look = _look(world.uow, seen, world.reads, start=world.start, servers=OUTLOOK)

    await look.execute(CTX)

    assert seen.servers and set(seen.servers) == {"outlook"}


async def test_a_look_in_a_tenant_not_listed_asks_gmail() -> None:
    world = await mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)
    seen = _Seen(world.mailbox)
    look = _look(
        world.uow, seen, world.reads, start=world.start, servers={"someone-else": "outlook"}
    )

    await look.execute(CTX)

    assert seen.servers and set(seen.servers) == {"gmail"}


async def test_a_draft_is_read_and_sent_through_the_tenant_s_server() -> None:
    uow = FakeUnitOfWork()
    seen = _Seen(_Mailbox())
    await _a_run(uow)
    question = await _asked(uow)
    await DraftForTheAsker(uow, seen, FakeClock(), FakeIdFactory(), servers=OUTLOOK).execute(
        CTX, _pending(), question=question, run_id="run_1"
    )
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]

    await SendTheDraft(uow, seen, FakeClock(), FakeIdFactory(), servers=OUTLOOK).execute(
        CTX, threads[0].id, drafted.id
    )

    assert seen.servers and set(seen.servers) == {"outlook"}
    assert len(seen.inner.sent) == 1


async def test_this_system_s_mail_is_sent_through_the_server_it_is_given() -> None:
    uow = FakeUnitOfWork()
    seen = _Seen(_Mailbox())

    await send_as_this_system(
        CTX, uow, seen, {"to": "a@x.example"}, at=datetime(2026, 9, 27, tzinfo=UTC), servers=OUTLOOK
    )

    assert seen.servers == ["outlook"]


async def test_a_run_an_outlook_mail_started_waits_on_that_thread_at_outlook() -> None:
    world = await mail_world(
        sure=True, values={"Customer Type": "GT2"}, steel=True, thread=THREAD, servers=OUTLOOK
    )
    look = _look(world.uow, world.mailbox, world.reads, start=world.start, servers=OUTLOOK)

    await look.execute(CTX)

    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.mail is not None and run.mail["thread"] == THREAD
    assert run.awaiting is not None and run.awaiting["server"] == "outlook"


async def test_the_repository_finds_a_run_an_outlook_mail_started_by_its_server() -> None:
    world = await mail_world(
        sure=True, values={"Customer Type": "GT2"}, steel=True, thread=THREAD, servers=OUTLOOK
    )
    await world.from_the_mail.execute(CTX)
    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    run.needs = ["Customer Type"]
    await world.uow.workflow_runs.save(run)

    runs = world.uow.workflow_runs
    assert await runs.started_on(f.TENANT, server="outlook", thread=THREAD)
    assert not await runs.started_on(f.TENANT, server="gmail", thread=THREAD)
    found = await runs.waiting_on(f.TENANT, server="outlook", thread=THREAD)
    assert found is not None and found.id == run.id
    assert await runs.waiting_on(f.TENANT, server="gmail", thread=THREAD) is None


async def test_the_chat_s_yes_starts_the_run_on_the_tenant_s_server() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True, servers=OUTLOOK)
    await world.polling(_addressed(OPERATOR, "colleague@example.com"), _sure()).execute()
    await _should_we(world)
    thread = await _thread(world.uow)
    converse = Converse(
        world.uow,
        ResolveIntent(world.uow, PlanTask(Retrieve(world.uow, FakeEmbedder()))),
        FakeClock(),
        FakeIdFactory(),
        start=world.start,
    )

    await converse.execute(CTX, thread_id=thread.id, text="yes")

    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.awaiting is not None and run.awaiting["server"] == "outlook"
    assert world.start.mail_server(CTX) == "outlook"


async def test_the_gather_looks_in_the_tenant_s_mailbox() -> None:
    seen = _Seen(FakeToolCaller({"search_threads": ToolResult(text="{}")}))

    await GatherContext(seen, _Steps(), OUTLOOK).execute(CTX, job="a job", wanted=["x"], rounds=0)

    assert seen.servers and set(seen.servers) == {"outlook"}


async def test_a_mail_job_sends_through_the_tenant_s_server() -> None:
    uow, mailbox = FakeUnitOfWork(), _Sent()
    seen = _Seen(mailbox)
    written = Written("alex@example.com", "Re: who", "body", THREAD, "")

    await send_the_mail(CTX, uow, seen, written, clock=FakeClock(), servers=OUTLOOK)

    assert seen.servers == ["outlook"] and len(mailbox.sent) == 1


async def test_an_answered_question_is_redrafted_and_sent_through_the_tenant_s_server() -> None:
    uow, mailbox = FakeUnitOfWork(), _Sent()
    seen = _Seen(mailbox)
    run = await _asked_who(uow)
    asking = Progress.of(run.progress).asking
    answered = {
        **run.progress,
        "asking": {
            **asking,
            "answered": "yes",
            "verdict": "",
            "address": "vendor@supplier.example",
            "by": "devansh",
        },
    }
    assert await uow.workflow_runs.record_progress(f.TENANT, run.id, answered)
    again = await uow.workflow_runs.get(f.TENANT, run.id)
    assert again is not None

    await redraft_the_mail_job(
        CTX,
        again,
        _reply_job(),
        {},
        uow=uow,
        tools=seen,
        asker=_written("vendor@supplier.example"),
        clock=FakeClock(),
        ids=FakeIdFactory(),
        servers=OUTLOOK,
    )

    assert seen.servers and set(seen.servers) == {"outlook"} and len(mailbox.sent) == 1


async def test_a_skill_step_recorded_on_gmail_calls_the_tenant_s_mail_server() -> None:
    tools = FakeToolCaller({"send_message": ToolResult(text='{"id": "m", "status": "sent"}')})
    await _skill_run(tools, "gmail", OUTLOOK)
    await _skill_run(tools, "gmail", {})
    await _skill_run(tools, "crm", OUTLOOK)

    assert [server for server, _, _ in tools.calls] == ["outlook", "gmail", "crm"]


async def _skill_run(tools: FakeToolCaller, recorded: str, servers: Mapping[str, str]) -> None:
    uow = FakeUnitOfWork()
    version = f.skill_version(
        steps=(
            SkillStep(
                index=0,
                intent="reply",
                tool_plan=ToolPlan(
                    server=recorded,
                    tool="send_message",
                    arguments=(("to", Template("a@b.test")),),
                    writes=True,
                ),
            ),
        ),
        parameters=(),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    await ExecuteSkill(
        uow,
        FakeHttpCaller(),
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        tools=tools,
        servers=servers,
    ).execute(CTX, ExecutionRequest(skill_id=skill.id, parameters={}, authorized_by="supervisor"))


class _Steps:
    async def ask(self, **_: object) -> Answer:
        return Answer(data={"action": "done", "values": [], "why": "nothing"})
