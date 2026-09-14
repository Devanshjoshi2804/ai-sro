"""The press a model saw and passed over.

From a real sign-in. The job's last step said "Sign in to Keycloak." and cited
the login card, the eye icon that reveals the password, and two typings -- every
one of them a real recorded click, none of them the button. Run, the step
clicked the card, the browser answered ok, and the verifier reported a page
"still displaying the login page with the credentials entered": a run that
typed a password into a form and pressed nothing.

The sibling of `test_the_step_a_model_cannot_see`. There the gesture is
invisible because redaction struck it; here it is plainly visible and was not
chosen. What is held is the narrowness -- a step that cites a real control must
keep it -- and the order, because the runner plans from the first citation it
can act on.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.skill.presses import SOON_S, with_the_press
from sro.domain.skill.workflow import Step, Workflow

KEYCLOAK = "https://keycloak.test/auth"
WMS = "https://wms.test/admin"


def _gesture(
    gesture_id: str,
    at: float,
    *,
    kind: str = "click",
    tag: str = "div",
    name: str | None = None,
    role: str | None = None,
    test_id: str | None = None,
    url: str = KEYCLOAK,
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
            target=Target(tag=tag, name=name, role=role, test_id=test_id),
            value="RKUCHIYAGM" if kind == "type" else None,
        ),
    )


def _signing_in() -> tuple[Workflow, dict[str, Gesture]]:
    """The job as it was really mined, and the press it really was done with."""
    card = _gesture("ges-card", 462.0, name="Sign in to your account\nUsername or email\nPassword")
    typed = _gesture("ges-type", 465.8, kind="type", tag="input")
    icon = _gesture("ges-icon", 466.0, tag="i")
    press = _gesture("ges-press", 473.6, tag="input", name="Sign In")
    workflow = Workflow(
        id="wfl_1",
        tenant="new",
        title="Log In",
        narrative="the operator signed in",
        steps=[
            Step(
                order=0,
                says="Sign in to Keycloak.",
                system=KEYCLOAK,
                cites=["ges-card", "ges-type", "ges-icon"],
            )
        ],
        parameters=[],
    )
    return workflow, {one.id: one for one in (card, typed, icon, press)}


def test_the_step_is_repointed_at_the_button() -> None:
    workflow, gestures = _signing_in()

    assert with_the_press(workflow, gestures) == 1
    assert workflow.steps[0].cites[0] == "ges-press", (
        "the runner plans from the first citation it can act on, so a press"
        " appended to the end would leave the step clicking the card again"
    )


def test_the_strays_go_and_what_was_typed_stays() -> None:
    workflow, gestures = _signing_in()

    with_the_press(workflow, gestures)

    assert "ges-card" not in workflow.steps[0].cites
    assert "ges-icon" not in workflow.steps[0].cites
    assert "ges-type" in workflow.steps[0].cites


def test_a_step_that_already_cites_a_control_is_left_alone() -> None:
    # Nearly every step. A model that cited the button got it right, and a rule
    # that went looking anyway would move a step off the evidence it was mined
    # from.
    workflow, gestures = _signing_in()
    workflow.steps[0].cites = ["ges-press"]

    assert with_the_press(workflow, gestures) == 0
    assert workflow.steps[0].cites == ["ges-press"]


def test_a_step_with_no_click_at_all_is_not_given_one() -> None:
    workflow, gestures = _signing_in()
    workflow.steps[0].cites = ["ges-type"]

    assert with_the_press(workflow, gestures) == 0


def test_a_press_another_step_is_built_on_is_that_steps() -> None:
    workflow, gestures = _signing_in()
    workflow.steps.append(
        Step(order=1, says="Sign in.", system=KEYCLOAK, cites=["ges-press"])
    )

    assert with_the_press(workflow, gestures) == 0


def test_a_button_pressed_much_later_is_the_next_job() -> None:
    workflow, gestures = _signing_in()
    late = _gesture("ges-late", 466.0 + SOON_S + 1, tag="button", name="Save")
    gestures = {one: g for one, g in gestures.items() if one != "ges-press"}
    gestures[late.id] = late

    assert with_the_press(workflow, gestures) == 0


def test_a_button_on_another_system_was_never_part_of_this_one() -> None:
    workflow, gestures = _signing_in()
    gestures.pop("ges-press")
    elsewhere = _gesture("ges-other", 470.0, tag="button", name="Save", url=WMS)
    gestures[elsewhere.id] = elsewhere

    assert with_the_press(workflow, gestures) == 0


def test_a_clickable_div_that_says_it_is_a_button_is_a_control() -> None:
    """A page may make a div clickable, and when it does it says so with a
    role. Read from the role and the test id rather than from the name: the
    card in the recording carries the label of everything inside it."""
    workflow, gestures = _signing_in()
    workflow.steps[0].cites = ["ges-role"]
    gestures["ges-role"] = _gesture("ges-role", 462.0, tag="div", role="button")

    assert with_the_press(workflow, gestures) == 0
