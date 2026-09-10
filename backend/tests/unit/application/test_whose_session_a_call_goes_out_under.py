"""Which system's credentials one step of a workflow is allowed to use.

Everything credential-shaped hangs off one string: the stored cookie, the minted
CSRF token, the live referer and the bearer are all keyed by `<system>/<site>`.
That string used to come from the skill's own objective key, which is exact
while every step calls the same system.

A workflow does not. Keyed by where its work lands, its ERP half would be handed
the WMS's session -- one customer system's credentials sent to another, silently,
by a system whose whole promise is that evidence stays where it was captured.

The second rule here is about what a device run needs at all. `Cookie` is a
forbidden header name for `fetch`, so a session resolved out of the vault is
dropped by the browser and the tab's own is sent instead
(`test_a_session_the_backend_supplies_is_not_what_goes_out`, in a real Chrome).
Requiring it refused the one case naming a device exists for.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    ExecutionRequest,
    StartRun,
    _missing_named,
)
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.run import StepDisposition
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeAgentDrivers,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS, ERP = "blue_yonder", "sap"


class _Tokens:
    """An offline token per system, which is what a bearer is. Unlike a cookie
    it is not a forbidden header, so it does reach the wire from a browser."""

    def __init__(self, **held: str) -> None:
        self.held = held

    async def access_token(self, *, tenant: str, system: str) -> str | None:
        return self.held.get(system)


def _connection(ident: str, system: str, base_url: str) -> Connection:
    connection = Connection(
        id=ConnectionId(ident),
        tenant_id=f.TENANT,
        name=system,
        target_system=system,
        base_url=base_url,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    return connection


def _step(index: int, url: str) -> SkillStep:
    """One call, carrying the reference induction writes onto every step.

    The WMS in both, because induction knows one system per skill and writes it
    into all of them -- which is exactly the reference the second half must not
    be resolved by.
    """
    return f.step(
        index=index,
        network_plan=f.network_plan(
            url=Template(url),
            body=None,
            headers=(
                HeaderPlan(
                    name="cookie",
                    sensitivity=Sensitivity.SESSION,
                    credential_ref=f"{WMS}/DC01/cookie",
                ),
                HeaderPlan(name="Referer", sensitivity=Sensitivity.TRANSPORT, managed=True),
            ),
        ),
    )


async def _world(
    *,
    connect_erp: bool = True,
    steps: tuple[SkillStep, ...] | None = None,
    systems: tuple[str, ...] = (WMS, ERP),
) -> tuple[FakeUnitOfWork, FakeHttpCaller, FakeCredentialVault]:
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    async with uow:
        await uow.connections.add(_connection("con-1", WMS, "https://wms.test/portal"))
        if connect_erp:
            await uow.connections.add(_connection("con-2", ERP, "https://erp.test/portal"))
        await uow.commit()

    await vault.store(f"{f.TENANT}/{WMS}/DC01/cookie", "wms=the-warehouse-session")
    await vault.store(f"{f.TENANT}/{WMS}/DC01/referer", "https://wms.test/waves")
    await vault.store(f"{f.TENANT}/{ERP}/DC01/referer", "https://erp.test/receipts")

    version = f.skill_version(
        steps=steps
        or (
            _step(0, "https://wms.test/api/waves/close"),
            _step(1, "https://erp.test/api/receipts"),
        ),
        parameters=(),
        systems=systems,
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    async with uow:
        await uow.skills.add(skill)
        await uow.commit()

    for _ in range(len(version.steps)):
        http.answer(status_code=200, text="{}")
    return uow, http, vault


def _request(*, device: bool = True) -> ExecutionRequest:
    return ExecutionRequest(
        skill_id=SkillId("skill-1"),
        parameters={},
        authorized_by="supervisor",
        device_id=DeviceId("dev-1") if device else None,
    )


async def _run(
    uow: FakeUnitOfWork, http: FakeHttpCaller, vault: FakeCredentialVault, *, device: bool = True
) -> object:
    # Bound to a browser, because a cross-system skill is refused without one:
    # the calls still go out of this process, addressed by the device's driver.
    return await ExecuteSkill(
        uow,
        http,
        vault,
        FakeClock(),
        FakeIdFactory(),
        agents=FakeAgentDrivers(http=http) if device else None,
    ).execute(CTX, _request(device=device))


async def test_each_half_is_scoped_to_the_system_it_calls() -> None:
    uow, http, vault = await _world()

    await _run(uow, http, vault)

    # The referer is looked up under `<system>/<facility>`, and pointing the ERP
    # at a WMS page is how Blue Yonder's own filter decides a call came from
    # nowhere. Keyed by the skill, both of these were the warehouse's.
    assert [call["headers"]["referer"] for call in http.sent] == [
        "https://wms.test/waves",
        "https://erp.test/receipts",
    ]


async def test_a_stored_session_never_travels_with_a_run_in_somebody_s_browser() -> None:
    uow, http, vault = await _world()

    await _run(uow, http, vault)

    # Not the ERP's, and not the WMS's either. The browser holds both sessions;
    # `Cookie` is a forbidden header for `fetch`, so anything resolved here
    # would be dropped on the way out -- and sending one system's session
    # towards another is the thing this must never do even in a header that
    # goes nowhere.
    assert all("cookie" not in call["headers"] for call in http.sent), http.sent


async def test_a_system_this_deployment_has_no_session_for_still_runs() -> None:
    """The whole reason for naming a device.

    Requiring the vault's copy failed the step with "connect the system" -- for
    a system nobody needs to connect, over a value the browser would have
    dropped.
    """
    uow, http, vault = await _world(connect_erp=False)

    run = await _run(uow, http, vault)

    assert len(http.sent) == 2
    assert all(step.disposition is StepDisposition.PERFORMED for step in run.steps)


async def test_the_other_system_s_token_is_not_sent_to_this_one() -> None:
    """A bearer is not a forbidden header, so unlike a cookie it does reach the
    wire from a browser -- which makes it the one credential a workflow could
    still leak."""
    uow, http, vault = await _world(connect_erp=False)
    tokens = _Tokens(**{WMS: "offline-token-for-the-warehouse"})

    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(CTX, _request())
    step = ExecuteStep(uow, http, vault, tokens=tokens, agents=FakeAgentDrivers(http=http))
    for index in range(2):
        await step.execute(CTX, run_id=run.id, index=index)

    assert http.sent[0]["headers"]["Authorization"] == "Bearer offline-token-for-the-warehouse"
    # An unconnected host in a workflow is *another system*, not this one with a
    # different name: falling back to the skill's own system would hand its
    # token to whoever answers at erp.test.
    assert "Authorization" not in http.sent[1]["headers"], http.sent[1]["headers"]


async def test_an_ordinary_skill_run_here_still_resolves_the_session_it_was_taught() -> None:
    """The fallback that must survive all of this.

    A single-system skill calling a host nobody registered as a connection is
    every deployment: the connection names the portal, and the API answers on
    another name. That is not a second system, and dropping its session would
    break every run there has ever been.
    """
    uow, http, vault = await _world(
        steps=(_step(0, "https://api.wms-internal.test/api/waves/close"),),
        systems=(WMS,),
    )

    await _run(uow, http, vault, device=False)

    assert http.sent[0]["headers"]["cookie"] == "wms=the-warehouse-session"


async def test_what_a_browser_run_is_told_when_a_value_has_to_be_minted() -> None:
    """ "Connect the system" is advice that would not have helped.

    A device run already has the browser's session; what can still be missing is
    a token minted per run, and that belongs to whichever session it was issued
    for. The names before the semicolon are the record the self-healer reads
    back, so they stay exactly where they were.
    """
    minted = f.step(
        index=0,
        network_plan=f.network_plan(
            url=Template("https://erp.test/api/receipts"),
            body=None,
            headers=(HeaderPlan(name="x-csrf-token", sensitivity=Sensitivity.CSRF, mint=True),),
        ),
    )
    uow, http, vault = await _world(steps=(minted,), systems=(WMS, ERP))

    run = await _run(uow, http, vault)

    detail = run.steps[0].detail or ""
    assert _missing_named(detail) == ("x-csrf-token",)
    assert "a run in your browser cannot mint it" in detail
    assert "connect the system" not in detail
