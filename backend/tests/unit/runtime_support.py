"""Shared fixtures for the runtime lanes' unit tests.

`scripted_driver` is a `FakePageDriver` configured by keyword; `save_step`,
`type_step`, `type_then_save_step`, `read_step`, `mail_send_step` and
`lane_context` build a `Step`, its cited
`Gesture`s and a `LaneContext` without every lane test re-typing the same
evidence by hand. `proven_write_step` is a save the ledger has watched
succeed, demonstrated twice so its body has a slot for the run's value, and
`headers_broker` is a real `SessionBroker` whose page answers the given
session headers.

`with_a_recorded_sign_in` stores a tagged sign-in job typed on an identity
provider (`IDP` unless told otherwise) that lands on a system, and
`SigningLane` stands in for the UI lane that replays it against a
`FakePageDriver`.

`lookup_world` saves the given gestures beside a recorded sign-in that lands
on their system, and builds `RunLookups` over a real `SessionBroker` on fakes;
`reauths` counts the broker's `reauth` calls.

`save_job` stores a one-step job typing its one required value, "Customer
Type", with its evidence.

`lease_for` inserts a `ready` lease a sweeper test can expire.

`steel_run` builds a whole Steel run for `RunSteps`: the run, its job and
gestures and a recorded sign-in in a `FakeUnitOfWork`, a real `SessionBroker`
on fakes, and an executor over four `RecordingLane`s. The job has the shape
mining gives it -- no declared parameter that no step can fill -- and runs with
`values`, by default a value for each declared parameter (or a given `job`);
its `fill` is a `ScriptedFill` answering each field fill from `answers`, and
`progress()`, `job()` and `learned()` read back the run's progress, the stored
job and its learned locators.

For the executor, `RecordingLane` answers scripted results and counts its
calls (`no_tool`, `no_api` and `never` are lanes the step must not reach),
and `FakeBroker` counts its re-sign-ins.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.mail_job import Written
from sro.application.lookup.run_lookups import RunLookups
from sro.application.ports.page import PageAnswer, SessionRef
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.answer_run import AnswerRun, WriteVerdict
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.fill_field import Filled, FillField
from sro.application.runtime.run_steps import RunSteps
from sro.application.runtime.step import Held, LaneContext
from sro.application.runtime.teach import Teach
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState, new_lease_id
from sro.domain.execution.compose import Adding, Composed
from sro.domain.execution.lanes import Lane, SeenCall, StepResult, Verdict
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.progress import Progress
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import (
    Action,
    AfterState,
    Body,
    Call,
    Component,
    Gesture,
    Outline,
    PageMark,
    Target,
)
from sro.domain.shared.hosts import origin_of
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.checks import undeliverable
from sro.domain.skill.signing_in import sign_in_chain
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeBrowserPool,
    FakeClock,
    FakeCredentialVault,
    FakeDurableExecution,
    FakeHttpCaller,
    FakeIdFactory,
    FakePageDriver,
    FakeUnitOfWork,
)

_TENANT = "acme"
_SYSTEM = "https://wms.example"

_ACCOUNT = Account.of(_TENANT, _SYSTEM, "clerk")

_LEASE = Lease(
    id="lse_test",
    account=_ACCOUNT,
    container_url="http://steel.local",
    steel_session_id="sess-1",
    context_id="ctx-1",
    holder="worker-1",
    heartbeat_at=datetime(2026, 1, 1, tzinfo=UTC),
    expires_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
    state=LeaseState.READY,
)

_WORKFLOW = Workflow(
    id="wfl_test",
    tenant=_TENANT,
    title="Save the customer type",
    narrative="",
    parameters=[{"name": "Customer Type", "seen_values": ["GT0", "GT1"]}],
)

TENANT = TenantId(_TENANT)
CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("clerk"))
NOW = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
WORKFLOW = _WORKFLOW

GMAIL = "https://mail.google.com/mail/u/0/#inbox"


async def _nothing(lane: Lane) -> None:
    return None


def scripted_driver(
    *,
    answer: PageAnswer | None = None,
    calls: Sequence[SeenCall] = (),
    before: Sequence[SeenCall] = (),
    holds: bool = False,
    sign_in: bool = False,
    url: str = "",
    unsettled: bool = False,
    hit: Mapping[str, object] | None = None,
    resolved: PageAnswer | None = None,
    outline: Mapping[str, object] | None = None,
) -> FakePageDriver:
    driver = FakePageDriver(
        answer=answer,
        calls=calls,
        before=before,
        holds=holds,
        sign_in=sign_in,
        url=url,
        unsettled=unsettled,
        hit=hit,
        resolved=resolved,
        outline=outline,
    )
    if url:
        driver.tabs["tab-1"], driver.owners["tab-1"] = url, _DEFAULT_HELD.session.context_id
    return driver


def _held() -> Held:
    return Held(lease=_LEASE, target_id="tab-1", session=SessionRef("sess-1", "http://cdp.local"))


_DEFAULT_HELD = _held()


def lane_context(
    by_id: Mapping[str, Gesture],
    *,
    held: Held | None = _DEFAULT_HELD,
    learned: Mapping[int, LearnedStep] = MappingProxyType({}),
    ledger: tuple[VerifiedWrite, ...] = (),
    secret: str | None = None,
    about_to_write: Callable[[Lane], Awaitable[None]] | None = None,
    thread: str = "",
    reauthed: bool = False,
    adding: Mapping[int, Adding] = MappingProxyType({}),
    workflow: Workflow = _WORKFLOW,
) -> LaneContext:
    return LaneContext(
        tenant_id=TenantId(_TENANT),
        principal_id=PrincipalId("clerk"),
        workflow=workflow,
        by_id=by_id,
        learned=learned,
        ledger=ledger,
        held=held,
        stop=asyncio.Event(),
        secret=secret,
        thread=thread,
        about_to_write=about_to_write if about_to_write is not None else _nothing,
        reauthed=reauthed,
        adding=adding,
    )


SAVE_URL = f"{_SYSTEM}/api/customer-types"


def save_step(
    *,
    status: int = 201,
    after: AfterState | None = None,
    body: Body | None = None,
    gid: str = "ges_save",
    at: float = 1.0,
    outline: Outline | None = None,
) -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id=gid,
        tenant=_TENANT,
        stream_id="stream-1",
        batch_id="batch-1",
        at=at,
        url=f"{_SYSTEM}/app",
        system=_SYSTEM,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="click",
            at=at,
            target=Target(role="button", name="Save"),
            after=after,
            outlines=() if outline is None else (outline,),
        ),
        requests=[
            Call(
                method="POST",
                url=SAVE_URL,
                status=status,
                started_at=at,
                request_body=body,
            )
        ],
    )
    by_id = {gesture.id: gesture}
    step = Step(order=1, says="Save the customer type", system=_SYSTEM, cites=[gesture.id])
    return step, by_id


def type_then_save_step() -> tuple[Step, dict[str, Gesture]]:
    _, typed = type_step(after=AfterState(value=None, visible=True, enabled=True))
    _, saved = save_step(status=201)
    by_id = {**typed, **saved}
    step = Step(
        order=3,
        says="Type the customer type and save it",
        system=_SYSTEM,
        cites=[*typed, *saved],
        parameters=["Customer Type"],
    )
    return step, by_id


def proven_write_step(
    *,
    read_back: str | None,
    request_headers: Mapping[str, str] = MappingProxyType({"Content-Type": "application/json"}),
    read_headers: Mapping[str, str] = MappingProxyType({}),
    described: tuple[str, str] | None = None,
) -> tuple[Step, dict[str, Gesture], tuple[VerifiedWrite, ...]]:
    by_id: dict[str, Gesture] = {}
    for nth, name in enumerate(("GT0", "GT1")):
        sent: dict[str, str] = {"name": name}
        if described is not None:
            sent["description"] = described[nth]
        at = float(nth + 1)
        requests = [
            Call(
                method="POST",
                url=f"{_SYSTEM}/api/customer-types",
                status=201,
                started_at=at,
                request_body=Body(text=json.dumps(sent), mime_type="application/json"),
                request_headers=dict(request_headers),
            )
        ]
        if read_back is not None:
            read = read_back.format(name=name)
            read = read if read.startswith("http") else f"{_SYSTEM}{read}"
            requests.append(
                Call(
                    method="GET",
                    url=read,
                    status=200,
                    started_at=at + 0.5,
                    request_headers=dict(read_headers),
                )
            )
        gesture = Gesture(
            id=f"ges_save_{nth}",
            tenant=_TENANT,
            stream_id="stream-1",
            batch_id="batch-1",
            at=at,
            url=f"{_SYSTEM}/app",
            system=_SYSTEM,
            tab_id=1,
            frame_url=None,
            action=Action(kind="click", at=at, target=Target(role="button", name="Save")),
            requests=requests,
        )
        by_id[gesture.id] = gesture
    step = Step(
        order=1,
        says="Save the customer type",
        system=_SYSTEM,
        cites=list(by_id),
        parameters=["Customer Type", *(["Description"] if described else [])],
    )
    return step, by_id, (VerifiedWrite("POST", "/api/customer-types"),)


def headers_broker(
    headers: Mapping[str, str], *, driver: FakePageDriver | None = None
) -> SessionBroker:
    page = driver or FakePageDriver()
    page.cookie = headers.get("cookie", "")
    page.headers = {name: value for name, value in headers.items() if name != "cookie"}
    return SessionBroker(
        FakeUnitOfWork(),
        FakeBrowserPool({}),
        page,
        FakeAccountLocks(),
        FakeCredentialVault(),
        FakeClock(),
        ui=SigningLane(page),
    )


def read_step(
    *, after: AfterState | None = None, role: str = "link"
) -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id="ges_orders",
        tenant=_TENANT,
        stream_id="stream-1",
        batch_id="batch-1",
        at=1.0,
        url=f"{_SYSTEM}/app",
        system=_SYSTEM,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0, target=Target(role=role, name="Orders"), after=after),
        requests=[Call(method="GET", url=f"{_SYSTEM}/api/orders", status=200, started_at=1.0)],
    )
    step = Step(order=4, says="Open the orders", system=_SYSTEM, cites=[gesture.id])
    return step, {gesture.id: gesture}


def type_step(
    *,
    after: AfterState | None = None,
    page: str = f"{_SYSTEM}/app",
    gid: str = "ges_type",
    at: float = 1.0,
) -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id=gid,
        tenant=_TENANT,
        stream_id="stream-1",
        batch_id="batch-1",
        at=at,
        url=page,
        system=_SYSTEM,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="type",
            at=at,
            value="GT1",
            target=Target(
                role="textbox",
                name="Customer Type",
                component=Component(field_label="Customer Type"),
            ),
            after=after,
        ),
    )
    by_id = {gesture.id: gesture}
    step = Step(
        order=2,
        says="Type the customer type",
        system=_SYSTEM,
        cites=[gesture.id],
        parameters=["Customer Type"],
    )
    return step, by_id


async def save_job(uow: UnitOfWork, workflow_id: str) -> Workflow:
    step, by_id = type_step()
    job = replace(
        _WORKFLOW,
        id=workflow_id,
        steps=[replace(step, order=0)],
        parameters=[{"name": "Customer Type", "seen_values": ["GT0", "GT1"], "required": True}],
    )
    await uow.workflows.save(job)
    await uow.gestures.add_gestures(tuple(by_id.values()))
    return job


def posted(name: str, at: float, status: int | None = 201) -> Call:
    """A `POST SAVE_URL` whose body names `name`, as the page sends it."""
    body = Body(text=json.dumps({"name": name}), mime_type="application/json")
    return Call(method="POST", url=SAVE_URL, status=status, started_at=at, request_body=body)


def demonstrated_save(
    gid: str, at: float, names: tuple[str, str]
) -> tuple[Step, dict[str, Gesture]]:
    """A save demonstrated twice, ten seconds apart, once with each of `names`:
    two demonstrations are what say which parameter a write carries."""
    by_id: dict[str, Gesture] = {}
    for n, name in enumerate(names):
        _, one = save_step(gid=f"{gid}_{n}", at=at + 10 * n)
        (gesture,) = one.values()
        by_id[gesture.id] = replace(gesture, requests=[posted(name, at + 10 * n)])
    return Step(order=0, says="Save it", system=_SYSTEM, cites=list(by_id)), by_id


def two_saves(form: str = f"{_SYSTEM}/app") -> list[tuple[Step, dict[str, Gesture]]]:
    """Type, save `First`, type on `form`, save `Second`."""
    return [
        type_step(gid="ges_type_0", at=1.0),
        demonstrated_save("ges_save_1", 2.0, ("A1", "A2")),
        type_step(gid="ges_type_2", at=3.0, page=form),
        demonstrated_save("ges_save_3", 4.0, ("B1", "B2")),
    ]


async def two_writes_job(uow: UnitOfWork, workflow_id: str) -> Workflow:
    steps = two_saves()
    job = replace(
        _WORKFLOW,
        id=workflow_id,
        steps=[replace(step, order=n) for n, (step, _) in enumerate(steps)],
        parameters=[
            {"name": "First", "seen_values": ["A1", "A2"]},
            {"name": "Second", "seen_values": ["B1", "B2"]},
        ],
    )
    await uow.workflows.save(job)
    await uow.gestures.add_gestures(tuple(g for _, cited in steps for g in cited.values()))
    return job


async def operator_did(
    uow: UnitOfWork, *, device: str, tab: int, at: float, calls: Sequence[Call]
) -> None:
    """One gesture uploaded from `device`'s browser tab `tab`, carrying `calls`."""
    await uow.gestures.add_gestures(
        (
            Gesture(
                id=f"ges_{device}_{at}",
                tenant=_TENANT,
                stream_id=device,
                batch_id="batch-op",
                at=at,
                url=f"{_SYSTEM}/app",
                system=_SYSTEM,
                tab_id=tab,
                frame_url=None,
                action=Action(kind="click", at=at, target=Target(role="button", name="Save")),
                requests=list(calls),
            ),
        )
    )


def mail_send_step() -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id="g-send",
        tenant="t1",
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=GMAIL,
        system=GMAIL,
        tab_id=7,
        frame_url=None,
        action=Action(
            kind="click",
            at=1_000.0,
            url=GMAIL,
            target=Target(tag="button", role="button", name="Send"),
        ),
    )
    step = Step(order=0, says="Send the mail", system=None, cites=["g-send"])
    return step, {"g-send": gesture}


async def write_ok(workflow: Workflow, values: Mapping[str, str], thread: str) -> Written | str:
    return Written(to="ops@example.com", subject="s", body="b", thread=thread, in_reply_to="")


async def _sent(sent: list[Written], mail: Written, msg_id: str) -> tuple[str, str]:
    sent.append(mail)
    return msg_id, ""


async def _answer(msg_id: str, why: str) -> tuple[str, str]:
    return msg_id, why


IDP = "https://login.idp.example"


async def with_a_recorded_sign_in(
    uow: UnitOfWork,
    *,
    lands_on: str,
    username: str | None,
    at: str = IDP,
    tenant: str = "greyorange",
) -> Workflow:
    lands = origin_of(lands_on)

    def did(name: str, when: float, system: str, action: Action) -> Gesture:
        return Gesture(
            id=f"ges_{name}",
            tenant=tenant,
            stream_id="stream-sign-in",
            batch_id="batch-sign-in",
            at=when,
            url=f"{system}/login",
            system=system,
            tab_id=1,
            frame_url=None,
            action=action,
        )

    go = did(
        "go", 3.0, at, Action(kind="click", at=3.0, target=Target(tag="button", css_path="#go"))
    )
    go.page_events.append(PageMark(at=3.5, page_kind="load", url=f"{lands}/app"))
    gestures = (
        did(
            "user",
            1.0,
            at,
            Action(
                kind="type",
                at=1.0,
                value=username,
                target=Target(tag="input", css_path="#username"),
            ),
        ),
        did(
            "pass",
            2.0,
            at,
            Action(
                kind="type", at=2.0, target=Target(tag="input", css_path="#password", secret=True)
            ),
        ),
        go,
        did("there", 4.0, lands, Action(kind="click", at=4.0)),
    )
    job = Workflow(
        id="wfl_sign_in",
        tenant=tenant,
        title="Sign in",
        narrative="n",
        steps=[
            Step(order=n, says=f"sign-in step {n}", system=at, cites=[f"ges_{one}"])
            for n, one in enumerate(("user", "pass", "go"))
        ],
        signs_in=True,
    )
    await uow.workflows.save(job)
    await uow.gestures.add_gestures(gestures)
    return job


class SigningLane:
    """Replays a sign-in chain against a `FakePageDriver`: it records the step
    orders it was given in `stepped` and the secret it was handed in
    `secret_seen`, and the chain's last step signs the context in unless the
    driver `refuses`; `sign_ins` counts the chains that reached that step."""

    lane = Lane.UI

    def __init__(self, driver: FakePageDriver) -> None:
        self._driver = driver
        self.stepped: list[int] = []
        self.secret_seen: str | None = None
        self.sign_ins = 0

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        self.stepped.append(step.order)
        self.secret_seen = ctx.secret or self.secret_seen
        last = sign_in_chain(ctx.workflow, ctx.by_id)[-1]
        if step.order == last.order:
            self.sign_ins += 1
        if step.order == last.order and ctx.held is not None and not self._driver.refuses:
            self._driver.signed.add(ctx.held.session.context_id)
        return StepResult("done", Lane.UI)


@dataclass
class LookupWorld:
    run_lookups: RunLookups
    broker: SessionBroker
    uow: FakeUnitOfWork
    driver: FakePageDriver
    http: FakeHttpCaller
    lane: SigningLane
    reauths: int = 0


class _CountingBroker(SessionBroker):
    world: LookupWorld

    async def reauth(
        self,
        ctx: RequestContext,
        held: Held,
        start_url: str,
        *,
        back_to: str | None = None,
        park: bool = True,
    ) -> None:
        self.world.reauths += 1
        await super().reauth(ctx, held, start_url, back_to=back_to, park=park)


async def lookup_world(*gestures: Gesture) -> LookupWorld:
    uow, driver, vault, http = (
        FakeUnitOfWork(),
        FakePageDriver(),
        FakeCredentialVault(),
        FakeHttpCaller(),
    )
    await with_a_recorded_sign_in(
        uow, lands_on=gestures[0].url or "", username="lena", tenant=_TENANT
    )
    await vault.store(Account.of(_TENANT, IDP, "lena").vault_key("password"), "not-a-real-secret")
    await uow.gestures.add_gestures(gestures)
    driver.shows_sign_in_until_signed = True
    lane = SigningLane(driver)
    broker = _CountingBroker(
        uow,
        FakeBrowserPool({"http://steel:3000": 1}),
        driver,
        FakeAccountLocks(),
        vault,
        FakeClock(),
        ui=lane,
        close_s=0.05,
    )
    world = LookupWorld(RunLookups(uow, broker, http), broker, uow, driver, http, lane)
    broker.world = world
    return world


async def lease_for(uow: UnitOfWork, clock: Clock, *, holder: str = "run_1") -> Lease:
    """Inserts a `ready` lease on a Steel session held in `http://steel:3000`,
    its context id and steel session id deliberately distinct -- a sweeper
    test has to tell which one a pool close was actually given."""
    now = clock.now()
    lease = Lease(
        id=new_lease_id(),
        account=Account.of(_TENANT, _SYSTEM, "clerk"),
        container_url="http://steel:3000",
        steel_session_id=new_lease_id(),
        context_id=new_lease_id(),
        holder=holder,
        heartbeat_at=now,
        expires_at=now + K_LEASE_TTL,
        state=LeaseState.READY,
    )
    async with uow:
        saved = await uow.browser_sessions.lease(TenantId(_TENANT), lease)
        await uow.commit()
    return saved


APP = f"{_SYSTEM}/app"


class RecordingLane:
    """Answers each `execute` with the next of `results` (more are added with
    `answers`) and counts them in `calls`, keeping each context it was handed
    in `contexts` and first running what `on_execute` was given on it; a lane
    given no results is one the step must never reach. `read_back` answers `settles`
    and counts itself in `read_backs`, as the API lane's read-back would."""

    def __init__(self, lane: Lane, *results: StepResult, settles: Verdict | None = None) -> None:
        self.lane = lane
        self._results = list(results)
        self.settles = settles
        self.calls = 0
        self.read_backs = 0
        self.contexts: list[LaneContext] = []
        self._on_execute: Callable[[LaneContext], Awaitable[None] | None] | None = None

    def answers(self, *results: StepResult) -> None:
        self._results.extend(results)

    def on_execute(self, act: Callable[[LaneContext], Awaitable[None] | None]) -> None:
        self._on_execute = act

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        self.calls += 1
        self.contexts.append(ctx)
        if self._on_execute is not None and (acted := self._on_execute(ctx)) is not None:
            await acted
        assert self._results, f"the {self.lane} lane was not expected to run"
        return self._results.pop(0)

    async def read_back(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> Verdict | None:
        self.read_backs += 1
        self.contexts.append(ctx)
        return self.settles


def no_tool() -> RecordingLane:
    return RecordingLane(Lane.TOOL)


def no_api() -> RecordingLane:
    return RecordingLane(Lane.API)


def never() -> RecordingLane:
    return RecordingLane(Lane.SIGHT)


class FakeBroker(SessionBroker):
    """A `SessionBroker` whose `reauth` counts itself in `reauths`, keeps the
    page it was asked to go back to in `back_tos`, and raises `refuses` when
    set, the way a sign-in that needs a person does."""

    def __init__(self, *, refuses: BaseException | None = None) -> None:
        page = FakePageDriver()
        super().__init__(
            FakeUnitOfWork(),
            FakeBrowserPool({}),
            page,
            FakeAccountLocks(),
            FakeCredentialVault(),
            FakeClock(),
            ui=SigningLane(page),
        )
        self.reauths = 0
        self.back_tos: list[str | None] = []
        self.refuses = refuses

    async def reauth(
        self,
        ctx: RequestContext,
        held: Held,
        start_url: str,
        *,
        back_to: str | None = None,
        park: bool = True,
    ) -> None:
        self.reauths += 1
        self.back_tos.append(back_to)
        if self.refuses is not None:
            raise self.refuses


STEEL = "http://steel:3000"


class ScriptedFill(FillField):
    """Answers each `fill` with the next of the `Filled` given to `answers`,
    keeping what it was asked in `filled` as (field, value, learned locator);
    a fill given no answers is one the run must never make."""

    def __init__(self) -> None:
        super().__init__(FakePageDriver(), None)
        self._results: list[Filled] = []
        self.filled: list[tuple[Composed, str, LearnedStep | None]] = []

    def answers(self, *filled: Filled) -> None:
        self._results.extend(filled)

    async def fill(
        self,
        composed: Composed,
        value: str,
        write: Step,
        ctx: LaneContext,
        *,
        learned: LearnedStep | None = None,
    ) -> Filled:
        self.filled.append((composed, value, learned))
        assert self._results, "no field was expected to be filled"
        return self._results.pop(0)


@dataclass
class Lanes:
    tool: RecordingLane
    api: RecordingLane
    ui: RecordingLane
    sight: RecordingLane


@dataclass
class SteelRun:
    """A Steel run of a job made of the given steps, numbered from 0 in the
    order given, stored in `uow` with its job, its gestures and a recorded
    sign-in whose saved state restores without a password. `run_steps` drives
    it over a real `SessionBroker` on fakes and an executor over `lanes`."""

    uow: FakeUnitOfWork
    run_id: str
    run_steps: RunSteps
    lanes: Lanes
    broker: SessionBroker
    driver: FakePageDriver
    account: Account
    vault: FakeCredentialVault
    clock: FakeClock
    durable: FakeDurableExecution
    fill: ScriptedFill

    def progress(self) -> Progress:
        return Progress.of(self.uow.workflow_runs.rows[self.run_id].progress)

    async def job(self) -> Workflow:
        return await self.uow.workflows.get(TENANT, _WORKFLOW.id)

    async def learned(self) -> tuple[LearnedStep, ...]:
        return await self.uow.workflows.learned_for(_WORKFLOW.id)

    async def answer(
        self, question_id: str, *, value: str = "", verdict: WriteVerdict = ""
    ) -> None:
        """Answers as the panel does, then runs what the workflow runs on it."""
        await AnswerRun(self.uow, self.durable).execute(
            CTX, run_id=self.run_id, question_id=question_id, value=value, verdict=verdict
        )
        await self.run_steps.answered(CTX, self.run_id, question_id)

    async def thread_says(self) -> list[dict[str, object]]:
        """What the run's operator (`clerk`) has been told in their own thread,
        oldest first, each message as its `text` and `decision`."""
        found = await ReadThreads(self.uow).current(CTX)
        if found is None:
            return []
        return [{"text": one.text, "decision": one.decision} for one in found.messages]

    async def asks(self, question: dict[str, str]) -> None:
        """Leaves `question` standing on the run, as a step that asked it would."""
        progress = Progress.of((await self.saved_run()).progress)
        progress.asking = question
        assert await self.uow.workflow_runs.record_progress(TENANT, self.run_id, progress.as_json())

    def restarted(self) -> RunSteps:
        """The run's steps as a fresh worker process drives them: a new broker
        and executor over the same database and the same browser, holding
        nothing the old process knew."""
        return _worker(self.uow, self.driver, self.vault, self.clock, self.lanes, self.fill)[1]

    async def saved_run(self, run_id: str = "") -> WorkflowRun:
        run = await self.uow.workflow_runs.get(TENANT, run_id or self.run_id)
        assert run is not None
        return run

    async def another_run(self, run_id: str) -> None:
        run = await self.saved_run()
        await self.uow.workflow_runs.save(replace(run, id=run_id, steps=[], progress={}))

    async def mark_sending(self, order: int, lane: Lane = Lane.UI) -> None:
        progress = Progress.of((await self.saved_run()).progress)
        progress.sending(order, lane.value)
        assert await self.uow.workflow_runs.record_progress(TENANT, self.run_id, progress.as_json())


async def steel_run(
    *,
    steps: Sequence[tuple[Step, dict[str, Gesture]]],
    live: bool = True,
    run_id: str = "run_a",
    recorded_sign_in: bool = True,
    progress: Progress | None = None,
    values: Mapping[str, str] | None = None,
    job: Workflow | None = None,
) -> SteelRun:
    uow, driver, clock, vault = (
        FakeUnitOfWork(),
        FakePageDriver(),
        FakeClock(NOW),
        FakeCredentialVault(),
    )
    by_id = {
        one: replace(seen, tenant=_TENANT) for _, cited in steps for one, seen in cited.items()
    }
    if job is None:
        job = replace(
            _WORKFLOW, steps=[replace(step, order=n) for n, (step, _) in enumerate(steps)]
        )
        kept = set(undeliverable(job, by_id))
        job.parameters = [one for one in job.parameters if one["name"] not in kept]
    if values is None:
        declared = {str(one["name"]) for one in job.parameters}
        values = {name: "GT1" for name in ("Customer Type",) if name in declared}
    await uow.workflows.save(job)
    await uow.gestures.add_gestures(tuple(by_id.values()))
    if recorded_sign_in:
        await with_a_recorded_sign_in(uow, lands_on=APP, username="clerk", tenant=_TENANT)
    account = Account.of(_TENANT, IDP, "clerk")
    await vault.store(account.vault_key("state"), '{"cookies": []}')
    await uow.workflow_runs.save(
        WorkflowRun(
            id=run_id,
            tenant=_TENANT,
            workflow_id=job.id,
            device_id="",
            values=dict(values),
            started_by="clerk",
            live=live,
            allow_focus=False,
            started_at=NOW.isoformat(),
            executor="steel",
            progress=progress.as_json() if progress else {},
        )
    )
    lanes = Lanes(
        *(RecordingLane(lane, settles=None) for lane in (Lane.TOOL, Lane.API, Lane.UI, Lane.SIGHT))
    )
    fill = ScriptedFill()
    broker, run_steps = _worker(uow, driver, vault, clock, lanes, fill)
    return SteelRun(
        uow,
        run_id,
        run_steps,
        lanes,
        broker,
        driver,
        account,
        vault,
        clock,
        FakeDurableExecution(),
        fill,
    )


def _worker(
    uow: FakeUnitOfWork,
    driver: FakePageDriver,
    vault: FakeCredentialVault,
    clock: FakeClock,
    lanes: Lanes,
    fill: FillField | None = None,
) -> tuple[SessionBroker, RunSteps]:
    broker = SessionBroker(
        uow,
        FakeBrowserPool({STEEL: 2}),
        driver,
        FakeAccountLocks(),
        vault,
        clock,
        ui=SigningLane(driver),
    )
    executor = StepExecutor(lanes.tool, lanes.api, lanes.ui, lanes.sight, broker)
    return broker, RunSteps(
        uow,
        broker,
        executor,
        Teach(uow, clock),
        lanes.api,
        clock,
        FakeIdFactory(),
        fill=fill or ScriptedFill(),
    )


QID = "q-run_ask-0-0"


async def asking_steel_run(uow: UnitOfWork, *, kind: str) -> WorkflowRun:
    """A running Steel run whose standing question is `QID`, of `kind`."""
    run = WorkflowRun(
        id="run_ask",
        tenant=_TENANT,
        workflow_id=_WORKFLOW.id,
        device_id="",
        values={},
        started_by="clerk",
        live=True,
        allow_focus=False,
        started_at=NOW.isoformat(),
        executor="steel",
        progress={"asking": {"id": QID, "kind": kind, "text": "what now?"}},
    )
    async with uow:
        await uow.workflow_runs.save(run)
        await uow.commit()
    return run


async def running_steel_run(uow: FakeUnitOfWork, run_id: str = "run_steel") -> WorkflowRun:
    """A live run on Steel, still `running`, stored in `uow` under `CTX`."""
    run = WorkflowRun(
        id=run_id,
        tenant=_TENANT,
        workflow_id=_WORKFLOW.id,
        device_id="",
        values={},
        started_by="clerk",
        live=True,
        allow_focus=False,
        started_at=NOW.isoformat(),
        executor="steel",
    )
    await uow.workflow_runs.save(run)
    return run
