"""Writing down what somebody asked for, and reading it back in the audit.

Everything this system records, it records as state. Nothing at all is written
when nothing happens -- and *I pressed it and nothing happened* is the question
support is actually asked.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest

from sro.application.analytics.audit import ReadAudit
from sro.application.context import RequestContext
from sro.application.observation.record_attempt import RecordAttempt
from sro.domain.observation.attempts import DONE, NOTHING, REFUSED
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

TENANT = TenantId("greyorange")
CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("rudy"))
SINCE = datetime(2026, 1, 1, tzinfo=UTC)


def _recorder(uow: FakeUnitOfWork) -> RecordAttempt:
    return RecordAttempt(uow, FakeIdFactory(), FakeClock())


async def test_a_press_that_started_nothing_leaves_a_record() -> None:
    """The case this exists for. A rule fires, the job needs a value the rule
    has no answer for, and `FireTrigger` skips -- which answers 202 with a null
    run id. From the browser that is a press that did nothing, and there was no
    record anywhere that it had happened."""
    uow = FakeUnitOfWork()

    await _recorder(uow).execute(
        CTX,
        asked_for="fire an arrival rule",
        came_of=NOTHING,
        why="the rule had no value for something the job needs",
        about={"trigger": "trg_1", "device": "dev_1"},
    )

    [kept] = uow.attempts.rows
    assert kept.came_of == NOTHING
    assert kept.asked_for == "fire an arrival rule"
    assert kept.why == "the rule had no value for something the job needs"
    assert kept.about == {"trigger": "trg_1", "device": "dev_1"}
    assert (kept.tenant, kept.principal) == ("greyorange", "rudy")


async def test_only_ids_it_recognises_travel_with_it() -> None:
    """This row leaves the tenant's deployment whenever somebody exports an
    audit, so a bag that can hold anything ends up holding what a customer is
    called."""
    uow = FakeUnitOfWork()

    await _recorder(uow).execute(
        CTX,
        asked_for="press an offer",
        came_of=DONE,
        about={"run": "run_1", "customer": "ACME", "value": "SROCL01", "trigger": ""},
    )

    assert uow.attempts.rows[0].about == {"run": "run_1"}


async def test_an_outcome_this_system_does_not_know_is_not_raised_at_a_door(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A door asking for an outcome that does not exist is a bug in that door,
    and not one the person in front of it should meet as a 500."""
    uow = FakeUnitOfWork()

    with caplog.at_level(logging.ERROR):
        await _recorder(uow).execute(CTX, asked_for="press an offer", came_of="succeeded")

    assert uow.attempts.rows == []
    assert any("could not be made" in record.getMessage() for record in caplog.records)


async def test_a_store_that_will_not_take_it_does_not_fail_the_door() -> None:
    """Every caller is a door in the middle of answering somebody, and most are
    in the middle of refusing them. A refusal that becomes a 500 because the
    recording of it failed is strictly worse than the silence this replaces."""
    uow = FakeUnitOfWork()
    uow.attempts.refusing = True

    await _recorder(uow).execute(CTX, asked_for="press an offer", came_of=REFUSED, why="no")

    assert uow.attempts.rows == []


async def test_the_audit_carries_them_beside_what_already_worked() -> None:
    """The other four reads are state. This is the half a person opens an audit
    to find."""
    uow = FakeUnitOfWork()
    await _recorder(uow).execute(CTX, asked_for="fire an arrival rule", came_of=NOTHING)

    audit = await ReadAudit(uow).execute(CTX, since=SINCE)

    assert [one.came_of for one in audit.attempts] == [NOTHING]
