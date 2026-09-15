"""What the field dictionary already knows about the values a write carries.

The one failure the ladder cannot see is a record created exactly as asked that
is not the record the operator wanted, and the sharpest instance of it is a
value the field is too small to hold: the form sends `ZV9680`, the column keeps
`ZV96`, and the warehouse answers 201 for it. Nothing downstream can tell that
from success -- the status is right, the read-back shows the record the system
actually made, and only a person who knows the field knows it is wrong.

Somebody already wrote that down. The knowledge base carries 404 `field` claims
read off the system's own documentation, and `customerType`'s says
`max_length: 60` beside its label and the screens it is required on. So the
question "will this value fit" is answerable before the write goes out, from
evidence nobody has to gather again.

**A note and never a refusal**, and the disagreement is the reason. The
dictionary is what the vendor DOCUMENTS; the ledger's own gotcha for this same
field says `csttyp truncates at 4 chars`, which is what somebody MEASURED. Two
sources, both real, and refusing on the documented one would stop correct runs
against a system that behaves differently from its manual. So this puts the
fact in front of the person who taps Approve and lets them decide, which is the
same division of labour the whole approval gate is built on.

Pure, and given the claims rather than fetching them: what the store holds is
the application's to read, and this is the rule for reading it.
"""

from __future__ import annotations

from collections.abc import Mapping


def notes_on(sent: Mapping[str, str], known: Mapping[str, Mapping[str, object]]) -> tuple[str, ...]:
    """One line per value the dictionary says will not fit, in body-key order.

    Silent about everything else on purpose. A note beside every field is a
    card nobody reads, and "this field is required and you supplied it" is not
    news -- what earns a line is a fact that predicts a wrong record.
    """
    said: list[str] = []
    for slot in sorted(sent):
        claim = known.get(slot)
        if not isinstance(claim, Mapping):
            continue
        limit = claim.get("max_length")
        # `> 0` because a zero or negative limit is a claim about nothing, and
        # a bool is an int in Python -- `max_length: true` would otherwise read
        # as a one-character field and warn about every value.
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            continue
        value = sent[slot]
        if len(value) > limit:
            said.append(
                f"{_label(claim, slot)} holds {limit} characters and this run supplies {len(value)}"
            )
    return tuple(said)


def _label(claim: Mapping[str, object], slot: str) -> str:
    """What the operator calls this field, falling back to what the body does.

    `labels` is what the screen shows -- `Customer Type` -- and the body key is
    the API's spelling. The person reading this card is looking at the screen.
    """
    labels = claim.get("labels")
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, str) and label.strip():
                return label.strip()
    return slot
