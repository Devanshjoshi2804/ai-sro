from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import PrincipalId, TenantId


@dataclass(frozen=True, slots=True)
class Caller:
    tenant_id: TenantId
    principal_id: PrincipalId


class CredentialRejected(Exception): ...


class Unconfigured(Exception): ...


class Credentials(Protocol):
    def verify(self, presented: str) -> Caller: ...

    def issue(self, caller: Caller, *, lasting_hours: float) -> str: ...
