from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

K_TELLING = 0.25

K_SHORT = 2

NOT_TELLING = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "was",
        "there",
        "that",
        "this",
        "with",
        "what",
        "which",
        "how",
        "many",
        "any",
        "does",
        "has",
        "have",
        "been",
        "called",
        "named",
        "show",
        "list",
        "get",
        "set",
        "all",
        "count",
        "from",
        "into",
        "exist",
        "exists",
        "please",
        "find",
        "look",
        "see",
    }
)


def asked_for(question: str) -> tuple[str, ...]:
    words = re.split(r"[^A-Za-z0-9]+", str(question or "").lower())
    return tuple(word for word in words if len(word) > K_SHORT and word not in NOT_TELLING)


def names(record: Mapping[str, object], words: Sequence[str]) -> bool:
    for value in record.values():
        if value is None or isinstance(value, dict | list):
            continue
        said = str(value).lower()
        if said and any(word in said for word in words):
            return True
    return False


def telling(words: Sequence[str], records: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    if not records:
        return tuple(words)
    most = max(1, int(len(records) * K_TELLING))
    kept = []
    for word in words:
        picks = sum(1 for record in records if names(record, (word,)))
        if 0 < picks <= most:
            kept.append(word)
    return tuple(kept)


def named(
    question: str, records: Sequence[Mapping[str, object]], subject: str = ""
) -> tuple[Mapping[str, object], ...]:
    of_the_set = set(asked_for(subject))
    words = telling(tuple(word for word in asked_for(question) if word not in of_the_set), records)
    if not words:
        return ()
    return tuple(record for record in records if names(record, words))


__all__ = ["K_SHORT", "K_TELLING", "NOT_TELLING", "asked_for", "named", "names", "telling"]
