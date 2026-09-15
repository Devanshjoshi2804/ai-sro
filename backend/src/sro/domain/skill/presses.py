"""The control the operator actually pressed, when the step cites the page.

A real sign-in, mined from a real recording. The job's last step said "Sign in
to Keycloak." and cited four gestures: a click on `div.card-pf` -- the login
card itself -- the eye icon that shows the password, and two typings. It did
not cite the one gesture that signed anybody in:

    click  input#kc-login  "Sign In"

The operator had clicked around the form before pressing it, and every one of
those strays is a real recorded click. The model picked from them. Run, the
step clicked the card, the browser answered `ok`, and the verifier said the
page was "still displaying the login page with the credentials entered" -- a
run that typed a password into a form and then pressed nothing.

`passwords.py` is the sibling of this: there the gesture is invisible to a
model because redaction struck it, here it is visible and was passed over. The
rule is the same shape and just as narrow:

**Only a step whose clicks are all on things that are not controls.** A div, a
span, an icon: no tag a browser treats as interactive, no ARIA role, no test
id. A step that cites a real button keeps it, which is nearly every step.

**Only a control nothing else cites.** The press belongs to one step. A click
another step is built on is that step's, not this one's.

**Only just after, and on the same system.** Bounded by `SOON_S` from the last
gesture the step cites: a button pressed a minute later is the next job, and
one on another host was never part of this one.

**The press goes first.** `primary_gesture` takes the first citation it can
act on, so a press appended to the end would leave the step planning against
the card again. The strays are dropped, the typings kept -- they are context
for the model, and no longer anything the step plans from.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow

SOON_S = 20.0
"""How long after a step's own evidence a press may still be its press.

Long enough for a page that took a moment and an operator who looked before
pressing; short enough that the next job's first click is out of reach."""

CONTROLS = frozenset({"button", "a", "input", "select", "summary", "option", "label"})
"""Tags a browser treats as a control. Not `div` or `span` -- a page may make
either clickable, and when it does it says so with a role."""

ROLES = frozenset(
    {
        "button",
        "link",
        "menuitem",
        "menuitemcheckbox",
        "tab",
        "option",
        "checkbox",
        "radio",
        "switch",
    }
)


def _is_a_control(gesture: Gesture) -> bool:
    """Whether this click landed on something built to be clicked.

    Name and text are deliberately not read. The card in the recording that
    prompted this module carries the name "Sign in to your account\\nUsername
    or email\\nPassword" -- the label of everything inside it -- so a rule that
    counted a name would call the whole login form a control.
    """
    target = gesture.action.target
    if target is None:
        return False
    return (
        (target.tag or "").lower() in CONTROLS
        or (target.role or "").lower() in ROLES
        or bool(target.test_id)
    )


def with_the_press(workflow: Workflow, gestures: dict[str, Gesture]) -> int:
    """Give each click step the control it was really done with.

    In place, returning how many steps changed. A job whose click steps already
    cite controls is untouched and answers 0, which is most jobs.
    """
    cited_anywhere = {gesture_id for step in workflow.steps for gesture_id in step.cites}
    changed = 0

    for step in workflow.steps:
        mine = [gestures[one] for one in step.cites if one in gestures]
        clicks = [one for one in mine if one.action.kind == "click"]
        if not clicks or any(_is_a_control(one) for one in clicks):
            continue

        after = max(one.at for one in mine)
        systems = {origin_of(one.url or "") for one in mine}
        presses = [
            one
            for one in gestures.values()
            if one.id not in cited_anywhere
            and one.action.kind == "click"
            and _is_a_control(one)
            and after <= one.at <= after + SOON_S
            and origin_of(one.url or "") in systems
        ]
        if not presses:
            continue

        press = min(presses, key=lambda one: one.at)
        # First, and the strays gone. The typings stay: they are what the step
        # was done after, and the step no longer plans from them.
        step.cites = [press.id] + [
            one for one in step.cites if one in gestures and gestures[one].action.kind != "click"
        ]
        cited_anywhere.add(press.id)
        changed += 1

    return changed
