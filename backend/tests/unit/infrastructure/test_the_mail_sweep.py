"""The mail poll's loop and its switch, with a container that must not be touched."""

from __future__ import annotations

import asyncio
from typing import NoReturn

from sro.config import Settings
from sro.infrastructure.temporal.worker import look_in_the_mail_lately


class _Untouchable:
    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"the poll is off and still reached for {name}()")


async def test_a_mail_sweep_of_zero_seconds_returns_instead_of_looping() -> None:
    await asyncio.wait_for(look_in_the_mail_lately(_Untouchable(), 0.0), timeout=1.0)


def test_the_mail_is_polled_as_often_as_the_heartbeat_looks() -> None:
    assert Settings(_env_file=None).mail_sweep_seconds == 60.0
