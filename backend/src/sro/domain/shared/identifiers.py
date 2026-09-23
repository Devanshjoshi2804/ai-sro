from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Identifier:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise InvariantViolation(f"{type(self).__name__} cannot be blank")

    def __str__(self) -> str:
        return self.value


class TenantId(Identifier): ...


class RecordingId(Identifier): ...


class SkillId(Identifier): ...


class PrincipalId(Identifier): ...


class DeviceId(Identifier): ...


class BatchId(Identifier): ...


class CandidateId(Identifier): ...


class TriggerId(Identifier): ...


class ConfirmationId(Identifier): ...


class BrowserSessionId(Identifier): ...
