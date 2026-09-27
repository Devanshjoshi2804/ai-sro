from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta
from email.utils import getaddresses, parseaddr

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.tools import ToolCaller, ToolResult
from sro.domain.shared.identifiers import TenantId

logger = logging.getLogger(__name__)

SERVER = "gmail"

K_REMEMBER = timedelta(days=30)


K_OURS = "a mail this system sent, which is not a request"


class NotSent(Exception):
    code = "not_sent"


def mail_key(message: str) -> str:
    return f"mail:{message}"


def sent_key(message: str) -> str:
    """This system sent it -- apart from mail_key, which only says it was read."""
    return f"sent:{message}"


async def send_as_this_system(
    ctx: RequestContext,
    uow: UnitOfWork,
    tools: ToolCaller,
    arguments: Mapping[str, str],
    *,
    at: datetime,
) -> ToolResult:
    marker = secrets.token_hex(16)
    async with uow as unit:
        claimed = await unit.tool_calls.remember(
            ctx.tenant_id, sent_key(marker), tool=K_OURS, at=at, stale_after=K_REMEMBER
        )
        await unit.commit()
    if not claimed:
        raise NotSent("this mail could not be claimed as this system's own, so it was not sent")
    answered = await tools.call(
        ctx.tenant_id,
        ctx.principal_id,
        SERVER,
        "send_message",
        {**arguments, "marker": marker},
    )
    try:
        said = json.loads(answered.text or "{}")
    except ValueError:
        said = {}
    sent_id = str(said.get("id") or "") if isinstance(said, dict) else ""
    if not sent_id:
        return answered
    try:
        async with uow as unit:
            await unit.tool_calls.remember(
                ctx.tenant_id, sent_key(sent_id), tool=K_OURS, at=at, stale_after=K_REMEMBER
            )
            await unit.commit()
    except Exception:
        # The mail went and its marker is already claimed, so it is known as this
        # system's own; failing here would turn a sent mail into an error to retry.
        logger.exception("the sent mail %s is known by its marker only", sent_id)
    return answered


async def is_ours(
    uow: UnitOfWork, tenant_id: TenantId, message: Mapping[str, object], *, since: datetime
) -> bool:
    keys = [str(message.get(name) or "") for name in ("id", "marker")]
    async with uow as unit:
        for key in keys:
            if key and await unit.tool_calls.held(tenant_id, sent_key(key), since=since):
                return True
    return False


def sent_to_others(sender: str, to: str, cc: str, mailbox: str) -> tuple[str, ...]:
    me = mailbox.strip().casefold()
    if not me or parseaddr(sender)[1].casefold() != me:
        return ()
    return tuple(
        address for _, address in getaddresses([to, cc]) if address and address.casefold() != me
    )
