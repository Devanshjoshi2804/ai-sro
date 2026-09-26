from __future__ import annotations

from sro.domain.chat.asking import Pending

K_ONE_WORD = 60

K_SENTENCE = "?!,;:"

K_PROSE = 200


def plainly_a_value(pending: Pending, said: str) -> bool:
    value = said.strip()
    if not value:
        return False
    holds = pending.limits.get(pending.asking_for)
    if holds is not None and holds >= K_PROSE:
        return len(value) <= holds and "?" not in value
    if len(value.split()) != 1 or len(value) > K_ONE_WORD:
        return False
    if any(mark in value for mark in K_SENTENCE):
        return False
    return holds is None or len(value) <= holds


K_SAID_AS = (":", "=")


def said_as_the_value(pending: Pending, said: str) -> str | None:
    value = said.strip()
    for mark in K_SAID_AS:
        head, found, rest = value.partition(mark)
        if not found:
            continue
        return rest.strip() or None if _plainly(head) == _plainly(pending.asking_for) else None
    return None


def _plainly(name: str) -> str:
    return " ".join(name.replace("_", " ").replace("-", " ").lower().split())


__all__ = [
    "K_ONE_WORD",
    "K_PROSE",
    "K_SAID_AS",
    "plainly_a_value",
    "said_as_the_value",
]
