from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from sro.application.ports.vault import CredentialVault

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


class HeldForTheRun:
    """A password lent "just this once" for one Steel run, held where every process of
    this deployment reads it: the vault, under a key of that run's own, never the
    credential's own key. The api takes the answer and the worker signs the run in, so
    a value held in one process's memory never reached the sign-in. Taken exactly once,
    and gone after K_HELD_FOR whether taken or not."""

    def __init__(self, vault: CredentialVault, *, clock: Callable[[], float] = time.time) -> None:
        self._vault = vault
        self._clock = clock

    async def hold(self, key: str, value: str, *, run_id: str) -> float:
        until = self._clock() + K_HELD_FOR
        await self._vault.store(_lent(key, run_id), json.dumps({"value": value, "until": until}))
        return until

    async def take(self, key: str, *, run_id: str) -> str | None:
        said = await self._vault.get(_lent(key, run_id))
        if not said:
            return None
        await self._vault.delete(_lent(key, run_id))
        try:
            held = json.loads(said)
            value, until = str(held["value"]), float(held["until"])
        except (ValueError, KeyError, TypeError):
            return None
        return value if until > self._clock() else None


def _lent(key: str, run_id: str) -> str:
    return f"{key}#lent:{run_id}"
