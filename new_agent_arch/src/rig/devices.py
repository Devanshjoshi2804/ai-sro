"""One token per browser.

The rig had one bearer for everything: the extension's ingest, its command
socket, the page, a curl. That is a tenant's secret in every browser, and a
call that cannot say which browser made it. A registered device holds a
token of its own -- minted once against the tenant's bearer, stored here as
a hash, revocable by that bearer -- and every route that takes it learns the
device id for free. The tenant's bearer keeps working; nothing that dials
with it breaks.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from rig.store import Store

PREFIX = "dev_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(store: Store, device_id: str) -> str:
    """A fresh token for this device; any earlier one stops working."""
    token = PREFIX + secrets.token_hex(24)
    store.execute(
        "INSERT OR REPLACE INTO device_tokens (device_id, token_hash, issued_at, revoked_at)"
        " VALUES (?, ?, ?, NULL)",
        (device_id, _hash(token), datetime.now(tz=UTC).isoformat()),
    )
    return token


def holder(store: Store, token: str) -> str | None:
    """The device this token belongs to, or None for an unknown or revoked one."""
    if not token.startswith(PREFIX):
        return None
    rows = store.query(
        "SELECT device_id FROM device_tokens WHERE token_hash = ? AND revoked_at IS NULL",
        (_hash(token),),
    )
    return str(rows[0]["device_id"]) if rows else None


def revoke(store: Store, device_id: str) -> bool:
    """Whether there was a live token to revoke."""
    with store.connect() as connection:
        changed = connection.execute(
            "UPDATE device_tokens SET revoked_at = ? WHERE device_id = ? AND revoked_at IS NULL",
            (datetime.now(tz=UTC).isoformat(), device_id),
        ).rowcount
    return bool(changed)
