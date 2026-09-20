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


# --- the doors themselves ----------------------------------------------------


def test_every_door_that_records_one_uses_an_outcome_this_system_knows() -> None:
    """A door is the only thing that decides what an attempt came to, and a
    door that invents an outcome has it dropped -- logged, not raised, so the
    person in front of it never learns. Which makes this the one place the
    vocabulary can be checked at all.

    Read off the source rather than by driving each route: what is being
    asserted is that no door anywhere passes a bare string, which no amount of
    exercising the routes I happen to think of can establish.
    """
    import re
    from pathlib import Path

    doors = Path("src/sro/interface/http/v1/routers")
    calls: list[tuple[str, str]] = []
    for door in doors.rglob("*.py"):
        said = door.read_text()
        for call in re.finditer(r"record_attempt\(\)\.execute\((.*?)\n    \)", said, re.S):
            calls.append((door.name, call.group(1)))

    assert calls, "no door records an attempt"
    for name, written in calls:
        outcome = re.search(r"came_of=([^,\n]+)", written)
        assert outcome, f"{name}: a recorded attempt with no outcome"
        # A name from the domain's own vocabulary, or a conditional between
        # two of them. Never a literal: a string here is a column of free text
        # within a month.
        assert not outcome.group(1).strip().startswith(('"', "'")), (
            f"{name}: {outcome.group(1).strip()} is a literal, not one of the names"
        )


def test_every_way_a_person_can_ask_this_system_for_something() -> None:
    """The whole vocabulary, in one place, read off the doors themselves.

    Not the set of FILES that record one -- that passed with a door's recording
    deleted, because its neighbour in the same file still had one. This is the
    list somebody reads to know what an audit can tell them, and a door that
    stops recording takes its line out of it.
    """
    import re
    from pathlib import Path

    doors = Path("src/sro/interface/http/v1/routers")
    asked = set()
    for door in doors.rglob("*.py"):
        for line in re.findall(r"asked_for=.*", door.read_text()):
            # Every string in the value, because a door may choose between two
            # -- the press door says "take back a run" or "press a job"
            # depending on whether the run undoes another. Cut at `came_of`,
            # since a short door puts the whole call on one line and the ids in
            # `about` are strings too.
            asked.update(re.findall(r'"([^"]+)"', line.split("came_of")[0]))

    assert asked == {
        "fire an arrival rule",  # a rule they made, firing where they arrived
        "ask for a job in words",  # a sentence that named a job, or did not
        "ask a question",  # and one this system could look up, or could not
        "say something in a conversation",  # what the thread made of it
        "approve a write",  # yes on a card
        "decline a write",  # no on a card
        "press a job",  # the button
        "take back a run",  # the undo
        "stop a run",
        "approve a step",  # the tap that lets one write out
        "call a run's result wrong",
    }, asked
