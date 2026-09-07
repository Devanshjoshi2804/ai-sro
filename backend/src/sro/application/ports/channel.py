"""One command down, one answer back.

The extension dials out and the backend sends commands down the socket it
opened; there is no route that drives a browser, because one would let a
leaked device id reach a browser that is not the caller's.

This is the seam a run holds. ``AgentDrivers`` is the typed view of the same
sockets for the backend's own executor; a mined workflow sends the envelope
itself, because what it sends is what the demonstration recorded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sro.domain.shared.identifiers import DeviceId, TenantId


@dataclass(frozen=True, slots=True)
class Reply:
    ok: bool
    result: Mapping[str, object] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        """What went wrong, keeping the kind the extension named."""
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class Channel(Protocol):
    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply: ...

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]: ...

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool: ...
