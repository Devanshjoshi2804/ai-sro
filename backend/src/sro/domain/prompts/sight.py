from __future__ import annotations

from dataclasses import replace

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = (
    "You are helping finish one step of a warehouse task that was demonstrated "
    "by an operator and can no longer be replayed as recorded."
)

_TASK = (
    "Propose exactly "
    "one gesture towards the step's goal, using what is visible now. "
    "Do not attempt the whole task. Do not enter credentials. If the step "
    "already appears done, say so instead of acting. If you cannot see how to "
    "proceed, refuse and say why.\n\n"
    "Answer with one gesture. Coordinates are 0-1000, left to right and top "
    "to bottom of the screenshot."
)

SIGHT = Prompt(
    name="sight",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "`allowed_actions` as JSON; the step's `goal`, what was `already_tried` on this "
        "step, and the `visible_controls` (label: x,y, already 0-1000) each in its own "
        "untrusted block. The screenshot is the image."
    ),
    output_schema={},
    edge_cases=(
        EdgeCase(
            "a screen on which the step is already done",
            "no gesture, and says so",
        ),
        EdgeCase(
            "a goal that needs a password typed",
            "refuses: credentials are never entered",
        ),
        EdgeCase(
            "a screen with no visible way forward",
            "refuses, and says why",
        ),
    ),
)

SIGHT_ESCALATED = replace(SIGHT, name="sight_escalated", model="gemini-3.1-pro-preview")
