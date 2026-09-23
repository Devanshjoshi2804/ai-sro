# Notes for `backend/src/sro/domain/skill/presses.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/presses.py`](../../../../../../../backend/src/sro/domain/skill/presses.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/presses.py#L1): Docstring

> The control the operator actually pressed, when the step cites the page.
>
> A real sign-in, mined from a real recording. The job's last step said "Sign in
> to Keycloak." and cited four gestures: a click on `div.card-pf` -- the login
> card itself -- the eye icon that shows the password, and two typings. It did
> not cite the one gesture that signed anybody in:
>
>     click  input#kc-login  "Sign In"
>
> The operator had clicked around the form before pressing it, and every one of
> those strays is a real recorded click. The model picked from them. Run, the
> step clicked the card, the browser answered `ok`, and the verifier said the
> page was "still displaying the login page with the credentials entered" -- a
> run that typed a password into a form and then pressed nothing.
>
> `passwords.py` is the sibling of this: there the gesture is invisible to a
> model because redaction struck it, here it is visible and was passed over. The
> rule is the same shape and just as narrow:
>
> **Only a step whose clicks are all on things that are not controls.** A div, a
> span, an icon: no tag a browser treats as interactive, no ARIA role, no test
> id. A step that cites a real button keeps it, which is nearly every step.
>
> **Only a control nothing else cites.** The press belongs to one step. A click
> another step is built on is that step's, not this one's.
>
> **Only just after, and on the same system.** Bounded by `SOON_S` from the last
> gesture the step cites: a button pressed a minute later is the next job, and
> one on another host was never part of this one.
>
> **The press goes first.** `primary_gesture` takes the first citation it can
> act on, so a press appended to the end would leave the step planning against
> the card again. The strays are dropped, the typings kept -- they are context
> for the model, and no longer anything the step plans from.

## module, [line 7](../../../../../../../backend/src/sro/domain/skill/presses.py#L7): Note on the line above

Code: `SOON_S = 20.0`

> How long after a step's own evidence a press may still be its press.
>
> Long enough for a page that took a moment and an operator who looked before
> pressing; short enough that the next job's first click is out of reach.

## module, [line 9](../../../../../../../backend/src/sro/domain/skill/presses.py#L9): Note on the line above

Code: `CONTROLS = frozenset({"button", "a", "input", "select", "summary", "option", "label"})`

> Tags a browser treats as a control. Not `div` or `span` -- a page may make
> either clickable, and when it does it says so with a role.

## `_is_a_control`, [line 26](../../../../../../../backend/src/sro/domain/skill/presses.py#L26): Docstring

> Whether this click landed on something built to be clicked.
>
> Name and text are deliberately not read. The card in the recording that
> prompted this module carries the name "Sign in to your account\nUsername
> or email\nPassword" -- the label of everything inside it -- so a rule that
> counted a name would call the whole login form a control.

## `with_the_press`, [line 37](../../../../../../../backend/src/sro/domain/skill/presses.py#L37): Docstring

> Give each click step the control it was really done with.
>
> In place, returning how many steps changed. A job whose click steps already
> cite controls is untouched and answers 0, which is most jobs.

## `with_the_press`, [line 62](../../../../../../../backend/src/sro/domain/skill/presses.py#L62): Comment

Code: `step.cites = [press.id] + [`

> First, and the strays gone. The typings stay: they are what the step
> was done after, and the step no longer plans from them.
