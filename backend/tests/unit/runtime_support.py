"""Shared fixtures for the runtime lanes' unit tests.

`scripted_driver` is a `FakePageDriver` configured by keyword; `save_step`,
`type_step`, `type_then_save_step`, `read_step`, `mail_send_step` and
`lane_context` build a `Step`, its cited
`Gesture`s and a `LaneContext` without every lane test re-typing the same
evidence by hand.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.execution.mail_job import Written
from sro.application.ports.page import PageAnswer, SessionRef
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.account import Account, Lease, LeaseState
from sro.domain.execution.lanes import SeenCall
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import (
    Action,
    AfterState,
    Body,
    Call,
    Component,
    Gesture,
    Target,
)
from sro.domain.shared.identifiers import PrincipalId, TenantId
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
) -> FakePageDriver:
    return FakePageDriver(
        answer=answer,
        calls=calls,
        before=before,
        holds=holds,
        sign_in=sign_in,
        url=url,
        unsettled=unsettled,
    )


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
