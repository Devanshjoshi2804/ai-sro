from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_INTERPRET_ROLE = (
    "You are reading one recorded demonstration of a warehouse task, performed by "
    "an operator in a warehouse management system. You are given every gesture, "
    "every HTTP call it caused, the responses, and anything the operator said."
)

_INTERPRET_TASK = (
    "Describe what was done, step by step, in the words the system and the "
    "operator use. Then name the values that look like inputs to the task — the "
    "identifiers and quantities that would be different next time — and give the "
    "exact literal each one had in this run, copied character for character from "
    "the evidence.\n\n"
    "Rules: describe only what is in the evidence. Do not invent a step nobody "
    "performed. Do not name a parameter whose value you cannot find. A value that "
    "is the same on every run of this task — a site code, a warehouse id — is not "
    "a parameter. If part of the demonstration makes no sense to you, say so in "
    "the caveat rather than guessing."
)

INTERPRET = Prompt(
    name="interpret",
    version=1,
    model="gemini-3.1-pro-preview",
    thinking=None,
    role=_INTERPRET_ROLE,
    task=_INTERPRET_TASK,
    input_contract="One untrusted block `evidence`: the recording's gestures, calls and speech.",
    output_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "when_to_use": {"type": "string"},
            "caveat": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "what": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["index", "what"],
                },
            },
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                        "description": {"type": "string"},
                        "step_index": {"type": "integer"},
                    },
                    "required": ["name", "value"],
                },
            },
        },
        "required": ["title", "summary", "steps"],
    },
    edge_cases=(
        EdgeCase("a site code that is the same on every run", "not a parameter"),
        EdgeCase(
            "a quantity the operator typed",
            "a parameter, with the literal copied from the evidence",
        ),
        EdgeCase(
            "a gesture that makes no sense",
            "said in the caveat, not guessed at",
        ),
    ),
)

_NAME_ROLE = (
    "You are naming a task that an operator of a warehouse management system "
    "performs over and over. You are given what the task is made of: the system "
    "it happens in, how often it is done, how long it takes, and the calls each "
    "doing of it makes, in order."
)

_NAME_TASK = (
    "Answer with one short line an operator would recognise on a list — what the "
    "task accomplishes, not what the software does. 'Adjust an LPN quantity after "
    "a short ship', not 'POST inventory adjust'. No system names, no URLs, no "
    "HTTP verbs, under about eight words.\n\n"
    "If the evidence does not say clearly enough what the task accomplishes, "
    "answer with an empty title rather than a guess: a wrong name on a list is "
    "worse than a dull one, because somebody will teach it believing the name."
)

NAME_SKILL = Prompt(
    name="name_skill",
    version=1,
    model="gemini-3.1-pro-preview",
    thinking=None,
    role=_NAME_ROLE,
    task=_NAME_TASK,
    input_contract="One untrusted block `evidence`: what the task is made of.",
    output_schema={
        "type": "object",
        "properties": {"title": {"type": "string"}, "because": {"type": "string"}},
        "required": ["title"],
    },
    edge_cases=(
        EdgeCase(
            "a task whose calls POST an inventory adjust after a short ship",
            "'Adjust an LPN quantity after a short ship', not 'POST inventory adjust'",
        ),
        EdgeCase(
            "a name that would carry the system, a URL or an HTTP verb",
            "none of them: what the task accomplishes, under about eight words",
        ),
        EdgeCase(
            "evidence that does not say clearly what the task accomplishes",
            "an empty title, not a guess",
        ),
    ),
)

JUDGED = ("variant", "workflow")

_JUDGE_ROLE = "You are deciding whether two observed tasks are one piece of work."

_JUDGE_TASK = (
    "`kind` says which question this is.\n\n"
    "When `kind` is `variant`: "
    "Two tasks were observed in the same system by the same operator, and "
    "their steps are close but not identical. Decide whether they are the "
    "same piece of work done two ways — an extra page visited, a step done "
    "in a different order — or two genuinely different tasks that happen to "
    "touch the same screens.\n\n"
    "Say no unless the evidence is clear. These are shown to a person as a "
    "suggestion, and a confident wrong one costs more than a missed one.\n\n"
    "When `kind` is `workflow`: "
    "Two tasks were observed in different systems, one immediately after the "
    "other, more than once. Decide whether they are two halves of one piece "
    "of work — something checked in one system and then recorded in the "
    "other — or two unrelated tasks that happen to be done at the same time "
    "of day.\n\n"
    "Say no unless the evidence is clear. Doing two things in a row is not "
    "the same as doing one thing across two systems."
)

JUDGE_SKILL = Prompt(
    name="judge_skill",
    version=1,
    model="gemini-3.1-pro-preview",
    thinking=None,
    role=_JUDGE_ROLE,
    task=_JUDGE_TASK,
    input_contract=(
        "`kind` as JSON; the `first` and `second` task, each in its own untrusted block."
    ),
    output_schema={
        "type": "object",
        "properties": {"joined": {"type": "boolean"}, "because": {"type": "string"}},
        "required": ["joined", "because"],
    },
    edge_cases=(
        EdgeCase(
            "a `variant` whose second doing visits one extra page",
            "joined: the same work done two ways",
        ),
        EdgeCase(
            "a `workflow` of two tasks done in a row only because they fall at the same time",
            "not joined",
        ),
        EdgeCase(
            "evidence that is not clear either way",
            "not joined",
        ),
    ),
)
