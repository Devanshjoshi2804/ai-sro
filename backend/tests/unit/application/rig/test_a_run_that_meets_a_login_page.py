"""A step that failed in front of a login page says which.

`control_not_found: no control matched` is true and says nothing about why.
Somebody reading it goes looking for a broken selector, and what is actually
wrong is that nobody is signed in.

Measured on the deployment 2026-09-18: a session expired, the operator spent
minutes signing back in, and every run in between blamed a missing tab item.
The page in front of them was a login form the whole time.
"""

from __future__ import annotations

from sro.application.execution.run_workflow import (
    _ask_for_the_password,
    _said_signed_out,
    _sign_in_here,
)
from sro.application.ports.channel import Reply
from sro.domain.execution.belts import StepVerdict
from sro.domain.execution.planning import Look
from sro.domain.execution.secrets import secret_key_of
from sro.domain.execution.workflow_run import RunStep
from sro.domain.shared.identifiers import DeviceId
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


def test_a_failure_under_a_dialog_says_what_the_dialog_said() -> None:
    """The case this deployment's own ledger already names.

    `Existing Carriers duplicate check is SERVER-side: the form accepts the
    click and only then shows an in-app 'Record already exists' modal.` A step
    that clicked Save and then found nothing is a step whose answer is on the
    screen, in a box, in words -- and the run reported a missing control.
    """
    said = _said_signed_out(
        _failed(),
        Look("u", None, "", dialog="Record already exists. Choose another code."),
    )

    # What the warehouse said, first and in full: a person reading this is
    # looking for that sentence, and every word wrapped around it is a word
    # between them and it.
    assert said.reason.startswith("the screen is showing: Record already exists.")
    assert "control_not_found" in said.reason


def test_a_login_page_is_named_before_a_dialog_on_the_same_screen() -> None:
    """Both at once is a login in a modal, which is a login: signing in is the
    thing to do about it, and "the screen is showing" is not."""
    said = _said_signed_out(_failed(), Look("u", None, "", signed_out=True, dialog="Sign in"))

    assert "session has gone" in said.reason


def test_a_step_that_held_under_a_dialog_is_left_alone() -> None:
    """Plenty of screens confirm a save in one."""
    held = StepVerdict("held", "status", "201", Answer())

    assert _said_signed_out(held, Look("u", None, "", dialog="Saved")) is held


def test_a_failure_on_another_screen_says_which_screen() -> None:
    """The plainest of the three, and the one seen last.

    Not a login, no dialog, and a control nothing matched -- because the screen
    this step was demonstrated on is not the screen in front of it. On the
    deployment 2026-09-18 a run reported a missing tab item while the browser
    sat on the Warehouse configuration screen, after the operator had signed
    back in and landed somewhere else.
    """
    said = _said_signed_out(
        _failed(),
        Look("https://wms.test/portal#wm.config/warehouse", None, ""),
        "https://wms.test/portal#wm.config/customers.types",
    )

    assert "the browser is on" in said.reason
    assert "warehouse" in said.reason
    assert "customers.types" in said.reason
    assert "control_not_found" in said.reason


def test_the_same_screen_reached_by_another_url_is_not_another_screen() -> None:
    """`same_screen` and not string equality, which is the comparison this
    makes everywhere else: the query is where a session token and one visit's
    particulars live, and a run reporting a wrong screen every time one differed
    would be noise somebody learns to read past."""
    same = _failed()
    said = _said_signed_out(
        same,
        Look("https://wms.test/portal?siteId=SG#wm.config/customers.types////", None, ""),
        "https://wms.test/portal?siteId=MY#wm.config/customers.types////",
    )

    assert said is same


def test_a_step_with_no_screen_to_compare_says_what_it_always_said() -> None:
    """Plenty of steps name no page. A run that invented a screen to be wrong
    about would be worse than one that said nothing."""
    same = _failed()

    assert _said_signed_out(same, Look("https://wms.test/x", None, ""), None) is same


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


KEPT = "a password nobody logs"


async def _stored(_key: str) -> str | None:
    return KEPT


async def test_the_credential_reaches_the_browser_and_the_record_holds_none_of_it() -> None:
    """The whole reason the sign-in lives in one command.

    A run record is read by a person, by the panel, and by the model asked to
    rescue the next step. None of those has any business holding a credential
    -- which is the rule `without_secrets` keeps for every other step that
    types one.
    """
    channel = _Channel(Reply(ok=True, result={"did": ["entered the username", "submitted"]}))
    step = RunStep(order=2, says="s", verdict="failed", reason="control_not_found")

    went = await _sign_in_here(
        channel=channel,
        tenant_id=f.TENANT,
        device_id=DeviceId("dev_1"),
        run_id="run_1",
        origin="https://wms.example.com",
        where="https://wms.example.com/login",
        secret_for=_stored,
        record=step,
    )

    assert went is True
    # It reached the browser.
    (sent,) = channel.sent
    assert sent["kind"] == "sign_in"
    assert sent["payload"]["password"] == KEPT
    # And nothing of it reached the record.
    assert KEPT not in step.reason
    assert "signed in again (entered the username, submitted)" in step.reason


async def test_a_browser_that_refused_the_sign_in_leaves_the_step_failed() -> None:
    """A sign-in that did not happen must not read as one that did: the step is
    still failed and still about to ask for a password."""
    channel = _Channel(Reply(ok=False, error_kind="not_actionable", error_detail="a second factor"))
    step = RunStep(order=2, says="s", verdict="failed", reason="control_not_found")

    went = await _sign_in_here(
        channel=channel,
        tenant_id=f.TENANT,
        device_id=DeviceId("dev_1"),
        run_id="run_1",
        origin="https://wms.example.com",
        where="https://wms.example.com/login",
        secret_for=_stored,
        record=step,
    )

    assert went is False
    assert "a second factor" in step.reason


async def test_nothing_stored_is_no_sign_in_and_no_command() -> None:
    """A run with an empty vault asks for the password instead, which is the
    next thing this does -- and a command sent with a blank credential would
    submit a login form with nothing in it."""
    channel = _Channel(Reply(ok=True, result={}))
    step = RunStep(order=2, says="s", verdict="failed", reason="control_not_found")

    went = await _sign_in_here(
        channel=channel,
        tenant_id=f.TENANT,
        device_id=DeviceId("dev_1"),
        run_id="run_1",
        origin="https://wms.example.com",
        where="https://wms.example.com/login",
        secret_for=_nothing_stored,
        record=step,
    )

    assert went is False
    assert channel.sent == [], "it tried to sign in with nothing"


class _Channel:
    """One reply, and what it was asked."""

    def __init__(self, reply: Reply) -> None:
        self._reply = reply
        self.sent: list[dict[str, object]] = []

    async def send(
        self,
        tenant_id: object,
        device_id: object,
        *,
        kind: str,
        run_id: str,
        payload: dict[str, object],
        **_rest: object,
    ) -> Reply:
        self.sent.append({"kind": kind, "run_id": run_id, "payload": payload})
        return self._reply
