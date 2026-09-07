"""What a model call costs, and what it answered.

The prices are dollars per million tokens; a model missing from the table is
unpriced, never free.
"""

from dataclasses import dataclass
from typing import Literal

# Dollars per million tokens, (input, output).
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),  # introductory, to 2026-12-31
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),  # doubles to (4, 18) above 200K
    # A preview is priced like the model it previews. Without these rows a real
    # pass on a preview name records cost_usd 0.0 with unpriced=True -- which is
    # honest, and useless: the measurement run that proved this architecture
    # works billed $1.12 and every row said free. A name missing from this table
    # is the one failure mode `unpriced` cannot fix, because nothing downstream
    # can price a call the table never knew about.
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3-flash-preview": (0.50, 3.00),
    "gemini-3.8-flash-preview": (0.75, 3.75),
}

LONG_PROMPT_TOKENS = 200_000

# Above a 200K-token prompt, Gemini 3.1 Pro's rates double.
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


# The levels the SDK accepts. Narrowed to a Literal rather than left as str
# because google-genai does not reject an unknown one: ThinkingLevel("nonsense")
# returns a pseudo-member carrying the typo straight to the API on 2.22.0. A
# constant that silently means "model default" is the exact failure wiring
# K_EFFORT was meant to close, one layer down, so mypy catches it instead.
Effort = Literal["minimal", "low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class DaySpend:
    """What one tenant has been billed for since midnight UTC.

    ``blind`` is read beside the sum rather than derived from it, because the
    two say different things and only one of them can be trusted: a model name
    the price table never knew about records $0.0000 with ``unpriced`` set, so
    a day summed on ``cost_usd`` alone reads as free while it spends. A day
    whose cost cannot be established is not a cheap day, and the rule that
    judges this pair says so.
    """

    cost_usd: float
    blind: int


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, object] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    # Part of out_tokens for pricing, kept separately so a reader can see how
    # much of the bill was reasoning nobody ever read.
    thought_tokens: int = 0
    cost_usd: float = 0.0
    # True when cost_usd cannot be trusted: the model is missing from PRICES,
    # or the SDK did not give back real usage counts. A $0.00 row and an
    # honestly-unpriced row look the same in cost_usd alone -- this is what
    # tells them apart.
    unpriced: bool = False
    error: str | None = None
