"""One call to a hosted model, recorded whether or not it worked.

Written for the incident review that has not happened yet: which run, which
step, what left the deployment, what came back, and what was removed first. A
model call with no such record is a hole in the audit trail exactly where
somebody will look.
"""

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
    """What it was asked for -- ``propose_gesture``, ``transcribe`` -- not a prompt."""

    destination: str
    model: str
    started_at: datetime
    duration_ms: int

    sent_bytes: int
    image_sent: bool
    redacted_fields: tuple[str, ...] = ()
    """Field names removed before sending. Never their values."""

    outcome: str = ""
    """What came back, in one line: the proposed gesture, a refusal, or an error."""

    failed: bool = False

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise InvariantViolation("ModelCall.started_at must be timezone-aware")
        if self.step_index < 0:
            raise InvariantViolation("ModelCall.step_index must be non-negative")
