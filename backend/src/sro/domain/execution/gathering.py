from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

K_ROUNDS = 6

K_PATIENCE_S = 45.0

K_NOTE = 240


K_HIT = 160

K_BODY = 1200


@dataclass(frozen=True, slots=True)
class Found:
    value: str
    from_message: str
    quoting: str = ""


@dataclass(frozen=True, slots=True)
class Gathered:
    values: Mapping[str, Found] = field(default_factory=dict)
    missing: tuple[str, ...] = ()

    looked: tuple[str, ...] = ()

    why: str = ""

    unasked: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.missing


def still_wanted(wanted: Sequence[str], found: Mapping[str, Found]) -> tuple[str, ...]:
    return tuple(name for name in wanted if name not in found)


def keep(values: Mapping[str, Found], wanted: Sequence[str]) -> dict[str, Found]:
    allowed = set(wanted)
    return {
        name: found
        for name, found in values.items()
        if name in allowed and found.value.strip() and found.from_message.strip()
    }


def dropped(values: Mapping[str, Found], wanted: Sequence[str]) -> tuple[str, ...]:
    allowed = set(wanted)
    return tuple(sorted(name for name in values if name not in allowed))


def note(what: str, answered: str) -> str:
    rows = _messages(answered)
    if rows is not None:
        return f"{what} -> " + (" | ".join(_row(row) for row in rows) if rows else "no messages")
    return f"{what} -> {_trimmed(answered, K_BODY if _is_a_message(answered) else K_NOTE)}"


def _messages(answered: str) -> list[dict[str, object]] | None:
    try:
        said = json.loads(answered)
    except ValueError:
        return None
    if not isinstance(said, dict) or not isinstance(rows := said.get("messages"), list):
        return None
    return [row for row in rows if isinstance(row, dict)]


def _is_a_message(answered: str) -> bool:
    try:
        said = json.loads(answered)
    except ValueError:
        return False
    return isinstance(said, dict) and "body" in said


def _row(row: Mapping[str, object]) -> str:
    said = " ".join(
        str(row.get(part) or "").strip() for part in ("id", "subject", "snippet", "body")
    )
    return _trimmed(said, K_HIT)


def _trimmed(said: str, cap: int) -> str:
    said = " ".join(said.split())
    return said if len(said) <= cap else said[:cap] + "…"
