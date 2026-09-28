from __future__ import annotations

from dataclasses import replace

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = """You are performing one step of a job an operator demonstrated in a warehouse
system, in their own browser. You are given the step's sentence, the evidence
it was read from (the gesture the operator made and any calls the page sent),
the values this run was given, and where the browser is now."""

_TASK = """Plan exactly ONE command:
- ui.perform: act on the control the evidence points at. Give the action and,
  for type/select/upload, the value from this run's values. Prefer this.
- http.send: only when the evidence carries a call and there is no usable
  control to drive. The call itself is taken from the evidence.
- navigate: only when the browser is on the wrong page for this step -- compare
  `browser.url` with `step_page`, the screen this step was demonstrated on.
  Give the url. After a navigate the same step is planned again.

Never invent a control, a url or a value that is not in the evidence or the
run's values. If the step cannot be done from what you are shown, say so in
`why` and choose the kind that gets closest."""

PLAN_STEP = Prompt(
    name="plan_step",
    version=1,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "One untrusted block `evidence`, as JSON: the `step`, its cited `evidence`, the run's "
        "`values`, the `browser`'s url and screen text, `step_page`, and "
        "`previous_attempt_failed` and `previous_attempt_left` when an attempt already "
        "missed. The screen now is the first image; the screen a failed attempt left, "
        "when there is one, the second."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["ui.perform", "http.send", "navigate"]},
            "action": {
                "type": "string",
                "nullable": True,
                "enum": ["click", "type", "select", "press", "upload", "scroll", "hover"],
            },
            "value": {"type": "string", "nullable": True},
            "url": {"type": "string", "nullable": True},
            "why": {"type": "string"},
        },
        "required": ["kind", "why"],
        "propertyOrdering": ["kind", "action", "value", "url", "why"],
    },
    edge_cases=(
        EdgeCase(
            "a step whose evidence has a usable control",
            "`ui.perform` on that control",
        ),
        EdgeCase(
            "the browser on another page than `step_page`",
            "`navigate`, with the url",
        ),
        EdgeCase(
            "evidence with a call and no control to drive",
            "`http.send`",
        ),
    ),
)

PLAN_STEP_ESCALATED = replace(
    PLAN_STEP, name="plan_step_escalated", model="gemini-3.1-pro-preview", fallback_model=None
)
