"""Induction failures. Messages are written for the operator deciding whether
to re-record, so they name the step and the disagreement."""

from __future__ import annotations

from sro.domain.shared.errors import DomainError


class InductionFailed(DomainError):
    code = "induction_failed"

    def __init__(self, message: str, *, step_index: int | None = None) -> None:
        location = f"step {step_index}: " if step_index is not None else ""
        super().__init__(f"{location}{message}")
        self.step_index = step_index
