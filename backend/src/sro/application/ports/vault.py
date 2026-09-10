"""Where secrets live.

Nothing in the evidence plane, the skill plane or a log ever holds a credential
value. They hold a *key* into this, and the value is fetched at the moment it is
needed. That is what makes a recording safe to keep and a skill safe to share
between sites.
"""

from __future__ import annotations

from typing import Protocol


class CredentialVault(Protocol):
    async def store(self, key: str, value: str) -> None:
        """Write a secret. Overwrites: rotation is an ordinary event."""
        ...

    async def get(self, key: str) -> str | None:
        """Read a secret. ``None`` when absent -- callers decide what that means."""
        ...

    async def delete(self, key: str) -> None:
        """Idempotent: deleting an absent key is success, not an error."""
        ...


class VaultUnavailable(Exception):
    """No usable secret store. Not a ``DomainError``: the request was fine.

    Raised rather than falling back to plaintext. A vault that quietly degrades
    into a file of readable passwords is worse than one that refuses to start,
    because nothing downstream can tell the difference.
    """

    code = "no_vault"
