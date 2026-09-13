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
    learned_parameters: int = 0
    """Parameters this pass added to jobs it had seen before.

    Kept apart from `kept`, because they answer different questions: `kept` is
    what the pass recognised, this is what it LEARNT. A pass that recognises
    nothing new and widens two parameters did real work, and without this the
    row says it did nothing.

    It is also the only figure that can say whether parameter learning is
    getting better. `MineResult` computed it from the first day and the row had
    nowhere to put it, so a pass that learnt three left no record it had --
    measured on 2026-09-09, when the second pass over the real store learnt
    exactly that and the only place the number appeared was a return value in
    a terminal. The rig has the same gap; this is not a port regression, it is
    an inherited one that had to stop here to be measurable at all.
    """
    coverage: float = 0.0
    skew: float = 0.0
    lopsided: bool = False

    window_size: int = 0
    left_out: int = 0
    """How much evidence this pass was shown, and how much the budget dropped.

    Beside `coverage`, which is a different question: coverage says where the
    pass's citations fell WITHIN its window, and these say how much of the
    tenant there was to put in one. A pass that left nothing out has read
    everything there was; one that left evidence out has more to say about
    evidence that has not changed, which is what the scheduled sweep reads to
    decide whether to pay for another pass."""
    error: str | None = None
    """Why it found nothing, when it found nothing for a reason the API gave.
    An honest zero and a refused call are the same row without this."""
