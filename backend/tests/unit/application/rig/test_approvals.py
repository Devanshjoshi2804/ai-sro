"""The register a run waits on while a person looks at the write.

Ported from `new_agent_arch/src/rig/runner.py` (`Approvals`, `Aborts` and
`K_APPROVAL_WAIT_S`); the rig's own tests for it were scattered through
`test_runner.py`, `test_api.py` and `test_devices.py` and are gathered here.

Nothing sleeps. Every wait is an `asyncio.Event` and every join an
`asyncio.wait_for` with a short deadline, so a test that would hang fails
instead -- which is the whole subject of this file.
"""

import asyncio
import inspect

import pytest

from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.stops import Stops
from sro.domain.execution.run import RunId
from tests.unit.fakes import FakeWorkflowRunRepository

# Plain strings, because a workflow run's id is one: the register is keyed the
# same way as `WorkflowRunRepository.approve`, and `RunId` belongs to the skill
# run next door. `Stops` is the exception below -- it is the skill run's.
RUN = "run_parked"
OTHER = "run_elsewhere"
# `Stops` is keyed on the skill run's `RunId`, this register on the workflow
# run's plain id. That the two are not even the same aggregate is the shape of
# the missing seam: no route today can stop a run parked here. The two tests
# below pair them as the loop will once one exists.
STOPPED, STOPPED_ELSEWHERE = RunId(RUN), RunId(OTHER)
DEVICE = "dev_1"
OTHER_DEVICE = "dev_9"
AT = "2026-09-05T10:02:00+00:00"
LATER = "2026-09-05T10:09:00+00:00"

JOIN_S = 2.0
"""How long a test waits for something that should already have happened. Not
the subject of any test -- long enough that a loaded machine does not fail a
green suite, short enough that a wait which will never end fails the run."""

GAVE_UP_S = 0.05
"""A stand-in for the five minutes, so the give-up path can be exercised."""


async def _parked(
    approvals: Approvals,
    run_id: str,
    timeout: float,  # noqa: ASYNC109 -- the wait under test carries its own
) -> asyncio.Task[bool]:
    """A run parked on a person, whose wait is really under way when this
    returns. An event and not a sleep: the point of the handshake is that a
    wait which never starts fails the test rather than making it flaky."""
    started = asyncio.Event()

    async def park() -> bool:
        # `started` is set before the wait and nothing here registers: the
        # register must be populated by `wait_for` itself, or this helper would
        # be asserting its own work and a `wait_for` that queued behind a lock
        # would still look parked.
        started.set()
        return await approvals.wait_for(run_id, timeout=timeout)

    task = asyncio.create_task(park())
    await asyncio.wait_for(started.wait(), JOIN_S)
    assert run_id in approvals.waiting(), "the wait did not start"
    return task


async def test_a_tap_releases_the_run_that_is_parked() -> None:
    approvals = Approvals()
    parked = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)

    assert approvals.approve(RUN) is True
    assert await asyncio.wait_for(parked, JOIN_S) is True


async def test_nobody_answers_and_the_run_gives_up_rather_than_hanging() -> None:
    """The five minutes exist so an unanswered run ends. A wait with no
    deadline is a run that holds a browser open until the process dies."""
    approvals = Approvals()

    released = await asyncio.wait_for(approvals.wait_for(RUN, timeout=GAVE_UP_S), JOIN_S)

    assert released is False
    assert approvals.waiting() == frozenset()


def test_five_minutes_is_the_wait_and_is_what_a_caller_gets_by_default() -> None:
    """The number is a measurement of a person reading a panel, not a round
    number someone liked. If it moves, the docstring that explains it moves."""
    assert K_APPROVAL_WAIT_S == 300.0
    assert inspect.signature(Approvals.wait_for).parameters["timeout"].default == K_APPROVAL_WAIT_S


async def test_a_tap_on_a_run_nobody_is_waiting_on_is_not_an_approval() -> None:
    """What the route turns into a 409: nothing is awaiting approval here."""
    approvals = Approvals()

    assert approvals.approve(RUN) is False


async def test_the_wait_is_popped_on_the_way_out_so_a_later_tap_finds_nothing() -> None:
    """A second tap is not a second authorisation. Once the run has moved on,
    the register must say so -- otherwise the panel offers a button that
    reports success while the run it belonged to is long gone."""
    approvals = Approvals()
    parked = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)
    approvals.approve(RUN)
    await asyncio.wait_for(parked, JOIN_S)

    assert approvals.waiting() == frozenset()
    assert approvals.approve(RUN) is False


async def test_a_run_that_gave_up_waiting_cannot_be_approved_afterwards() -> None:
    """The other way out of the wait. A tap arriving at minute six authorises
    nothing: the step already failed for want of an answer."""
    approvals = Approvals()

    assert await asyncio.wait_for(approvals.wait_for(RUN, timeout=GAVE_UP_S), JOIN_S) is False
    assert approvals.approve(RUN) is False


async def test_registering_before_the_wait_starts_lets_a_racing_tap_land() -> None:
    """`register` is called before the step is saved, so a person who taps the
    instant the panel shows the write finds an event rather than a 409."""
    approvals = Approvals()
    approvals.register(RUN)

    assert approvals.approve(RUN) is True
    assert await asyncio.wait_for(approvals.wait_for(RUN, timeout=GAVE_UP_S), JOIN_S) is True


async def test_registering_twice_keeps_the_event_the_tap_already_set() -> None:
    """`wait_for` registers too. If that replaced the event, an approval that
    landed during the save would be dropped and the run would wait out the
    full five minutes for a person who has already answered."""
    approvals = Approvals()
    approvals.register(RUN)
    approvals.approve(RUN)
    approvals.register(RUN)

    assert await asyncio.wait_for(approvals.wait_for(RUN, timeout=GAVE_UP_S), JOIN_S) is True


async def test_a_tap_on_one_run_does_not_release_another() -> None:
    """Keyed by run. One person's authorisation is for their run's write."""
    approvals = Approvals()
    parked = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)
    theirs = await _parked(approvals, OTHER, timeout=GAVE_UP_S)

    assert approvals.approve(OTHER) is True
    assert await asyncio.wait_for(theirs, JOIN_S) is True
    assert approvals.waiting() == frozenset({RUN})

    approvals.approve(RUN)
    assert await asyncio.wait_for(parked, JOIN_S) is True


async def test_two_runs_park_at_the_same_time_rather_than_in_turn() -> None:
    """Two browsers, two runs, two people. The register must not serialise
    them: a second run parking behind the first would wait five minutes for a
    write nobody is being shown."""
    approvals = Approvals()
    mine = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)
    theirs = await _parked(approvals, OTHER, timeout=K_APPROVAL_WAIT_S)
    both = asyncio.gather(mine, theirs)

    assert approvals.waiting() == frozenset({RUN, OTHER}), "the second run queued"
    approvals.approve(RUN)
    approvals.approve(OTHER)

    mine_released, theirs_released = await asyncio.wait_for(both, JOIN_S)
    assert (mine_released, theirs_released) == (True, True)


async def test_forgetting_a_run_drops_the_wait_without_releasing_it() -> None:
    """Cleaning up after a run is not a person approving its write. If forget
    set the event, the tidy-up at the end of one run would let the write of a
    run parked under the same id out."""
    approvals = Approvals()
    parked = await _parked(approvals, RUN, timeout=GAVE_UP_S)
    theirs = await _parked(approvals, OTHER, timeout=K_APPROVAL_WAIT_S)

    approvals.forget(RUN)

    assert await asyncio.wait_for(parked, JOIN_S) is False
    # The one run named, not every run this process is holding: a run ending
    # must not drop the wait of the run parked in the next browser.
    assert approvals.waiting() == frozenset({OTHER})
    assert approvals.approve(OTHER) is True
    assert await asyncio.wait_for(theirs, JOIN_S) is True


async def test_a_stop_releases_the_wait_but_is_not_an_authorisation() -> None:
    """What an abort route WILL do, once one exists for these runs: the flag
    first, then the release, so a run parked on a write wakes now instead of in
    five minutes. Nobody does it yet -- `StopRun` reaches skill runs only, and
    the loop's half is Task 6's -- so this test performs both calls itself and
    proves only the property the pair must have: a released wait alone cannot
    tell a stop from a yes, and the answer is in the other register.

    Which means it cannot fail if the routes never appear. It is the shape the
    seam has to take, written down where the loop's author will read it."""
    approvals, stops = Approvals(), Stops()
    parked = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)

    stops.ask(STOPPED)
    approvals.approve(RUN)

    assert await asyncio.wait_for(parked, JOIN_S) is True
    assert stops.asked(STOPPED), "a released wait alone cannot tell a stop from a yes"


async def test_stopping_one_run_says_nothing_about_the_other() -> None:
    """Neither register is global. Same caveat as above: the calls here are
    the ones a stop route would make, not ones any route makes today."""
    approvals, stops = Approvals(), Stops()
    stops.ask(STOPPED_ELSEWHERE)
    parked = await _parked(approvals, RUN, timeout=GAVE_UP_S)

    assert await asyncio.wait_for(parked, JOIN_S) is False, "a stop elsewhere released this wait"
    assert not stops.asked(STOPPED)


@pytest.mark.parametrize("ord_", [0, 3])
async def test_the_storage_half_agrees_that_the_first_tap_wins(ord_: int) -> None:
    """The register releases the wait once; the run repository records who
    authorised which step. Both halves say a second tap is not a second
    authorisation, and this is the check that they still agree."""
    approvals, runs = Approvals(), FakeWorkflowRunRepository()
    parked = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)

    assert approvals.approve(RUN) is True
    assert await runs.approve(RUN, ord_, at=AT, device_id=DEVICE) is True
    await asyncio.wait_for(parked, JOIN_S)

    assert approvals.approve(RUN) is False
    assert await runs.approve(RUN, ord_, at=LATER, device_id=OTHER_DEVICE) is False
    assert await runs.approvals(RUN) == ((ord_, AT, DEVICE),)


async def test_an_approval_for_one_step_does_not_authorise_the_next() -> None:
    """A run parks once per write. The tap that let step 3 out says nothing
    about step 4, which parks again and takes its own tap -- in the register,
    which the second park re-registers, and in the row, which is keyed by
    step."""
    approvals, runs = Approvals(), FakeWorkflowRunRepository()

    third = await _parked(approvals, RUN, timeout=K_APPROVAL_WAIT_S)
    approvals.approve(RUN)
    assert await asyncio.wait_for(third, JOIN_S) is True
    assert await runs.approve(RUN, 3, at=AT, device_id=DEVICE) is True

    fourth = await _parked(approvals, RUN, timeout=GAVE_UP_S)
    assert await asyncio.wait_for(fourth, JOIN_S) is False, "step 3's tap released step 4's wait"
    assert await runs.approve(RUN, 4, at=LATER, device_id=DEVICE) is True
    assert await runs.approvals(RUN) == ((3, AT, DEVICE), (4, LATER, DEVICE))
