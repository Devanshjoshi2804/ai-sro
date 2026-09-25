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

`lease_for` inserts a `ready` lease a sweeper test can expire.

For the executor, `RecordingLane` answers scripted results and counts its
calls (`no_tool`, `no_api` and `never` are lanes the step must not reach),
and `FakeBroker` counts its re-sign-ins.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.context import RequestContext
from sro.application.execution.mail_job import Written
from sro.application.lookup.run_lookups import RunLookups
from sro.application.ports.page import PageAnswer, SessionRef
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState, new_lease_id
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Lane, SeenCall, StepResult, Verdict
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import (
    Action,
    AfterState,
    Body,
    Call,
    Component,
    Gesture,
    PageMark,
    Target,
)
from sro.domain.shared.hosts import origin_of
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.signing_in import sign_in_chain
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeBrowserPool,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
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

GMAIL = "https://mail.google.com/mail/u/0/#inbox"


async def _nothing() -> None:
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
    about_to_write: Callable[[], Awaitable[None]] | None = None,
    thread: str = "",
    reauthed: bool = False,
    adding: Mapping[int, Adding] = MappingProxyType({}),
) -> LaneContext:
    return LaneContext(
        tenant_id=TenantId(_TENANT),
        principal_id=PrincipalId("clerk"),
        workflow=_WORKFLOW,
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


def save_step(
    *, status: int = 201, after: AfterState | None = None, body: Body | None = None
) -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id="ges_save",
        tenant=_TENANT,
        stream_id="stream-1",
        batch_id="batch-1",
        at=1.0,
        url=f"{_SYSTEM}/app",
        system=_SYSTEM,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0, target=Target(role="button", name="Save"), after=after),
        requests=[
            Call(
                method="POST",
                url=f"{_SYSTEM}/api/customer-types",
                status=status,
                started_at=1.0,
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
) -> tuple[Step, dict[str, Gesture], tuple[VerifiedWrite, ...]]:
    by_id: dict[str, Gesture] = {}
    for nth, name in enumerate(("GT0", "GT1")):
        at = float(nth + 1)
        requests = [
            Call(
                method="POST",
                url=f"{_SYSTEM}/api/customer-types",
                status=201,
                started_at=at,
                request_body=Body(text=f'{{"name": "{name}"}}', mime_type="application/json"),
                request_headers=dict(request_headers),
            )
        ]
        if read_back is not None:
            read = read_back.format(name=name)
            read = read if read.startswith("http") else f"{_SYSTEM}{read}"
            requests.append(Call(method="GET", url=read, status=200, started_at=at + 0.5))
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
        parameters=["Customer Type"],
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


def type_step(*, after: AfterState | None = None) -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id="ges_type",
        tenant=_TENANT,
        stream_id="stream-1",
        batch_id="batch-1",
        at=1.0,
        url=f"{_SYSTEM}/app",
        system=_SYSTEM,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="type",
            at=1.0,
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
    driver: FakePageDriver
    http: FakeHttpCaller
    reauths: int = 0


class _CountingBroker(SessionBroker):
    world: LookupWorld

    async def reauth(
        self, ctx: RequestContext, held: Held, start_url: str, *, back_to: str | None = None
    ) -> None:
        self.world.reauths += 1
        await super().reauth(ctx, held, start_url, back_to=back_to)


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
    broker = _CountingBroker(
        uow,
        FakeBrowserPool({"http://steel:3000": 1}),
        driver,
        FakeAccountLocks(),
        vault,
        FakeClock(),
        ui=SigningLane(driver),
        close_s=0.05,
    )
    world = LookupWorld(RunLookups(uow, broker, http), driver, http)
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
    """Answers each `execute` with the next of `results` and counts them in
    `calls`, keeping each context it was handed in `contexts`; a lane given no
    results is one the step must never reach. `read_back` answers `settles`
    and counts itself in `read_backs`, as the API lane's read-back would."""

    def __init__(self, lane: Lane, *results: StepResult, settles: Verdict | None = None) -> None:
        self.lane = lane
        self._results = list(results)
        self.settles = settles
        self.calls = 0
        self.read_backs = 0
        self.contexts: list[LaneContext] = []

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        assert self._results, f"the {self.lane} lane was not expected to run"
        self.calls += 1
        self.contexts.append(ctx)
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
        self, ctx: RequestContext, held: Held, start_url: str, *, back_to: str | None = None
    ) -> None:
        self.reauths += 1
        self.back_tos.append(back_to)
        if self.refuses is not None:
            raise self.refuses
