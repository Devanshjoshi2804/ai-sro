from __future__ import annotations

import json
import logging

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.mailbox import SERVER, NotSent, send_as_this_system
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.chat.asking import Pending, pending_job
from sro.domain.chat.asking_the_asker import draft_for, worth_asking
from sro.domain.chat.thread import Message, Speaker, ThreadId
from sro.domain.execution.mail_job import DRAFTED, SENT
from sro.domain.execution.waiting import read_wait
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId

logger = logging.getLogger(__name__)


class DraftForTheAsker:
    def __init__(self, uow: UnitOfWork, tools: ToolCaller, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        pending: Pending,
        *,
        question: str,
        thread: str = "",
        run_id: str = "",
    ) -> bool:
        if not worth_asking(pending):
            return False
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id) if run_id else None
        waiting = read_wait(run.awaiting) if run else None
        conversation = thread.strip() or (waiting.thread if waiting else "")
        if not conversation:
            return False
        if run is not None and run.asked_the_asker:
            logger.info("%s: %s has already asked whoever sent it", ctx.tenant_id.value, run_id)
            return False
        operator = PrincipalId(run.started_by) if run and run.started_by else ctx.principal_id
        owner = RequestContext(ctx.tenant_id, operator)
        if await self._already_drafted(owner, conversation):
            logger.info("%s: %s is already drafted for", ctx.tenant_id.value, conversation)
            return False

        asked_by, replying_to, about = await self._who_asked(ctx, conversation)
        if not asked_by:
            logger.info(
                "%s: %s has nobody to ask -- the conversation names no sender",
                ctx.tenant_id.value,
                run_id,
            )
            return False

        subject, body = draft_for(pending, about=about, signed=ctx.principal_id.value)
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=operator,
            text=f"I can ask {asked_by}. This is what I would send — read it first.",
            speaker=Speaker.SYSTEM,
            about=conversation,
            decision={
                "kind": DRAFTED,
                "run_id": run_id,
                "to": asked_by,
                "subject": subject,
                "body": body,
                "thread": conversation,
                "in_reply_to": replying_to,
                "question": question,
            },
        )
        logger.info(
            "%s: drafted a mail to %s about %s",
            ctx.tenant_id.value,
            asked_by,
            run_id or conversation,
        )
        return True

    async def _already_drafted(self, owner: RequestContext, conversation: str) -> bool:
        thread = await ReadThreads(self._uow).asking(owner, conversation)
        if thread is None:
            return False
        return any(
            isinstance(message.decision, dict)
            and message.decision.get("kind") == DRAFTED
            and message.decision.get("thread") == conversation
            for message in thread.messages
        )

    async def _who_asked(self, ctx: RequestContext, thread: str) -> tuple[str, str, str]:
        try:
            answered = await self._tools.call(
                ctx.tenant_id, ctx.principal_id, SERVER, "get_thread", {"id": thread}
            )
        except ToolsUnavailable as gone:
            logger.info("%s: the conversation could not be read: %s", ctx.tenant_id.value, gone)
            return "", "", ""
        try:
            said = json.loads(answered.text)
        except ValueError:
            return "", "", ""
        rows = said.get("messages") if isinstance(said, dict) else None
        if not isinstance(rows, list) or not rows:
            return "", "", ""
        first = rows[0] if isinstance(rows[0], dict) else {}
        return (
            _address(str(first.get("from") or "")),
            str(first.get("rfc822_message_id") or ""),
            " ".join(str(first.get("subject") or "").split()),
        )


def _address(sender: str) -> str:
    said = sender.strip()
    if "<" in said and ">" in said:
        said = said[said.index("<") + 1 : said.index(">")].strip()
    return said if "@" in said else ""


class SendTheDraft:
    def __init__(self, uow: UnitOfWork, tools: ToolCaller, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, thread_id: ThreadId, message_id: str) -> str:
        async with self._uow as uow:
            thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)
            if thread.opened_by != ctx.principal_id:
                raise Conflict("only the operator who opened this thread acts in it")
            draft = _the_draft(thread.messages, message_id)
            if draft is None:
                logger.info("%s: no draft to send under %s", ctx.tenant_id.value, message_id)
                return ""
            question = str(draft.get("question") or "")
            if not question or pending_job(thread.messages, question) is None:
                logger.info(
                    "%s: the question the draft %s asks was answered",
                    ctx.tenant_id.value,
                    message_id,
                )
                return ""
            if not await self._claim(uow, ctx, message_id):
                logger.info(
                    "%s: the draft %s has already been sent", ctx.tenant_id.value, message_id
                )
                return ""
            await uow.commit()

        run_id = str(draft.get("run_id") or "")
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id) if run_id else None
            if run is not None:
                if run.asked_the_asker:
                    logger.info("%s: %s was already asked", ctx.tenant_id.value, run_id)
                    return ""
                run.asked_the_asker = True
                await uow.workflow_runs.save(run)
                await uow.commit()

        to = str(draft.get("to") or "")
        try:
            await send_as_this_system(
                ctx,
                self._uow,
                self._tools,
                {
                    "to": to,
                    "subject": str(draft.get("subject") or ""),
                    "body": str(draft.get("body") or ""),
                    "thread_id": str(draft.get("thread") or ""),
                    "in_reply_to": str(draft.get("in_reply_to") or ""),
                },
                at=self._clock.now(),
            )
        except (ToolsUnavailable, NotSent) as gone:
            logger.warning(
                "%s: the mail to %s may not have gone: %s", ctx.tenant_id.value, to, gone
            )
            await self._say(
                ctx,
                thread_id,
                f"I could not reach the mailbox to write to {to}.",
                run_id,
                message_id,
                to,
                sent=False,
            )
            return ""

        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
        await self._say(
            ctx,
            thread_id,
            f"Asked {to}. I will carry on when they reply."
            if pending_job(thread.messages, question) is not None
            else f"Asked {to}, but the question was answered here meanwhile, "
            "so their reply is not needed.",
            run_id,
            message_id,
            to,
            sent=True,
        )
        logger.info("%s: asked %s about %s", ctx.tenant_id.value, to, run_id)
        return to

    async def _claim(self, uow: UnitOfWork, ctx: RequestContext, message_id: str) -> bool:
        return await uow.tool_calls.remember(
            ctx.tenant_id,
            f"draft:{message_id}",
            tool="a mail drafted for whoever asked, sent once",
            at=self._clock.now(),
        )

    async def _say(
        self,
        ctx: RequestContext,
        thread_id: ThreadId,
        text: str,
        run_id: str = "",
        draft_id: str = "",
        to: str = "",
        *,
        sent: bool,
    ) -> None:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.SYSTEM,
                    text=text,
                    said_at=self._clock.now(),
                    decision={
                        "kind": SENT,
                        "run_id": run_id,
                        "draft_id": draft_id,
                        "to": to,
                        "sent": sent,
                    },
                )
            )
            await uow.threads.save(thread)
            await uow.commit()


def _the_draft(messages: object, message_id: str) -> dict[str, object] | None:
    for message in reversed(list(messages if isinstance(messages, tuple | list) else ())):
        decision = getattr(message, "decision", None)
        if not isinstance(decision, dict) or decision.get("kind") != DRAFTED:
            continue
        if str(getattr(message, "id", "")) == str(message_id):
            return decision
    return None


__all__ = ["DRAFTED", "SENT", "DraftForTheAsker", "SendTheDraft"]
