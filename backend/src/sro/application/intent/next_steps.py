from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.intent import IntentParser
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap, Unattributed
from sro.domain.knowledge.entry import EntryKind
from sro.domain.skill.skill import Skill

MOST = 3

ENOUGH_TO_FILTER = 2
TOO_MANY_TO_FILTER = 8


@dataclass(frozen=True, slots=True)
class Suggestion:
    text: str
    because: str


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
        found: list[Suggestion] = []
        for column, held in values.items():
            if not (ENOUGH_TO_FILTER <= len(held) <= TOO_MANY_TO_FILTER):
                continue
            if len(held) >= rows > 0:
                continue
            found.append(
                Suggestion(
                    text=f"which {entity.replace('_', ' ')} records have {column} {held[0]}",
                    because=f"{column} holds {', '.join(held[:3])} in these records",
                )
            )
        return found[:2]

    async def _labels(self, ctx: RequestContext, *, system: str, entity: str) -> dict[str, str]:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, system=system, kinds=(EntryKind.FIELD,), terms=entity, limit=40
            )
        return {entry.key: entry.title or entry.key for entry in found}

    async def _phrase(
        self, candidates: list[Suggestion], entity: str, labels: dict[str, str]
    ) -> list[Suggestion]:
        if self._parser is None or not self._parser.available or not candidates:
            return candidates

        wanted = tuple(f"suggestion_{index}" for index, _ in enumerate(candidates))
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
        except (OverCap, Unattributed):
            raise
        except Exception:  # pragma: no cover - a phrasing failure is not an outage
            return candidates

        said = extraction.items[0] if extraction.items else {}
        return [
            Suggestion(text=_kept(said.get(name, ""), found), because=found.because)
            for name, found in zip(wanted, candidates, strict=True)
        ]


def _kept(phrasing: str, earned: Suggestion) -> str:
    words = phrasing.strip()
    if not words or len(words) > 80:
        return earned.text
    literals = [
        part for part in earned.text.split() if any(c.isdigit() or c.isupper() for c in part)
    ]
    if any(literal.casefold() not in words.casefold() for literal in literals):
        return earned.text
    if "(" in words or ")" in words:
        return earned.text
    return words


def _about(skill: Skill, system: str, entity: str) -> bool:
    key = skill.objective_key
    return key.target_system == system and key.entity_type == entity and bool(skill.versions)


def _plainly(skill: Skill) -> str:
    key = skill.objective_key
    return f"{key.objective_type.replace('_', ' ')} a {key.entity_type.replace('_', ' ')}"
