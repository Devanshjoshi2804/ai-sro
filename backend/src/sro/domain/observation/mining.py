"""What one mining pass cost, kept apart from what it found."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MiningPass:
    """One reading of one tenant's day, and what it cost.

    A pass makes exactly one model call. Every workflow it found names this
    pass rather than carrying a copy of its bill: three workflows out of one
    $0.04 call summed to $0.12 when they each carried it.
    """

    id: str
    tenant: str
    started_at: str
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    """Inside out_tokens, not beside them."""

    cost_usd: float = 0.0
    unpriced: bool = False
    proposed: int = 0
    kept: int = 0
    rejected: int = 0
    coverage: float = 0.0
    skew: float = 0.0
    lopsided: bool = False
    error: str | None = None
    """Why it found nothing, when it found nothing for a reason the API gave.
    An honest zero and a refused call are the same row without this."""
