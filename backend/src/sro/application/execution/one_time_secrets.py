from __future__ import annotations

import time
from dataclasses import dataclass

K_HELD_FOR = 15 * 60.0


@dataclass(frozen=True, slots=True)
class _Held:
    value: str
    until: float


class OneTimeSecrets:
    def __init__(self) -> None:
        self._held: dict[tuple[str, str], _Held] = {}

    def hold(self, key: str, value: str, *, run_id: str, now: float | None = None) -> float:
        at = time.time() if now is None else now
        self._sweep(at)
        until = at + K_HELD_FOR
        self._held[(key, run_id)] = _Held(value=value, until=until)
        return until

    def take(self, key: str, *, run_id: str, now: float | None = None) -> str | None:
        at = time.time() if now is None else now
        self._sweep(at)
        found = self._held.pop((key, run_id), None)
        return None if found is None else found.value

    def waiting(self, key: str, *, run_id: str, now: float | None = None) -> bool:
        at = time.time() if now is None else now
        found = self._held.get((key, run_id))
        return found is not None and found.until > at

    def forget_everything(self) -> None:
        self._held.clear()

    def _sweep(self, at: float) -> None:
        expired = [k for k, held in self._held.items() if held.until <= at]
        for k in expired:
            del self._held[k]
