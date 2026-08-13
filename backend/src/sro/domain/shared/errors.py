"""Error types raised by the domain and application layers."""

from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"


class InvariantViolation(DomainError):
    """An operation would leave an entity in a state it forbids."""

    code = "invariant_violation"


class NotFound(DomainError):
    """Entity does not exist, or belongs to another tenant.

    The two cases are deliberately indistinguishable: distinguishing them would
    confirm that an id exists in some other tenant.
    """

    code = "not_found"


class Conflict(DomainError):
    """Valid request that conflicts with current state."""

    code = "conflict"
