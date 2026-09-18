"""A step that failed in front of a login page says which.

`control_not_found: no control matched` is true and says nothing about why.
Somebody reading it goes looking for a broken selector, and what is actually
wrong is that nobody is signed in.

Measured on the deployment 2026-09-18: a session expired, the operator spent
minutes signing back in, and every run in between blamed a missing tab item.
The page in front of them was a login form the whole time.
"""

from __future__ import annotations

from sro.application.execution.run_workflow import _said_signed_out
from sro.domain.execution.belts import StepVerdict
from sro.domain.execution.planning import Look
from sro.domain.shared.prices import Answer


def _failed(reason: str = "control_not_found: no control matched") -> StepVerdict:
    return StepVerdict("failed", "none", reason, Answer())


def test_a_failure_at_a_login_page_says_the_session_has_gone() -> None:
    said = _said_signed_out(_failed(), Look(url="u", screenshot=None, digest="", signed_out=True))

    assert "session has gone" in said.reason
    assert "Sign in and start it again" in said.reason
    # And what it was ALSO going to say, because the selector may be broken too
    # and a run that swallowed the original reason would hide the second fault
    # behind the first.
    assert "control_not_found" in said.reason


def test_the_verdict_itself_is_not_rewritten() -> None:
    """What changes is what it SAYS. A run that renamed the failure would be a
    run deciding it knows why the step failed, and what this knows is only what
    is on the screen."""
    said = _said_signed_out(_failed(), Look(url="u", screenshot=None, digest="", signed_out=True))

    assert said.state == "failed"
    assert said.by == "none"


def test_a_step_that_held_in_front_of_a_login_page_is_left_alone() -> None:
    """A held step is a step that held. The run has no business editorialising
    about the furniture behind it -- and a page can carry a password field for
    reasons that have nothing to do with this run."""
    held = StepVerdict("held", "screen", "the record was created", Answer())

    assert _said_signed_out(held, Look("u", None, "", signed_out=True)) is held


def test_a_failure_anywhere_else_says_what_it_always_said() -> None:
    same = _failed()

    assert _said_signed_out(same, Look("u", None, "", signed_out=False)) is same
