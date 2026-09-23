"""A mail job, drafted through the mailbox's API and sent on a press.

See `domain/execution/mail_job.py` for why a job that is nothing but mail is not
replayed through Gmail's page. This is the half that does it: read the
conversation the job answers, have a model write the mail, and put it in front
of the operator as the draft card they already know -- `SendTheDraft` sends it,
once, when they press, and finishes the run on Gmail's answer.

Nothing here sends. The tool caller is used to READ the conversation, and the
only write is into the operator's own thread.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.ask_the_asker import DRAFTED, SERVER
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
"""How much of a conversation the model reads: the latest few messages. A
reply answers what was said last; a thread three weeks deep is not context,
it is noise the model will quote from."""

K_BODY = 2000
"""How much of one message it reads. Enough for a request and its quoted
history to be recognisable; a newsletter is not what is being answered."""

AWAITING_THE_PRESS = "drafted — read it in the conversation and press Send it"


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
    """Write the mail this job sends and park the run on the operator's press.

    Ends `stopped` with one step `awaiting`, which is what a run waiting on a
    person already looks like -- and which, unlike `running`, does not hold
    this browser: the operator's other jobs are not blocked by a mail they
    have not read yet.
    """
    waiting = read_wait(run.awaiting) if run.awaiting else None
    thread = waiting.thread if waiting else ""
    conversation = await _conversation(ctx, tools, thread) if thread else []

    known = addresses_in(run.values.values()) | addresses_in(
        str(one.get("from") or "") for one in conversation
    )
    evidence = json.dumps(
        {
            "job": workflow.title,
            "what_it_does": workflow.narrative,
            "steps": [step.says for step in sorted(workflow.steps, key=lambda one: one.order)],
            "values": dict(run.values),
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
    subject = " ".join(str(data.get("subject") or "").split())
    body = str(data.get("body") or "").strip()

    if not body:
        return await _stop(
            uow, run, f"the mail could not be written: {written.error or 'the model said nothing'}"
        )
    # Never an address nobody gave. A mail to the wrong person is the one step
    # of this job that cannot be taken back, and the model is only allowed to
    # copy a recipient -- from the values, or from the conversation it answers.
    if not recipient_allowed(to, known):
        return await _stop(
            uow,
            run,
            "the mail is written but names nobody this job was given to send it to"
            + (f" ({to})" if to else "")
            + " -- start it from the mail it answers, or give it a recipient",
        )

    latest = conversation[-1] if conversation else {}
    await SayWhatHappened(uow, clock, ids).execute(
        ctx,
        for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
        text=f"{workflow.title} — this is the mail I would send to {to}. Read it first.",
        # SYSTEM for the reason `DraftForTheAsker` gives: a draft standing where
        # the assistant's question should be would eat the operator's next
        # sentence.
        speaker=Speaker.SYSTEM,
        decision={
            "kind": DRAFTED,
            "run_id": run.id,
            "to": to,
            "subject": subject,
            "body": body,
            "thread": thread,
            "in_reply_to": str(latest.get("rfc822_message_id") or ""),
            # What makes this the job's own mail rather than a question to
            # whoever asked: `SendTheDraft` finishes the run on it.
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
            sent={"kind": "mail.draft", "payload": {"to": to, "subject": subject}},
        )
    )
    run.outcome = "stopped"
    await _save(uow, run)
    logger.info("%s: drafted %s's mail to %s", run.id, workflow.title, to)
    return run


async def _conversation(
    ctx: RequestContext, tools: ToolCaller, thread: str
) -> list[dict[str, object]]:
    """The messages of the conversation this job answers, oldest first."""
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
