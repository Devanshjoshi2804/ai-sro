from __future__ import annotations

import re
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.derived_read import AskTheSystem
from sro.application.induction.sites import as_a_filter, filter_terms_of
from sro.application.knowledge.open_questions import AskAbout
from sro.application.ports.intent import IntentParser
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import SkillVersion


def value_key(system: str, entity: str, word: str) -> str:
    return f"{system}/{entity}/value/{word.lower()}"


MOST_FIELDS = 30


@dataclass(frozen=True, slots=True)
class NeedToAsk:
    word: str
    entity: str
    system: str
    options: tuple[str, ...]
    question: str
    because: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Narrowed:
    url: str
    field: str
    value: str
    because: tuple[str, ...]


class NarrowARead:
    def __init__(
        self,
        uow: UnitOfWork,
        parser: IntentParser | None,
        ask: AskAbout | None = None,
        system_says: AskTheSystem | None = None,
    ) -> None:
        self._uow = uow
        self._parser = parser
        self._ask = ask
        self._system_says = system_says

    async def for_utterance(
        self,
        ctx: RequestContext,
        *,
        utterance: str,
        version: SkillVersion,
        system: str,
        entity: str,
        skill_id: SkillId | None = None,
        unexplained: tuple[str, ...] = (),
        verb: str = "",
    ) -> Narrowed | NeedToAsk | None:
        if self._parser is None or not self._parser.available:
            return None

        listing = _the_read(version)
        if listing is None:
            return None

        fields = await self._fields(ctx, system=system, entity=entity)
        if not fields:
            return None

        extraction = await self._parser.extract(
            utterance,
            parameters=tuple(fields),
            context=(
                f"Fields of {entity} in {system}. "
                "Only fill in a field the sentence names a value for."
            ),
        )
        chosen = next(
            (
                (name, value.strip())
                for item in extraction.items
                for name, value in item.items()
                if name in fields and value.strip()
            ),
            None,
        )
        if chosen is None:
            return await self._place(
                ctx,
                system=system,
                entity=entity,
                words=tuple(w for w in unexplained if w.casefold() != verb.casefold()),
                fields=fields,
                listing=listing,
                skill_id=skill_id,
            )

        field, value = chosen
        shape = await self._term_shape(ctx, system=system)
        narrowed = as_a_filter(listing, column=field, placeholder=value, shape=shape)
        if narrowed is None:
            return None

        return Narrowed(
            url=narrowed,
            field=field,
            value=value,
            because=(
                f"{fields[field]} is how {entity} records name that value",
                "the filter is the one this endpoint answered 200 to when it was demonstrated",
            ),
        )

    async def _place(
        self,
        ctx: RequestContext,
        *,
        system: str,
        entity: str,
        words: tuple[str, ...],
        fields: dict[str, str],
        listing: str,
        skill_id: SkillId | None = None,
    ) -> Narrowed | NeedToAsk | None:
        for word in words[:3]:
            if len(word) < 3:
                continue
            settled = await self._settled(ctx, system=system, entity=entity, word=word)
            mentions = await self._mentioning(ctx, system=system, word=word)
            if not settled and not mentions:
                continue
            if settled and "=" in settled:
                field, held = settled.split("=", 1)
                narrowed = await self._compose(
                    ctx,
                    listing,
                    system,
                    field,
                    held,
                    fields,
                    because=f"somebody here said {word!r} means {field}={held}",
                )
                if narrowed is not None:
                    return narrowed
                continue
            if settled:
                placed = await self._as_the_records_have_it(
                    ctx, listing=listing, field=settled, word=word, skill_id=skill_id
                )
                if isinstance(placed, str):
                    narrowed = await self._compose(
                        ctx,
                        listing,
                        system,
                        settled,
                        placed,
                        fields,
                        because=(
                            f"somebody here said {word!r} means {settled}, and the records "
                            f"carry it as {placed!r}"
                        ),
                    )
                    if narrowed is not None:
                        return narrowed
                    continue
                if placed:
                    return NeedToAsk(
                        word=word,
                        entity=entity,
                        system=system,
                        options=tuple(f"{settled}={seen}" for seen in placed),
                        question=(
                            f"Which {settled} means {word!r}? "
                            f"These records carry: {', '.join(placed)}"
                        ),
                        because=(
                            f"{settled} is the field, settled earlier",
                            "the values are the ones this system actually holds",
                        ),
                    )
                return NeedToAsk(
                    word=word,
                    entity=entity,
                    system=system,
                    options=(),
                    question=(
                        f"{word!r} means {settled} here, but the {entity} list does not "
                        f"return that field — so I cannot answer it from this read. "
                        f"Teach me the screen that shows it and I will."
                    ),
                    because=(),
                )

            if len(mentions) == 1:
                field = next(iter(mentions))
                narrowed = await self._compose(
                    ctx,
                    listing,
                    system,
                    field,
                    word,
                    {**fields, field: mentions[field]},
                    because=f"{mentions[field]} is the only field this system documents "
                    f"as carrying {word!r}",
                )
                if narrowed is not None:
                    return narrowed

            choices = tuple(mentions or fields)[:5]
            if not choices:
                continue
            return NeedToAsk(
                word=word,
                entity=entity,
                system=system,
                options=choices,
                question=f"Which field of {entity.replace('_', ' ')} does {word!r} name?",
                because=(
                    *(f"{name} — {(mentions or fields)[name]}" for name in choices),
                    f"{len(mentions)} fields mention it in this system's catalogue"
                    if mentions
                    else "nothing in the catalogue documents that word",
                    f"asked once: the answer settles {word!r} for everybody",
                ),
            )
        return None

    async def _compose(
        self,
        ctx: RequestContext,
        listing: str,
        system: str,
        field: str,
        value: str,
        fields: dict[str, str],
        because: str = "",
    ) -> Narrowed | None:
        shape = await self._term_shape(ctx, system=system)
        narrowed = as_a_filter(listing, column=field, placeholder=value, shape=shape)
        if narrowed is None:
            return None
        return Narrowed(
            url=narrowed,
            field=field,
            value=value,
            because=(
                because or f"{fields.get(field, field)} is how these records name that value",
                "the filter is the one this endpoint answered 200 to when it was demonstrated",
            ),
        )

    async def _as_the_records_have_it(
        self,
        ctx: RequestContext,
        *,
        listing: str,
        field: str,
        word: str,
        skill_id: SkillId | None,
    ) -> str | tuple[str, ...]:
        if self._system_says is None or skill_id is None:
            return ()
        asked = await self._system_says.execute(ctx, skill_id=skill_id, url=listing)
        if asked.answer is None:
            return ()

        held = {value.strip() for value in asked.answer.distinct.get(field, ()) if value.strip()}
        for value in held:
            if value.casefold() == word.casefold():
                return value
        return tuple(sorted(held)[:6])

    async def _settled(
        self, ctx: RequestContext, *, system: str, entity: str, word: str
    ) -> str | None:
        if self._ask is None:
            return None
        return await self._ask.settled(ctx, key=value_key(system, entity, word))

    async def _mentioning(self, ctx: RequestContext, *, system: str, word: str) -> dict[str, str]:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, system=system, kinds=(EntryKind.FIELD,), terms=word, limit=10
            )
        return {
            entry.key: entry.title or entry.key
            for entry in found
            if entry.key.isidentifier() and _mentions(entry.title or entry.key, word)
        }

    async def _term_shape(self, ctx: RequestContext, *, system: str) -> dict[str, str] | None:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=200)
        for skill in skills:
            if skill.objective_key.target_system != system or not skill.versions:
                continue
            for step in skill.versions[-1].steps:
                plan = step.network_plan
                if plan is None or plan.method.upper() != "GET":
                    continue
                for term in filter_terms_of(str(plan.url)):
                    return {key: value for key, value in term.items() if key != "value"}
        return None

    async def _fields(self, ctx: RequestContext, *, system: str, entity: str) -> dict[str, str]:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id,
                system=system,
                kinds=(EntryKind.FIELD,),
                terms=entity,
                limit=MOST_FIELDS * 3,
            )
        fields: dict[str, str] = {}
        for entry in found:
            name = entry.key.strip()
            if name.isidentifier() and name not in fields:
                fields[name] = entry.title or name
            if len(fields) >= MOST_FIELDS:
                break
        return fields


def _mentions(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE) is not None


def _the_read(version: SkillVersion) -> str | None:
    for step in version.steps:
        plan = step.network_plan
        if plan is None or plan.method.upper() != "GET":
            continue
        address = str(plan.url)
        if "${" not in address:
            return address
    return None
