"""A password the operator gave for one run and nothing after it.

The vault is for a credential somebody means to keep: stored once, reused by
every run that signs into that system, rotated when it changes. What this
holds is the other answer to the same question -- "here is my password, use it
now, do not keep it" -- which an operator gives when they are signing into a
system they do not own, or when policy says a credential does not live in a
deployment's vault at all.

So nothing here is written down. The value sits in this process's memory,
is handed out exactly once, and is gone after that or after `K_HELD_FOR`,
whichever comes first. A restart forgets it; so does a second run that arrives
too late. Both are the honest failure: the step refuses with the key it
wanted, which is the same sentence an operator gets when they never gave one.

Not per run, deliberately. The step that asks for a password has already
failed, and the retry the operator presses is a NEW run with a new id -- a
hold keyed by the run that asked would be a hold nothing could ever read.

ponytail: process memory, because the deployment serves this from one uvicorn
worker (`backend/Dockerfile`). The day the api runs more than one, this has to
move to something the processes share -- with the same two rules, once and
briefly -- or an operator will type a password into one process and have the
run ask again from another.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

K_HELD_FOR = 15 * 60.0
"""How long a one-time password waits for the run that will type it.

Long enough for somebody to answer the card, press the retry and watch the
sign-in happen; short enough that a password nobody used is not still in
memory at the end of a shift. It is not a session: a run that has not asked
for it in a quarter of an hour is a run nobody is watching.
"""


@dataclass(frozen=True, slots=True)
class _Held:
    value: str
    until: float


_held: dict[str, _Held] = {}


def hold(key: str, value: str, *, now: float | None = None) -> float:
    """Keep one value for the next run that asks for this key.

    Answers when it will be forgotten, which is what the caller tells the
    operator. Holding the same key twice replaces the first: somebody who
    typed it again meant the second one.
    """
    at = time.time() if now is None else now
    until = at + K_HELD_FOR
    _held[key] = _Held(value=value, until=until)
    return until


def take(key: str, *, now: float | None = None) -> str | None:
    """The value, once. A second read gets nothing, and neither does a read
    after it has aged out -- both are `None`, which the runner already knows
    how to say out loud."""
    at = time.time() if now is None else now
    found = _held.pop(key, None)
    if found is None:
        return None
    if found.until <= at:
        return None
    return found.value


def waiting(key: str, *, now: float | None = None) -> bool:
    """Whether a value is held for this key, without taking it. For tests and
    for nothing that runs a step: reading a secret is `take`."""
    at = time.time() if now is None else now
    found = _held.get(key)
    return found is not None and found.until > at


def forget_everything() -> None:
    """Drop every held value. For tests, and for a deployment that wants to
    clear them without a restart."""
    _held.clear()
