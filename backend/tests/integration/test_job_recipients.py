from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.execution.mail_job import SEND_A_MAIL, JobRecipient
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.repositories import SqlUnitOfWork

ACME, OTHER = TenantId("acme"), TenantId("other")


async def test_an_operator_confirmed_recipient_is_kept_per_job_and_per_tenant(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = JobRecipient("vendor@supplier.example", "clerk", datetime(2026, 9, 26, tzinfo=UTC))
    again = JobRecipient("vendor@supplier.example", "boss", datetime(2026, 9, 27, tzinfo=UTC))
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.workflows.confirm_recipient(ACME, "wfl_mail", first)
        await uow.workflows.confirm_recipient(ACME, "wfl_mail", again)
        await uow.commit()

    async with SqlUnitOfWork(session_factory) as uow:
        assert await uow.workflows.recipients_for(ACME, "wfl_mail") == (again,)
        assert await uow.workflows.recipients_for(ACME, "wfl_other") == ()
        assert await uow.workflows.recipients_for(OTHER, "wfl_mail") == ()


async def test_a_built_in_mail_action_is_found_with_no_row_and_keeps_its_recipients(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """M4: send, reply and forward are code, never mined rows -- `get` hands one
    to every tenant, and who its operators named is kept per tenant."""
    named = JobRecipient("vendor@supplier.example", "clerk", datetime(2026, 9, 28, tzinfo=UTC))
    async with SqlUnitOfWork(session_factory) as uow:
        got = await uow.workflows.get(ACME, SEND_A_MAIL)
        await uow.workflows.confirm_recipient(ACME, SEND_A_MAIL, named)
        await uow.commit()

    assert (got.id, got.tenant, got.title) == (SEND_A_MAIL, "acme", "Send an email")
    async with SqlUnitOfWork(session_factory) as uow:
        assert SEND_A_MAIL not in [one.id for one in await uow.workflows.known(ACME)]
        assert await uow.workflows.recipients_for(ACME, SEND_A_MAIL) == (named,)
        assert await uow.workflows.recipients_for(OTHER, SEND_A_MAIL) == ()
