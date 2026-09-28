"""Whether a job signs in, decided once from what the operator did.

The rule it replaces read "every cited gesture on one origin" as a sign-in,
which is also every ordinary job done on one warehouse host: a run of `Create
a Customer Type` that lost its page was reported as succeeded with its Save
never pressed. A sign-in is a credential typed and nothing written back.
"""

from __future__ import annotations

from dataclasses import replace

from sro.domain.observation.gesture import Action, Call, Gesture, PageMark, Target
from sro.domain.skill.checks import is_sign_in_step, signs_in, signs_in_to
from sro.domain.skill.signing_in import signs_in_at
from sro.domain.skill.workflow import Step, Workflow

KEYCLOAK = "https://keycloak.example"
WMS = "https://wms.example"


def _at(gesture_id: str, url: str, at: float) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{url}/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at),
    )


def _secret(gesture_id: str, url: str, at: float) -> Gesture:
    return replace(_at(gesture_id, url, at), action=Action(kind="type", at=at, secret=True))


def _wrote(
    gesture_id: str, url: str, at: float, status: int | None = 201, landed: str | None = None
) -> Gesture:
    """A press that posted to its own host. `landed` is another host the
    browser was sent to afterwards -- what a sign-in's submit does."""
    return replace(
        _at(gesture_id, url, at),
        action=Action(kind="press", at=at),
        requests=[Call(method="POST", url=f"{url}/api/things", status=status)],
        page_events=[PageMark(at=at, page_kind="navigated", url=f"{landed}/home")]
        if landed
        else [],
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one]) for n, one in enumerate(cites)
        ],
    )


def test_a_credential_typed_and_nothing_written_is_a_sign_in() -> None:
    """The credential need not be cited: redaction strips it of anything a
    model would point at, so it is read off the job's span."""
    store = {"a": _at("a", KEYCLOAK, 1), "b": _secret("b", KEYCLOAK, 2), "c": _at("c", KEYCLOAK, 3)}

    assert signs_in(_job("a", "c"), store) is True


def test_a_job_on_one_host_that_types_no_credential_does_not_sign_in() -> None:
    """The shape the old rule got wrong: one origin, no password."""
    store = {"a": _at("a", WMS, 1), "b": _at("b", WMS, 2)}

    assert signs_in(_job("a", "b"), store) is False


def test_a_credential_typed_on_the_way_to_a_write_is_not_a_sign_in() -> None:
    """Signed in, then created something: work that happens to start with a
    password."""
    store = {"a": _secret("a", WMS, 1), "b": _wrote("b", WMS, 2)}

    assert signs_in(_job("a", "b"), store) is False


def test_a_credential_post_that_hands_the_browser_on_signs_in() -> None:
    """A sign-in posts the credential and is sent somewhere else."""
    store = {"a": _secret("a", KEYCLOAK, 1), "b": _wrote("b", KEYCLOAK, 2, 302, landed=WMS)}

    assert signs_in(_job("a", "b"), store) is True


def test_a_credential_post_that_stays_on_its_page_is_a_write() -> None:
    """A supervisor PIN, an e-signature: a secret typed, then a post answered
    with a redirect back to the same system -- or with no status recorded at
    all. Nothing proves that is a sign-in, and a write must fail safe."""
    for status in (302, None):
        store = {"a": _secret("a", WMS, 1), "b": _wrote("b", WMS, 2, status)}
        job = _job("a", "b")

        assert is_sign_in_step(job, job.steps[1], store) is False
        assert signs_in(job, store) is False


def test_the_step_that_types_the_credential_is_a_sign_in_step() -> None:
    store = {"a": _secret("a", KEYCLOAK, 1), "b": _wrote("b", KEYCLOAK, 2, 302, landed=WMS)}
    job = _job("a", "b")

    assert is_sign_in_step(job, job.steps[0], store) is True
    assert is_sign_in_step(job, job.steps[1], store) is True


def test_a_press_that_follows_no_credential_is_not_a_sign_in_step() -> None:
    """Even one that sends the browser elsewhere: without the credential in
    front of it, a hand-off is not a sign-in."""
    store = {"a": _at("a", KEYCLOAK, 1), "b": _wrote("b", KEYCLOAK, 2, 302, landed=WMS)}
    job = _job("a", "b")

    assert is_sign_in_step(job, job.steps[1], store) is False


def test_a_step_that_wrote_back_is_never_a_sign_in_step() -> None:
    store = {"a": _secret("a", WMS, 1), "b": _wrote("b", WMS, 2, 201, landed=KEYCLOAK)}
    job = _job("a", "b")

    assert is_sign_in_step(job, job.steps[1], store) is False


def test_a_job_citing_nothing_anybody_kept_does_not_sign_in() -> None:
    assert signs_in(_job("gone"), {}) is False


def test_a_credential_and_a_press_that_stays_on_its_host_are_not_a_sign_in() -> None:
    """One step, as the miner writes them: a PIN typed and Approve pressed, the
    page moving within the same system and no traffic recorded. No recorded
    write is not evidence of no write -- a top-level form post is never
    captured -- so the press is a possible write, and the job is not a
    sign-in."""
    store = {
        "a": _secret("a", WMS, 1),
        "b": replace(
            _at("b", WMS, 2),
            action=Action(kind="press", at=2),
            page_events=[PageMark(at=2, page_kind="navigated", url=f"{WMS}/approved")],
        ),
    }
    job = Workflow(
        id="wfl_pin",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="approve with the PIN", system=None, cites=["a", "b"])],
    )

    assert is_sign_in_step(job, job.steps[0], store) is False
    assert signs_in(job, store) is False


def test_a_credential_and_a_press_that_leaves_the_host_are_a_sign_in() -> None:
    """The same step on a real sign-in: the press sent the browser elsewhere."""
    store = {
        "a": _secret("a", KEYCLOAK, 1),
        "b": replace(
            _at("b", KEYCLOAK, 2),
            action=Action(kind="press", at=2),
            page_events=[PageMark(at=2, page_kind="navigated", url=f"{WMS}/home")],
        ),
    }
    job = Workflow(
        id="wfl_login",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="sign in", system=None, cites=["a", "b"])],
    )

    assert is_sign_in_step(job, job.steps[0], store) is True
    assert signs_in(job, store) is True


def test_a_credential_then_a_press_that_stays_on_its_host_is_not_a_sign_in() -> None:
    """The same shape split across two steps. The press right after the
    credential is what a sign-in's submit would be, so the job is only a
    sign-in if that press proves it."""
    store = {
        "a": _secret("a", WMS, 1),
        "b": replace(_at("b", WMS, 2), action=Action(kind="press", at=2)),
    }

    assert signs_in(_job("a", "b"), store) is False


def test_a_credential_and_a_same_host_select_are_not_a_sign_in_step() -> None:
    """Not only a press can submit: a select that posts on change, an upload
    carrying the PIN. Anything but typing a value has to prove it left."""
    store = {
        "a": _secret("a", WMS, 1),
        "b": replace(_at("b", WMS, 2), action=Action(kind="select", at=2, value="yes")),
    }
    job = Workflow(
        id="wfl_pin",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="approve with the PIN", system=None, cites=["a", "b"])],
    )

    assert is_sign_in_step(job, job.steps[0], store) is False


def test_a_same_host_press_anywhere_after_the_credential_unmarks_the_job() -> None:
    """A PIN, a step on another system, then Approve on the first system with
    nothing recorded. The press is gated where it stands, but a job with it is
    no sign-in to end a run on or to splice into one."""
    store = {
        "a": _secret("a", WMS, 1),
        "b": replace(_at("b", KEYCLOAK, 2), action=Action(kind="type", at=2, value="x")),
        "c": replace(_at("c", WMS, 3), action=Action(kind="press", at=3)),
    }

    assert signs_in(_job("a", "b", "c"), store) is False


B2C = "https://idp-chooser.example"


def _did(
    gesture_id: str, url: str, at: float, kind: str = "click", *, on_secret: bool = False
) -> Gesture:
    """A gesture shaped like the deployment's own. `on_secret` is the
    recorder's mark on the input itself -- a click that focuses the password
    box, an Enter pressed in it -- which is not the recorder's mark on a typed
    value."""
    target = Target(role="textbox", secret=True) if on_secret else Target(role="button")
    return replace(
        _at(gesture_id, url, at),
        action=Action(kind=kind, at=at, target=target),
    )


def _typed_secret(gesture_id: str, url: str, at: float) -> Gesture:
    return replace(
        _at(gesture_id, url, at),
        action=Action(kind="type", at=at, secret=True, target=Target(role="textbox", secret=True)),
    )


def _left(gesture: Gesture, landed: str) -> Gesture:
    return replace(
        gesture, page_events=[PageMark(at=gesture.at, page_kind="navigated", url=f"{landed}/home")]
    )


def _azure_store() -> dict[str, Gesture]:
    """The deployed chain `Log in using Azure B2C SSO`, as its evidence stood:
    the identity chooser, the username, a first password refused on its own
    host, focus clicks and an Enter on the password box, the Sign In that
    finally left for the warehouse, and a click in the warehouse after it."""
    return {
        "chooser": _did("chooser", B2C, 1.0),
        "user-focus": _did("user-focus", KEYCLOAK, 2.0),
        "user": replace(_at("user", KEYCLOAK, 3.0), action=Action(kind="type", at=3.0, value="u")),
        "pw-focus-1": _did("pw-focus-1", KEYCLOAK, 4.0, on_secret=True),
        "pw-1": _typed_secret("pw-1", KEYCLOAK, 5.0),
        "refused": _did("refused", KEYCLOAK, 5.1),
        "pw-focus-2": _did("pw-focus-2", KEYCLOAK, 6.0, on_secret=True),
        "pw-2": _typed_secret("pw-2", KEYCLOAK, 7.0),
        "enter": _did("enter", KEYCLOAK, 7.0, "press", on_secret=True),
        "submit": _left(_did("submit", KEYCLOAK, 7.0), WMS),
        "landed": _did("landed", WMS, 20.0),
    }


def _azure_job() -> Workflow:
    return Workflow(
        id="wfl_azure",
        tenant="acme",
        title="Log in using Azure B2C SSO",
        narrative="n",
        steps=[
            Step(order=0, says="choose local users", system=None, cites=["chooser"]),
            Step(order=1, says="username", system=None, cites=["user-focus", "user"]),
            Step(
                order=2,
                says="password",
                system=None,
                cites=["pw-focus-1", "pw-1", "refused", "pw-focus-2", "pw-2", "enter"],
            ),
            Step(order=3, says="password again", system=None, cites=["pw-1"]),
            Step(order=4, says="sign in", system=None, cites=["submit", "landed"]),
        ],
    )


def test_a_login_with_a_refused_attempt_and_focus_clicks_signs_in() -> None:
    """Focus clicks and an Enter on the password box are part of typing it; a
    same-host Sign In followed by the password typed again is a refused first
    attempt; the chain ends at the submit that left the host, so the click in
    the warehouse after it is not part of the sign-in."""
    assert signs_in(_azure_job(), _azure_store()) is True


def test_the_refused_attempt_is_never_exempt_from_write_rules() -> None:
    job, store = _azure_job(), _azure_store()

    assert is_sign_in_step(job, job.steps[2], store) is False


def test_what_is_done_before_the_credential_is_typed_is_part_of_signing_in() -> None:
    """The chooser and the username (final review I-3, 2026-09-24): nobody is
    signed in yet, so nothing pressed there writes for anybody. This replaced
    a list of identity-provider paths that spared any press on such a path,
    on any job. The deployed chain's chooser and username focus click record
    no traffic and never leave their host, so no other shape covers them."""
    job, store = _azure_job(), _azure_store()

    assert [is_sign_in_step(job, step, store) for step in job.steps[:3]] == [True, True, False]


def test_the_azure_chain_keeps_its_sign_in_steps_and_its_tag() -> None:
    job, store = _azure_job(), _azure_store()

    assert [is_sign_in_step(job, step, store) for step in job.steps] == [
        True,
        True,
        False,
        True,
        False,
    ]
    assert signs_in(job, store) is True


def test_a_silent_press_on_the_landing_system_before_the_credential_is_no_sign_in_step() -> None:
    """Final re-review N-1, 2026-09-24: "Release wave" pressed in the WMS (a
    full-page post the recorder never hears), the session had lapsed, the
    operator signed in and landed back in the WMS. The release is not part
    of signing in. (Whether the job is a sign-in changed with F4's Google
    ruling, 2026-09-28: a click on the landing that writes and types nothing
    is an entry into the sign-in -- see
    `test_a_silent_click_on_the_landing_before_a_sign_in_is_an_entry`.)"""
    store = {
        "release": _did("release", WMS, 1.0),
        "pw": _typed_secret("pw", KEYCLOAK, 2.0),
        "go": _left(_did("go", KEYCLOAK, 3.0), WMS),
    }
    job = _job("release", "pw", "go")

    assert is_sign_in_step(job, job.steps[0], store) is False


def test_a_keycloak_sign_in_stays_a_sign_in() -> None:
    store = {
        "user": replace(_at("user", KEYCLOAK, 1), action=Action(kind="type", at=1, value="u")),
        "pw": _typed_secret("pw", KEYCLOAK, 2),
        "go": _left(_did("go", KEYCLOAK, 3), WMS),
    }
    job = _job("user", "pw", "go")

    assert [is_sign_in_step(job, step, store) for step in job.steps] == [True, True, True]
    assert signs_in(job, store) is True


def test_a_recorded_write_before_the_credential_is_still_a_write() -> None:
    store = {"a": _wrote("a", KEYCLOAK, 1, 302), "b": _secret("b", KEYCLOAK, 2)}
    job = _job("a", "b")

    assert is_sign_in_step(job, job.steps[0], store) is False


def test_a_step_mixing_the_submit_with_work_after_landing_is_never_exempt() -> None:
    job, store = _azure_job(), _azure_store()

    assert is_sign_in_step(job, job.steps[3], store) is True
    assert is_sign_in_step(job, job.steps[4], store) is False


def test_the_chain_is_found_at_its_first_host() -> None:
    store = _azure_store()
    job = replace(_azure_job(), signs_in=signs_in(_azure_job(), store))

    assert signs_in_at(f"{B2C}/authorize", [job], store) == "wfl_azure"


def test_a_pin_and_enter_on_its_own_box_that_stays_on_the_host_is_not_a_sign_in() -> None:
    """The Enter on the secret box only counts as typing when the chain goes on
    to leave the host: pressed on a PIN box that answers on the same system it
    is a submit, and a possible write."""
    store = {
        "a": _typed_secret("a", WMS, 1),
        "b": _did("b", WMS, 2, "press", on_secret=True),
    }
    job = Workflow(
        id="wfl_pin",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="approve with the PIN", system=None, cites=["a", "b"])],
    )

    assert is_sign_in_step(job, job.steps[0], store) is False
    assert signs_in(job, store) is False


def test_a_same_host_press_with_no_second_try_after_it_is_not_forgiven() -> None:
    """A refused attempt is a same-host press the password is typed AGAIN
    after. One with nothing retyped behind it is the PIN shape, even when
    something later leaves the host."""
    store = {
        "a": _typed_secret("a", WMS, 1),
        "b": _did("b", WMS, 2, "press"),
        "c": _left(_did("c", WMS, 3), KEYCLOAK),
    }

    assert signs_in(_job("a", "b", "c"), store) is False


def test_one_step_with_a_refused_press_and_the_leaving_one_is_not_exempt() -> None:
    store = {
        "a": _typed_secret("a", KEYCLOAK, 1),
        "b": _did("b", KEYCLOAK, 2),
        "c": _typed_secret("c", KEYCLOAK, 3),
        "d": _left(_did("d", KEYCLOAK, 4), WMS),
    }
    job = Workflow(
        id="wfl_login",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[Step(order=0, says="sign in", system=None, cites=["a", "b", "c", "d"])],
    )

    assert is_sign_in_step(job, job.steps[0], store) is False
    assert signs_in(job, store) is True


def test_a_sign_in_is_the_credential_host_and_where_it_landed() -> None:
    """Not the first host of the chain (an identity chooser the operator may or
    may not pass through): the host that took the credential, and the host the
    browser was sent to after it -- one identity provider in front of two
    applications is two sign-ins."""
    assert signs_in_to(_azure_job(), _azure_store()) == ("keycloak.example", "wms.example")


def test_a_job_with_no_credential_signs_in_to_nothing() -> None:
    store = {"a": _at("a", WMS, 1), "b": _at("b", WMS, 2)}

    assert signs_in_to(_job("a", "b"), store) is None


def test_the_landing_is_read_off_the_doing_when_the_job_stops_at_the_password() -> None:
    """The model summarises a sign-in as the typing and leaves the submit
    uncited; the doing still holds it, on the same tab, right after."""
    store = {
        "user": replace(_at("user", KEYCLOAK, 1), action=Action(kind="type", at=1, value="u")),
        "pw": _typed_secret("pw", KEYCLOAK, 2),
        "go": _left(_did("go", KEYCLOAK, 3), WMS),
    }

    assert signs_in_to(_job("user", "pw"), store) == ("keycloak.example", "wms.example")


def test_a_sign_in_that_never_left_has_no_key() -> None:
    store = {"user": _at("user", KEYCLOAK, 1), "pw": _typed_secret("pw", KEYCLOAK, 2)}

    assert signs_in_to(_job("user", "pw"), store) is None


def test_a_press_back_on_the_credential_host_after_the_leave_untags_the_job() -> None:
    """A PIN on the warehouse, a click that happens to navigate away, then
    Approve pressed back on the warehouse: the leave does not forgive a
    same-host press after it."""
    store = {
        "a": _secret("a", WMS, 1),
        "b": _left(_did("b", WMS, 2), KEYCLOAK),
        "c": replace(_at("c", WMS, 3), action=Action(kind="press", at=3)),
    }

    assert signs_in(_job("a", "b", "c"), store) is False
