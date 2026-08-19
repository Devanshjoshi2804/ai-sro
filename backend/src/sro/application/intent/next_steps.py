"""What to ask next, worked out rather than written into the console.

The chips under a result used to be three sentences hard-coded in the browser:
"show me one X in detail", "create a new X", "which X are used for parcel". The
last one was written for a transport-mode demo and then offered under every
result in the system, including for entities where nothing can answer it. A
suggestion the system cannot act on is worse than no suggestion: it advertises
a capability that does not exist and teaches operators to distrust the ones
that do.

So a suggestion has to be earned, the same way everything else here is:

- **a taught skill for this entity** can obviously be asked for, by name;
- **a column in the answer with a handful of values** can be filtered on,
  because the narrowing path composes exactly that request and the values come
  from records this system just read;
- **an identifying column** can be asked about one record at a time.

The model's job is the wording -- turning `smallPackageFlag=Y` into something a
warehouse says out loud. It cannot add a suggestion, remove one, or change what
any of them will do: every phrasing is checked against the evidence that
produced it, and anything that drifts falls back to the plain wording.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.intent import IntentParser
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind
from sro.domain.skill.skill import Skill

MOST = 3
"""Three. A row of chips is a nudge, not a menu."""

ENOUGH_TO_FILTER = 2
TOO_MANY_TO_FILTER = 8
"""A column worth offering as a filter has a few values, not one and not forty:
one is not a choice, and forty is a list nobody scans."""


@dataclass(frozen=True, slots=True)
class Suggestion:
    text: str
    because: str
    """What makes this answerable. Never shown as a caption -- it is here so a
    suggestion cannot exist without evidence behind it."""


class SuggestNext:
    def __init__(self, uow: UnitOfWork, parser: IntentParser | None) -> None:
        self._uow = uow
        self._parser = parser

    async def after(
        self,
        ctx: RequestContext,
        *,
        system: str,
        entity: str,
        values: dict[str, tuple[str, ...]],
        rows: int,
    ) -> tuple[str, ...]:
        """Follow-ups this system can actually answer, best first."""
        candidates = [
            *await self._other_skills(ctx, system=system, entity=entity),
            *self._filters(entity, values, rows),
        ]
        if not candidates:
            return ()

        labels = await self._labels(ctx, system=system, entity=entity)
        return tuple(found.text for found in await self._phrase(candidates[:MOST], entity, labels))

    async def _other_skills(
        self, ctx: RequestContext, *, system: str, entity: str
    ) -> list[Suggestion]:
        """Things somebody taught for this entity, other than reading it."""
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=200)
        return [
            Suggestion(
                text=_plainly(skill),
                because=f"{skill.name} is taught for this entity",
            )
            for skill in skills
            if _about(skill, system, entity) and skill.objective_key.objective_type != "list"
        ][:2]

    def _filters(
        self, entity: str, values: dict[str, tuple[str, ...]], rows: int
    ) -> list[Suggestion]:
        """Narrowings the data itself supports.

        Every one of these is a request the composing path can build, because
        the column and the value both came out of the answer being suggested
        under.
        """
        found: list[Suggestion] = []
        for column, held in values.items():
            if not (ENOUGH_TO_FILTER <= len(held) <= TOO_MANY_TO_FILTER):
                continue
            if len(held) >= rows > 0:
                # As many values as records: an identifier, not a category.
                continue
            found.append(
                Suggestion(
                    # "Which supplier records have countryName CAN" rather
                    # than "which supplier have": grammatical without guessing
                    # at a plural, and still the operator's own vocabulary.
                    text=f"which {entity.replace('_', ' ')} records have {column} {held[0]}",
                    because=f"{column} holds {', '.join(held[:3])} in these records",
                )
            )
        return found[:2]

    async def _labels(self, ctx: RequestContext, *, system: str, entity: str) -> dict[str, str]:
        """What the screens call these fields, so a chip reads like the screen."""
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, system=system, kinds=(EntryKind.FIELD,), terms=entity, limit=40
            )
        return {entry.key: entry.title or entry.key for entry in found}

    async def _phrase(
        self, candidates: list[Suggestion], entity: str, labels: dict[str, str]
    ) -> list[Suggestion]:
        """The same suggestions, in words a warehouse uses.

        Checked, not trusted: a phrasing that drops the value or the entity is
        no longer the suggestion that was earned, and the plain wording is used
        instead. The model never decides what is offered -- only how it reads.
        """
        if self._parser is None or not self._parser.available or not candidates:
            return candidates

        wanted = tuple(f"suggestion_{index}" for index, _ in enumerate(candidates))
        # The wording only. The reason each one is answerable is not part of
        # what the model sees, because the last version put it in the chip.
        described = "; ".join(
            f"{name}: {found.text}" for name, found in zip(wanted, candidates, strict=True)
        )
        vocabulary = ", ".join(
            f"{key} is called {label}" for key, label in list(labels.items())[:12]
        )
        try:
            extraction = await self._parser.extract(
                f"Rewrite each of these as a short request a warehouse operator would type "
                f"about {entity}. Keep every value exactly as it appears. {described}",
                parameters=wanted,
                context=f"Field names on the screen: {vocabulary}" if vocabulary else "",
            )
        except Exception:  # pragma: no cover - a phrasing failure is not an outage
            return candidates

        said = extraction.items[0] if extraction.items else {}
        return [
            Suggestion(text=_kept(said.get(name, ""), found), because=found.because)
            for name, found in zip(wanted, candidates, strict=True)
        ]


def _kept(phrasing: str, earned: Suggestion) -> str:
    """The model's wording, when it is still the suggestion that was earned."""
    words = phrasing.strip()
    if not words or len(words) > 80:
        return earned.text
    # Every value in the plain wording has to survive: a chip that drops the
    # value it was built from is a different request wearing its face.
    literals = [
        part for part in earned.text.split() if any(c.isdigit() or c.isupper() for c in part)
    ]
    if any(literal.casefold() not in words.casefold() for literal in literals):
        return earned.text
    if "(" in words or ")" in words:
        # A phrasing carrying its own justification is not a request anybody
        # would type.
        return earned.text
    return words


def _about(skill: Skill, system: str, entity: str) -> bool:
    key = skill.objective_key
    return key.target_system == system and key.entity_type == entity and bool(skill.versions)


def _plainly(skill: Skill) -> str:
    key = skill.objective_key
    return f"{key.objective_type.replace('_', ' ')} a {key.entity_type.replace('_', ' ')}"
