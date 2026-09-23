from __future__ import annotations

import asyncio
import weakref

_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]] = (
    weakref.WeakKeyDictionary()
)


def one_at_a_time(name: str) -> asyncio.Lock:
    return _LOCKS.setdefault(asyncio.get_running_loop(), {}).setdefault(name, asyncio.Lock())
