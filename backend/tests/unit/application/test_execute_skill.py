"""L1 execution: what leaves the process, and what deliberately does not.

The interesting assertions here are all about restraint. A skill is a recipe for
changing a warehouse, so most of what an executor must get right is refusing.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest, NotRunnable
from sro.application.induction.assertions import extract
from sro.domain.execution.run import RunStatus, StepDisposition
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
COOKIE_REF = "blue_yonder/SG/cookie"
SCOPED = f"{f.TENANT}/{COOKIE_REF}"


def _executor(
    uow: FakeUnitOfWork, http: FakeHttpCaller, vault: FakeCredentialVault
) -> ExecuteSkill:
    return ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory())


async def _skill(  # type: ignore[no-untyped-def]
    uow: FakeUnitOfWork, version, stage: PromotionStage = PromotionStage.RECORDED
) -> None:
    """A skill at ``stage``, promoted one rung at a time as a reviewer would."""
    skill = f.skill(versions=0)
    skill.add_version(version)
    current = PromotionStage.RECORDED
    while current is not stage:
        current = current.next_stage()
        version.promote(current, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


def _write_step(**plan_overrides: object) -> SkillStep:
    return f.step(
        index=0,
        network_plan=f.network_plan(
            headers=(
                HeaderPlan(
                    name="cookie", sensitivity=Sensitivity.SESSION, credential_ref=COOKIE_REF
                ),
                HeaderPlan(name="Referer", sensitivity=Sensitivity.TRANSPORT, managed=True),
                HeaderPlan(
                    name="Content-Type",
                    sensitivity=Sensitivity.SEMANTIC,
                    value=Template("application/json"),
                ),
            ),
            **plan_overrides,
        ),
    )


async def test_a_shadow_run_produces_the_write_without_sending_it() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(
        uow,
        f.skill_version(steps=(_write_step(),)),
        PromotionStage.SHADOW,
    )

    run = await _executor(uow, http, vault).execute(
        CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "555"})
    )

    assert http.sent == [], "shadow must not change a warehouse"
    assert run.steps[0].disposition is StepDisposition.WITHHELD
    assert run.steps[0].url == "https://wms.test/api/shipments/555/release"
    assert run.steps[0].idempotency_key is not None
    assert run.status is RunStatus.SUCCEEDED


async def test_a_recorded_skill_cannot_be_run_at_all() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _skill(uow, f.skill_version(steps=(_write_step(),)))

    with pytest.raises(NotRunnable, match="reviewed"):
        await _executor(uow, http, vault).execute(
            CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "1"})
        )

    assert uow.runs.rows == {}, "a refusal must not leave a run behind"


async def test_a_write_above_shadow_names_the_human_who_allowed_it() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    with pytest.raises(NotRunnable, match="authorised"):
        await _executor(uow, http, vault).execute(
            CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "1"})
        )


async def test_an_assisted_run_sends_the_write_with_the_live_session() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.answer(status_code=200, text='{"ok": true}')
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert len(http.sent) == 1
    sent = http.sent[0]
    assert sent["headers"] == {
        # `referer` is set for this call, not replayed from the demonstration.
        "referer": "https://wms.test/",
        "cookie": "session=live",
        "Content-Type": "application/json",
    }
    assert sent["body"] == '{"shipmentId": "555"}'
    assert run.steps[0].disposition is StepDisposition.PERFORMED
    assert run.status is RunStatus.SUCCEEDED


async def test_a_missing_session_stops_the_step_instead_of_sending_it_anyway() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert http.sent == [], "a call without its credential is a call as nobody"
    assert run.steps[0].disposition is StepDisposition.FAILED
    assert "cookie" in (run.steps[0].detail or "")
    assert run.status is RunStatus.FAILED


async def test_a_failed_assertion_fails_the_run_even_though_the_call_worked() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.answer(status_code=200, text='{"status": "REJECTED"}')
    step = f.step(
        index=0,
        network_plan=_write_step().network_plan,
        assertions=(
            Assertion(
                kind=AssertionKind.RESPONSE_FIELD_EQUALS,
                pointer="/status",
                expected=Template("RELEASED"),
            ),
        ),
    )
    await _skill(uow, f.skill_version(steps=(step,)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.status is RunStatus.FAILED
    assert run.steps[0].assertion_failures == ("/status is 'REJECTED', expected 'RELEASED'",)


async def test_a_step_reads_a_value_the_next_step_needs() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.answer(status_code=200, text='{"data": [{"itemNumber": "0113228000"}]}')
    http.answer(status_code=200, text="{}")

    read = f.step(
        index=0,
        intent="find the item",
        network_plan=f.network_plan(
            method="GET", url=Template("https://wms.test/api/items"), body=None
        ),
    )
    write = f.step(
        index=1,
        network_plan=f.network_plan(
            url=Template("https://wms.test/api/adjust"),
            body=Template('{"item": "${item_number}"}'),
        ),
    )
    await _skill(
        uow,
        f.skill_version(
            steps=(read, write),
            parameters=(
                Parameter(
                    name="item_number",
                    kind=ParameterKind.DERIVED,
                    source_step_index=0,
                    source_pointer="/data/0/itemNumber",
                ),
            ),
        ),
        PromotionStage.ASSISTED,
    )

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(skill_id=SkillId("skill-1"), parameters={}, authorized_by="supervisor"),
    )

    assert http.sent[1]["body"] == '{"item": "0113228000"}'
    assert run.status is RunStatus.SUCCEEDED


async def test_a_timeout_on_a_write_says_the_call_may_have_landed() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.unreachable = True
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.status is RunStatus.FAILED
    assert "may have arrived" in (run.steps[0].detail or "")


async def test_a_same_origin_referer_is_set_for_the_call_being_made() -> None:
    """Blue Yonder redirects an API call with no `Referer` to the login page,
    however good the session is. The captured value belongs to a page that no
    longer exists, so the executor sends one true of this request instead."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    headers = http.sent[0]["headers"]
    assert isinstance(headers, dict)
    assert headers["referer"] == "https://wms.test/"
    assert "origin" not in headers, "only the headers the demonstration carried"


async def test_a_boolean_matches_what_induction_wrote_down() -> None:
    """The WMS answers `"approvalRequired": true`. Induction rendered that with
    Python's `str` -- "True" -- and the executor read the live value back as
    "true", so a run that did exactly the right thing reported a mismatch
    against itself."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    answer = '{"approvalRequired": true}'
    http.answer(status_code=200, text=answer)

    evidence = extract(
        f.frame(requests=(f.request(response_body=f.body(answer)),)),
        f.frame(requests=(f.request(response_body=f.body(answer)),)),
    )
    step = f.step(index=0, network_plan=_write_step().network_plan, assertions=evidence.assertions)
    await _skill(uow, f.skill_version(steps=(step,)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert any(a.pointer == "/approvalRequired" for a in evidence.assertions)
    assert run.steps[0].assertion_failures == ()


async def test_a_skill_taught_at_one_site_uses_the_system_s_login() -> None:
    """A skill names `<system>/<site>/cookie`; a login is to a system.

    Two places used to hold "the session" — the blob written when an operator
    connected, and a cookie header written separately. They aged apart, and
    every call came back 302 to the login page while the browser was signed in.
    """
    from sro.application.execution.headers import resolve_headers
    from sro.domain.recording.sensitivity import Sensitivity
    from sro.domain.skill.plan import HeaderPlan

    vault = FakeCredentialVault()
    await vault.store("acme/blue_yonder/cookie", "session=current")

    resolved = await resolve_headers(
        (
            HeaderPlan(
                name="cookie",
                sensitivity=Sensitivity.SESSION,
                credential_ref="blue_yonder/SG/cookie",
            ),
        ),
        values={},
        vault=vault,
        scope="acme",
        session_scope="blue_yonder/SG",
    )

    assert resolved.missing == ()
    assert resolved.headers["cookie"] == "session=current"
