"""Shared fixtures for the runtime lanes' unit tests.

`scripted_driver` is a `FakePageDriver` configured by keyword; `save_step`,
`type_step`, `type_then_save_step`, `read_step`, `mail_send_step` and
`lane_context` build a `Step`, its cited
`Gesture`s and a `LaneContext` without every lane test re-typing the same
evidence by hand.

`with_a_recorded_sign_in` stores a tagged sign-in job typed on an identity
provider (`IDP` unless told otherwise) that lands on a system, and
`SigningLane` stands in for the UI lane that replays it against a
`FakePageDriver`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.execution.mail_job import Written
from sro.application.ports.page import PageAnswer, SessionRef
from sro.application.ports.repositories import UnitOfWork
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.account import Account, Lease, LeaseState
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Lane, SeenCall, StepResult
from sro.domain.execution.learned_step import LearnedStep
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
from tests.unit.fakes import FakePageDriver

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

_WORKFLOW = Workflow(id="wfl_test", tenant=_TENANT, title="Save the customer type", narrative="")

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
    secret: str | None = None,
    about_to_write: Callable[[], Awaitable[None]] | None = None,
    thread: str = "",
    adding: Mapping[int, Adding] = MappingProxyType({}),
) -> LaneContext:
    return LaneContext(
        tenant_id=TenantId(_TENANT),
        principal_id=PrincipalId("clerk"),
        workflow=_WORKFLOW,
        by_id=by_id,
        learned=learned,
        ledger=(),
        held=held,
        stop=asyncio.Event(),
        secret=secret,
        thread=thread,
        about_to_write=about_to_write if about_to_write is not None else _nothing,
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
