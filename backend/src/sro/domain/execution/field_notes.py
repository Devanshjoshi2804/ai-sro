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

from collections.abc import Iterable, Mapping


def notes_on(sent: Mapping[str, str], known: Mapping[str, Mapping[str, object]]) -> tuple[str, ...]:
    """One line per fact that predicts a wrong record, in body-key order.

    Silent about everything else on purpose. A note beside every field is a
    card nobody reads, and "this field is required and you supplied it" is not
    news.

    Two facts earn a line. A value the field cannot hold -- see the module
    docstring. And a field the FORM marks required that this write does not
    carry at all: on a replay that is a demonstration which did not fill it,
    which is worth a sentence in front of the person approving rather than a
    refusal, because the demonstration did land.
    """
    said: list[str] = []
    for slot in sorted(sent):
        claim = known.get(slot)
        if not isinstance(claim, Mapping):
            continue
        limit = _limit(claim)
        if limit is None:
            continue
        value = sent[slot]
        if len(value) > limit:
            said.append(
                f"{_label(claim, slot)} holds {limit} characters and this run supplies {len(value)}"
                + (" (what the form itself says)" if _observed(claim) else "")
            )
    for slot in sorted(known):
        claim = known[slot]
        if not isinstance(claim, Mapping) or slot in sent:
            continue
        if claim.get("required") is True:
            said.append(
                f"{_label(claim, slot)} is required on this form and this run sends nothing"
            )
    return tuple(said)


def _limit(claim: Mapping[str, object]) -> int | None:
    """How much this field holds, or `None` where nothing credible says.

    `> 0` because a zero or negative limit is a claim about nothing, and a bool
    is an int in Python -- `max_length: true` would otherwise read as a
    one-character field and warn about every value.
    """
    limit = claim.get("max_length")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        return None
    return limit


def _observed(claim: Mapping[str, object]) -> bool:
    """Whether this number was read off the real form rather than the manual.

    Worth saying out loud on the card. The two sources disagree and the
    disagreement is the point: the documentation says `customerType` holds 60,
    the form the operator actually uses says 4, and the ledger's own gotcha --
    somebody's measurement -- says `csttyp truncates at 4 chars`. A person
    deciding whether to send `NEWSROTEST` is owed which of those they are
    reading.
    """
    return bool(claim.get("observed"))


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


def limits_named(
    names: Iterable[str], *sources: Mapping[str, Mapping[str, object]]
) -> dict[str, int]:
    """What the boxes behind these screen names are DECLARED to hold.

    A job's parameters are named the way the screen names them -- `Customer
    Type Description` -- and everything already known about a field is filed
    under the key the body posts it as, `longDescription`. The labels are the
    join, and they are the only join: a body key is not derivable from a label
    and guessing one is how a system starts writing into slots nothing
    demonstrated.

    **The smallest number wins, whatever said it.** The sources disagree by
    construction and the disagreement is measured: the dictionary says
    `customerType` holds 60, the real create form says 4, and the ledger's own
    gotcha -- somebody sitting in front of the screen -- says `csttyp truncates
    at 4 chars`. A limit is a ceiling, so the lowest ceiling is the one that
    binds, and being wrong in this direction asks somebody to shorten a value
    further than they had to. Being wrong in the other direction sends
    `NEWSROTEST`, keeps `NEWS`, and answers 201.

    **Silent where two keys answer to one label.** `Description` is a label on
    ten different keys on this deployment, holding anywhere from 20 characters
    to 2000, and a guess between them is a number this would state to somebody
    as a fact. 23 of 378 labels are ambiguous that way; the other 355 are not,
    and a screen's own form -- passed first -- resolves most of the rest,
    because it says what THAT screen calls THAT slot.

    Declared and never measured, which is why `limits_for` treats what a run
    found out as another ceiling rather than as the answer. The manual is a
    claim about the system; a truncation is the system.
    """
    wanted = {_flat(name): name for name in names if _flat(name)}
    limits: dict[str, int] = {}
    for source in sources:
        seen: dict[str, int | None] = {}
        for slot, claim in source.items():
            limit = _limit(claim)
            for label in (*_labels(claim), slot):
                if (flat := _flat(label)) not in wanted:
                    continue
                # Two keys answering to one label, and this is the second: the
                # label decides nothing here and must not be made to.
                seen[flat] = None if flat in seen and seen[flat] != limit else limit
        for flat, limit in seen.items():
            if limit is None:
                continue
            name = wanted[flat]
            limits[name] = min(limit, limits.get(name, limit))
    return limits


def _labels(claim: Mapping[str, object]) -> tuple[str, ...]:
    """Every name a screen shows for this field, not only the first.

    `longDescription` is `Customer Type Description` on one screen and
    `Description` on another, and a job's parameter is named by the screen it
    was demonstrated on.
    """
    labels = claim.get("labels")
    if not isinstance(labels, list):
        return ()
    return tuple(one.strip() for one in labels if isinstance(one, str) and one.strip())


def _flat(name: str) -> str:
    """A label with the punctuation and case a screen and a mined parameter
    disagree about taken out. `Customer Type:` and `customer type` are one
    name."""
    return "".join(one for one in name.lower() if one.isalnum())
