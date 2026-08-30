"""Typed identifiers. See docs/01-architecture.md#tenancy."""

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


# Subclasses exist so mypy rejects a SkillId where a RecordingId belongs, and so
# ids of different kinds never compare equal at runtime.
class TenantId(Identifier): ...


class RecordingId(Identifier): ...


class SkillId(Identifier): ...


class PrincipalId(Identifier): ...


class DeviceId(Identifier):
    """One installed extension in one browser profile."""


class BatchId(Identifier):
    """Minted by the extension, not here: a retried upload must be recognised as
    the same batch rather than stored twice."""


class CandidateId(Identifier):
    """A task somebody keeps doing, noticed rather than reported."""


class TriggerId(Identifier):
    """What starts a run when nobody typed a sentence."""


class ConfirmationId(Identifier):
    """A fire waiting for somebody to say yes."""


class BrowserSessionId(Identifier):
    """Session in the browser provider. Owned by them, referenced by us."""
