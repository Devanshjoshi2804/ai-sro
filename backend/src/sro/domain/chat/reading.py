from __future__ import annotations

import secrets
from dataclasses import dataclass


def new_chat_id() -> str:
    return "cht_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class ChatReading:
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
