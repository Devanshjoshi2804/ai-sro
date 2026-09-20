"""One system's answer to one lookup, in the shape every surface draws it from.

An answer is read in three places -- the panel's card, the conversation, and
whatever model is asked to make sense of it -- and each of them was parsing the
raw body for itself. So each of them guessed, and the panel guessed badly:
asked "is there a customer type called KKYT" it drew `URNFORMAT |
ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` as five columns of em dashes, beside a
warehouse screen showing `Customer Type` and `Description`. Those were the
first six KEYS of a payload that alphabetises.

**Nothing here decides what a record is.** `application.execution.answer` does,
for every other read in this system, and it decided all of it already: a
column earns its place by carrying a value, the ranking puts code, name and
description first, a `self_uri` is dropped as a link, two columns holding the
same value in every row are one, the count is the system's own total rather
than the page length, and `sentence()` says it in a line. This carries that
across the wire and adds the one thing the reader cannot know -- what the
records are OF, which is in the address they came from.

The raw body still travels for an answer that is not records: a page of HTML,
one scalar, a screen whose picture stays on the other side. Those have nothing
structural to preserve and are trimmed by character, the way they always were.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from sro.application.execution.answer import Answer

K_ANSWER_CHARS = 64 * 1024
"""How much of a body that is NOT records travels.

Records do not use this: they cross as the reader's own bounded sample. This
is the last guard, for a page of HTML or a scalar, and it is a character cut
because there is nothing structural in those to cut along."""

K_SAMPLE = 200
"""How many read records cross to a surface that draws them.

`answer.py` bounds its sample at two thousand, which is right where the answer
IS the product -- a taught read whose rows a person works from. A panel beside
a warehouse screen draws eight and offers the console for the rest, and two
thousand records of ten columns is a megabyte of JSON for a question somebody
typed. Two hundred is far past what is drawn and far short of that."""


def subject_of(target: str) -> str:
    """What the records are OF, from the address they came from.

    `/data/WM/wm/customerTypes` is customer types. The reader cannot know this
    -- it is handed a body and never the question -- and `sentence()` needs it
    to say "There are 50 customer types" rather than "There are 50".

    The last path segment, un-camel-cased and singularised, because that is
    what a REST collection is named after and this base has no counter-example
    in 296 captured exchanges. A target that is not a path -- a screen route --
    answers empty, and the sentence says "records".
    """
    last = [part for part in str(target or "").split("/") if part and "#" not in part]
    if not last:
        return ""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", last[-1]).lower().replace("_", " ").strip()
    if not words or not re.fullmatch(r"[a-z0-9 ]+", words):
        return ""
    # Singular, because `sentence` counts them: "There are 50 customer type"
    # is the one place English needs this and the rest of the system names an
    # entity in the singular everywhere.
    return re.sub(r"ies$", "y", words) if words.endswith("ies") else words.removesuffix("s")


def trimmed(text: str | None) -> tuple[str | None, bool]:
    """A body that is not records, small enough to send."""
    if text is None or len(text) <= K_ANSWER_CHARS:
        return text, False
    return text[:K_ANSWER_CHARS], True


def as_seen(
    *,
    system: str,
    target: str,
    ok: bool,
    detail: str,
    answer: Mapping[str, object],
    read: Answer | None = None,
) -> dict[str, object]:
    """One answer, as every surface draws it.

    The picture a screen lookup takes is deliberately not here: it is hundreds
    of kilobytes of base64 per screen, and what a picture MEANS is a model's
    question rather than a field on this shape.
    """
    status = answer.get("status")
    seen: dict[str, object] = {
        "system": system,
        "target": target,
        "ok": ok,
        "detail": detail,
        "status": status if isinstance(status, int) else None,
    }
    if read is None:
        body = answer.get("body")
        kept, cut = trimmed(body if isinstance(body, str) else None)
        return {**seen, "body": kept, "truncated": cut, "read": None}

    subject = subject_of(target) or "record"
    return {
        **seen,
        "body": None,
        # The reader's own word for it, so a page nobody can size is never
        # reported as a total. See `Answer.counted`.
        "truncated": read.truncated or len(read.sample) > K_SAMPLE,
        "read": {
            "rows": read.rows,
            "counted": read.counted,
            "partial": read.partial,
            "subject": subject,
            "sentence": read.sentence(subject),
            "columns": list(read.columns),
            "records": [dict(one) for one in read.sample[:K_SAMPLE]],
        },
    }


__all__ = ["K_ANSWER_CHARS", "K_SAMPLE", "as_seen", "subject_of", "trimmed"]
