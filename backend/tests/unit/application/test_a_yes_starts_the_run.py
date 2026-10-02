"""A yes starts the run on the backend, whichever door it came through (S2).

Measured on QA 2026-09-28, thread thr_fa6507fa: the operator typed "yes" in the
console, the thread said "Running Create a Customer Type now.", and nothing ran
-- only the extension started runs on that decision, and the console has no
extension. Every test here goes converse -> the start use case -> the run row.
"""

from __future__ import annotations

from collections.abc import Coroutine
from dataclasses import replace
from typing import Any

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.converse import K_CLOSED, K_NOT_YOURS, Converse, StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.gather import GatherContext
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.observation.record_attempt import RecordAttempt
from sro.domain.chat.asking import Pending, offered_job
from sro.domain.chat.thread import Message, ThreadId
from sro.domain.execution.mail_job import SENT
from sro.domain.observation.attempts import DONE, FAILED, REFUSED
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from tests import factories as f
from tests.unit.application.rig.test_a_mail_job_is_written_not_clicked import (
    GMAIL,
    THREAD,
    _gesture,
    _Mailbox,
    _reply_job,
    _written,
)
from tests.unit.application.test_converse import _PlacesTheJob, _understood
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import save_job

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
COLLEAGUE = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("colleague@acme.test"))
JOB = "wfl_1"


LAPTOP = DeviceId("dev-1")
DESK = DeviceId("dev-2")
MAIL_JOB = "wfl_reply"


class _Online(FakeChannel):
    """Which browsers are connected right now: the socket's answer, nothing else."""

    def __init__(self, *connected: DeviceId) -> None:
        super().__init__()
        self.connected = connected

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return self.connected


class _HandoffFails(FakeDurableExecution):
    async def start_run(self, ctx: RequestContext, *, run_id: str, budget_s: float) -> None:
        raise ConnectionError("temporal is unreachable")


class _World:
    def __init__(
        self,
        *,
        steel: bool = True,
        cap_usd: float = 5.0,
        online: tuple[DeviceId, ...] = (),
        durable: FakeDurableExecution | None = None,
        asker: FakeAsker | None = None,
    ) -> None:
        self.uow = FakeUnitOfWork()
        self.durable = durable or FakeDurableExecution()
        self.channel = _Online(*online)
        self.mailbox = _Mailbox()
        asker = asker or FakeAsker()
        self.wiring: dict[str, Any] = {
            "channel": self.channel,
            "asker": asker,
            "clock": FakeClock(),
            "cap_usd": cap_usd,
            "stops": Stops(),
            "approvals": Approvals(),
            "one_time_secrets": OneTimeSecrets(),
            "gather": GatherContext(tools=self.mailbox, asker=asker, servers={}),
            "servers": {},
            "ids": FakeIdFactory(),
            "durable": self.durable,
            "steel_tenants": frozenset({f.TENANT.value}) if steel else frozenset(),
        }
        self.start = StartWorkflowRun(self.uow, **self.wiring)
        self.spawned: list[Coroutine[Any, Any, None]] = []
        self.title = ""

    async def ready(self) -> _World:
        self.title = (await save_job(self.uow, JOB)).title
        return self

    def converse(self) -> Converse:
        uow = self.uow
        return Converse(
            uow,
            ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder()))),
            FakeClock(),
            FakeIdFactory(),
            reads_jobs=_PlacesTheJob(_understood(JOB, values={"Customer Type": "GT2"})),
            start=self.start,
            spawn=self.spawned.append,
            attempts=RecordAttempt(uow, FakeIdFactory(), FakeClock()),
        )

    async def mine(self, *devices: DeviceId, who: PrincipalId = f.OPERATOR) -> None:
        for one in devices:
            await self.uow.devices.add(f.device(id=one, principal_id=who))

    async def a_mail_job(self) -> ThreadId:
        """Compose and Send Email, asked about the way the mail door asks: a
        job that is nothing but the mailbox, offered in the chat of its mail."""
        job = _reply_job()
        await self.uow.workflows.save(job)
        await self.uow.gestures.add_gestures((_gesture("g-open", GMAIL), _gesture("g-send", GMAIL)))
        self.title = job.title
        await StartThread(self.uow, FakeClock(), FakeIdFactory()).execute(CTX)
        await AskAboutTheOffer(self.uow, FakeClock(), FakeIdFactory()).execute(
            CTX,
            Pending(
                workflow_id=MAIL_JOB, title=job.title, values={}, missing=(), mail_thread=THREAD
            ),
            mail_thread=THREAD,
            ask_to_run=True,
        )
        chat = await ReadThreads(self.uow).asking(CTX, THREAD)
        assert chat is not None
        return chat.id

    def attempts(self) -> list[tuple[str, str]]:
        return [
            (one.came_of, one.about.get("run", ""))
            for one in self.uow.attempts.rows
            if one.asked_for == "start a job from chat"
        ]

    async def offered(self, converse: Converse) -> tuple[ThreadId, Message]:
        thread = await StartThread(self.uow, FakeClock(), FakeIdFactory()).execute(CTX)
        said = await converse.execute(CTX, thread_id=thread.id, text="create customer type GT2")
        offer = said.messages[-1]
        assert (offer.decision or {}).get("kind") == "job", offer
        return thread.id, offer

    async def runs(self) -> list[str]:
        return [one.id for one in await self.uow.workflow_runs.for_workflow(f.TENANT, JOB)]


async def test_a_typed_yes_in_the_console_starts_exactly_one_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    assert run.offer == offer.id.value, "a second start of this offer would not be refused"
    assert run.values == {"Customer Type": "GT2"}
    assert run.executor == "steel" and run.started_by == CTX.principal_id.value
    assert [started for started, _ in world.durable.runs_started] == [run_id]
    last = said.messages[-1]
    assert last.text == f"Running {world.title} now. Values: Customer Type = GT2 (your request)."
    assert last.decision is not None and last.decision["run_id"] == run_id


async def test_the_last_answer_to_a_question_starts_the_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread = await StartThread(world.uow, FakeClock(), FakeIdFactory()).execute(CTX)
    await AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX, Pending(workflow_id=JOB, title=world.title, values={}, missing=("Customer Type",))
    )

    said = await converse.execute(CTX, thread_id=thread.id, text="GT2")

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and run.values == {"Customer Type": "GT2"}
    # The value the answer gave, and where it came from (YPHD, 2026-09-30).
    assert said.messages[-1].text == (
        f"Running {world.title} now. Values: Customer Type = GT2 (your answer in the chat)."
    )
    assert (said.messages[-1].decision or {}).get("run_id") == run_id


async def test_a_second_yes_under_the_same_offer_starts_nothing_more() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)
    await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    again = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)
    typed = await converse.execute(CTX, thread_id=thread_id, text="yes")

    assert again.messages[-1].text == K_CLOSED
    assert len(await world.runs()) == 1
    assert len(world.durable.runs_started) == 1
    assert sum(m.text.startswith("Running ") for m in typed.messages) == 1


class _BeatenTo(StartWorkflowRun):
    """The other panel's yes lands between this one reading the question open
    and this one claiming the offer: the race, made to happen every time."""

    rival: tuple[Converse, ThreadId, str] | None = None

    async def execute(self, ctx: RequestContext, **given: Any) -> Any:
        if self.rival is not None:
            converse, thread_id, answering = self.rival
            self.rival = None
            await converse.execute(ctx, thread_id=thread_id, text="yes", answering=answering)
        return await super().execute(ctx, **given)


async def test_the_yes_that_lost_the_race_is_told_the_run_it_lost_to() -> None:
    world = await _World().ready()
    winner = world.converse()
    thread_id, offer = await world.offered(winner)
    world.start = _BeatenTo(world.uow, **world.wiring)
    world.start.rival = (winner, thread_id, offer.id.value)
    loser = world.converse()

    lost = await loser.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    assert lost.messages[-1].text == K_CLOSED
    assert (lost.messages[-1].decision or {}).get("run_id") == run_id, "the loser cannot watch it"
    assert sum(m.text.startswith("Running ") for m in lost.messages) == 1


async def test_a_refused_start_says_why_and_never_that_it_is_running() -> None:
    world = await _World(cap_usd=0.0).ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    assert await world.runs() == []
    assert world.durable.runs_started == []
    assert not any(m.text.startswith("Running ") for m in said.messages), said.messages[-1]
    last = said.messages[-1]
    assert last.text.startswith("Nothing was started: ") and "daily cap reached" in last.text
    assert "run_id" not in (last.decision or {})
    assert offered_job(said.messages) is not None, "the offer is gone; a yes cannot retry it"
    assert world.attempts() == [(REFUSED, "")]


async def test_an_extension_tenant_s_yes_runs_live_in_the_operator_s_own_browser() -> None:
    """QA's greyorange is not on Steel: the yes runs where `resumeTheJob` ran
    it, in the starter's connected browser, live and watched -- and the chat
    request does not sit on the whole run."""
    world = await _World(steel=False, online=(LAPTOP,)).ready()
    await world.mine(LAPTOP)
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    assert (run.executor, run.device_id) == ("extension", LAPTOP.value)
    assert (run.live, run.allow_focus) == (True, True)
    assert run.offer == offer.id.value
    assert said.messages[-1].text.startswith(f"Running {world.title} now.")
    assert (said.messages[-1].decision or {}).get("run_id") == run_id
    assert world.durable.runs_started == []
    (performing,) = world.spawned
    assert performing.cr_code.co_name == "perform", "the run was not handed on to be driven"
    performing.close()
    assert world.attempts() == [(DONE, run_id)]


async def test_of_two_connected_browsers_the_one_seen_last_runs_it() -> None:
    world = await _World(steel=False, online=(LAPTOP, DESK)).ready()
    await world.uow.devices.add(f.device(id=LAPTOP, last_seen_at=f.at(10)))
    await world.uow.devices.add(f.device(id=DESK, label="desk", last_seen_at=f.at(20)))
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and run.device_id == DESK.value
    world.spawned[0].close()


async def test_only_a_colleague_s_browser_connected_is_no_browser_of_yours() -> None:
    """A device online for the tenant is not the starter's hand: a run in a
    colleague's browser would be one operator driving another's window."""
    world = await _World(steel=False, online=(LAPTOP,)).ready()
    await world.mine(LAPTOP, who=COLLEAGUE.principal_id)
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    assert await world.runs() == []
    assert world.spawned == []
    last = said.messages[-1]
    assert last.text == "Nothing was started: none of your browsers is connected."
    assert not any(m.text.startswith("Running ") for m in said.messages)
    assert offered_job(said.messages) is not None


async def test_a_mail_only_job_on_an_extension_tenant_is_sent_with_no_browser() -> None:
    world = _World(steel=False, asker=_written("alex.r@example.com", body="Done.\n\ndevansh"))
    thread_id = await world.a_mail_job()
    converse = world.converse()

    said = await converse.execute(CTX, thread_id=thread_id, text="yes")

    assert said.messages[-1].text == f"Running {world.title} now.", said.messages[-1]
    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, MAIL_JOB)
    assert (run.executor, run.device_id) == ("extension", "")
    (performing,) = world.spawned
    await performing
    assert world.channel.sent == [], "a mail job drove a browser"
    assert [one["to"] for one in world.mailbox.sent] == ["alex.r@example.com"], "sent at once"
    fresh = await world.uow.threads.get(f.TENANT, thread_id)
    assert (fresh.messages[-1].decision or {}).get("kind") == SENT, "said outside the run's chat"


async def test_a_mail_only_job_on_a_steel_tenant_runs_on_steel() -> None:
    world = _World()
    thread_id = await world.a_mail_job()
    converse = world.converse()

    said = await converse.execute(CTX, thread_id=thread_id, text="yes")

    assert said.messages[-1].text == f"Running {world.title} now.", said.messages[-1]
    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, MAIL_JOB)
    assert run.executor == "steel"
    assert [one for one, _ in world.durable.runs_started] == [run.id]
    assert world.spawned == []


async def test_a_handoff_that_fails_after_the_commit_leaves_the_thread_saying_so() -> None:
    world = await _World(durable=_HandoffFails()).ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and run.outcome == "failed"
    last = said.messages[-1]
    assert not last.text.startswith("Running "), last.text
    assert last.text.startswith(f"{world.title} did not start: ") and "unreachable" in last.text
    assert "ask for it again" in last.text
    assert (last.decision or {}).get("run_id") == run_id
    assert world.attempts() == [(FAILED, run_id)]


async def test_a_steel_yes_to_a_job_stopped_part_way_says_so_in_chat_words() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread = await StartThread(world.uow, FakeClock(), FakeIdFactory()).execute(CTX)
    job = await world.uow.workflows.get(f.TENANT, JOB)
    await world.uow.workflows.save(replace(job, steps=[*job.steps, replace(job.steps[0], order=1)]))
    await AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        Pending(
            workflow_id=JOB,
            title=world.title,
            values={},
            missing=("Customer Type",),
            from_step=1,
        ),
    )

    said = await converse.execute(CTX, thread_id=thread.id, text="GT2")

    assert await world.runs() == []
    last = said.messages[-1].text
    assert "stopped part-way in your browser" in last, last
    assert "extension" not in last


async def test_the_last_answer_starts_the_run_under_the_offer_s_own_key() -> None:
    """A mail-door offer carries the mail's key; the question it became is only
    where the operator answered it. Keyed on the question, the mail's key would
    never be claimed, and another door could start the same mail again."""
    world = await _World().ready()
    converse = world.converse()
    thread = await StartThread(world.uow, FakeClock(), FakeIdFactory()).execute(CTX)
    await AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        Pending(workflow_id=JOB, title=world.title, values={}, missing=("Customer Type",)),
        offer="mail:the-request",
    )

    await converse.execute(CTX, thread_id=thread.id, text="GT2")

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and run.offer == "mail:the-request"


async def test_a_yes_to_an_offer_the_card_already_started_answers_that_run() -> None:
    """The panel's card for this reply pressed first (E2): the yes is told the
    run the press made, so the panel watches one run, and nothing starts twice."""
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)
    pressed = await world.start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values={"Customer Type": "GT2"},
        live=True,
        allow_focus=False,
        # The offer's name as the panel reads it off the reply: the decision's
        # own, or the question's id -- `_offer_of`'s rule.
        offer=str((offer.decision or {}).get("offer") or offer.id.value),
    )

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    assert await world.runs() == [pressed.id]
    assert world.durable.runs_started == [], "the yes handed the pressed run on a second time"
    last = said.messages[-1]
    assert last.text == f"{world.title} is already running."
    assert (last.decision or {}).get("run_id") == pressed.id
    assert not any(m.text.startswith("Nothing was started") for m in said.messages)


async def test_a_colleague_s_yes_in_the_opener_s_thread_starts_no_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(
        COLLEAGUE, thread_id=thread_id, text="yes", answering=offer.id.value
    )

    assert said.messages[-1].text == K_NOT_YOURS
    assert await world.runs() == []
    assert offered_job(said.messages) is not None
