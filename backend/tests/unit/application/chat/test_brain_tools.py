"""The brain's read-only tools: what it can see, and only what is its own.

Each tool wraps the use case the panel and the worker already call, so what
these pin is the shape the model is handed and the guards around it: real jobs
only, the limits the reader checks, the caller's own runs, the tenant's own
data, and a bounded, secret-free answer.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.brain_tools import (
    AskOperator,
    CheckMail,
    FindJobs,
    Lookup,
    RunStatus,
    StartJob,
    UndoRun,
    WorkItOut,
    brain_tools,
    described,
)
from sro.application.chat.mailbox import SERVER
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import GetWorkflowRun, StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.knowledge.retrieve import Retrieve
from sro.application.lookup.look_it_up import LookItUp
from sro.application.lookup.plan_lookups import PlanLookups
from sro.domain.chat.asking import Pending
from sro.domain.chat.brain_turn import ToolResult, Turn
from sro.domain.execution.workflow_run import OfferTaken
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.observation.gesture import Outline, OutlineField
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Workflow
from tests import factories as f
from tests.unit.application.chat.brain_support import (
    CTX,
    THEIRS,
    a_failed_step,
    world_with_job,
)
from tests.unit.application.rig.test_from_the_mail import JOB
from tests.unit.application.rig.test_start_workflow_run import _starter
from tests.unit.application.test_where_to_look_for_an_answer import KNOWN, _Knows
from tests.unit.fakes import (
    FakeAsker,
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import read_step, save_job, save_step

DEPARTMENT = OutlineField("combobox", "Department", None, ("Finance", "Operations"))


def _jobs(result: ToolResult) -> list[dict[str, Any]]:
    return list(result.data["jobs"])  # type: ignore[call-overload]


def _runs(result: ToolResult) -> list[dict[str, Any]]:
    return list(result.data["runs"])  # type: ignore[call-overload]


async def test_find_jobs_answers_real_jobs_with_their_parameters_and_limits() -> None:
    world = await world_with_job()
    await world.uow.workflows.remember_limit(JOB, 0, 4)

    result = await FindJobs(world.uow, FakeClock()).run(CTX, {"query": "create customer type"})

    (job,) = [one for one in _jobs(result) if one["id"] == JOB]
    assert job["title"] == "Create a Customer Type"
    assert [(p["name"], p["required"]) for p in job["parameters"]] == [
        ("Customer Type", True),
        ("Customer Type Description", True),
    ]
    assert job["runnable"] is True
    assert {p["name"]: p["max_length"] for p in job["parameters"]}["Customer Type"] == 4


async def test_find_jobs_leaves_out_a_copy_that_writes_nothing() -> None:
    world = await world_with_job()
    stub, seen = read_step()
    await world.uow.workflows.save(
        Workflow(
            id="wfl_copy",
            tenant=f.TENANT.value,
            title="Create a Customer Type",
            narrative="",
            steps=[replace(stub, order=0)],
        )
    )
    await world.uow.gestures.add_gestures(
        tuple(replace(one, tenant=f.TENANT.value) for one in seen.values())
    )

    result = await FindJobs(world.uow, FakeClock()).run(CTX, {"query": "create customer type"})

    assert "wfl_copy" not in [one["id"] for one in _jobs(result)]


async def test_find_jobs_never_lists_a_job_that_sends_mail() -> None:
    world = await world_with_job()

    result = await FindJobs(world.uow, FakeClock()).run(CTX, {"query": "send a mail"})

    assert not {"mail_send", "mail_reply", "mail_forward"} & {one["id"] for one in _jobs(result)}


async def test_find_jobs_shows_only_this_tenant_s_jobs() -> None:
    world = await world_with_job()
    other = await world.uow.workflows.get(f.TENANT, JOB)
    await world.uow.workflows.save(replace(other, id="wfl_other", tenant="another-tenant"))

    result = await FindJobs(world.uow, FakeClock()).run(CTX, {"query": "create customer type"})

    assert "wfl_other" not in [one["id"] for one in _jobs(result)]


async def test_check_mail_reports_what_the_look_did_as_data() -> None:
    world = await world_with_job("hello, nothing to do here")

    result = await CheckMail(world.look).run(CTX, {})

    assert result.ok
    assert "asks for no job here" in str(result.data["said"])
    assert result.data["read"] == 1


async def test_check_mail_bounds_what_a_mail_can_say() -> None:
    world = await world_with_job("x")
    said = "a" * 10_000

    async def _long(*_: object, **__: object) -> Any:
        return replace(await world.look.execute(CTX), why=said, offered=(), asks_nothing=(said,))

    result = await CheckMail(_Look(_long)).run(CTX, {})

    assert len(str(result.data["said"])) <= 2000


class _Look:
    def __init__(self, execute: Any) -> None:
        self.execute = execute


async def test_check_mail_says_when_the_cap_stopped_it() -> None:
    world = await world_with_job("hello")
    world.look._cap_usd = 0.0
    async with world.uow as uow:
        await uow.chats.record(_spent())
        await uow.commit()

    result = await CheckMail(world.look).run(CTX, {})

    assert not result.ok and result.error


def _spent() -> Any:
    from sro.domain.chat.reading import ChatReading

    return ChatReading(
        id="c1",
        tenant=f.TENANT.value,
        at=FakeClock().now().isoformat(),
        workflow_id=None,
        in_tokens=1,
        out_tokens=1,
        thought_tokens=0,
        cost_usd=5.0,
        unpriced=False,
        error="",
    )


async def test_run_status_names_the_run_its_values_and_its_state() -> None:
    world = await world_with_job()
    run = await world.ran("held", {"Customer Type": "SR11"})

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    (one,) = _runs(result)
    assert (one["id"], one["values"]) == (run.id, {"Customer Type": "SR11"})
    # Plain words, never the stored outcome "held": a model reads that as "on hold".
    assert one["state"] == "finished: its changes were read back and confirmed"
    assert one["from_mail"] is False and one["question"] == ""


async def test_run_status_gives_the_system_s_reason_for_a_failed_run() -> None:
    world = await world_with_job()
    await world.ran("failed", {}, steps=(a_failed_step("Customer Type is too long"),))

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    assert _runs(result)[0]["stopped_because"] == "Customer Type is too long"


async def test_run_status_says_a_run_came_from_mail_and_what_it_asks() -> None:
    world = await world_with_job()
    run = await world.ran("running", {}, mail={"thread": "t-9", "subject": "new type"})
    await world.asked(run, "Which customer type code should I use?")

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    (one,) = _runs(result)
    assert one["from_mail"] is True
    assert one["question"] == "Which customer type code should I use?"


async def test_run_status_sends_a_password_question_to_the_run_s_card_and_never_to_chat() -> None:
    world = await world_with_job()
    run = await world.ran("running", {})
    progress = {
        "asking": {
            "id": "q_1",
            "kind": "password",
            "text": "clerk at login.idp.example has no usable password. Enter it on the run's card.",
            "origin": "login.idp.example",
            "username": "clerk",
            "field": "password",
        }
    }
    assert await world.uow.workflow_runs.record_progress(f.TENANT, run.id, progress)
    await world.asked(run, "clerk at login.idp.example has no usable password. Enter it on the run's card.")

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    (one,) = _runs(result)
    assert one["question"] == "waiting: enter the password on the run's card, not in this chat"


async def test_run_status_shows_the_caller_s_own_runs_and_no_others() -> None:
    world = await world_with_job()
    await world.ran("held", {}, run_id="run_mine")
    await world.ran("held", {}, run_id="run_theirs", by=THEIRS)
    await world.ran("held", {}, run_id="run_elsewhere", tenant="another-tenant")

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    assert [one["id"] for one in _runs(result)] == ["run_mine"]


async def test_run_status_never_shows_a_secret_value() -> None:
    world = await world_with_job()
    await world.ran("held", {"Customer Type": "SR11", "Password": "hunter2"})

    result = await RunStatus(world.runs, world.threads).run(CTX, {})

    assert "hunter2" not in str(result.data)


async def _lookup_over(uow: FakeUnitOfWork, planned: Any) -> Lookup:
    planner = PlanLookups(uow, _Knows(KNOWN), FakeAsker(planned), clock=FakeClock(), cap_usd=5.0)
    return Lookup(LookItUp(planner, _NoRuns()))


class _NoRuns:
    async def execute(self, *_: object, **__: object) -> Any:
        raise AssertionError("a plan that is not ready runs nothing")


async def test_lookup_says_so_when_nothing_here_knows_how_to_look_it_up() -> None:
    from sro.domain.shared.prices import Answer

    tool = await _lookup_over(FakeUnitOfWork(), Answer(data={"why": "none", "lookups": []}))

    result = await tool.run(CTX, {"question": "which suppliers are set up at SG"})

    assert not result.ok and "look that up" in result.error


async def test_lookup_answers_from_the_system_and_names_where_it_read() -> None:
    from sro.domain.lookup.plan import Lookup as Asked
    from sro.domain.lookup.plan import Plan

    class _Read:
        async def execute(self, *_: object, **__: object) -> Any:
            from sro.application.lookup.run_lookups import Answers, Looked

            asked = Asked(system="blue_yonder", how="call", target="/data/WM/wm/suppliers")
            return Answers(plan=Plan(question="q", lookups=(asked,)), looked=(Looked(asked, True),))

    class _Plans:
        async def execute(self, *_: object, **__: object) -> Any:
            from sro.application.lookup.plan_lookups import Planned

            return Planned(Plan(question="q", lookups=(Asked(system="s", how="call", target="t"),)))

    result = await Lookup(LookItUp(_Plans(), _Read())).run(CTX, {"question": "q"})

    assert result.ok and "/data/WM/wm/suppliers" in str(result.data["source"])


def test_every_tool_is_described_with_its_arguments() -> None:
    tools = [FindJobs(FakeUnitOfWork(), FakeClock()), CheckMail(None)]
    one, two = described(tools)
    assert (one["name"], two["name"]) == ("find_jobs", "check_mail")
    assert one["args"] == FindJobs.args


GIVEN = {"Customer Type": "SR11", "Customer Type Description": "new"}

SAID = Turn(said="create customer type SR11 with the description new")


class _Counting(StartWorkflowRun):
    tried = 0

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.tried += 1
        return await super().execute(*args, **kwargs)


class _Acting:
    """The real start use case over the fakes: a Steel run, so nothing drives a browser."""

    def __init__(self, world: Any, *, cap_usd: float = 5.0) -> None:
        self.world, self.durable = world, FakeDurableExecution()
        self.spawned: list[Any] = []
        real = _starter(
            world.uow,
            durable=self.durable,
            steel_tenants=frozenset({f.TENANT.value}),
            cap_usd=cap_usd,
            clock=world.clock,
        )
        self.start = _Counting.__new__(_Counting)
        self.start.__dict__.update(real.__dict__)
        self.job = StartJob(world.uow, world.clock, self.start, self.spawned.append)
        self.undo = UndoRun(GetWorkflowRun(world.uow), self.start, self.spawned.append)

    @property
    def started(self) -> list[str]:
        return [one for one, _ in self.durable.runs_started]


async def _acting(*, cap_usd: float = 5.0) -> _Acting:
    world = await world_with_job()
    await world.uow.workflows.remember_limit(JOB, 0, 4)
    return _Acting(world, cap_usd=cap_usd)


async def test_start_job_starts_at_once_with_the_given_values() -> None:
    acting = await _acting()

    result = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, SAID)

    assert result.ok and result.data["state"] == "running"
    assert acting.started == [result.data["run_id"]]
    assert result.decision == {"kind": "run", "run_id": result.data["run_id"]}
    run = await acting.world.uow.workflow_runs.get(f.TENANT, str(result.data["run_id"]))
    assert run is not None and run.values == GIVEN and run.started_by == CTX.principal_id.value


async def test_a_value_the_field_cannot_hold_is_refused_by_name_and_nothing_starts() -> None:
    acting = await _acting()

    result = await acting.job.run(
        CTX,
        {"job_id": JOB, "values": {**GIVEN, "Customer Type": "SROT1"}},
        Turn(said="create customer type SROT1 with the description new"),
    )

    assert not result.ok and "Customer Type you gave is longer than 4" in result.error
    assert "SROT1" not in result.error
    assert acting.started == [] and acting.start.tried == 0


async def test_a_value_the_operator_never_said_is_refused_and_a_near_miss_cannot_pass() -> None:
    acting = await _acting()
    typed = Turn(said="create customer type SROT1 with the description new")

    invented = await acting.job.run(
        CTX,
        {"job_id": JOB, "values": {**GIVEN, "Customer Type Description": "bonded goods"}},
        typed,
    )
    retried = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Customer Type": "SROT"}}, typed
    )

    assert not invented.ok and "Customer Type Description" in invented.error
    assert "not in what was said" in invented.error and "bonded goods" not in invented.error
    assert not retried.ok and "Customer Type you gave is not in what was said" in retried.error
    assert acting.started == [] and acting.start.tried == 0


async def test_a_value_from_a_tool_result_but_never_said_does_not_start() -> None:
    acting = await _acting()

    result = await acting.job.run(
        CTX, {"job_id": JOB, "values": GIVEN}, Turn(said="create a customer type")
    )

    assert not result.ok and "not in what was said" in result.error
    assert acting.started == [] and acting.start.tried == 0


async def test_a_missing_required_value_comes_back_as_a_question_for_the_model() -> None:
    acting = await _acting()

    result = await acting.job.run(CTX, {"job_id": JOB, "values": {"Customer Type": "SR11"}}, SAID)

    assert not result.ok and "missing: Customer Type Description" in result.error
    assert acting.started == [] and acting.start.tried == 0


async def test_an_offer_a_run_already_took_answers_that_run() -> None:
    acting = await _acting()
    call = {"job_id": JOB, "values": GIVEN}
    turn = Turn(said=SAID.said, offer="chat:m1")

    first = await acting.job.run(CTX, call, turn)
    again = await acting.job.run(CTX, {**call, "why": "once more"}, turn)
    other = await acting.job.run(CTX, call, Turn(said=SAID.said, offer="chat:m2"))

    assert again.ok and again.data["run_id"] == first.data["run_id"]
    assert again.data["state"] == "already running" and again.decision is None
    assert other.data["run_id"] != first.data["run_id"] and len(acting.started) == 2


async def test_two_jobs_in_one_message_are_two_runs_under_one_message_id() -> None:
    acting = await _acting()
    turn = Turn(said=SAID.said, offer="chat:m1")

    first = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, turn)
    second = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Customer Type": "SR11 "}}, turn
    )
    third = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Customer Type Description": "new "}}, turn
    )

    assert second.data["run_id"] == first.data["run_id"] == third.data["run_id"]
    assert len(acting.started) == 1


async def test_the_model_cannot_choose_the_offer_a_run_is_made_under() -> None:
    acting = await _acting()
    first = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, SAID)

    hijack = await acting.job.run(
        CTX, {"job_id": JOB, "values": GIVEN, "offer": f"mail:{first.data['run_id']}"}, SAID
    )

    assert "offer" not in StartJob.args["properties"]
    assert hijack.ok and hijack.data["run_id"] != first.data["run_id"]
    assert len(acting.started) == 2


async def test_a_job_that_is_not_real_is_never_started() -> None:
    acting = await _acting()
    other = await acting.world.uow.workflows.get(f.TENANT, JOB)
    await acting.world.uow.workflows.save(replace(other, id="wfl_copy"))

    for job_id in ("wfl_copy", "wfl_nowhere"):
        result = await acting.job.run(CTX, {"job_id": job_id, "values": GIVEN}, SAID)
        assert not result.ok
    assert acting.started == [] and acting.start.tried == 0


async def test_another_tenant_s_job_is_not_startable_here() -> None:
    acting = await _acting()
    theirs = RequestContext(TenantId("another-tenant"), PrincipalId("devansh"))

    result = await acting.job.run(theirs, {"job_id": JOB, "values": GIVEN}, SAID)

    assert not result.ok and acting.started == [] and acting.start.tried == 0


async def test_a_secret_is_never_taken_and_never_repeated() -> None:
    acting = await _acting()

    result = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Password": "hunter2"}}, SAID
    )

    assert not result.ok and "Password" in result.error and "hunter2" not in result.error
    assert acting.started == [] and acting.start.tried == 0


async def test_a_parameter_the_job_does_not_have_is_refused() -> None:
    acting = await _acting()

    result = await acting.job.run(CTX, {"job_id": JOB, "values": {**GIVEN, "Colour": "red"}}, SAID)

    assert not result.ok and "can't set Colour" in result.error and acting.start.tried == 0


async def test_a_refusal_from_the_system_is_data_and_is_tried_once() -> None:
    acting = await _acting(cap_usd=0.0)

    result = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, SAID)

    assert not result.ok and result.error and not result.ends_turn
    assert acting.start.tried == 1 and acting.started == []


async def test_no_job_that_sends_mail_can_be_started_from_chat() -> None:
    acting = await _acting()
    said = Turn(said="send a mail to bob@corp.com saying hello")

    for job_id in ("mail_send", "mail_reply", "mail_forward"):
        sent = await acting.job.run(CTX, {"job_id": job_id, "values": {"To": "bob@corp.com"}}, said)
        assert not sent.ok and "Send it" in sent.error
    unknown = await acting.job.run(CTX, {"job_id": "mail_nope", "values": {}}, said)

    assert not unknown.ok and acting.start.tried == 0 and acting.started == []


async def test_undo_run_refuses_a_run_that_is_not_the_callers() -> None:
    acting = await _acting()
    theirs = await acting.world.ran("done", GIVEN, by=THEIRS)

    result = await acting.undo.run(CTX, {"run_id": theirs.id})

    assert not result.ok and "not yours" in result.error and acting.start.tried == 0


async def test_undo_run_refuses_a_run_that_made_nothing_or_does_not_exist() -> None:
    acting = await _acting()
    mine = await acting.world.ran("done", GIVEN)

    nothing = await acting.undo.run(CTX, {"run_id": mine.id})
    gone = await acting.undo.run(CTX, {"run_id": "run_nope"})

    assert not nothing.ok and not gone.ok and acting.start.tried == 0


async def test_undo_run_starts_the_delete_job_taking_the_run_back() -> None:
    acting = await _acting()
    mine = await acting.world.ran("done", GIVEN)

    await save_job(acting.world.uow, "wfl_del")

    async def _delete(self: GetWorkflowRun, ctx: Any, run: Any) -> tuple[str, str, str]:
        return "wfl_del", "Customer Type", "SR11"

    GetWorkflowRun.undo_for, was = _delete, GetWorkflowRun.undo_for  # type: ignore[method-assign]
    try:
        result = await acting.undo.run(CTX, {"run_id": mine.id})
        undo = await acting.world.uow.workflow_runs.get(f.TENANT, str(result.data["run_id"]))
        assert undo is not None
        await acting.world.uow.workflow_runs.save(replace(undo, outcome="held"))
        again = await acting.undo.run(CTX, {"run_id": mine.id})
    finally:
        GetWorkflowRun.undo_for = was  # type: ignore[method-assign]

    assert result.ok and undo.undoes_run == mine.id
    assert undo.values == {"Customer Type": "SR11"}
    assert not again.ok and "already taken back" in again.error and len(acting.started) == 1


async def test_ask_operator_ends_the_turn_with_one_question() -> None:
    result = await AskOperator().run(CTX, {"question": "Which customer type?"})

    assert result.ok and result.ends_turn
    assert result.decision == {"kind": "brain_asks", "question": "Which customer type?"}
    assert not (await AskOperator().run(CTX, {"question": "  "})).ok


async def test_work_it_out_returns_the_plan_and_says_it_changes_the_system() -> None:
    uow = FakeUnitOfWork()
    tool = WorkItOut(PlanTask(Retrieve(uow, FakeEmbedder())))

    result = await tool.run(CTX, {"task": "delete equipment type 4471"})

    assert result.ok and result.data["changes_the_system"] is True
    assert "delete equipment type 4471" in str(result.data["plan"]) and result.data["say"]


class _Plans:
    pass


async def test_the_registry_is_in_the_planned_order() -> None:
    acting = await _acting()
    world = acting.world
    tools = brain_tools(
        uow=world.uow,
        clock=world.clock,
        runs=world.runs,
        run=GetWorkflowRun(world.uow),
        threads=world.threads,
        look_mail=world.look,
        look_up=LookItUp(_Plans(), _NoRuns()),
        start=acting.start,
        plan=PlanTask(Retrieve(world.uow, FakeEmbedder())),
        spawn=acting.spawned.append,
    )

    assert [one.name for one in tools] == [
        "find_jobs",
        "start_job",
        "run_status",
        "check_mail",
        "undo_run",
        "lookup",
        "ask_operator",
        "work_it_out",
    ]


async def test_a_run_in_the_operator_s_browser_is_handed_to_the_spawner_not_awaited() -> None:
    world = await world_with_job()
    await world.uow.devices.add(f.device(id=DeviceId("dev-1"), principal_id=CTX.principal_id))
    spawned: list[Any] = []
    tool = StartJob(world.uow, world.clock, _starter(world.uow), spawned.append)

    result = await tool.run(CTX, {"job_id": JOB, "values": GIVEN}, SAID)

    assert result.ok and len(spawned) == 1
    spawned[0].close()


async def _a_card_offers(acting: _Acting, *, job: str = JOB, offer: str = "msg-card") -> None:
    """What the mail door leaves in the operator's chat: a card waiting on a yes."""
    await AskAboutTheOffer(acting.world.uow, acting.world.clock, FakeIdFactory()).execute(
        CTX,
        Pending(workflow_id=job, title="Create a Customer Type", values=GIVEN, missing=()),
        about="a mail",
        mail_thread="thr-mail",
        ask_to_run=True,
        offer=offer,
        sure=True,
    )


async def _answer_the_card(acting: _Acting, offer: str = "msg-card") -> Any:
    return await acting.start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values=GIVEN,
        live=True,
        allow_focus=True,
        conversation=(SERVER, ""),
        offer=offer,
    )


CHAT = replace(SAID, offer="chat:m1")


async def test_a_job_typed_in_chat_while_its_card_is_open_runs_under_the_card() -> None:
    acting = await _acting()
    await _a_card_offers(acting)

    chat = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, CHAT)
    with pytest.raises(OfferTaken) as card:
        await _answer_the_card(acting)

    assert chat.ok and len(acting.started) == 1
    assert card.value.run_id == chat.data["run_id"]


async def test_a_card_answered_first_makes_the_chat_start_say_it_is_already_running() -> None:
    acting = await _acting()
    await _a_card_offers(acting)
    first = await _answer_the_card(acting)

    chat = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, CHAT)

    assert chat.ok and chat.data == {"run_id": first.id, "state": "already running"}
    assert chat.said == "That one is already running." and acting.started == []


async def test_a_card_for_another_job_changes_nothing() -> None:
    acting = await _acting()
    await _a_card_offers(acting, job="wfl_elsewhere")

    chat = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, CHAT)

    run = await acting.world.uow.workflow_runs.get(f.TENANT, str(chat.data["run_id"]))
    assert run is not None and (run.offer or "").startswith("chat:m1:")


async def test_somebody_else_s_card_is_not_this_operator_s_offer() -> None:
    acting = await _acting()
    await AskAboutTheOffer(acting.world.uow, acting.world.clock, FakeIdFactory()).execute(
        THEIRS,
        Pending(workflow_id=JOB, title="Create a Customer Type", values=GIVEN, missing=()),
        mail_thread="thr-theirs",
        ask_to_run=True,
        offer="msg-theirs",
        sure=True,
    )

    chat = await acting.job.run(CTX, {"job_id": JOB, "values": GIVEN}, CHAT)

    run = await acting.world.uow.workflow_runs.get(f.TENANT, str(chat.data["run_id"]))
    assert run is not None and (run.offer or "").startswith("chat:m1:")


async def _the_dictionary_places(acting: _Acting, label: str, key: str) -> None:
    await acting.world.uow.knowledge.add(
        KnowledgeEntry(
            id=KnowledgeId(f"kb-field-{key}"),
            tenant_id=f.TENANT,
            system="blue_yonder",
            kind=EntryKind.FIELD,
            key=key,
            title=key,
            body={"labels": [label], "max_length": 30},
            source="index/field-dictionary.json",
            evidence=EvidenceLevel.ASSERTED,
            observed_at=datetime.now(tz=UTC),
        )
    )


async def test_a_field_the_dictionary_can_place_is_taken_and_passed_to_the_run() -> None:
    acting = await _acting()
    await _the_dictionary_places(acting, "Department", "deptCode")
    said = Turn(said=SAID.said + " in the department Finance")
    values = {**GIVEN, "Department": "Finance"}

    result = await acting.job.run(CTX, {"job_id": JOB, "values": values}, said)

    assert result.ok, result.error
    run = await acting.world.uow.workflow_runs.get(f.TENANT, str(result.data["run_id"]))
    assert run is not None and run.values == values


async def test_a_field_the_dictionary_cannot_place_is_refused_with_the_honest_reason() -> None:
    acting = await _acting()
    await _the_dictionary_places(acting, "Department", "deptCode")
    said = Turn(said=SAID.said + " from the manufacturer Acme")

    result = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Manufacturer": "Acme"}}, said
    )

    assert not result.ok and "this job can't set Manufacturer" in result.error
    assert "has no" not in result.error and acting.started == []


async def test_a_placeable_value_still_has_to_be_the_operator_s_own_words() -> None:
    acting = await _acting()
    await _the_dictionary_places(acting, "Department", "deptCode")

    result = await acting.job.run(
        CTX, {"job_id": JOB, "values": {**GIVEN, "Department": "Finance"}}, SAID
    )

    assert not result.ok and "Department" in result.error and acting.started == []


async def test_find_jobs_lists_a_field_the_page_shows_as_optional_and_read_back() -> None:
    world = await world_with_job()
    (gesture,) = save_step(gid="g", outline=Outline(fields=(DEPARTMENT,)))[1].values()
    # The same recorded save, now with the form it was pressed on in view.
    world.uow.gestures.rows["g"] = replace(gesture, tenant=f.TENANT.value)

    result = await FindJobs(world.uow, FakeClock()).run(CTX, {"query": "create customer type"})

    (job,) = [one for one in _jobs(result) if one["id"] == JOB]
    (extra,) = [p for p in job["parameters"] if p["name"] == "Department"]
    assert extra["required"] is False and extra["options"] == ["Finance", "Operations"]
    assert "read back after saving" in extra["checked"]


def _optional(name: str) -> dict[str, Any]:
    from sro.domain.execution.field_classes import FieldClass, FieldLimits

    return {name: FieldClass(name, "sometimes", (), FieldLimits(10))}


def test_a_start_with_no_value_at_all_is_refused_even_when_every_field_is_optional() -> None:
    from sro.application.chat.brain_tools import what_is_wrong
    from sro.domain.skill.signing_in import Logins

    wrong = what_is_wrong({}, _optional("Equipment"), "create transport equipment type", Logins())

    assert wrong and "no value" in wrong[0] and "Equipment" in wrong[0]


def test_a_job_with_no_parameters_may_start_with_no_values() -> None:
    from sro.application.chat.brain_tools import what_is_wrong
    from sro.domain.skill.signing_in import Logins

    assert what_is_wrong({}, {}, "refresh the board", Logins()) == []


def test_the_values_of_the_card_the_operator_is_answering_count_as_their_words() -> None:
    from sro.application.chat.brain_tools import the_words
    from sro.application.chat.open_offers import OpenOffer

    card = OpenOffer("offer_1", "wfl_a", "Create a Customer Type", {"Customer Type": "SRT5"})
    other = OpenOffer(
        "offer_2", "wfl_b", "Create a Warehouse Equipment Type", {"Description": "x9"}
    )

    said = the_words("run whatever we have", (card, other), "wfl_a")

    assert "SRT5" in said and "x9" not in said and said.startswith("run whatever we have")
    assert the_words("hello", (card,), "wfl_z") == "hello"
