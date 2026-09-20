"""One system's answer to one lookup, small enough to keep and still itself.

An answer is read in three places -- the panel's card, the conversation, and
whatever model is asked to make sense of it -- and each of them parses it. So
the shaping belongs here, once, rather than at whichever door happens to be
sending it: a body trimmed one way for the wire and another way for a thread
is two answers to the same question.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

K_ANSWER_CHARS = 64 * 1024
"""How much of one system's answer travels.

The extension already caps a response body at 1MB. This is smaller because
four systems answering at that size is a four-megabyte answer to a question
somebody typed, and the part that answers "which suppliers are at SG" is at
the front."""

K_ANSWER_ROWS = 40
"""How many records survive a trim, when the answer is records.

A cut at a character count leaves BROKEN JSON, and broken JSON is not a
shorter answer -- it is a different kind of thing. Everything downstream
parses the body: `result.js` reads `data` to draw a count and a table, and
falls back to 240 characters of raw preview when the parse fails.

Measured on the deployment 2026-09-21: asked "is there a customer type called
KKYT", the lookup planned the right call, the warehouse answered 200 with
fifty customer types of forty fields each, the body went past 64KB, and the
panel showed

    {"@type":"ResponseBodyWrapper","data":[{"URNFormat":null,"absoluteGrou…

which answers nothing and never reaches the row the question was about.

So a body that IS records is trimmed BY RECORD and stays valid JSON. Forty is
five times what the panel draws and enough to see the shape; past that, the
question wanted a filter rather than a page."""


def trimmed(text: str | None) -> tuple[str | None, bool]:
    """The body, small enough to send, and whether anything was left behind.

    By record where it is records. Falls back to the character cut for a body
    that is not a list of them -- a page of HTML, one object, a picture --
    because there is nothing structural to preserve in those.
    """
    if text is None or len(text) <= K_ANSWER_CHARS:
        return text, False
    try:
        said = json.loads(text)
    except ValueError:
        return text[:K_ANSWER_CHARS], True
    rows = said.get("data") if isinstance(said, dict) else said
    if not isinstance(rows, list) or len(rows) <= K_ANSWER_ROWS:
        return text[:K_ANSWER_CHARS], True
    fewer = rows[:K_ANSWER_ROWS]
    return json.dumps({**said, "data": fewer} if isinstance(said, dict) else fewer), True


def as_seen(
    *, system: str, target: str, ok: bool, detail: str, answer: Mapping[str, object]
) -> dict[str, object]:
    """One answer, in the shape every surface draws it from.

    The picture a screen lookup takes is deliberately not here: it is hundreds
    of kilobytes of base64, and what a picture MEANS is a model's question.
    """
    body = answer.get("body")
    kept, cut = trimmed(body if isinstance(body, str) else None)
    status = answer.get("status")
    return {
        "system": system,
        "target": target,
        "ok": ok,
        "detail": detail,
        "status": status if isinstance(status, int) else None,
        "body": kept,
        "truncated": cut,
    }


__all__ = ["K_ANSWER_CHARS", "K_ANSWER_ROWS", "as_seen", "trimmed"]
