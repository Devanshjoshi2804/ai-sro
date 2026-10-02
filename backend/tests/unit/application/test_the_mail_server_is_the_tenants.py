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
from sro.application.chat.mailbox import SERVER, send_as_this_system, server_for
from sro.application.ports.tools import ToolResult
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.application.rig.test_asking_the_asker import (
    THREAD,
    _a_run,
    _asked,
    _Mailbox,
    _pending,
)
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _look,
    mail_world,
)
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

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
