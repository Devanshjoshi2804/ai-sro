"""Who is asking.

Until now the answer came from a header the caller wrote themselves, which
means the tenant boundary this system is built around was decoration: anybody
who could reach the port could read another customer's recordings and send
writes into their WMS under any name they liked.

The port is narrow because the surface that decides identity should be small
enough to read in one sitting. One thing turns a credential into a caller, and
one thing mints credentials, and they live behind this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import PrincipalId, TenantId


@dataclass(frozen=True, slots=True)
class Caller:
    tenant_id: TenantId
    principal_id: PrincipalId
    """The human or service the credential was issued to. This is what a write
    records as its authorisation -- never a name supplied in the request, which
    is a signature nobody checked."""


class CredentialRejected(Exception):
    """Not a valid credential: absent, expired, tampered with, or signed by a
    key this deployment does not hold. The reason is never narrowed for the
    caller, because the difference is only useful to somebody guessing."""


class Unconfigured(Exception):
    """This deployment cannot verify anybody. Distinct from a rejection: the
    fault is ours, the answer is 503, and it must never be read as permission."""


class Credentials(Protocol):
    def verify(self, presented: str) -> Caller:
        """The caller this credential belongs to, or raise."""
        ...

    def issue(self, caller: Caller, *, lasting_hours: float) -> str:
        """A credential for this caller. Used by the CLI that onboards someone,
        and by nothing that a request can reach."""
        ...
