from __future__ import annotations

import time
from dataclasses import dataclass

K_HELD_FOR = 15 * 60.0


@dataclass(frozen=True, slots=True)
class _Held:
    value: str
    run_id: str
    until: float


class OneTimeSecrets:
    def __init__(self) -> None:
        self._held: dict[str, _Held] = {}

    def hold(self, key: str, value: str, *, run_id: str, now: float | None = None) -> float:
        at = time.time() if now is None else now
        self._sweep(at)
        until = at + K_HELD_FOR
        self._held[key] = _Held(value=value, run_id=run_id, until=until)
        return until

    def take(self, key: str, *, run_id: str, now: float | None = None) -> str | None:
        at = time.time() if now is None else now
        self._sweep(at)
        found = self._held.get(key)
        if found is None or found.run_id != run_id:
            return None
        del self._held[key]
        return found.value

    def waiting(self, key: str, *, now: float | None = None) -> bool:
        at = time.time() if now is None else now
        found = self._held.get(key)
        return found is not None and found.until > at

    def forget_everything(self) -> None:
        self._held.clear()

    def _sweep(self, at: float) -> None:
        expired = [key for key, held in self._held.items() if held.until <= at]
        for key in expired:
            del self._held[key]
