"""What the chat door read, and what the reading cost."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatReading:
    """One sentence the chat door read, and what the reading cost.

    The sentence is not kept: it is an operator's words about a warehouse,
    and the bill is what this record is for.
    """

    id: str
    tenant: str
    at: str
    workflow_id: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
