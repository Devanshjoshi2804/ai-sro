"""The signed per-operator bearer an MCP connector accepts.

Nothing is looked up: the connector recomputes the MAC with the same key, so a
bearer exists only for an operator the backend has linked. The server name is in the
MAC input, so a bearer for one connector is refused by every other.
"""

from __future__ import annotations

import hashlib
import hmac

from sro.domain.shared.errors import InvariantViolation


def _mac(key: str, server: str, tenant: str, operator: str) -> str:
    """Each part is length-prefixed, so no two different triples share one MAC input."""
    if not key:
        raise InvariantViolation("A connector bearer needs a signing key")
    data = "".join(f"{len(part)}:{part}" for part in (server, tenant, operator))
    return hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()


def _plain(*parts: str) -> bool:
    """':' splits the bearer; control characters have no place in an id."""
    return all(p and ":" not in p and p.isprintable() for p in parts)


def sign_bearer(key: str, server: str, tenant: str, operator: str) -> str:
    if not _plain(server, tenant, operator):
        raise InvariantViolation("A bearer's server, tenant and operator must be plain text")
    return f"{tenant}:{operator}.{_mac(key, server, tenant, operator)}"


def verify_bearer(key: str, server: str, bearer: str) -> tuple[str, str] | None:
    """The (tenant, operator) the bearer was signed for, or None when it is not ours."""
    who, _, mac = bearer.rpartition(".")
    parts = who.split(":")
    if not key or len(parts) != 2 or not _plain(server, *parts):
        return None
    tenant, operator = parts
    if hmac.compare_digest(mac.encode(), _mac(key, server, tenant, operator).encode()):
        return tenant, operator
    return None
