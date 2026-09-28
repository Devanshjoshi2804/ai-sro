from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3-flash-preview": (0.50, 3.00),
    "gemini-3.8-flash-preview": (0.75, 3.75),
    "gemini-embedding-001": (0.15, 0.00),
    "gemini-embedding-2": (0.20, 0.00),
}

LONG_PROMPT_TOKENS = 200_000

LONG_PROMPT_PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.1-pro": (4.00, 18.00),
    "gemini-3.1-pro-preview": (4.00, 18.00),
}


def price(model: str, in_tokens: int, out_tokens: int) -> float:
    rates = PRICES.get(model)
    if rates is None:
        return 0.0
    if in_tokens > LONG_PROMPT_TOKENS:
        rates = LONG_PROMPT_PRICES.get(model, rates)
    return in_tokens * rates[0] / 1_000_000 + out_tokens * rates[1] / 1_000_000


def is_priced(model: str) -> bool:
    return model in PRICES


Effort = Literal["minimal", "low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class DaySpend:
    cost_usd: float
    blind: int


@dataclass(frozen=True, slots=True)
class ModelSpend:
    id: str
    tenant: str
    model: str
    at: datetime
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, object] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    truncated: bool = False

    unpriced: bool = False
    error: str | None = None
    dropped: int = 0
    fell_back: bool = False
    malformed: bool = False
