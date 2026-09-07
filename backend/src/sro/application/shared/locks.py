"""One pass at a time, per event loop.

A lock that outlives the loop it was made for is not a lock, it is an
exception waiting for the next loop.
"""

from __future__ import annotations

import asyncio
import weakref

_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]] = (
    weakref.WeakKeyDictionary()
)


def one_at_a_time(name: str) -> asyncio.Lock:
    """The named lock belonging to the running event loop, made on first use.

    A module-level `asyncio.Lock()` binds to whichever loop first touches it and
    raises `Lock is bound to a different event loop` for every loop after --
    which is what `api._reading` and `mine._mining` were, and what broke the
    moment the suite ran in more than one shard. Latent in production
    too: any process that restarts its loop, and any test runner that gives each
    test its own, hits the same wall.

    Keyed weakly, so a finished loop takes its locks with it rather than pinning
    them for the life of the process.
    """
    return _LOCKS.setdefault(asyncio.get_running_loop(), {}).setdefault(name, asyncio.Lock())
