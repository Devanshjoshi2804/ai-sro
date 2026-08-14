"""Turning a sentence into parameter values.

The model's whole job here is extraction: the skill is already chosen, its
parameters are already declared, and what remains is reading the values out of
what the operator wrote. It is never asked which skill to run, and it is never
allowed to invent a parameter -- both of those are decided against the library
before this is called.

"Update these six SKUs to the counts from this morning" is six parameter sets.
Getting that wrong is not a wrong answer, it is six wrong writes, so nothing it
returns is used without an operator confirming the table it produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Extraction:
    items: tuple[dict[str, str], ...] = ()
    """One parameter set per thing to do. Empty means the sentence named no
    values, which is a question back to the operator rather than a run."""

    missing: tuple[str, ...] = ()
    """Declared inputs the sentence did not supply."""

    note: str = ""
    """What the model could not resolve -- "this morning's count" needs a
    source it was not given."""


class IntentParser(Protocol):
    @property
    def available(self) -> bool: ...

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        """Values for ``parameters``, as many sets as the sentence describes."""
        ...
