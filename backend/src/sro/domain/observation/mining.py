from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MiningPass:
    id: str
    tenant: str
    started_at: str
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0

    cost_usd: float = 0.0
    unpriced: bool = False
    proposed: int = 0
    kept: int = 0
    rejected: int = 0
    learned_parameters: int = 0
    coverage: float = 0.0
    skew: float = 0.0
    lopsided: bool = False

    window_size: int = 0
    left_out: int = 0
    unplaced: int = 0

    error: str | None = None
