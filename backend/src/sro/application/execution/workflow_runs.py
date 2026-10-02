from __future__ import annotations

import logging
import math
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import datetime
from urllib.parse import urlencode

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.feedback import RecordFeedback
from sro.application.chat.mailbox import server_for
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.declared import declared_limits, names_of, screen_for
from sro.application.execution.effects import wrote
from sro.application.execution.gather import GatherContext
from sro.application.execution.mail_job import (
    MailHand,
    Written,
    draft_the_mail_job,
    redraft_the_mail_job,
    send_the_mail,
    write_the_mail,
)
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.read_runs import NOT_IN_A_BROWSER_HERE, CannotStop
from sro.application.execution.run_secrets import RunSecrets, WatchingChannel
from sro.application.execution.run_workflow import GatherValues, KnownFields, run_workflow
from sro.application.execution.stops import Stops
from sro.application.intent.spend import over_cap
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.application.observation.register import refuse_unless_itself
from sro.application.ports.channel import Channel
from sro.application.ports.durable import DurableExecution
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.pool import BrowserPool
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.vault import CredentialVault
from sro.application.shared.refusals import OverCap, RunRefused
from sro.application.skill.job_facts import job_facts
from sro.domain.chat.asking import (
    NEEDS,
    Pending,
    also_set,
    asking_state,
    cannot_without,
    pending_job,
    question,
    refusal_question,
    still_to_ask,
)
from sro.domain.chat.thread import K_ASKING, Speaker
from sro.domain.execution.account import LIVE
from sro.domain.execution.compiled import why_not
from sro.domain.execution.field_classes import field_classes
from sro.domain.execution.gathering import Gathered
from sro.domain.execution.learned_step import limits_for
from sro.domain.execution.mail_job import built_in, is_mail_only
from sro.domain.execution.progress import Progress, run_budget
from sro.domain.execution.takeover import Took, take_over
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import (
    RunStep,
    WorkflowRun,
    already_running,
    answers_for,
    named_by,
    new_run_id,
    pin,
    refused_by,
)
from sro.domain.execution.write_plan import begins_again_at, seen_values
from sro.domain.knowledge.entry import EntryKind
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import Conflict, DomainError, NotFound
from sro.domain.shared.identifiers import DeviceId, PrincipalId
from sro.domain.skill.learned import demanded, offerable
from sro.domain.skill.reversals import addresses, asks_for, identifies, undoes
from sro.domain.skill.shape import resumes_at
from sro.domain.skill.workflow import MAIN, Workflow, cited_ids, ordered_cites


def _on_the_mail(server: str, thread: str, *, ours: str) -> dict[str, str]:
    return {"thread": thread.strip()} if server == ours and thread.strip() else {}


__all__ = [
    "AbortWorkflowRun",
    "ApproveWorkflowStep",
    "GetWorkflowRun",
    "ListWorkflowRuns",
    "NotDrivingThisRun",
    "RunRefused",
    "StartWorkflowRun",
]

logger = logging.getLogger(__name__)


DraftsForTheAsker = Callable[[RequestContext, str, Pending, str], Awaitable[bool]]


K_EVERY_FORM = 400


def _asking(needs: Sequence[str], title: str, limits: Mapping[str, int]) -> str:
    capped = [name for name in needs if name in limits]
    if not capped:
        return f"I could not find {', '.join(needs)} for {title}. "
    said = ", ".join(f"{name} holds {limits[name]} characters" for name in capped)
    rest = [name for name in needs if name not in limits]
    return f"For {title}, {said} — longer than what I was given. " + (
        f"I could not find {', '.join(rest)} either. " if rest else ""
    )


STILL_UPLOADING = "your recent work is still uploading; press again in a moment"


class StartWorkflowRun:
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        channel: Channel,
        asker: Asker | None,
        clock: Clock,
        cap_usd: float,
        stops: Stops,
        approvals: Approvals,
        one_time_secrets: OneTimeSecrets,
        verified_writes: tuple[VerifiedWrite, ...] = (),
        vault: CredentialVault | None = None,
        retrieve: Retrieve | None = None,
        gather: GatherContext | None = None,
        ids: IdFactory | None = None,
        asker_drafts: DraftsForTheAsker | None = None,
        durable: DurableExecution | None = None,
        steel_tenants: frozenset[str] = frozenset(),
        feedback: RecordFeedback | None = None,
        servers: Mapping[str, str],
    ) -> None:
        self._servers = servers
        self._uow = uow
        self._feedback = feedback
        self._durable = durable
        self._steel_tenants = steel_tenants
        self._asker_drafts: DraftsForTheAsker | None = asker_drafts
        self._vault = vault
        self._one_time_secrets = one_time_secrets
        self._retrieve = retrieve
        self._gather = gather
        self._ids = ids
        self._channel = channel
        self._asker = asker
        self._clock = clock
        self._cap_usd = cap_usd
        self._stops = stops
        self._approvals = approvals
        self._verified_writes = verified_writes

    def mail_server(self, ctx: RequestContext) -> str:
        return server_for(ctx.tenant_id.value, self._servers)

    def _on_the_mail(
        self, ctx: RequestContext, conversation: tuple[str, str], mail: Mapping[str, str] | None
    ) -> dict[str, str] | None:
        ours = self.mail_server(ctx)
        envelope = {**_on_the_mail(*conversation, ours=ours), **(mail or {})}
        return {**envelope, "server": ours} if envelope.get("thread") else envelope or None

    def runs_on_steel(self, ctx: RequestContext) -> bool:
        return self._durable is not None and ctx.tenant_id.value in self._steel_tenants

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        device_id: DeviceId | None,
        values: Mapping[str, str],
        live: bool,
        allow_focus: bool,
        watched: bool = False,
        from_step: int = 0,
        matched: int | None = None,
        items: Sequence[Mapping[str, str]] = (),
        run_id: str | None = None,
        conversation: tuple[str, str] = ("", ""),
        undoes_run: str = "",
        offer: str = "",
        mail: Mapping[str, str] | None = None,
        took_over: Took | None = None,
        device_secret: str = "",
        then: Callable[[UnitOfWork, WorkflowRun], Awaitable[None]] | None = None,
    ) -> WorkflowRun:
        asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        steel = self.runs_on_steel(ctx) and built_in(workflow_id, ctx.tenant_id.value) is None
        undone: WorkflowRun | None = None
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            if not steel and device_id is not None:
                await self._free(uow, ctx, device_id)
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow)))
            )
            by_id = {gesture.id: gesture for gesture in cited}
            if not steel and device_id is None and not is_mail_only(workflow, by_id):
                device_id = await self._their_browser(uow, ctx)
                await self._free(uow, ctx, device_id)
            given = {name: value.strip() for name, value in values.items() if value.strip()}
            things = (
                [
                    {name: value.strip() for name, value in item.items() if value.strip()}
                    for item in items
                ]
                if workflow.repeat is not None
                else []
            )
            if steel and things:
                raise RunRefused("a Steel run does one thing per run; a list is not supported yet")
            supplied = [{**given, **thing} for thing in things] or [given]
            absent = sorted(
                str(declared["name"])
                for declared in workflow.parameters
                if declared.get("name")
                and demanded(declared)
                and any(str(declared["name"]) not in one for one in supplied)
            )
            blank = sorted(
                name
                for one in ([values, *items] if workflow.repeat is not None else [values])
                for name, value in one.items()
                if not value.strip() and any(d.get("name") == name for d in workflow.parameters)
            )
            if blank:
                raise RunRefused(f"this job needs a value for: {', '.join(blank)}")
            if absent and (self._gather is None or things):
                raise RunRefused(f"this job needs a value for: {', '.join(absent)}")
            if not workflow.steps:
                raise RunRefused("this job has no steps")
            if matched is not None:
                from_step = resumes_at(workflow, by_id, matched)
            last = max(step.order for step in workflow.steps)
            if isinstance(from_step, bool) or not 0 <= from_step <= last:
                raise RunRefused(f"from_step must be a step of this job (0..{last})")
            first_progress: dict[str, object] = {}
            check_from = from_step
            if steel and took_over is not None and device_id is not None:
                device = await uow.devices.get(ctx.tenant_id, device_id)
                refuse_unless_itself(device, device_secret, device_id)
                if device.principal_id != ctx.principal_id:
                    raise NotFound(f"device {device_id} was not found")
                seen = await uow.gestures.gestures_for(
                    ctx.tenant_id,
                    stream_id=device_id.value,
                    after=math.nextafter(took_over.since, -math.inf),
                )
                if not any(one.at >= took_over.newest for one in seen):
                    raise RunRefused(STILL_UPLOADING)
                took = take_over(
                    workflow, by_id, matched=matched or 0, took=took_over, seen=seen, values=given
                )
                first_progress = took.progress().as_json()
                ordered = sorted(workflow.steps, key=lambda step: step.order)
                check_from = (
                    ordered[took.replay_from].order if took.replay_from < len(ordered) else last + 1
                )
            elif steel and from_step and matched is None:
                raise RunRefused(
                    "this job stopped part-way in your browser, and a Steel run cannot tell "
                    "what was already done there; ask for it afresh to run it from the start"
                )
            elif steel and from_step:
                raise RunRefused(
                    "this press did not say which of your gestures it counted, so a Steel run "
                    "cannot tell what you already did; update the extension and press again"
                )
            if undoes_run.strip():
                already = await uow.workflow_runs.taken_back_by(ctx.tenant_id, undoes_run.strip())
                if already is not None:
                    raise RunRefused(f"{undoes_run.strip()} was already taken back by {already}")
                undone = await uow.workflow_runs.get(ctx.tenant_id, undoes_run.strip())
            (facts,) = await job_facts(
                uow, ctx.tenant_id, [workflow], now=now, values=given, from_step=check_from
            )
            if not facts.compiled.runnable:
                raise RunRefused(
                    f"this job cannot run yet: {'; '.join(why_not(facts.compiled.reasons))}"
                )
            run = WorkflowRun(
                id=run_id or new_run_id(),
                tenant=ctx.tenant_id.value,
                workflow_id=workflow.id,
                device_id="" if device_id is None or steel else device_id.value,
                executor="steel" if steel else "extension",
                values=given,
                started_by=ctx.principal_id.value,
                live=live,
                allow_focus=allow_focus,
                watched=watched,
                started_at=now.isoformat(),
                from_step=from_step,
                items=things,
                awaiting=as_said(waiting_on(*conversation, now=now)),
                undoes_run=undoes_run.strip() or None,
                offer=offer.strip() or None,
                progress=first_progress,
                pinned=pin(workflow),
                mail=self._on_the_mail(ctx, conversation, mail),
            )
            await uow.workflow_runs.save(run)
            if then is not None:
                await then(uow, run)
            await uow.commit()
        if undone is not None and self._feedback is not None:
            # Every way to take a run back comes through here (the brain's, the panel's).
            await self._feedback.undone(ctx, undone, run)
        return run

    async def _free(self, uow: UnitOfWork, ctx: RequestContext, device_id: DeviceId) -> None:
        if device_id not in self._channel.online(ctx.tenant_id):
            raise Conflict(f"{device_id.value} is not connected")
        busy = await uow.workflow_runs.in_flight(ctx.tenant_id, device_id)
        if busy is not None:
            raise Conflict(already_running(device_id.value, busy))

    async def _their_browser(self, uow: UnitOfWork, ctx: RequestContext) -> DeviceId:
        online = set(self._channel.online(ctx.tenant_id))
        theirs = [
            device
            for device in await uow.devices.list_for_tenant(ctx.tenant_id)
            if device.id in online
            and device.principal_id == ctx.principal_id
            and not device.revoked
        ]
        if not theirs:
            raise Conflict("none of your browsers is connected")
        return max(theirs, key=lambda device: device.last_seen_at).id

    async def _a_mail_job(
        self, ctx: RequestContext, run: WorkflowRun
    ) -> tuple[Workflow, dict[str, Gesture]] | None:
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id, ids=tuple(ordered_cites(workflow))
            )
        by_id = {gesture.id: gesture for gesture in cited}
        return (workflow, by_id) if is_mail_only(workflow, by_id) else None

    async def answered(self, ctx: RequestContext, run_id: str) -> None:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        mail = await self._a_mail_job(ctx, run) if run is not None else None
        if run is None or mail is None or self._gather is None or self._ids is None:
            return
        await redraft_the_mail_job(
            ctx,
            run,
            mail[0],
            mail[1],
            uow=self._uow,
            tools=self._gather.tools,
            asker=asker_or_refuse(self._asker),
            clock=self._clock,
            ids=self._ids,
            servers=self._servers,
        )

    async def start_on_steel(self, ctx: RequestContext, run: WorkflowRun) -> bool:
        try:
            if self._durable is None:
                raise RunRefused("this process cannot start a Steel run")
            async with self._uow as uow:
                workflow = (
                    run.pinned
                    if run.pinned is not None
                    else await uow.workflows.get(ctx.tenant_id, run.workflow_id)
                )
                cited = await uow.gestures.gestures_for(
                    ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow)))
                )
            await self._durable.start_run(
                ctx,
                run_id=run.id,
                budget_s=run_budget(workflow, {one.id: one for one in cited}),
            )
        except Exception as error:
            logger.exception("%s: a Steel run could not be handed to Temporal", run.id)
            await self._close(ctx, run.id, f"{type(error).__name__}: {error}")
            return False
        return True

    async def perform(self, ctx: RequestContext, run: WorkflowRun) -> None:
        if run.executor == "steel":
            await self.start_on_steel(ctx, run)
            return
        try:
            asker = asker_or_refuse(self._asker)
            mail = await self._a_mail_job(ctx, run)
            if mail is not None and self._gather is not None and self._ids is not None:
                await draft_the_mail_job(
                    ctx,
                    run,
                    mail[0],
                    mail[1],
                    uow=self._uow,
                    tools=self._gather.tools,
                    asker=asker,
                    clock=self._clock,
                    ids=self._ids,
                    servers=self._servers,
                )
                return
            async with self._uow as uow:
                workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
                title = workflow.title
                learned = await uow.workflows.learned_writes(ctx.tenant_id)
                secrets = RunSecrets(self._vault, self._one_time_secrets, run_id=run.id)
                done = await run_workflow(
                    uow,
                    workflow,
                    cap_usd=self._cap_usd,
                    tenant_id=ctx.tenant_id,
                    values=run.values,
                    channel=WatchingChannel(self._channel, secrets),
                    device_id=DeviceId(run.device_id),
                    asker=asker,
                    live=run.live,
                    allow_focus=run.allow_focus,
                    watched=run.watched,
                    started_by=run.started_by,
                    stops=self._stops,
                    approvals=self._approvals,
                    run_id=run.id,
                    from_step=run.from_step,
                    items=run.items,
                    verified_writes=self._verified_writes + learned,
                    secret_for=secrets,
                    known_fields=None if self._retrieve is None else self._known_fields(ctx),
                    gather_values=(
                        None
                        if self._gather is None
                        else self._gathering(ctx, workflow.title, seen_values(workflow))
                    ),
                    mail=self._mail_hand(ctx, asker),
                    step_ended=secrets.step_ended,
                )
        except Exception as error:
            logger.exception("a run in an operator's browser could not be finished")
            await self._close(ctx, run.id, f"{type(error).__name__}: {error}")
        else:
            await secrets.finished()
            await self._settle_the_wait(ctx, done)
            await self.ask_for_values(ctx, done, title)

    async def _settle_the_wait(self, ctx: RequestContext, run: WorkflowRun) -> None:
        if not run.awaiting:
            return
        async with self._uow as uow:
            saved = await uow.workflow_runs.get(ctx.tenant_id, run.id)
            if saved is None or saved.needs:
                return
            saved.awaiting = None
            await uow.workflow_runs.save(saved)
            await uow.commit()

    async def _no_longer_waiting(self, ctx: RequestContext, run_id: str) -> None:
        async with self._uow as uow:
            saved = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if saved is None:
                return
            saved.needs = []
            saved.awaiting = None
            await uow.workflow_runs.save(saved)
            await uow.commit()

    async def ask_for_values(self, ctx: RequestContext, run: WorkflowRun, title: str) -> None:
        if not run.needs or self._ids is None:
            return
        async with self._uow as uow:
            learnt = await uow.workflows.learned_for(run.workflow_id)
            workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
            cited = (
                await uow.gestures.gestures_for(
                    ctx.tenant_id,
                    ids=tuple(sorted({one for step in workflow.steps for one in step.cites})),
                )
                if workflow
                else ()
            )
        by_id = {gesture.id: gesture for gesture in cited}
        steps = workflow.steps if workflow else []
        declared = await declared_limits(
            self._uow,
            ctx.tenant_id,
            names_of(workflow) if workflow else [],
            await screen_for(self._uow, ctx.tenant_id, workflow) if workflow else "",
        )
        limits = limits_for(steps, learnt, declared)
        fields = (
            field_classes(workflow, by_id, {one.ord: one for one in learnt}, declared)
            if workflow
            else ()
        )
        operator = PrincipalId(run.started_by) if run.started_by else ctx.principal_id
        owner = RequestContext(ctx.tenant_id, operator)
        envelope = dict(run.mail or {})
        mail_thread = envelope.pop("thread", "")
        envelope.pop("server", None)
        async with self._uow as uow:
            named = await uow.threads.naming(ctx.tenant_id, opened_by=operator, run_id=run.id)
        thread = named or await ReadThreads(self._uow).current(owner)
        # A run started by an answer in an ask chat asks again in that chat: its
        # own id would open another, and the question would leave its history.
        asked_in = named.id if named is not None and named.id.value.startswith(K_ASKING) else None
        # Where this run's question lives: the ask chat it was started from, else its own.
        chat = (
            named
            if asked_in is not None
            else await ReadThreads(self._uow).asking(owner, mail_thread or run.id)
        )
        standing_here = next(
            (
                one
                for one in (chat.messages if chat is not None else ())
                if (one.decision or {}).get("kind") == NEEDS
                and (one.decision or {}).get("from_run") == run.id
            ),
            None,
        )
        if standing_here is not None:
            # Asked already (a retried finish): never twice, but a draft the worker lost
            # after the question is made now; the drafter makes one draft per question.
            question_id = str(standing_here.id.value)
            rebuilt = pending_job(chat.messages, question_id) if chat else None
            if self._asker_drafts is not None and rebuilt is not None:
                try:
                    await self._asker_drafts(ctx, run.id, rebuilt, question_id)
                except Exception:
                    logger.exception("%s could not be drafted a mail about", run.id)
            return
        refusal = refused_by(run)
        pending = still_to_ask(
            Pending(
                workflow_id=run.workflow_id,
                title=title,
                values=dict(run.values),
                missing=tuple(run.needs),
                items=tuple(dict(one) for one in run.items),
                watched=run.watched,
                limits=limits,
                mail_thread=mail_thread,
                offered=offerable(workflow.parameters, run.values) if workflow else (),
                from_step=(
                    begins_again_at(workflow, by_id, stopped_at=run.steps[-1].order)
                    if workflow and run.steps
                    else 0
                ),
                options={
                    one.name: one.limits.options
                    for one in fields
                    if one.limits.options and one.name in run.needs
                },
                refused=dict.fromkeys(run.needs, refusal) if refusal else {},
                changing=bool(
                    refusal
                    and workflow
                    and len(run.needs) > 1
                    and not named_by(workflow, run.values, refusal)
                ),
            ),
            thread.messages if thread else (),
        )
        if pending.without:
            await self._no_longer_waiting(ctx, run.id)
            said, noted = cannot_without(pending, ran=True)
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=operator,
                text=said,
                speaker=Speaker.ASSISTANT,
                decision=noted,
                about=mail_thread or run.id,
                in_thread=asked_in,
            )
            return
        asked = await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=operator,
            about=mail_thread or run.id,
            in_thread=asked_in,
            text=(
                refusal_question(pending, refusal, also_set(pending))
                if refusal
                else _asking(pending.missing, title, limits)
                + (f"{also} " if (also := also_set(pending)) else "")
                + question(pending)
            ),
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": NEEDS,
                "workflow_id": pending.workflow_id,
                "title": pending.title,
                "values": dict(pending.values),
                "missing": list(pending.missing),
                "items": [dict(one) for one in pending.items],
                "watched": pending.watched,
                "limits": dict(limits),
                "offered": [list(one) for one in pending.offered],
                "from_step": pending.from_step,
                "from_run": run.id,
                "mail_thread": mail_thread,
                **({"mail": envelope} if envelope else {}),
                **asking_state(pending),
            },
        )
        if self._asker_drafts is not None:
            try:
                await self._asker_drafts(ctx, run.id, pending, asked)
            except Exception:
                logger.exception("%s could not be drafted a mail about", run.id)

    def _mail_hand(self, ctx: RequestContext, asker: Asker) -> MailHand | None:
        if self._gather is None:
            return None
        tools = self._gather.tools

        async def write(
            workflow: Workflow,
            values: Mapping[str, str],
            thread: str,
            by_id: Mapping[str, Gesture],
            request: Sequence[str],
        ) -> Written | str:
            return await write_the_mail(
                ctx,
                workflow,
                values,
                thread,
                by_id=by_id,
                request=request,
                uow=self._uow,
                tools=tools,
                asker=asker,
                servers=self._servers,
            )

        async def send(mail: Written) -> tuple[str, str]:
            return await send_the_mail(
                ctx, self._uow, tools, mail, clock=self._clock, servers=self._servers
            )

        return MailHand(write=write, send=send)

    def _gathering(
        self, ctx: RequestContext, job: str, seen: Mapping[str, frozenset[str]]
    ) -> GatherValues:

        async def look(wanted: Sequence[str]) -> Gathered:
            return await self._gather.execute(  # type: ignore[union-attr]
                ctx,
                job=job,
                wanted=wanted,
                seen={name: tuple(sorted(values)) for name, values in seen.items()},
            )

        return look

    def _known_fields(self, ctx: RequestContext) -> KnownFields:

        async def look(
            keys: tuple[str, ...], screen: str = ""
        ) -> Mapping[str, Mapping[str, object]]:
            if not keys:
                return {}
            found = await self._retrieve.execute(  # type: ignore[union-attr]
                ctx,
                Question(text=" ".join(keys), kinds=(EntryKind.FIELD,), limit=len(keys) * 4),
            )
            known: dict[str, dict[str, object]] = {
                entry.key: dict(entry.body)
                for entry in found
                if entry.key in keys and isinstance(entry.body, Mapping)
            }
            for slot, seen in (await self._forms(ctx, screen)).items():
                known.setdefault(slot, {}).update(seen)
            return known

        return look

    async def _forms(self, ctx: RequestContext, screen: str) -> Mapping[str, Mapping[str, object]]:
        if not screen.strip():
            return {}
        found = await self._retrieve.execute(  # type: ignore[union-attr]
            ctx, Question(text="", kinds=(EntryKind.FORM,), limit=K_EVERY_FORM)
        )
        seen: dict[str, dict[str, object]] = {}
        for entry in found:
            route = (entry.key or "").rstrip("/")
            if not route or route not in screen:
                continue
            fields = (entry.body or {}).get("fields")
            if not isinstance(fields, list):
                continue
            for one in fields:
                if not isinstance(one, Mapping):
                    continue
                slot = one.get("field")
                if not isinstance(slot, str):
                    continue
                said: dict[str, object] = {"observed": True}
                if isinstance(one.get("label"), str):
                    said["labels"] = [one["label"]]
                if isinstance(one.get("maxLength"), int) and not isinstance(
                    one.get("maxLength"), bool
                ):
                    said["max_length"] = one["maxLength"]
                if one.get("required") is True:
                    said["required"] = True
                seen.setdefault(slot, {}).update(said)
        return seen

    async def _close(self, ctx: RequestContext, run_id: str, reason: str) -> None:
        try:
            async with self._uow as uow:
                saved = await uow.workflow_runs.get(ctx.tenant_id, run_id)
                if saved is None or saved.outcome != "running":
                    return
                if saved.steps:
                    last = saved.steps[-1]
                    last.verdict, last.verdict_by, last.reason = "failed", "none", reason
                else:
                    saved.steps.append(
                        RunStep(
                            order=0,
                            says="",
                            verdict="failed",
                            verdict_by="none",
                            reason=reason,
                        )
                    )
                saved.outcome = "failed"
                saved.finished_at = self._clock.now().isoformat()
                await uow.workflow_runs.save(saved)
                await uow.commit()
        except Exception:
            logger.exception("and its row could not be closed either")


class ListWorkflowRuns:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str | None,
        limit: int,
        awaiting: bool,
        mine: bool = False,
    ) -> tuple[WorkflowRun, ...]:

        async with self._uow as uow:
            parked: frozenset[str] | None = None
            if awaiting:
                parked = frozenset(
                    run_id for run_id, _, _ in await uow.workflow_runs.awaiting(ctx.tenant_id)
                )
            runs = await uow.workflow_runs.recent(
                ctx.tenant_id, limit=limit, workflow_id=workflow_id, ids=parked
            )
        return (
            tuple(run for run in runs if answers_for(run, ctx.principal_id.value)) if mine else runs
        )


class GetWorkflowRun:
    def __init__(self, uow: UnitOfWork, *, pool: BrowserPool | None = None) -> None:
        self._uow = uow
        self._pool = pool

    async def live_view_for(self, ctx: RequestContext, run: WorkflowRun) -> str:
        progress = Progress.of(run.progress)
        tab = progress.tabs.get(MAIN, "")
        if self._pool is None or run.executor != "steel" or run.outcome != "running" or not tab:
            return ""
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, progress.lease)
        if lease is None or lease.state not in LIVE:
            return ""
        try:
            viewer = await self._pool.live_view_url(lease.container_url, lease.steel_session_id)
        except Exception:
            # A link to watch by is never worth failing the read of the run.
            logger.warning("%s: no live view for its Steel session", run.id, exc_info=True)
            return ""
        if not viewer:
            return ""
        joiner = "&" if "?" in viewer else "?"
        return f"{viewer}{joiner}{urlencode({'pageId': tab, 'interactive': 'false'})}"

    async def execute(self, ctx: RequestContext, *, run_id: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                raise NotFound("no such run")
            return run

    async def undo_for(self, ctx: RequestContext, run: WorkflowRun) -> tuple[str, str, str] | None:
        if run.outcome == "running" or not any(step.made or wrote(step) for step in run.steps):
            return None
        async with self._uow as uow:
            known = list(await uow.workflows.known(ctx.tenant_id))
            made = next((one for one in known if one.id == run.workflow_id), None)
            if made is None:
                return None
            gestures = {
                gesture.id: gesture for gesture in await uow.gestures.gestures_for(ctx.tenant_id)
            }
            takes_back = undoes(made, gestures, known)
            if takes_back is None:
                return None
            undo_job = next(one for one in known if one.id == takes_back)
            which = addresses(
                [step.made for step in run.steps if step.made], identifies(undo_job, gestures)
            )
            asks = asks_for(undo_job)
            if which is None and asks:
                typed = str(run.values.get(asks, "")).strip()
                if typed:
                    which = (asks, typed)
            if which is None:
                return None
            _, names = which
            if asks is None:
                return None
            return takes_back, asks, names


class AbortWorkflowRun:
    def __init__(
        self, uow: UnitOfWork, stops: Stops, approvals: Approvals, *, durable: DurableExecution
    ) -> None:
        self._uow = uow
        self._stops = stops
        self._approvals = approvals
        self._durable = durable

    async def execute(self, ctx: RequestContext, *, run_id: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise NotFound("no such run")
        if run.outcome != "running":
            raise CannotStop(f"that run already {run.outcome}")
        if run.executor == "steel":
            await self._durable.cancel_run(run.id)
            return run
        if not run.device_id:
            raise CannotStop(NOT_IN_A_BROWSER_HERE)
        self._stops.ask(run.id)
        self._approvals.approve(run.id)
        return run


class NotDrivingThisRun(DomainError):
    code = "not_driving_this_run"


class ApproveWorkflowStep:
    def __init__(self, uow: UnitOfWork, approvals: Approvals, clock: Clock) -> None:
        self._uow = uow
        self._approvals = approvals
        self._clock = clock

    async def execute(
        self, ctx: RequestContext, *, run_id: str, asking: DeviceId | None
    ) -> tuple[int, bool, bool]:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                raise NotFound("no such run")
            if asking is not None and run.device_id != asking.value:
                raise NotDrivingThisRun("that run is not the one this browser is driving")
            parked = [step.order for step in run.steps if step.verdict == "awaiting"]
            if run.outcome != "running" or not parked:
                raise Conflict("nothing is awaiting approval on this run")
            ord_ = max(parked)
            first = await uow.workflow_runs.approve(
                run.id,
                ord_,
                at=self._clock.now().isoformat(),
                device_id=asking.value if asking else None,
            )
            await uow.commit()
        resumed = self._approvals.approve(run.id)
        return ord_, first, resumed
