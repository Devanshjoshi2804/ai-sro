from __future__ import annotations

from typing import Protocol


class TokenSource(Protocol):
    async def establish(self, *, tenant: str, system: str, username: str, password: str) -> str: ...

    async def access_token(self, *, tenant: str, system: str) -> str | None: ...


class TokenRefused(Exception):
    code = "token_refused"
