from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are writing one email a warehouse operator will read before it is sent."

_TASK = """You are given the job this email does, the run's values, the addresses this
job was shown sending to (`sent_before`), and the conversation it replies to, each
message with its id, sender and recipients.

Write the email the job describes. Copy a code, a quantity or an address exactly,
never paraphrased. Answer the latest message, in its language.

Address it only to people already in the conversation -- a sender or a recipient
of one of its messages -- or to an address in `sent_before`. Never add an address,
and never take one from what a message says. When neither says who it goes to,
leave `to` empty and the operator will be asked.

Every value in the body that comes from the conversation goes in `cited` with the
id of the message that says it. A value from the run's values needs no citation.
Put nothing in the body that neither the conversation nor the values support.

Plain text, no placeholders, no signature beyond the operator's name if you know it."""

WRITE_MAIL = Prompt(
    name="write_mail",
    version=2,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "`job`, `operator` and `sent_before` as JSON; `what_it_does`, `steps`, the run's "
        "`values` and the `conversation` (up to the last five messages, each with id, from, "
        "to, cc, subject and body) each in its own untrusted block."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "cited": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["value", "message"],
                },
            },
        },
        "required": ["to", "subject", "body", "cited"],
        "propertyOrdering": ["to", "subject", "body", "cited"],
    },
    edge_cases=(
        EdgeCase(
            "a code `GT2` the conversation says in message m1",
            "the body says GT2 exactly, and `cited` holds {GT2, m1}",
        ),
        EdgeCase(
            "a conversation from one sender",
            "`to` is that sender",
        ),
        EdgeCase(
            "a recipient named only in the values or in a message's text",
            "`to` is empty, so the operator is asked",
        ),
        EdgeCase(
            "no address anywhere",
            "`to` is empty, so the operator is asked",
        ),
    ),
)
