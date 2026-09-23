from __future__ import annotations

import time
from dataclasses import dataclass

K_HELD_FOR = 15 * 60.0


@dataclass(frozen=True, slots=True)
class _Held:
    value: str
    until: float


_held: dict[str, _Held] = {}


def hold(key: str, value: str, *, now: float | None = None) -> float:
    at = time.time() if now is None else now
    until = at + K_HELD_FOR
    _held[key] = _Held(value=value, until=until)
    return until


def take(key: str, *, now: float | None = None) -> str | None:
    at = time.time() if now is None else now
    found = _held.pop(key, None)
    if found is None:
        return None
    if found.until <= at:
        return None
    return found.value


def waiting(key: str, *, now: float | None = None) -> bool:
    at = time.time() if now is None else now
    found = _held.get(key)
    return found is not None and found.until > at


def forget_everything() -> None:
    _held.clear()
