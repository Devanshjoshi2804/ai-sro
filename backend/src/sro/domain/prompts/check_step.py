from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "held": {"type": "boolean"},
        "why": {"type": "string", "nullable": True},
    },
    "required": ["held", "why"],
    "propertyOrdering": ["held", "why"],
}

_CONTRACT = (
    "One untrusted block `evidence`, as JSON: what the `step` says, what was `sent`, what "
    "the `browser_answered`, the `screen_before` and `screen_after` as text, the run's "
    "`values`, and `next_step` where there is one. The screen after is the image."
)

_SCREEN_ROLE = """You are checking whether one step of a warehouse job was actually done.
You are shown the step, what was sent, what the browser answered, the screen
text before and after, and the screen after. Answer whether the step HELD --
whether the thing it was meant to do is now true on the screen -- and say why
in one sentence. Do not assume success from the absence of an error."""

_SCREEN_TASK = """Your sentence must be about the thing the STEP names. Where the step names a
field, a list or a control, say what that one now shows. If it is empty, or
you cannot find it on the screen at all, the step did not hold -- whatever
else on the page looks healthy. A page with no errors on it is not evidence
that this step did anything, and neither is a button further down being
visible."""

CHECK_SCREEN = Prompt(
    name="check_screen",
    version=1,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_SCREEN_ROLE,
    task=_SCREEN_TASK,
    input_contract=_CONTRACT,
    output_schema=_SCHEMA,
    edge_cases=(
        EdgeCase(
            "a field the step names showing empty",
            "held false",
        ),
        EdgeCase(
            "a healthy page with no sign of the field the step names",
            "held false",
        ),
        EdgeCase(
            "the list the step names showing the new row",
            "held true",
        ),
    ),
)

_WAY_THROUGH_ROLE = """You are checking one step of a warehouse job that changes nothing by itself.
Its own recording sent no request and put no value anywhere: it opened a menu,
focused a field, moved to a tab. The sentence describing it was written by
another model from the recording, and it may be a guess about what the click
was FOR -- so do not check it."""

_WAY_THROUGH_TASK = """Check only whether the job can go on. Where you are told `next_step`, that is
the question: could somebody looking at this screen now do that next thing?
Answer held=false if they could not -- an error, a sign-in page, a blank or
half-drawn screen, a dialog or a suggestion list sitting over what they would
have to use, or a screen that has not brought up the thing the next step needs
to act on. Answer held=true otherwise, including when the screen looks exactly
as it did before and the next step can still be done from it. Where there is
no `next_step`, this is the job's last step: answer held=false only if the
screen is showing something that plainly went wrong.

Say why in one sentence."""

CHECK_WAY_THROUGH = Prompt(
    name="check_way_through",
    version=1,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_WAY_THROUGH_ROLE,
    task=_WAY_THROUGH_TASK,
    input_contract=_CONTRACT,
    output_schema=_SCHEMA,
    edge_cases=(
        EdgeCase(
            "a suggestion list over the field the next step types into",
            "held false",
        ),
        EdgeCase(
            "the same screen as before, and the next step still possible from it",
            "held true",
        ),
        EdgeCase(
            "the job's last step, and a plain error on the screen",
            "held false",
        ),
    ),
)
