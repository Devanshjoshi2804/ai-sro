"""The password step, added from evidence a model was never able to cite.

An operator asked, more than once, why their browser fills their username,
presses Sign In and stops. The mined job really did have two steps: redaction
strips a credential gesture of its value AND its target name, so the one
gesture that would make the third step is the one gesture a model summarising
the job cannot point at. `checks.py` had already written that down for a
different purpose.

So the step is added rather than asked for. What is held here is the narrowness
-- a job that is not a sign-in must not grow one by accident -- and the order,
because a password typed after Sign In was pressed is not a login, it is a page
that has already refused.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.skill.passwords import with_passwords
from sro.domain.skill.workflow import Step, Workflow

KEYCLOAK = "https://keycloak.test"
SIGN_IN = f"{KEYCLOAK}/auth/realms/x/protocol/openid-connect/auth"
WMS = "https://wms.test"


def _gesture(
    gesture_id: str,
    at: float,
    *,
    kind: str = "type",
    secret: bool = False,
    name: str | None = "username",
    url: str = SIGN_IN,
) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="new",
        stream_id="str-1",
        batch_id="bat-1",
        at=at,
        url=url,
        system=url,
        tab_id=7,
        frame_url=None,
        action=Action(
            kind=kind,
            at=at,
            url=url,
            target=Target(tag="input", name=name, secret=secret),
            value=None if secret else "RKUCHIYAGM",
        ),
    )


def _signing_in() -> tuple[Workflow, dict[str, Gesture]]:
    """The job as it was really mined: the username and the click, and the
    password sitting in the evidence between them, cited by nobody."""
    typed = _gesture("ges-user", 100.0)
    secret = _gesture("ges-pass", 101.0, secret=True, name="password")
    clicked = _gesture("ges-click", 102.0, kind="click", name="Sign In")
    workflow = Workflow(
        id="wfl_1",
        tenant="new",
        title="Log In",
        narrative="the operator signed in",
        steps=[
            Step(order=0, says="Enter username.", system=SIGN_IN, cites=["ges-user"]),
            Step(order=1, says="Sign in.", system=SIGN_IN, cites=["ges-click"]),
        ],
        parameters=[],
    )
    return workflow, {one.id: one for one in (typed, secret, clicked)}


def test_the_password_becomes_a_step_of_its_own() -> None:
    workflow, gestures = _signing_in()

    added = with_passwords(workflow, gestures)

    assert added == 1
    typing = [step for step in workflow.steps if step.cites == ["ges-pass"]]
    assert len(typing) == 1
    assert typing[0].says == "Type the password."


def test_it_is_typed_before_sign_in_is_pressed() -> None:
    """A password typed after the click is not a login, it is a page that has
    already refused. The order the operator did it in is the only order that
    runs, and the evidence carries it."""
    workflow, gestures = _signing_in()

    with_passwords(workflow, gestures)

    said = [step.says for step in sorted(workflow.steps, key=lambda step: step.order)]
    assert said == ["Enter username.", "Type the password.", "Sign in."]
    assert [step.order for step in sorted(workflow.steps, key=lambda step: step.order)] == [0, 1, 2]


def test_the_step_carries_no_value_because_nothing_here_has_one() -> None:
    """The evidence holds no password and never will. What gets typed comes
    from the vault at run time, by a key built from the system and the field."""
    workflow, gestures = _signing_in()

    with_passwords(workflow, gestures)
    typing = next(step for step in workflow.steps if step.cites == ["ges-pass"])

    assert typing.parameters == []
    assert gestures["ges-pass"].action.value is None


def test_a_job_that_is_not_a_sign_in_grows_nothing() -> None:
    # The same three gestures with nothing marked secret: a form being filled
    # in, which is most of the work this system watches.
    typed = _gesture("ges-user", 100.0)
    also = _gesture("ges-code", 101.0, name="clientCode")
    clicked = _gesture("ges-click", 102.0, kind="click", name="Save")
    workflow = Workflow(
        id="wfl_2",
        tenant="new",
        title="Create a client",
        narrative="the operator created a client",
        steps=[
            Step(order=0, says="Type the code.", system=SIGN_IN, cites=["ges-user"]),
            Step(order=1, says="Save.", system=SIGN_IN, cites=["ges-click"]),
        ],
        parameters=[],
    )

    assert with_passwords(workflow, {one.id: one for one in (typed, also, clicked)}) == 0
    assert len(workflow.steps) == 2


def test_a_credential_typed_outside_this_doing_belongs_to_somebody_else_s_job() -> None:
    """`one_occurrence` has already struck every citation but one doing's by
    the time this runs, so the span is that doing. A password typed an hour
    later is not this job's password."""
    workflow, gestures = _signing_in()
    later = _gesture("ges-later", 5_000.0, secret=True, name="password")
    gestures[later.id] = later

    with_passwords(workflow, gestures)

    assert [step.cites for step in workflow.steps].count(["ges-later"]) == 0


def test_a_credential_on_a_host_this_job_never_touched_is_not_its_own() -> None:
    workflow, gestures = _signing_in()
    elsewhere = _gesture("ges-other", 101.5, secret=True, name="password", url=f"{WMS}/admin")
    gestures[elsewhere.id] = elsewhere

    with_passwords(workflow, gestures)

    assert [step.cites for step in workflow.steps].count(["ges-other"]) == 0


def test_a_model_that_did_cite_the_credential_keeps_its_own_step() -> None:
    # Rare and real: a field whose label survives redaction can be cited. One
    # step, not two.
    workflow, gestures = _signing_in()
    workflow.steps[1].cites = ["ges-pass", "ges-click"]

    assert with_passwords(workflow, gestures) == 0


def test_a_job_citing_nothing_this_window_holds_is_left_alone() -> None:
    workflow, gestures = _signing_in()
    workflow.steps = [Step(order=0, says="do it", system=SIGN_IN, cites=["ges-gone"])]

    assert with_passwords(workflow, gestures) == 0
