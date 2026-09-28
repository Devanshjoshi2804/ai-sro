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

logger = logging.getLogger(__name__)

SERVER = "gmail"

K_REMEMBER = timedelta(days=30)


K_OURS = "a mail this system sent, which is not a request"


class NotSent(Exception):
    code = "not_sent"


def mail_key(message: str) -> str:
    return f"mail:{message}"


K_ELSEWHERE = "a reply its starter's own look has to take"

K_TAKEN = "a reply its starter's own look took"


def elsewhere_key(run_id: str, question_id: str) -> str:
    return f"elsewhere:{run_id}:{question_id}"


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
    uow: UnitOfWork, ctx: RequestContext, message: Mapping[str, object], *, since: datetime
) -> bool:
    ids = [str(message.get(name) or "") for name in ("id", "marker")]
    legacy = str(message.get("id") or "")
    # Sends before sent_key were claimed as K_OURS under mail_key(id), or on
    # main under mail:{operator}:{id}, and were never recipient-checked.
    # ponytail: drop the legacy keys once K_REMEMBER has passed since deploy.
    claims = [(sent_key(one), None) for one in ids if one] + (
        [(mail_key(legacy), K_OURS), (f"mail:{ctx.principal_id.value}:{legacy}", K_OURS)]
        if legacy
        else []
    )
    async with uow as unit:
        for key, tool in claims:
            if await unit.tool_calls.held(ctx.tenant_id, key, since=since, tool=tool):
                return True
    return False


def sent_to_others(sender: str, to: str, cc: str, mailbox: str) -> tuple[str, ...]:
    me = mailbox.strip().casefold()
    if not me or parseaddr(sender)[1].casefold() != me:
        return ()
    return tuple(
        address for _, address in getaddresses([to, cc]) if address and address.casefold() != me
    )
