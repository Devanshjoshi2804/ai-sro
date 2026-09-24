"""Shared fixtures for the runtime lanes' unit tests.

`scripted_driver` is a `FakePageDriver` configured by keyword; `save_step`,
`type_step` and `lane_context` build a `Step`, its cited `Gesture`s and a
`LaneContext` without every lane test re-typing the same evidence by hand.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from types import MappingProxyType

from sro.application.ports.page import PageAnswer, SessionRef
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.account import Account, Lease, LeaseState
from sro.domain.execution.lanes import SeenCall
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Action, AfterState, Call, Component, Gesture, Target
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


async def _nothing() -> None:
    return None


def scripted_driver(
    *,
    answer: PageAnswer | None = None,
    calls: Sequence[SeenCall] = (),
    holds: bool = False,
    sign_in: bool = False,
    url: str = "",
    hit: object | None = None,
) -> FakePageDriver:
    return FakePageDriver(
        answer=answer, calls=calls, holds=holds, sign_in=sign_in, url=url, hit=hit
    )


def _held() -> Held:
    return Held(lease=_LEASE, target_id="tab-1", session=SessionRef("sess-1", "http://cdp.local"))


def lane_context(
    by_id: Mapping[str, Gesture],
    *,
    held: Held | None = None,
    learned: Mapping[int, LearnedStep] = MappingProxyType({}),
    secret: str | None = None,
    about_to_write: Callable[[], Awaitable[None]] | None = None,
) -> LaneContext:
    return LaneContext(
        tenant_id=TenantId(_TENANT),
        principal_id=PrincipalId("clerk"),
        workflow=_WORKFLOW,
        by_id=by_id,
        learned=learned,
        ledger=(),
        held=held if held is not None else _held(),
        stop=asyncio.Event(),
        secret=secret,
        about_to_write=about_to_write if about_to_write is not None else _nothing,
    )


def save_step(*, status: int = 201) -> tuple[Step, dict[str, Gesture]]:
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
        action=Action(kind="click", at=1.0, target=Target(role="button", name="Save")),
        requests=[
            Call(
                method="POST",
                url=f"{_SYSTEM}/api/customer-types",
                status=status,
                started_at=1.0,
            )
        ],
    )
    by_id = {gesture.id: gesture}
    step = Step(order=1, says="Save the customer type", system=_SYSTEM, cites=[gesture.id])
    return step, by_id


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
