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

from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class Reading:
    """What a sentence means, before anything is matched against it.

    Reading English is what a model is for. Deciding what runs is not: the
    reading is proposed here and validated against the library that actually
    exists, exactly as a proposed gesture is executed against real locators.
    A reading that names a task nobody taught changes nothing.

    Everything this replaces was a list of phrases -- "how many", "which",
    "list all" -- and every such list is a guess about wording that the next
    sentence breaks. "Show the list of all transport_mode then" broke one.
    """

    wants: str = "act"
    """`ask` when the operator wants to be told something, `act` when they want
    something done. The difference decides whether a skill that writes may
    answer at all."""

    verb: str = ""
    """What they want done, in their words -- list, create, adjust, release."""

    entity: str = ""
    """What they want it done to."""

    continues: bool = False
    """Whether this sentence leans on the one before it for its subject, rather
    than naming one. "I want them in detail" continues; "show the list of all
    transport modes" does not, however conversational it sounds."""

    values: dict[str, str] = field(default_factory=dict)
    """Anything that looks like a value they supplied."""

    confidence: float = 0.0


class IntentParser(Protocol):
    @property
    def available(self) -> bool: ...

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        """Values for ``parameters``, as many sets as the sentence describes."""
        ...

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        """What the sentence means, given the one before it.

        Never what to run. The caller matches the reading against the skills
        that exist and refuses anything it cannot account for, so a confident
        misreading costs a clarifying question rather than a wrong write.
        """
        ...
