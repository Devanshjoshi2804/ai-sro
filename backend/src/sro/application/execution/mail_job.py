from __future__ import annotations

import json
import logging
import math
import secrets
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.mailbox import (
    K_REMEMBER,
    SERVER,
    NotSent,
    is_ours,
    send_as_this_system,
)
from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.application.shared.asking import ask
from sro.domain.chat.asking import said_yes, the_request
from sro.domain.chat.thread import Speaker
from sro.domain.execution.mail_job import (
    DRAFT_QUESTIONS,
    DRAFTED,
    K_SEND_WINDOW_S,
    K_SENT_THREADS,
    MAIL_BODY,
    ON_A_MAIL,
    SEND_A_MAIL,
    WHICH_MAIL,
    Allowed,
    JobRecipient,
    built_in,
    check_draft,
    is_mail_only,
    mailboxes,
    named_in,
    sent_from,
)
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import as_said, read_wait, waiting_on
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.prompts.write_mail import WRITE_MAIL
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.workflow import Workflow, ordered_cites

logger = logging.getLogger(__name__)

K_MESSAGES = 5

K_BODY = 2000

AWAITING_THE_PRESS = "drafted — read it in the conversation and press Send it"

WHAT_IT_SAYS = "What should the mail say?"

WHICH_ONE = (
    "Which mail is this about? Say words that find it in your mailbox -- who sent it, "
    "or words from its subject."
)


@dataclass(frozen=True, slots=True)
class Written:
    to: str
    subject: str
    body: str
    thread: str
    in_reply_to: str
    bcc: str = ""
    job: str = ""
    named: tuple[str, ...] = ()


class Unaddressed(str):
    __slots__ = ()


class Unwritten(str):
    draft: dict[str, str]


async def write_the_mail(
    ctx: RequestContext,
    workflow: Workflow,
    values: Mapping[str, str],
    thread: str,
    *,
    by_id: Mapping[str, Gesture],
    request: Sequence[str],
    uow: UnitOfWork,
    tools: ToolCaller,
    asker: Asker,
    shown: Mapping[str, str] | None = None,
) -> Written | str:
    conversation = await _conversation(ctx, tools, thread) if thread else []
    allowed = await _allowed(ctx, uow, tools, workflow, by_id)
    data = (
        shown
        if shown is not None
        else await _write(ctx, workflow, values, conversation, allowed, request, asker)
    )
    if isinstance(data, str):
        return f"the mail could not be written: {data}"
    to = " ".join(str(data.get("to") or "").split())
    subject = " ".join(str(data.get("subject") or "").split())
    body = str(data.get("body") or "").strip()
    if not body:
        return "the mail could not be written: the model said nothing"
    cited = data.get("cited")
    checked = check_draft(
        to=to,
        body=body,
        cited=[one for one in cited if isinstance(one, Mapping)] if isinstance(cited, list) else [],
        conversation=conversation,
        values=values,
        allowed=allowed,
        request=request,
        vouched=(body,) if shown is not None else (),
    )
    if checked.why:
        logger.info(
            "%s: the draft of %s was refused: %s", ctx.tenant_id.value, workflow.id, checked.logged
        )
        if checked.recipient:
            return Unaddressed(f"{checked.why} -- nothing was sent; who does this mail go to?")
        refused = Unwritten(f"{checked.why} -- nothing was sent")
        refused.draft = {"to": to, "subject": subject, "body": body}
        return refused
    latest = conversation[-1] if conversation else {}
    return Written(
        to=", ".join(checked.to),
        subject=subject,
        body=body,
        thread=thread,
        in_reply_to=str(latest.get("rfc822_message_id") or ""),
        bcc=", ".join(checked.bcc),
        job=workflow.id,
        named=tuple(
            one
            for one in (*checked.to, *checked.bcc)
            if one in named_in(request) and one not in allowed.to | allowed.bcc
        ),
    )


async def _write(
    ctx: RequestContext,
    workflow: Workflow,
    values: Mapping[str, str],
    conversation: Sequence[Mapping[str, object]],
    allowed: Allowed,
    request: Sequence[str],
    asker: Asker,
) -> Mapping[str, object] | str:
    written = await ask(
        asker,
        WRITE_MAIL,
        trusted={
            "job": workflow.title,
            "operator": ctx.principal_id.value,
            "sent_before": sorted(allowed.to | allowed.bcc),
            "request": list(request),
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
    return written.data or written.error or "the model said nothing"


async def _allowed(
    ctx: RequestContext,
    uow: UnitOfWork,
    tools: ToolCaller,
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
) -> Allowed:
    to: set[str] = set()
    bcc: set[str] = set()
    shown = [workflow]
    if built_in(workflow.id, ctx.tenant_id.value) is not None:
        shown, by_id = await _mail_jobs(ctx, uow)
    clicks = [click for job in shown for click in sent_from(job, by_id)]
    seen: Counter[str] = Counter()
    for clicked, named in clicks:
        threads = named or await _mails_found(
            ctx,
            tools,
            f"in:sent after:{math.floor(clicked - K_SEND_WINDOW_S)} "
            f"before:{math.ceil(clicked + K_SEND_WINDOW_S)}",
        )
        seen.update(named=bool(named), looked=not named)
        since = datetime.fromtimestamp(clicked, UTC) - K_REMEMBER
        read = [one for thread in threads for one in await _conversation(ctx, tools, thread)]
        sent = [
            one
            for one in read
            if one.get("sent") is True
            and abs(_seconds(one.get("sent_at")) - clicked) <= K_SEND_WINDOW_S
            and not one.get("marker")
            and not await is_ours(uow, ctx, one, since=since)
        ]
        seen.update(threads=len(threads), messages=len(read), in_window=len(sent))
        seen["none" if not sent else "several" if sent[1:] else "one"] += 1
        if len(sent) != 1:
            continue
        for key, into in (("to", to), ("cc", to), ("bcc", bcc)):
            into.update(mailboxes(str(sent[0].get(key) or "")) or ())
    logger.info(
        "%s: %s: %d Send click(s): %d named no thread, %d looked up in Sent, %d thread(s) read, "
        "%d message(s), %d sent in the window; %d found no sent mail, %d found more than one, "
        "%d granted",
        ctx.tenant_id.value,
        workflow.id,
        len(clicks),
        len(clicks) - seen["named"],
        seen["looked"],
        seen["threads"],
        seen["messages"],
        seen["in_window"],
        seen["none"],
        seen["several"],
        seen["one"],
    )
    async with uow as unit:
        for one in {workflow.id, *(job.id for job in shown)}:
            confirmed = await unit.workflows.recipients_for(ctx.tenant_id, one)
            to.update(named.address for named in confirmed)
    return Allowed(to=frozenset(to), bcc=frozenset(bcc - to))


async def _mail_jobs(
    ctx: RequestContext, uow: UnitOfWork
) -> tuple[list[Workflow], dict[str, Gesture]]:
    async with uow as unit:
        known = await unit.workflows.known(ctx.tenant_id)
        cites = tuple(sorted({one for job in known for one in ordered_cites(job)}))
        seen = await unit.gestures.gestures_for(ctx.tenant_id, ids=cites) if cites else ()
    by_id = {gesture.id: gesture for gesture in seen}
    return [job for job in known if is_mail_only(job, by_id)], by_id


async def _mails_found(ctx: RequestContext, tools: ToolCaller, words: str) -> tuple[str, ...]:
    found = await _answer(
        ctx, tools, "search_threads", {"query": words, "limit": str(K_SENT_THREADS)}
    )
    rows = found.get("messages")
    threads = [
        str((await _answer(ctx, tools, "get_message", {"id": row["id"]})).get("thread_id") or "")
        for row in (rows if isinstance(rows, list) else ())
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    ]
    return tuple(dict.fromkeys(one for one in threads if one))


def _seconds(value: object) -> float:
    return float(value) if isinstance(value, int | float) else math.inf


async def send_the_mail(
    ctx: RequestContext, uow: UnitOfWork, tools: ToolCaller, mail: Written, *, clock: Clock
) -> tuple[str, str]:
    try:
        answered = await send_as_this_system(
            ctx,
            uow,
            tools,
            {
                "to": mail.to,
                **({"bcc": mail.bcc} if mail.bcc else {}),
                "subject": mail.subject,
                "body": mail.body,
                "thread_id": mail.thread,
                "in_reply_to": mail.in_reply_to,
            },
            at=clock.now(),
        )
    except (ToolsUnavailable, NotSent) as gone:
        return "", f"the mailbox could not be reached, so nothing was sent: {gone}"
    try:
        said = json.loads(answered.text or "{}")
    except ValueError:
        said = {}
    sent_id = str(said.get("id") or "") if isinstance(said, dict) else ""
    if not sent_id:
        return "", f"Gmail did not say the mail went: {answered.text[:200]}"
    if mail.named:
        by = {"address": ", ".join(mail.named), "by": ctx.principal_id.value}
        await keep_the_named(ctx, uow, mail.job, by, at=clock.now())
    return sent_id, ""


@dataclass(frozen=True, slots=True)
class MailHand:
    write: Callable[
        [Workflow, Mapping[str, str], str, Mapping[str, Gesture], Sequence[str]],
        Awaitable[Written | str],
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
    shown: Mapping[str, str] | None = None,
) -> WorkflowRun:
    waiting = read_wait(run.awaiting) if run.awaiting else None
    thread = waiting.thread if waiting and workflow.id != SEND_A_MAIL else ""
    if workflow.id in ON_A_MAIL and not thread:
        return await _ask(ctx, uow, run, WHICH_MAIL, WHICH_ONE, clock=clock, ids=ids)
    written = await write_the_mail(
        ctx,
        workflow,
        run.values,
        thread,
        by_id=by_id,
        request=(*await the_operator_s_words(ctx, uow, run), *Progress.of(run.progress).told),
        uow=uow,
        tools=tools,
        asker=asker,
        shown=shown,
    )
    if isinstance(written, Unaddressed):
        return await _ask(ctx, uow, run, "recipient", written, clock=clock, ids=ids)
    if isinstance(written, Unwritten):
        draft = written.draft
        return await _ask(
            ctx,
            uow,
            run,
            MAIL_BODY,
            written,
            f"{written}. The draft said:\n\nTo: {draft['to']}\nSubject: {draft['subject']}\n\n"
            f"{draft['body']}\n\nSay yes to use exactly this draft, or write what the "
            f"mail should say instead.",
            clock=clock,
            ids=ids,
            draft=json.dumps(draft, ensure_ascii=False),
        )
    if isinstance(written, str):
        return await _ask(
            ctx, uow, run, MAIL_BODY, written, f"{written}. {WHAT_IT_SAYS}", clock=clock, ids=ids
        )

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
            **({"named": ", ".join(written.named)} if written.named else {}),
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
    rows = (await _answer(ctx, tools, "get_thread", {"id": thread})).get("messages")
    return [one for one in rows if isinstance(one, dict)] if isinstance(rows, list) else []


async def _answer(
    ctx: RequestContext, tools: ToolCaller, tool: str, arguments: Mapping[str, str]
) -> dict[str, object]:
    try:
        answered = await tools.call(ctx.tenant_id, ctx.principal_id, SERVER, tool, arguments)
    except ToolsUnavailable as gone:
        logger.info("%s: the mailbox could not answer %s: %s", ctx.tenant_id.value, tool, gone)
        return {}
    try:
        said = json.loads(answered.text)
    except ValueError:
        return {}
    return said if isinstance(said, dict) else {}


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
    asking = progress.asking
    if asking.get("kind") not in DRAFT_QUESTIONS or not asking.get("answered"):
        return run
    await keep_the_named(ctx, uow, workflow.id, asking, at=clock.now())
    said = asking.get("said", "")
    which = asking.get("kind") == WHICH_MAIL
    shown = json.loads(asking["draft"]) if said_yes(said) and asking.get("draft") else None
    if said and shown is None and not which:
        progress.told.append(said)
    was, progress.asking = run.progress, {}
    async with uow as unit:
        taken = await unit.workflow_runs.record_progress(
            ctx.tenant_id, run.id, progress.as_json(), was=was
        )
        await unit.commit()
    if not taken:
        return run
    run.progress = progress.as_json()
    if which:
        found = await _mails_found(ctx, tools, said)
        if len(found) != 1:
            asked = f"{len(found)} mail(s) in your mailbox matched those words. {WHICH_ONE}"
            return await _ask(ctx, uow, run, WHICH_MAIL, asked, clock=clock, ids=ids)
        run.awaiting = as_said(waiting_on(SERVER, found[0], now=clock.now()))
    return await draft_the_mail_job(
        ctx,
        run,
        workflow,
        by_id,
        uow=uow,
        tools=tools,
        asker=asker,
        clock=clock,
        ids=ids,
        shown=shown,
    )


async def the_operator_s_words(
    ctx: RequestContext, uow: UnitOfWork, run: WorkflowRun
) -> tuple[str, ...]:
    if not run.offer or not run.started_by:
        return ()
    async with uow as unit:
        thread = await unit.threads.holding(
            ctx.tenant_id, opened_by=PrincipalId(run.started_by), message_id=run.offer
        )
    return the_request(thread.messages, run.offer, run.workflow_id) if thread else ()


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


async def _ask(
    ctx: RequestContext,
    uow: UnitOfWork,
    run: WorkflowRun,
    kind: str,
    why: str,
    text: str = "",
    *,
    clock: Clock,
    ids: IdFactory,
    draft: str = "",
) -> WorkflowRun:
    progress = Progress.of(run.progress)
    progress.asking = {
        "id": f"q_{secrets.token_hex(16)}",
        "kind": kind,
        "text": text or why,
        "step": "0",
        **({"draft": draft} if draft else {}),
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
        text=text or why,
        speaker=Speaker.ASSISTANT,
        decision={
            "kind": "run_asks",
            "run_id": run.id,
            "question_id": progress.asking["id"],
            "asks": kind,
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
