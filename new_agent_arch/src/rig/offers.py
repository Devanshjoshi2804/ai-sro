"""What was offered, and what became of it.

Written by the extension, which made the offer, over `POST /v1/offers`. Read
by nobody yet: this is the labelled record of whether recognition was right,
and the share of `diverged` is what decides whether `K_OFFER_AFTER` moves.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from rig.store import Store

FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")
"""accepted: Yes was pressed and a run started. dismissed: No thanks. did_it:
the operator made the workflow's write themselves while it asked. expired: the
nudge's lifetime passed. diverged: the tail stopped matching the prefix."""


def record_offer(
    store: Store,
    *,
    tenant: str,
    workflow_id: str,
    k: int,
    fate: str,
    run_id: str | None,
    device_id: str,
    at: str,
) -> str:
    if fate not in FATES:
        raise ValueError(f"{fate!r} is not a fate an offer can have")
    # The browser's clock, in whatever form it wrote it (`toISOString` says
    # `Z`); stored the way every server row is, so `since` compares.
    when = datetime.fromisoformat(at)
    at = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC).isoformat()
    offer_id = "off_" + secrets.token_hex(8)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO offers (id, tenant, workflow_id, device_id, k, fate, run_id, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (offer_id, tenant, workflow_id, device_id, k, fate, run_id, at),
        )
    return offer_id
