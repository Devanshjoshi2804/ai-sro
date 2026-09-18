"""A step that failed in front of a login page says which.

`control_not_found: no control matched` is true and says nothing about why.
Somebody reading it goes looking for a broken selector, and what is actually
wrong is that nobody is signed in.

Measured on the deployment 2026-09-18: a session expired, the operator spent
minutes signing back in, and every run in between blamed a missing tab item.
The page in front of them was a login form the whole time.
"""

from __future__ import annotations

from sro.application.execution.run_workflow import _ask_for_the_password, _said_signed_out
from sro.domain.execution.belts import StepVerdict
from sro.domain.execution.planning import Look
from sro.domain.execution.secrets import secret_key_of
from sro.domain.shared.prices import Answer
from tests import factories as f


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


async def test_a_run_stopped_at_a_login_page_asks_for_the_password_it_has_none_of() -> None:
    """The box already exists and this case never reached it.

    A step that types a password and finds the vault empty refuses with
    `needs_secret`, and the run card draws "this job needs your password for
    <system>" with a field. A job mined from an already-signed-in session has
    no login step at all, so nothing ever asked -- and the operator was left
    with a run that stopped and a sentence about a session.
    """
    asked = await _ask_for_the_password(
        {"kind": "none", "payload": {}},
        "https://wms.example.com/portal?siteId=SG",
        f.TENANT,
        _nothing_stored,
    )

    assert asked is not None
    wants = asked["payload"]["needs_secret"]  # type: ignore[index]
    assert wants["system"] == "wms.example.com"
    assert wants["field"] == "password"
    # The same key the storing side builds, or the value is invisible to the
    # one thing that needs it.
    assert wants["key"] == secret_key_of(f.TENANT.value, "wms.example.com", "password")


async def test_a_password_already_stored_is_not_asked_for_again() -> None:
    """A run that stopped at a login page with a credential in the vault has a
    different problem -- a wrong password, or a second factor -- and asking for
    it again would be this system's answer to everything."""
    same = {"kind": "none", "payload": {}}

    asked = await _ask_for_the_password(same, "https://wms.example.com/x", f.TENANT, _stored)

    assert asked == same
    assert "needs_secret" not in str(asked)


async def test_a_vault_that_will_not_answer_does_not_grow_a_password_box() -> None:
    """Somebody typing their credential to fix an outage is the one outcome
    worse than a run that stopped."""

    async def _raises(_key: str) -> str | None:
        raise RuntimeError("the vault is down")

    same = {"kind": "none", "payload": {}}

    assert await _ask_for_the_password(same, "https://wms.example.com/x", f.TENANT, _raises) == same


async def test_a_run_with_no_vault_at_all_asks_for_nothing() -> None:
    assert await _ask_for_the_password(None, "https://wms.example.com/x", f.TENANT, None) is None


async def _nothing_stored(_key: str) -> str | None:
    return None


async def _stored(_key: str) -> str | None:
    return "a password nobody logs"
