"""Expired confirmations are expired by the worker, not left listed.

`ExpireConfirmations` had no caller, so a card nobody answered in its window
stayed in the waiting list forever. The session keeper's loop already wakes
every few minutes for the whole deployment; expiring cards rides on it.
"""

from __future__ import annotations

import asyncio
import contextlib

from sro.application.connection.keep_open import Swept
from sro.infrastructure.temporal.worker import keep_sessions_open


class _Keeper:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def sweep(self) -> Swept:
        self._calls.append("swept")
        return Swept()


class _Expirer:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def execute(self) -> dict[str, int]:
        self._calls.append("expired")
        return {"acme": 1}


class _Container:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def keep_sessions_open(self) -> _Keeper:
        return _Keeper(self.calls)

    def expire_confirmations(self) -> _Expirer:
        return _Expirer(self.calls)


async def test_each_pass_of_the_keeper_expires_the_late_cards() -> None:
    container = _Container()

    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(keep_sessions_open(container, 0.001), timeout=0.1)

    assert container.calls[:2] == ["expired", "swept"], container.calls


async def test_a_failing_expiry_does_not_stop_the_keeper() -> None:
    class _Broken(_Container):
        def expire_confirmations(self) -> _Expirer:
            self.calls.append("tried")
            raise RuntimeError("the database went away")

    container = _Broken()

    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(keep_sessions_open(container, 0.001), timeout=0.1)

    # The session sweep still ran after the expiry raised, on every pass.
    assert container.calls[:4] == ["tried", "swept", "tried", "swept"], container.calls
