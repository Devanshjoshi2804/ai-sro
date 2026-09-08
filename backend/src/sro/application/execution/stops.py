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


class Stops:
    """Which runs have been asked to stop, and whether one has been.

    Keyed by a plain `str` rather than by `RunId`. Two aggregates press this
    one button -- the skill run next door and the workflow run the mined-job
    loop performs -- and their ids are two spaces of the same shape, `run_` and
    32 hex off a UUID. `Approvals` beside it is keyed the same way for the same
    reason: two registers in one package with two conventions is how they drift
    apart, and asserting an identity that does not hold to get through the door
    is not a check, only a coercion with a comment on it.
    """

    def __init__(self) -> None:
        self._asked: set[str] = set()

    def ask(self, run_id: str) -> None:
        self._asked.add(run_id)

    def asked(self, run_id: str) -> bool:
        return run_id in self._asked

    def forget(self, run_id: str) -> None:
        """Once the run has ended. Without this the set is a slow leak, and a
        run id is never reused so nothing else would ever clear it."""
        self._asked.discard(run_id)
