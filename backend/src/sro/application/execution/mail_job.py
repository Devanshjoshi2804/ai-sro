from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.ask_the_asker import DRAFTED
from sro.application.chat.mailbox import K_REMEMBER, SERVER
from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.application.shared.asking import ask
from sro.domain.chat.thread import Speaker
from sro.domain.execution.mail_job import (
    Allowed,
    JobRecipient,
    check_draft,
    mailboxes,
    sent_messages,
)
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.prompts.write_mail import WRITE_MAIL
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.workflow import Workflow

logger = logging.getLogger(__name__)

K_MESSAGES = 5

K_BODY = 2000

AWAITING_THE_PRESS = "drafted — read it in the conversation and press Send it"


@dataclass(frozen=True, slots=True)
class Written:
    to: str
    subject: str
    body: str
    thread: str
    in_reply_to: str
    bcc: str = ""


class Unaddressed(str):
    __slots__ = ()


async def write_the_mail(
    ctx: RequestContext,
    workflow: Workflow,
    values: Mapping[str, str],
    thread: str,
    *,
    by_id: Mapping[str, Gesture],
    uow: UnitOfWork,
    tools: ToolCaller,
    asker: Asker,
) -> Written | str:
    conversation = await _conversation(ctx, tools, thread) if thread else []
    allowed = await _allowed(ctx, uow, tools, workflow, by_id)
    written = await ask(
        asker,
        WRITE_MAIL,
        trusted={
            "job": workflow.title,
            "operator": ctx.principal_id.value,
            "sent_before": sorted(allowed.to | allowed.bcc),
        },
        untrusted={
            "what_it_does": workflow.narrative,
            "steps": json.dumps(
                [step.says for step in sorted(workflow.steps, key=lambda one: one.order)],
                indent=2,
                ensure_ascii=False,
            ),
            "values": json.dumps(dict(values), indent=2, ensure_ascii=False),
            "conversation": json.dumps(
                [
                    {
                        "id": str(one.get("id") or ""),
                        "from": str(one.get("from") or ""),
                        "to": str(one.get("to") or ""),
                        "cc": str(one.get("cc") or ""),
                        "by_the_operator": one.get("sent") is True,
                        "subject": str(one.get("subject") or ""),
                        "body": str(one.get("body") or "")[:K_BODY],
                    }
                    for one in conversation[-K_MESSAGES:]
                ],
                indent=2,
                ensure_ascii=False,
            ),
        },
    )
    data: Mapping[str, object] = written.data or {}
    to = " ".join(str(data.get("to") or "").split())
    body = str(data.get("body") or "").strip()
    if not body:
        return f"the mail could not be written: {written.error or 'the model said nothing'}"
    cited = data.get("cited")
    checked = check_draft(
        to=to,
        body=body,
        cited=[one for one in cited if isinstance(one, Mapping)] if isinstance(cited, list) else [],
        conversation=conversation,
        values=values,
        allowed=allowed,
    )
    if checked.why:
        logger.info(
            "%s: the draft of %s was refused: %s", ctx.tenant_id.value, workflow.id, checked.logged
        )
        if checked.recipient:
            return Unaddressed(f"{checked.why} -- nothing was sent; who does this mail go to?")
        return f"{checked.why} -- nothing was sent"
    latest = conversation[-1] if conversation else {}
    return Written(
        to=", ".join(checked.to),
        subject=" ".join(str(data.get("subject") or "").split()),
        body=body,
        thread=thread,
        in_reply_to=str(latest.get("rfc822_message_id") or ""),
        bcc=", ".join(checked.bcc),
    )


async def _allowed(
    ctx: RequestContext,
    uow: UnitOfWork,
    tools: ToolCaller,
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
) -> Allowed:
    to: set[str] = set()
    bcc: set[str] = set()
    for named in sent_messages(workflow, by_id):
        sent = [
            one
            for one in [await _message(ctx, tools, id_) for id_ in named]
            if one.get("sent") is True
        ]
        if len(sent) != 1:
            continue
        for key, into in (("to", to), ("cc", to), ("bcc", bcc)):
            into.update(mailboxes(str(sent[0].get(key) or "")) or ())
    async with uow as unit:
        confirmed = await unit.workflows.recipients_for(ctx.tenant_id, workflow.id)
    to.update(one.address for one in confirmed)
    return Allowed(to=frozenset(to), bcc=frozenset(bcc - to))


async def _message(ctx: RequestContext, tools: ToolCaller, message: str) -> dict[str, object]:
    try:
        answered = await tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_message", {"id": message}
        )
        said = json.loads(answered.text)
    except (ToolsUnavailable, ValueError):
        return {}
    return said if isinstance(said, dict) and not answered.failed else {}


async def send_the_mail(
    ctx: RequestContext, uow: UnitOfWork, tools: ToolCaller, mail: Written, *, clock: Clock
) -> tuple[str, str]:
    try:
        answered = await tools.call(
            ctx.tenant_id,
            ctx.principal_id,
            SERVER,
            "send_message",
            {
                "to": mail.to,
                **({"bcc": mail.bcc} if mail.bcc else {}),
                "subject": mail.subject,
                "body": mail.body,
                "thread_id": mail.thread,
                "in_reply_to": mail.in_reply_to,
            },
        )
    except ToolsUnavailable as gone:
        return "", f"the mailbox could not be reached, so nothing was sent: {gone}"
    try:
        said = json.loads(answered.text or "{}")
    except ValueError:
        said = {}
    sent_id = str(said.get("id") or "") if isinstance(said, dict) else ""
    if not sent_id:
        return "", f"Gmail did not say the mail went: {answered.text[:200]}"
    async with uow as unit:
        await unit.tool_calls.remember(
            ctx.tenant_id,
            f"mail:{ctx.principal_id.value}:{sent_id}",
            tool="a mail this system sent, which is not a request",
            at=clock.now(),
            stale_after=K_REMEMBER,
        )
        await unit.commit()
    return sent_id, ""


@dataclass(frozen=True, slots=True)
class MailHand:
    write: Callable[
        [Workflow, Mapping[str, str], str, Mapping[str, Gesture]], Awaitable[Written | str]
    ]
    send: Callable[[Written], Awaitable[tuple[str, str]]]


async def draft_the_mail_job(
    ctx: RequestContext,
    run: WorkflowRun,
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
    *,
    uow: UnitOfWork,
    tools: ToolCaller,
    asker: Asker,
    clock: Clock,
    ids: IdFactory,
) -> WorkflowRun:
    waiting = read_wait(run.awaiting) if run.awaiting else None
    thread = waiting.thread if waiting else ""
    written = await write_the_mail(
        ctx, workflow, run.values, thread, by_id=by_id, uow=uow, tools=tools, asker=asker
    )
    if isinstance(written, Unaddressed):
        return await _ask_who(ctx, uow, run, written, clock=clock, ids=ids)
    if isinstance(written, str):
        return await _stop(uow, run, written)

    await SayWhatHappened(uow, clock, ids).execute(
        ctx,
        for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
        text=f"{workflow.title} — this is the mail I would send to {written.to}. Read it first.",
        speaker=Speaker.SYSTEM,
        decision={
            "kind": DRAFTED,
            "run_id": run.id,
            "to": written.to,
            **({"bcc": written.bcc} if written.bcc else {}),
            "subject": written.subject,
            "body": written.body,
            "thread": written.thread,
            "in_reply_to": written.in_reply_to,
            "job": workflow.id,
        },
    )
    run.steps.append(
        RunStep(
            order=len(run.steps),
            of_step=0,
            says="Send the mail",
            verdict="awaiting",
            verdict_by="none",
            reason=AWAITING_THE_PRESS,
            sent={"kind": "mail.draft", "payload": {"to": written.to, "subject": written.subject}},
        )
    )
    run.outcome = "stopped"
    await _save(uow, run)
    logger.info("%s: drafted %s's mail", run.id, workflow.id)
    return run


async def _conversation(
    ctx: RequestContext, tools: ToolCaller, thread: str
) -> list[dict[str, object]]:
    try:
        answered = await tools.call(
            ctx.tenant_id, ctx.principal_id, SERVER, "get_thread", {"id": thread}
        )
    except ToolsUnavailable as gone:
        logger.info("%s: the conversation could not be read: %s", ctx.tenant_id.value, gone)
        return []
    try:
        said = json.loads(answered.text)
    except ValueError:
        return []
    rows = said.get("messages") if isinstance(said, dict) else None
    return [one for one in rows if isinstance(one, dict)] if isinstance(rows, list) else []


async def redraft_the_mail_job(
    ctx: RequestContext,
    run: WorkflowRun,
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
    *,
    uow: UnitOfWork,
    tools: ToolCaller,
    asker: Asker,
    clock: Clock,
    ids: IdFactory,
) -> WorkflowRun:
    progress = Progress.of(run.progress)
    if progress.asking.get("kind") != "recipient" or not progress.asking.get("answered"):
        return run
    await keep_the_named(ctx, uow, workflow.id, progress.asking, at=clock.now())
    was, progress.asking = run.progress, {}
    async with uow as unit:
        taken = await unit.workflow_runs.record_progress(
            ctx.tenant_id, run.id, progress.as_json(), was=was
        )
        await unit.commit()
    if not taken:
        return run
    run.progress = progress.as_json()
    return await draft_the_mail_job(
        ctx, run, workflow, by_id, uow=uow, tools=tools, asker=asker, clock=clock, ids=ids
    )


async def keep_the_named(
    ctx: RequestContext,
    uow: UnitOfWork,
    workflow_id: str,
    asking: Mapping[str, str],
    *,
    at: datetime,
) -> None:
    async with uow as unit:
        for address in mailboxes(asking.get("address", "")) or ():
            await unit.workflows.confirm_recipient(
                ctx.tenant_id, workflow_id, JobRecipient(address, asking.get("by", ""), at)
            )
        await unit.commit()


async def _ask_who(
    ctx: RequestContext,
    uow: UnitOfWork,
    run: WorkflowRun,
    why: str,
    *,
    clock: Clock,
    ids: IdFactory,
) -> WorkflowRun:
    progress = Progress.of(run.progress)
    progress.asking = {
        "id": f"q_{secrets.token_hex(16)}",
        "kind": "recipient",
        "text": why,
        "step": "0",
    }
    await _stop(uow, run, why)
    async with uow as unit:
        asked = await unit.workflow_runs.record_progress(
            ctx.tenant_id, run.id, progress.as_json(), was=run.progress
        )
        await unit.commit()
    if not asked:
        return run
    run.progress = progress.as_json()
    await SayWhatHappened(uow, clock, ids).execute(
        ctx,
        for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
        text=why,
        speaker=Speaker.ASSISTANT,
        decision={
            "kind": "run_asks",
            "run_id": run.id,
            "question_id": progress.asking["id"],
            "asks": "recipient",
        },
    )
    return run


async def _stop(uow: UnitOfWork, run: WorkflowRun, why: str) -> WorkflowRun:
    run.steps.append(
        RunStep(
            order=len(run.steps),
            of_step=0,
            says="Write the mail",
            verdict="failed",
            verdict_by="none",
            reason=why,
        )
    )
    run.outcome = "stopped"
    await _save(uow, run)
    logger.info("%s: the mail was not written, so nothing was sent", run.id)
    return run


async def _save(uow: UnitOfWork, run: WorkflowRun) -> None:
    async with uow as unit:
        await unit.workflow_runs.save(run)
        await unit.commit()
