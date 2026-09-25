from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.ask_the_asker import DRAFTED
from sro.application.chat.mailbox import K_REMEMBER, SERVER
from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.chat.thread import Speaker
from sro.domain.execution.mail_job import (
    MAIL_INSTRUCTIONS,
    MAIL_SCHEMA,
    addresses_in,
    recipient_allowed,
)
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
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


async def write_the_mail(
    ctx: RequestContext,
    workflow: Workflow,
    values: Mapping[str, str],
    thread: str,
    *,
    tools: ToolCaller,
    asker: Asker,
    model: str,
) -> Written | str:
    conversation = await _conversation(ctx, tools, thread) if thread else []
    known = addresses_in(values.values()) | addresses_in(
        str(one.get("from") or "") for one in conversation
    )
    evidence = json.dumps(
        {
            "job": workflow.title,
            "what_it_does": workflow.narrative,
            "steps": [step.says for step in sorted(workflow.steps, key=lambda one: one.order)],
            "values": dict(values),
            "operator": ctx.principal_id.value,
            "conversation": [
                {
                    "from": str(one.get("from") or ""),
                    "subject": str(one.get("subject") or ""),
                    "body": str(one.get("body") or "")[:K_BODY],
                }
                for one in conversation[-K_MESSAGES:]
            ],
        },
        indent=2,
        ensure_ascii=False,
    )
    written = await asker.ask(
        model=model,
        instructions=MAIL_INSTRUCTIONS,
        evidence=evidence,
        schema=MAIL_SCHEMA,
    )
    data: Mapping[str, object] = written.data or {}
    to = " ".join(str(data.get("to") or "").split())
    body = str(data.get("body") or "").strip()
    if not body:
        return f"the mail could not be written: {written.error or 'the model said nothing'}"
    if not recipient_allowed(to, known):
        return (
            "the mail is written but names nobody this job was given to send it to"
            + (f" ({to})" if to else "")
            + " -- start it from the mail it answers, or give it a recipient"
        )
    latest = conversation[-1] if conversation else {}
    return Written(
        to=to,
        subject=" ".join(str(data.get("subject") or "").split()),
        body=body,
        thread=thread,
        in_reply_to=str(latest.get("rfc822_message_id") or ""),
    )


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
    write: Callable[[Workflow, Mapping[str, str], str], Awaitable[Written | str]]
    send: Callable[[Written], Awaitable[tuple[str, str]]]


async def draft_the_mail_job(
    ctx: RequestContext,
    run: WorkflowRun,
    workflow: Workflow,
    *,
    uow: UnitOfWork,
    tools: ToolCaller,
    asker: Asker,
    model: str,
    clock: Clock,
    ids: IdFactory,
) -> WorkflowRun:
    waiting = read_wait(run.awaiting) if run.awaiting else None
    thread = waiting.thread if waiting else ""
    written = await write_the_mail(
        ctx, workflow, run.values, thread, tools=tools, asker=asker, model=model
    )
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
    logger.info("%s: drafted %s's mail to %s", run.id, workflow.title, written.to)
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
    logger.info("%s: %s", run.id, why)
    return run


async def _save(uow: UnitOfWork, run: WorkflowRun) -> None:
    async with uow as unit:
        await unit.workflow_runs.save(run)
        await unit.commit()
