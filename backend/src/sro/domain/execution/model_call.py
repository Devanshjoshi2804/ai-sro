from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.domain.execution.run import RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import TenantId


@dataclass(frozen=True, slots=True)
class ModelCall:
    id: str
    tenant_id: TenantId
    run_id: RunId
    step_index: int
    purpose: str

    destination: str
    model: str
    started_at: datetime
    duration_ms: int

    sent_bytes: int
    image_sent: bool
    redacted_fields: tuple[str, ...] = ()

    outcome: str = ""

    failed: bool = False

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise InvariantViolation("ModelCall.started_at must be timezone-aware")
        if self.step_index < 0:
            raise InvariantViolation("ModelCall.step_index must be non-negative")
