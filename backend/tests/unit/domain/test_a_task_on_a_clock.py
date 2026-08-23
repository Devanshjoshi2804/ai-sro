"""What a trigger refuses to be.

Every rule here exists because the run it starts happens with nobody watching.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, SkillId, TenantId, TriggerId
from sro.domain.trigger.trigger import Trigger, TriggerKind

AT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


def _trigger(**overrides: object) -> Trigger:
    fields: dict[str, object] = {
        "id": TriggerId("trg-1"),
        "tenant_id": TenantId("acme"),
        "skill_id": SkillId("skill-1"),
        "kind": TriggerKind.SCHEDULE,
        "created_by": PrincipalId("devansh"),
        "created_at": AT,
        "cron": "0 7 * * 1-5",
    }
    return Trigger(**{**fields, **overrides})  # type: ignore[arg-type]


def test_a_scheduled_write_must_name_who_stands_behind_it() -> None:
    # Refused here, weeks before it would have written to a warehouse with
    # nobody's name on it.
    with pytest.raises(InvariantViolation, match="who authorised"):
        _trigger(writes=True)


def test_an_authorised_write_trigger_is_allowed() -> None:
    trigger = _trigger(writes=True, authorized_by=PrincipalId("devansh"))

    assert trigger.authorized_by == PrincipalId("devansh")
    assert trigger.requires_confirmation is True
    assert trigger.auto_approves is False


def test_auto_approve_is_a_named_persons_decision_not_a_default() -> None:
    trigger = _trigger(
        writes=True, authorized_by=PrincipalId("devansh"), requires_confirmation=False
    )

    assert trigger.auto_approves is True


def test_a_schedule_with_no_cron_is_a_task_that_never_runs() -> None:
    with pytest.raises(InvariantViolation, match="cron"):
        _trigger(cron=None)


def test_a_cron_expression_that_cannot_be_read_is_refused_when_it_is_typed() -> None:
    with pytest.raises(InvariantViolation, match="minute field"):
        _trigger(cron="61 * * * *")


def test_a_time_zone_nobody_has_heard_of_is_refused() -> None:
    # Seven o'clock in the warehouse, not on the server, and a typo here is a
    # report that arrives at the wrong hour for half the year.
    with pytest.raises(InvariantViolation, match="time zone"):
        _trigger(timezone="Mars/Olympus")


def test_a_trigger_that_is_not_scheduled_has_no_schedule() -> None:
    with pytest.raises(InvariantViolation, match="does not run on a schedule"):
        _trigger(kind=TriggerKind.MANUAL, cron="0 7 * * *")


def test_disabling_without_a_reason_is_refused_because_somebody_will_ask() -> None:
    trigger = _trigger()

    with pytest.raises(InvariantViolation):
        trigger.disable("   ")

    trigger.disable("the report moved to a different system")
    assert trigger.enabled is False
    assert trigger.is_scheduled is False
    assert trigger.disabled_reason == "the report moved to a different system"


def test_enabling_clears_the_reason_it_was_stopped_for() -> None:
    trigger = _trigger()
    trigger.disable("paused during the cutover")

    trigger.enable()

    assert trigger.enabled is True
    assert trigger.disabled_reason is None
