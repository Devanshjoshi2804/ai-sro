"""Asking the system a question nobody taught it, out of what it already knows.

"Show me one supplier in detail TESTSUPPLIERSRO" used to return all 239
suppliers: retrieval found the taught read, replayed it exactly as demonstrated
and dropped the only word in the sentence that said which supplier. That is a
replay engine, not a system that understands anything.

Everything needed to do better is already here and was going unused:

- the taught read proves the endpoint, its session and its filter dialect;
- the knowledge base's field dictionary says what that entity's fields are
  called, in the system's own vocabulary and the screen's -- `supplierNumber`
  is labelled "Supplier";
- a model can say which of those fields a value in a sentence belongs to.

So the model chooses between fields that exist rather than inventing one, the
request is composed in the dialect a real 200 proved, and what comes back is
this warehouse answering the question that was actually asked.
"""

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
    """Where the answer to "what does this word mean here" is kept."""
    return f"{system}/{entity}/value/{word.lower()}"


MOST_FIELDS = 30
"""How many fields the model chooses between. A dictionary of everything is a
prompt nobody can afford and a choice nobody can check."""


@dataclass(frozen=True, slots=True)
class NeedToAsk:
    """A word in the sentence that names a value nothing here can place.

    "Which suppliers are used for parcel" -- parcel is plainly a value, and
    nothing in the field dictionary says which field it belongs to. Listing
    every supplier instead answers a wider question and calls it an answer, so
    the honest move is to ask, once, and remember what the operator says.
    """

    word: str
    entity: str
    system: str
    options: tuple[str, ...]
    question: str
    because: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Narrowed:
    """One request, composed rather than taught."""

    url: str
    field: str
    value: str
    because: tuple[str, ...]
    """Where each part came from. A derived request cites its evidence or it is
    a guess with a URL."""


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
        """The same read, asked about one record.

        ``None`` when the sentence named nothing to narrow by, and then the
        taught skill runs as it always did. A :class:`NeedToAsk` when it named
        something and nothing here can place it -- which is a question, not a
        reason to answer something wider.
        """
        if self._parser is None or not self._parser.available:
            return None

        listing = _the_read(version)
        if listing is None:
            return None

        fields = await self._fields(ctx, system=system, entity=entity)
        if not fields:
            return None

        # The model picks between fields that exist. It cannot name one that
        # does not, because what it returns is checked against this list.
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
            # The sentence named a value the dictionary has no field for. Where
            # somebody has said what such a word means, that answer is used;
            # where the catalogue itself mentions it under exactly one field,
            # that is evidence; otherwise it is asked.
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
        # The endpoint may take a filter it was sent nothing in. What a term
        # looks like then comes from a call on this system that did carry one.
        shape = await self._term_shape(ctx, system=system)
        narrowed = as_a_filter(listing, column=field, placeholder=value, shape=shape)
        if narrowed is None:
            # This endpoint never showed us a filter. Inventing one is the
            # confident wrong request this whole design refuses to make.
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
        """Work out which field an unplaceable word belongs to, or ask."""
        for word in words[:3]:
            if len(word) < 3:
                continue
            settled = await self._settled(ctx, system=system, entity=entity, word=word)
            mentions = await self._mentioning(ctx, system=system, word=word)
            if not settled and not mentions:
                # Nothing here has ever heard of this word. "Used" is not a
                # value anybody can place, and asking which field it names
                # produces a question nobody can answer either.
                continue
            if settled and "=" in settled:
                # Already settled down to the value the records actually carry.
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
                # Their answer, not our dictionary: an operator saying "parcel
                # means smallPackageFlag" outranks anything the catalogue
                # happens to list under the entity, which is why they were
                # asked in the first place.
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
                    # The field is settled; what the value looks like in the
                    # data is not. Asking for a word this system has never
                    # stored would return nothing and call it an answer.
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
                # Settled onto a field this read does not return. Saying so
                # beats both answering something wider and asking a question
                # whose answer would change nothing.
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

            # Either nothing mentions it, or several do -- and choosing between
            # several is the guess this exists to avoid.
            choices = tuple(mentions or fields)[:5]
            if not choices:
                continue
            return NeedToAsk(
                word=word,
                entity=entity,
                system=system,
                options=choices,
                # The question, and only the question. The candidates are
                # buttons directly underneath it, and reciting them inside the
                # sentence made a two-line question forty words long -- three of
                # those stacked filled the screen and none of them could be read
                # at a glance. What each one is called in the catalogue goes to
                # the reasons, which is where a reader looks for detail.
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
        """What this word looks like in the data, or what the data does hold.

        A word in a sentence is rarely what a WMS stores: "parcel" is a flag
        somewhere, spelled `Y` or `true` or `PARCEL`. Asking the system for a
        value it has never stored returns nothing and reads as "there are none"
        -- so the column's own values are read first, and if the word is not
        among them, they become the options for one question.
        """
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
        """What somebody already said this word means here."""
        if self._ask is None:
            return None
        return await self._ask.settled(ctx, key=value_key(system, entity, word))

    async def _mentioning(self, ctx: RequestContext, *, system: str, word: str) -> dict[str, str]:
        """Fields the catalogue documents as carrying this value."""
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, system=system, kinds=(EntryKind.FIELD,), terms=word, limit=10
            )
        return {
            entry.key: entry.title or entry.key
            for entry in found
            if entry.key.isidentifier()
            # The label counts as documentation: "Parcel (smallPackageFlag)" is
            # the catalogue saying what that flag is, in the words on the screen.
            # The label, not the whole entry. Every field's body mentions
            # half the dictionary somewhere -- "all" appears as a word in
            # `expectedResidualLocation`'s description, and asking which field
            # the word "all" names is a question with no answer.
            and _mentions(entry.title or entry.key, word)
        }

    async def _term_shape(self, ctx: RequestContext, *, system: str) -> dict[str, str] | None:
        """How this system writes a filter term, taken from one it answered.

        The supplier screen sends `query=[]`; the address screen sends
        `query=[{"column":…,"operator":"EQ","value":…}]`. Same deployment, same
        dialect -- and reading it off a call that got a 200 is the difference
        between composing a request and guessing at an API.
        """
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
        """This entity's fields, as the system and the screen name them."""
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
    """Whether this documentation is about that word, rather than containing it.

    Substrings are not mentions: "all" sits inside `allowMultipleOpenContainers`,
    and matching it there made "list all transport modes" ask which field the
    word "all" names. A word is mentioned when it appears as a word.
    """
    return re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE) is not None


def _the_read(version: SkillVersion) -> str | None:
    """The call this skill reads with, if it has one nothing has to fill in."""
    for step in version.steps:
        plan = step.network_plan
        if plan is None or plan.method.upper() != "GET":
            continue
        address = str(plan.url)
        if "${" not in address:
            return address
    return None
