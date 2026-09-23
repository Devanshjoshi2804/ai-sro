from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"


class InvariantViolation(DomainError):
    code = "invariant_violation"


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"
