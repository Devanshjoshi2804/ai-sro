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


def _hits(find: str, read: Answer | None) -> list[tuple[int, str]]:
    """(record, column) for every full record holding a value equal to `find`."""
    wanted = find.strip().casefold()
    found: list[tuple[int, str]] = []
    for at, record in enumerate(read.records if read else ()):
        column = next((key for key, value in record.items() if value.casefold() == wanted), None)
        if column is not None:
            found.append((at, column))
    return found


def _whole(read: Answer) -> bool:
    return not read.partial and read.counted == len(read.records)


def existence(find: str, subject: str, read: Answer | None) -> str:
    """Yes on a record whose value equals `find`; no only off a whole list; else unsure."""
    return existence_across(find, [(subject, read)])


def existence_across(find: str, reads: Sequence[tuple[str, Answer | None]]) -> str:
    """One verdict over every read that could hold `find` (a failed one is a None)."""
    for subject, read in reads:
        if read is not None and (hit := next(iter(_hits(find, read)), None)):
            at, column = hit
            shown = _describes(read.sample[at]) if at < len(read.sample) else find
            return f"Yes, {subject} {find} exists ({column}): {shown}."
    subject = reads[0][0]
    if any(read is None for _, read in reads):
        return f"I could not tell whether {subject} {find} exists: a read held no records."
    if not all(read is not None and _whole(read) for _, read in reads):
        return f"I could not tell whether {subject} {find} exists: only part of the list was read."
    count = sum(len(read.records) for _, read in reads if read is not None)
    return f"No, none of the {count} {subject} records is {find}."


def as_seen(
    *,
    system: str,
    target: str,
    ok: bool,
    detail: str,
    answer: Mapping[str, object],
    read: Answer | None = None,
    question: str = "",
    find: str = "",
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
    matched: list[dict[str, object]]
    if find:
        matched = [dict(every[at]) for at, _ in _hits(find, read) if at < len(every)]
    else:
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
                existence(find, subject, read)
                if find
                else _found(subject, matched, read.counted)
                if matched
                else read.sentence(subject)
            ),
            "columns": list(read.columns),
            "records": [dict(one) for one in shown[:K_SAMPLE]],
            "rest": [dict(one) for one in rest] if matched else [],
            "matched": len(matched),
            "of": read.counted,
        },
    }


__all__ = ["K_ANSWER_CHARS", "K_SAMPLE", "as_seen", "existence", "subject_of", "trimmed"]
