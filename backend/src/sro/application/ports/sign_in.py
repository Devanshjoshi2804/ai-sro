from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SignInResult:
    landed_at: str

    steps: tuple[str, ...]


class SignInDriver(Protocol):
    async def sign_in(
        self,
        *,
        debugger_url: str,
        url: str,
        username: str,
        password: str,
        choose: tuple[str, ...] = (),
        timeout_s: float = 90.0,
    ) -> SignInResult: ...


class SignInFailed(Exception):
    code = "sign_in_failed"


class CredentialsRefused(SignInFailed):
    code = "credentials_refused"
