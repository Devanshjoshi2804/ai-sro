from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from sro.application.execution.answer import Answer
from sro.application.lookup.naming import named

K_ANSWER_CHARS = 64 * 1024

K_SAMPLE = 200


def subject_of(target: str) -> str:
    last = [part for part in str(target or "").split("/") if part and "#" not in part]
    if not last:
        return ""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", last[-1]).lower().replace("_", " ").strip()
    if not words or not re.fullmatch(r"[a-z0-9 ]+", words):
        return ""
    return re.sub(r"ies$", "y", words) if words.endswith("ies") else words.removesuffix("s")


def trimmed(text: str | None) -> tuple[str | None, bool]:
    if text is None or len(text) <= K_ANSWER_CHARS:
        return text, False
    return text[:K_ANSWER_CHARS], True


def _found(subject: str, matched: Sequence[Mapping[str, object]], of: int | None) -> str:
    if not matched:
        return f"No {subject} matched that."
    shown = ", ".join(_describes(one) for one in matched[:3])
    if len(matched) == 1:
        rest = f" (of {of} {subject})" if of and of > 1 else ""
        return f"Yes — {shown}{rest}."
    more = len(matched) - min(3, len(matched))
    tail = f", and {more} more" if more > 0 else ""
    return f"{len(matched)} {subject} matched: {shown}{tail}."


def _describes(record: Mapping[str, object]) -> str:
    values = [str(value) for value in record.values() if str(value or "").strip()]
    if not values:
        return "(unnamed)"
    return values[0] if len(values) == 1 else f"{values[0]} ({values[1]})"


def existence(find: str, subject: str, read: Answer | None) -> str:
    """Yes on a record whose value equals `find`; no only off a whole list; else unsure."""
    if read is None:
        return f"I could not tell whether {subject} {find} exists: that read held no records."
    wanted = find.casefold()
    for one in read.sample:
        if any(value.casefold() == wanted for value in one.values()):
            return f"Yes, {subject} {find} exists: {_describes(one)}."
    whole = not read.partial and not read.truncated and read.counted == len(read.sample)
    if not whole:
        return f"I could not tell whether {subject} {find} exists: only part of the list was read."
    return f"No, none of the {read.rows} {subject}s is {find}."


def as_seen(
    *,
    system: str,
    target: str,
    ok: bool,
    detail: str,
    answer: Mapping[str, object],
    read: Answer | None = None,
    question: str = "",
) -> dict[str, object]:
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
    every = [dict(one) for one in read.sample]
    matched = [dict(one) for one in named(question, every, subject)] if question else []
    shown = matched or every
    rest = [one for one in every if one not in shown][: max(0, K_SAMPLE - len(shown))]
    return {
        **seen,
        "body": None,
        "truncated": read.truncated or len(every) > K_SAMPLE,
        "read": {
            "rows": read.rows,
            "counted": read.counted,
            "partial": read.partial,
            "subject": subject,
            "sentence": (
                _found(subject, matched, read.counted) if matched else read.sentence(subject)
            ),
            "columns": list(read.columns),
            "records": [dict(one) for one in shown[:K_SAMPLE]],
            "rest": [dict(one) for one in rest] if matched else [],
            "matched": len(matched),
            "of": read.counted,
        },
    }


__all__ = ["K_ANSWER_CHARS", "K_SAMPLE", "as_seen", "existence", "subject_of", "trimmed"]
