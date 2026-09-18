"""A run that ended waiting to hear back, and the address a reply finds it by.

`asking.py` already holds the durable half: a run that comes up short ends, and
the question lives in a thread rather than in a process. What it has is one
address -- the panel -- and the person who knows the missing value is usually
whoever sent the mail. These pin the address and the deadline, which is the
part that turns a pause into an abandonment if it is left out.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.domain.execution.waiting import (
    K_PATIENCE,
    Awaiting,
    as_said,
    read_wait,
    still_waiting,
    waiting_on,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_a_wait_names_the_conversation_and_when_it_stops_being_one() -> None:
    waiting = waiting_on("gmail", "thr-1", now=NOW)

    assert waiting is not None
    assert (waiting.server, waiting.thread) == ("gmail", "thr-1")
    assert waiting.until == (NOW + K_PATIENCE).isoformat()
    assert still_waiting(waiting, NOW)


def test_a_run_that_names_no_conversation_is_not_waiting_on_a_blank() -> None:
    """A blank would match the next blank. Two runs neither of which came out
    of a mailbox would answer each other's replies, which is a warehouse record
    written from somebody else's sentence."""
    assert waiting_on("gmail", "", now=NOW) is None
    assert waiting_on("", "thr-1", now=NOW) is None
    assert waiting_on("gmail", "   ", now=NOW) is None


def test_a_wait_that_ran_out_is_not_a_wait() -> None:
    """Somebody is asked, somebody does not answer, and without this the row
    says "waiting" until an archaeologist reads the table. What is waiting is a
    write: a record asked for in early September and created in October is not
    the record anybody wanted."""
    waiting = waiting_on("gmail", "thr-1", now=NOW)

    assert still_waiting(waiting, NOW + K_PATIENCE - timedelta(seconds=1))
    assert not still_waiting(waiting, NOW + K_PATIENCE + timedelta(seconds=1))
    assert not still_waiting(None, NOW)


def test_a_deadline_nothing_can_read_counts_as_over() -> None:
    """Treating an unknown age as young is how a row from last year answers a
    mail that arrived this morning."""
    assert not still_waiting(Awaiting("gmail", "thr-1", "not a date"), NOW)
    assert not still_waiting(Awaiting("gmail", "thr-1", ""), NOW)


def test_a_deadline_written_without_a_zone_is_read_as_utc() -> None:
    """Rather than raising on the comparison. Every instant this system writes
    carries a zone; a row that somehow does not is still a row somebody has to
    be able to read."""
    assert still_waiting(Awaiting("gmail", "thr-1", "2099-01-01T00:00:00"), NOW)
    assert not still_waiting(Awaiting("gmail", "thr-1", "2001-01-01T00:00:00"), NOW)


def test_a_wait_survives_the_round_trip_through_a_column() -> None:
    waiting = waiting_on("gmail", "thr-1", now=NOW)

    assert read_wait(as_said(waiting)) == waiting
    assert as_said(None) is None


def test_a_row_holding_half_a_wait_is_not_one() -> None:
    """Given `object` and not a typed shape, because this is JSON off a column
    and anything that pretends otherwise is pretending. A row half-written by
    an older deployment is not an address."""
    assert read_wait(None) is None
    assert read_wait("gmail") is None
    assert read_wait({"server": "gmail", "thread": "thr-1"}) is None
    assert read_wait({"server": "", "thread": "thr-1", "until": "x"}) is None
    assert read_wait({"server": "gmail", "thread": "", "until": "x"}) is None
