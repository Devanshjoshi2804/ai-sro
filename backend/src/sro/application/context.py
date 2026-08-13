"""Caller identity passed to every use case."""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.identifiers import PrincipalId, TenantId


@dataclass(frozen=True, slots=True)
class RequestContext:
    tenant_id: TenantId
    principal_id: PrincipalId
