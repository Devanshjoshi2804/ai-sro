from __future__ import annotations

from dataclasses import dataclass, field

K_WHY = 400

DONE = "done"
REFUSED = "refused"
FAILED = "failed"
NOTHING = "nothing"

OUTCOMES = frozenset({DONE, REFUSED, FAILED, NOTHING})


@dataclass(frozen=True, slots=True)
class Attempt:
    id: str
    tenant: str
    at: str

    asked_for: str

    came_of: str

    principal: str = ""

    why: str = ""

    about: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.came_of not in OUTCOMES:
            raise ValueError(f"{self.came_of!r} is not something an attempt can come to")


def as_row(attempt: Attempt) -> dict[str, object]:
    return {
        "id": attempt.id,
        "tenant_id": attempt.tenant,
        "at": attempt.at,
        "asked_for": attempt.asked_for[:K_WHY],
        "came_of": attempt.came_of,
        "principal": attempt.principal,
        "why": attempt.why.replace("\n", " ")[:K_WHY],
        "about": dict(attempt.about),
    }


__all__ = [
    "DONE",
    "FAILED",
    "K_WHY",
    "NOTHING",
    "OUTCOMES",
    "REFUSED",
    "Attempt",
    "as_row",
]
