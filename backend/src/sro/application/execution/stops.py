"""Runs somebody has asked to stop.

A run in an operator's own browser is the one they sit and watch, which is
exactly the one they will want to interrupt: it is clicking through a form in
front of them and they can see it going somewhere wrong. Every other way to end
a run belongs to the system -- a failed assertion, a tripped breaker, a closed
laptop -- and none of them is a person changing their mind.

In memory, for the same reason as the pursuits beside it: the run this stops is
being performed by a task in this process, driving a socket held by this
process. A durable record of an intention to stop would outlive the only thing
that could act on it.

Checked between steps rather than mid-command. A gesture already sent cannot be
recalled from a warehouse, and a stop that pretended otherwise would be the
worst kind of control: one that says the write did not happen when it did.
"""

from __future__ import annotations

from sro.domain.execution.run import RunId


class Stops:
    """Which runs have been asked to stop, and whether one has been."""

    def __init__(self) -> None:
        self._asked: set[str] = set()

    def ask(self, run_id: RunId) -> None:
        self._asked.add(run_id.value)

    def asked(self, run_id: RunId) -> bool:
        return run_id.value in self._asked

    def forget(self, run_id: RunId) -> None:
        """Once the run has ended. Without this the set is a slow leak, and a
        run id is never reused so nothing else would ever clear it."""
        self._asked.discard(run_id.value)
