"""A mail this system sends is claimed as its own before it is sent.

The look reads the operator's mailbox, where this system's mail lands as the
operator's own SENT mail. Claimed only after Gmail answered, a look in between
read it as the operator's -- a reply that could answer a question or name a
recipient. So the claim comes first, and without it nothing is sent.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import sro
from sro.application.chat.mailbox import NotSent, is_ours, mail_key, send_as_this_system
from sro.application.context import RequestContext
from sro.application.ports.tools import ToolResult
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
NOW = datetime(2026, 9, 27, tzinfo=UTC)


class _Mailbox:
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.sent: list[dict[str, str]] = []
        self.claimed_first: list[bool] = []

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
        assert tool == "send_message"
        self.claimed_first.append(
            await self.uow.tool_calls.held(tenant_id, mail_key(arguments["marker"]), since=NOW)
        )
        self.sent.append(dict(arguments))
        return ToolResult(text=json.dumps({"status": "sent", "id": "gm-7"}))


async def test_the_claim_is_made_before_the_mail_is_sent() -> None:
    uow = FakeUnitOfWork()
    mailbox = _Mailbox(uow)

    answered = await send_as_this_system(CTX, uow, mailbox, {"to": "a@x.example"}, at=NOW)

    assert json.loads(answered.text)["id"] == "gm-7"
    assert mailbox.claimed_first == [True]
    (sent,) = mailbox.sent
    tenant = CTX.tenant_id
    assert await is_ours(uow, tenant, {"id": "unknown", "marker": sent["marker"]}, since=NOW)
    assert await is_ours(uow, tenant, {"id": "gm-7"}, since=NOW)
    assert not await is_ours(uow, tenant, {"id": "m-9", "marker": "forged"}, since=NOW)


async def test_no_claim_no_send(monkeypatch: pytest.MonkeyPatch) -> None:
    uow = FakeUnitOfWork()
    mailbox = _Mailbox(uow)

    async def refused(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(uow.tool_calls, "remember", refused)
    with pytest.raises(NotSent):
        await send_as_this_system(CTX, uow, mailbox, {"to": "a@x.example"}, at=NOW)

    async def broken(*_: object, **__: object) -> bool:
        raise RuntimeError("the ledger is down")

    monkeypatch.setattr(uow.tool_calls, "remember", broken)
    with pytest.raises(RuntimeError):
        await send_as_this_system(CTX, uow, mailbox, {"to": "a@x.example"}, at=NOW)

    assert mailbox.sent == []


async def test_a_sent_mail_is_not_turned_into_an_error_by_its_id_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After the send, the id claim only adds to the marker's. Raising there
    would make a mail that went look failed, and a failure invites a resend."""
    uow = FakeUnitOfWork()
    mailbox = _Mailbox(uow)
    remember = uow.tool_calls.remember

    async def only_the_marker(tenant_id: TenantId, key: str, **kwargs: Any) -> bool:
        if key == mail_key("gm-7"):
            raise RuntimeError("the ledger is down")
        return await remember(tenant_id, key, **kwargs)

    monkeypatch.setattr(uow.tool_calls, "remember", only_the_marker)
    answered = await send_as_this_system(CTX, uow, mailbox, {"to": "a@x.example"}, at=NOW)

    assert json.loads(answered.text)["id"] == "gm-7" and len(mailbox.sent) == 1
    assert await is_ours(uow, CTX.tenant_id, {"marker": mailbox.sent[0]["marker"]}, since=NOW)


def test_every_send_goes_through_the_one_helper() -> None:
    root = Path(sro.__file__).parent
    senders = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if '"send_message"' in path.read_text(encoding="utf-8")
    )
    assert senders == ["application/chat/mailbox.py"]
