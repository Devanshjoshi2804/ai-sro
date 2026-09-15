"""L1 execution: what leaves the process, and what deliberately does not.

The interesting assertions here are all about restraint. A skill is a recipe for
changing a warehouse, so most of what an executor must get right is refusing.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest, NotRunnable
from sro.application.induction.assertions import extract
from sro.domain.execution.run import RunStatus, StepDisposition
from sro.domain.execution.verdict import Verdict, judge
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import DEMOTE_AFTER_FAILURES
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


async def test_a_shadow_run_records_the_body_it_would_have_sent() -> None:
    """Method and URL say where; only the body says what.

    The whole purpose of the stage is a person reading the write before anything
    writes, and every decision induction made -- which field is a parameter,
    what an optional one nobody filled falls back to -- is in the body and
    nowhere else.
    """
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(
        uow,
        f.skill_version(
            steps=(
                _write_step(
                    body=Template(
                        '{"shipmentId": "${shipment_id}", "deltaPriority": ${delta_priority}}'
                    )
                ),
            ),
            parameters=(
                f.parameter(),
                f.parameter(
                    name="delta_priority",
                    absent_as="null",
                    unquoted_as="number",
                    observed_values=("1", "2"),
                ),
            ),
        ),
        PromotionStage.SHADOW,
    )

    run = await _executor(uow, http, vault).execute(
        CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "555"})
    )

    assert http.sent == []
    assert run.steps[0].request_body is not None
    assert json.loads(run.steps[0].request_body) == {
        "shipmentId": "555",
        "deltaPriority": None,
    }


async def test_a_body_too_large_to_record_says_so_rather_than_being_cut() -> None:
    """A truncated body reads exactly like a whole one, and a reviewer would
    sign off a write on half of it."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(
        uow,
        f.skill_version(steps=(_write_step(body=Template('{"note": "' + "x" * 70_000 + '"}')),)),
        PromotionStage.SHADOW,
    )

    run = await _executor(uow, http, vault).execute(
        CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "555"})
    )

    assert run.steps[0].request_body is None
    assert "too large to record" in (run.steps[0].detail or "")


def _bodied_version(body: str) -> SkillVersion:
    """A write whose body carries one supplied value and one optional nobody
    filled in -- the two things a reviewer checks a body for."""
    return f.skill_version(
        steps=(_write_step(body=Template(body)),),
        parameters=(
            f.parameter(),
            f.parameter(
                name="delta_priority",
                absent_as="null",
                unquoted_as="number",
                observed_values=("1", "2"),
            ),
        ),
    )


BODY = '{"shipmentId": "${shipment_id}", "deltaPriority": ${delta_priority}}'


async def test_a_write_that_was_sent_records_the_body_it_sent() -> None:
    """A step that says only "POST -> 201" says a record was created in a live
    warehouse and nothing about what is in it, and the review this system's
    safety rests on cannot be done without re-rendering the write by hand."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.answer(status_code=201)
    await _skill(uow, _bodied_version(BODY), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.steps[0].disposition is StepDisposition.PERFORMED
    assert run.steps[0].request_body == http.sent[0]["body"]
    assert json.loads(run.steps[0].request_body or "") == {
        "shipmentId": "555",
        "deltaPriority": None,
    }


async def test_a_write_that_failed_on_the_wire_records_the_body_it_tried() -> None:
    """ "The call may have arrived" is exactly the moment somebody needs to know
    what would have arrived."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.unreachable = True
    await _skill(uow, _bodied_version(BODY), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.steps[0].disposition is StepDisposition.FAILED
    assert json.loads(run.steps[0].request_body or "") == {
        "shipmentId": "555",
        "deltaPriority": None,
    }


async def test_a_read_that_was_sent_keeps_no_body() -> None:
    """A read's body is not what anybody reviews, and keeping every one would
    make the run log a copy of the traffic."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(
        uow,
        f.skill_version(steps=(_write_step(method="GET", body=Template('{"q": "x"}')),)),
        PromotionStage.ASSISTED,
    )

    run = await _executor(uow, http, vault).execute(
        CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "555"})
    )

    assert run.steps[0].disposition is StepDisposition.PERFORMED
    assert run.steps[0].request_body is None


async def test_a_sent_body_too_large_to_record_says_so_rather_than_being_cut() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(
        uow,
        f.skill_version(steps=(_write_step(body=Template('{"note": "' + "x" * 70_000 + '"}')),)),
        PromotionStage.ASSISTED,
    )

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.steps[0].disposition is StepDisposition.PERFORMED
    assert run.steps[0].request_body is None
    assert "too large to record" in (run.steps[0].detail or "")


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


async def test_a_run_that_never_reached_the_system_does_not_mark_the_skill_down() -> None:
    """Found by running the system for real: a skill that had created two work
    areas was one closed browser away from demotion, because a run that never
    left the machine counted as a run that got the wrong answer."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http.unreachable = True
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.ASSISTED)

    for _ in range(DEMOTE_AFTER_FAILURES):
        await _executor(uow, http, vault).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "555"},
                authorized_by="supervisor",
            ),
        )

    version = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).latest
    assert version.stage is PromotionStage.ASSISTED, "the browser was shut, not the skill broken"
    assert version.track_record.consecutive_failures == 0
    assert version.track_record.unreachable_runs == DEMOTE_AFTER_FAILURES


async def test_a_url_the_skill_rendered_wrong_is_the_skill_being_wrong() -> None:
    """The one way this exemption could be abused: a step that fails before
    anything is sent still never reached the system. It is still the skill's
    fault, so it is still counted."""
    step = _write_step(url=Template("not-a-url://{shipment_id}"))
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http = FakeHttpCaller()
    http.malformed = True
    await _skill(uow, f.skill_version(steps=(step,)), PromotionStage.ASSISTED)

    run = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.steps[0].disposition is StepDisposition.FAILED
    assert not run.steps[0].unreachable
    assert judge(run) is Verdict.FAILED
    assert "may have arrived" not in (run.steps[0].detail or ""), "nothing was sent"


async def test_a_browser_already_running_a_skill_is_refused_the_second_one() -> None:
    """The guard the skill path never had, in the words a person can act on.

    The rig refuses a second press for one browser -- `in_flight` names the run
    that has it, and `uq_workflow_runs_one_running_per_device` catches the race
    the read cannot see. This path had neither, so two triggers firing two
    skills at one device in the same minute both started and interleaved their
    clicks in one window: the corrupted form against a live warehouse that
    migration 0043 is about. Migration 0049 gives `runs` the same index; this
    is the read in front of it.
    """
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.SHADOW)
    laptop = DeviceId("dev_1")

    first = await _executor(uow, http, vault).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            device_id=laptop,
            authorized_by="supervisor",
        ),
    )
    # Still driving: nothing has ended it. (`execute` runs to completion here,
    # so the row is reopened -- what is under test is the guard, not how long a
    # real run takes.)
    where = next(key for key, run in uow.runs.rows.items() if str(run.id) == str(first.id))
    uow.runs.rows[where] = replace(uow.runs.rows[where], ended_at=None)
    assert uow.runs.rows[where].ended_at is None

    with pytest.raises(Conflict) as refused:
        await _executor(uow, http, vault).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "666"},
                device_id=laptop,
                authorized_by="supervisor",
            ),
        )

    assert str(first.id) in str(refused.value)


async def test_a_browser_whose_skill_run_has_ended_may_start_another() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    await _skill(uow, f.skill_version(steps=(_write_step(),)), PromotionStage.SHADOW)
    laptop = DeviceId("dev_1")

    for shipment in ("555", "666"):
        await _executor(uow, http, vault).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": shipment},
                device_id=laptop,
                authorized_by="supervisor",
            ),
        )
