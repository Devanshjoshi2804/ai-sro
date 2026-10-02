"""The signed per-operator bearer an MCP connector accepts.

Nothing is looked up: the connector recomputes the MAC with the same key, so a
bearer exists only for an operator the backend has linked. The server name is in the
MAC input, so a bearer for one connector is refused by every other.
"""

from __future__ import annotations

import hashlib
import hmac


def _mac(key: str, server: str, tenant: str, operator: str) -> str:
    return hmac.new(
        key.encode(), f"{server}\n{tenant}\n{operator}".encode(), hashlib.sha256
    ).hexdigest()


def sign_bearer(key: str, server: str, tenant: str, operator: str) -> str:
    """`tenant` and `operator` must not hold ':' (application.integrations.end_user checks)."""
    return f"{tenant}:{operator}.{_mac(key, server, tenant, operator)}"


def verify_bearer(key: str, server: str, bearer: str) -> tuple[str, str] | None:
    """The (tenant, operator) the bearer was signed for, or None when it is not ours."""
    who, _, mac = bearer.rpartition(".")
    parts = who.split(":")
    if len(parts) != 2 or not all(parts):
        return None
    tenant, operator = parts
    if hmac.compare_digest(mac.encode(), _mac(key, server, tenant, operator).encode()):
        return tenant, operator
    return None
