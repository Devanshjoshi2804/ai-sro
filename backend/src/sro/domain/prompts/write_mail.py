from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are writing one email a warehouse operator will read before it is sent."

_TASK = """You are given the job this email does, the values the operator gave for it,
and -- where it answers one -- the conversation it replies to.

Write the email the job describes. Use the operator's values exactly as given:
a code, a quantity or an address is copied, never paraphrased. Where it replies
to a conversation, answer the latest message in it, in the same language, and
address it to whoever the job's values name or, failing that, to whoever sent
the message being answered.

Never invent a recipient. `to` is an address that appears in the values or in
the conversation, or it is empty -- an empty `to` is how you say you do not
know who this goes to, and the operator will be asked.

Plain text. No placeholders, no signature block beyond the operator's name if
you know it, and nothing the values and the conversation do not support."""

WRITE_MAIL = Prompt(
    name="write_mail",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "`job`, `what_it_does`, `steps` and `operator` as JSON; the run's `values` and the "
        "`conversation` (up to the last five messages, each with from, subject and body) "
        "each in its own untrusted block."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
        "propertyOrdering": ["to", "subject", "body"],
    },
    edge_cases=(
        EdgeCase(
            "values naming a code `GT2` and a conversation asking for it",
            "the body says GT2 exactly, never `gt-2` or `the code`",
        ),
        EdgeCase(
            "no address in the values and a conversation from one sender",
            "`to` is that sender",
        ),
        EdgeCase(
            "no address anywhere",
            "`to` is empty, so the operator is asked",
        ),
    ),
)
