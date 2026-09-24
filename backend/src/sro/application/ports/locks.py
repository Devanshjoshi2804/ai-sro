from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sro.domain.execution.account import Account


class AccountLocks(Protocol):
    def hold(self, account: Account) -> AbstractAsyncContextManager[None]: ...
