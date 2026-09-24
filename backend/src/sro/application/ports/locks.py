from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sro.domain.execution.account import Account


class AccountBusy(Exception):
    code = "account_busy"


class AccountLocks(Protocol):
    def hold(
        self, account: Account, *, on_wait: Callable[[], Awaitable[None]] = ...
    ) -> AbstractAsyncContextManager[None]: ...
