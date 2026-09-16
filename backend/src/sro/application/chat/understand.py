"""The chat door. Saying it offers the work; pressing start authorises it.

The model reads the utterance against the workflows this tenant holds and
answers which one, with which values, and what is still missing. Nothing
performs from here: the answer is an offer the form renders, and starting a run
is the press.

Ported from `new_agent_arch/src/rig/entry.py`, plus the half of the rig's
`/v1/chat` route that writes the bill down. The words and the response schema
are `sro.domain.chat.reading`; this is the half that asks.

The day's cap is the route's, not this module's: the rig answered 429 before it
reached `understand`, and a cap checked after the call is a cap that has
already paid for the call it stops.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.reading import INSTRUCTIONS, UNDERSTAND_SCHEMA, ChatReading, new_chat_id
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Workflow


@dataclass(frozen=True, slots=True)
class Understood:
    """What one sentence came to, and what reading it cost.

    `answer` has no default and is never None: every way out of `understand`
    -- named a job, named one nobody holds, or came back with nothing at all --
    went through the model and has to be billed for. A reading the caller
    cannot bill is a model call nobody can defend at the end of the month.
    """

    workflow_id: str | None
    answer: Answer
    values: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    sure: bool = True
    """Whether the sentence plainly named ONE of this tenant's jobs.

    `True` by default so a reading built by anything that predates this -- a
    test, an older row -- reads as it always did. What `False` means is the
    caller's: the panel asks a person which job was meant rather than pressing
    on, because a guess that creates one wrong record is a nuisance and the
    same guess against a list of twenty is twenty wrong records."""

    also: list[str] = field(default_factory=list)
    """The other jobs it nearly said, ids only, for the question a person is
    asked. Filtered to jobs this tenant actually holds, like `workflow_id`."""

    items: list[dict[str, str]] = field(default_factory=list)
    """The things this job is to be done for, where the operator named several.

    Empty for one thing, which is most sentences -- and a job run for one item
    performs exactly as a job run for none, so a caller that ignores this is
    not wrong, only limited to the first thing somebody asked for."""


async def understand(
    utterance: str,
    workflows: list[Workflow],
    asker: Asker,
    model: str,
    asked_by: Mapping[str, Sequence[str]] = MappingProxyType({}),
) -> Understood:
    """Which of these jobs the operator meant, with what values, missing what.

    `asked_by` is the mails each job was asked for by, where the demonstration
    recorded any -- see `domain.chat.asked_by`. It is the one thing this door
    was never shown and the one thing that says what a REQUEST for a job looks
    like, as opposed to what the job is called. A job with none is matched on
    its title and narrative exactly as it always was.
    """
    held = [
        {
            "id": w.id,
            "title": w.title,
            "narrative": w.narrative,
            "parameters": [
                {"name": p.get("name"), "seen": p.get("seen_values", [])}
                for p in w.parameters
                if isinstance(p, dict)
            ],
            # Omitted rather than empty where there are none: a field reading
            # `[]` invites "this job is never asked for by mail", which is a
            # claim about the tenant's history and not about the job.
            **({"asked_by": list(said)} if (said := asked_by.get(w.id)) else {}),
        }
        for w in workflows
    ]
    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=json.dumps(
            {"said": utterance, "jobs": held},
            indent=2,
            # The redaction marker is «redacted», and the default ensure_ascii
            # writes it into the prompt as \u00abredacted\u00bb -- a form
            # nothing else in this system uses. Every json.dumps on a path to a
            # prompt or to the store says so.
            ensure_ascii=False,
        ),
        schema=UNDERSTAND_SCHEMA,
    )
    if answer.data is None:
        return Understood(None, answer)
    # A job the rig does not hold is not a job: the model naming one is a
    # hallucination, not an offer, and the form has nothing to render for it.
    by_id = {w.id: w for w in workflows}
    chosen = by_id.get(str(answer.data.get("workflow_id") or ""))
    if chosen is None:
        return Understood(None, answer)
    # Values are what the run is performed with. A key the workflow never
    # declared is a value nothing asked for, arriving from a sentence a stranger
    # could have written -- so the offer carries only the parameters this
    # workflow itself names.
    declared = {p.get("name") for p in chosen.parameters if isinstance(p, dict)}
    raw = answer.data.get("values")
    pairs = (
        (p.get("name"), p.get("value"))
        for p in (raw if isinstance(raw, list) else ())
        if isinstance(p, dict)
    )
    values = {k: v for k, v in pairs if isinstance(k, str) and k in declared and isinstance(v, str)}
    items = _things(answer.data.get("items"), declared)
    # Read and ignored. `missing` stays in the schema because a model asked to
    # name what is absent picks values more carefully than one that is not --
    # but a parameter it leaves out of `missing` is a parameter the form never
    # asks for, and the run then performs with whatever the recording happened
    # to contain. What is missing is not an opinion: it is `declared` minus what
    # arrived, sorted, because `declared` is a set and a form whose fields
    # reorder between two identical sentences is a form nothing can screenshot.
    #
    # With several things named, a parameter is missing when some THING lacks
    # it: three equipment types of which one has no voice code is a form that
    # has to ask for the voice code, and a check against the job's shared
    # values alone would say every parameter was supplied by somebody.
    # Sure unless the model said otherwise, and never sure where it named
    # another job it might have meant instead: a reading that offers an
    # alternative has already said it was choosing.
    nearly = answer.data.get("also")
    also = [
        one
        for one in (nearly if isinstance(nearly, list) else [])
        if isinstance(one, str) and one in by_id and one != chosen.id
    ]
    sure = bool(answer.data.get("sure", True)) and not also
    supplied = [{**values, **item} for item in items] or [values]
    # A thing the filter emptied still counts here. The operator said "these
    # two", and a run that quietly does one of them is a run that did not do
    # what was asked -- so the parameters that thing did not name are missing,
    # the form asks for them, and nothing starts on a guess.
    items = [item for item in items if item]
    missing = sorted(
        name
        for name in declared
        if isinstance(name, str) and any(name not in one for one in supplied)
    )
    return Understood(chosen.id, answer, values, missing, sure, also, items)


def _things(raw: object, declared: set[object]) -> list[dict[str, str]]:
    """One set of values per thing the operator named, in the order they named
    them.

    Filtered exactly as `values` is, and for the same reason: a key this job
    never declared is a value nothing asked for, arriving from a sentence a
    stranger could have written.

    A thing that survives the filter with nothing left in it is kept HERE and
    dropped by the caller, which is not a contradiction: it counts for what is
    missing -- the operator said "these two" and a thing naming nothing leaves
    every parameter of that thing unanswered -- and it is not something a run
    can be handed, because the body performed for it would repeat the previous
    thing's values.
    """
    things: list[dict[str, str]] = []
    for one in raw if isinstance(raw, list) else ():
        if not isinstance(one, dict):
            continue
        said_values = one.get("values")
        pairs = (
            (pair.get("name"), pair.get("value"))
            for pair in (said_values if isinstance(said_values, list) else [])
            if isinstance(pair, dict)
        )
        said = {
            name: value
            for name, value in pairs
            if isinstance(name, str) and name in declared and isinstance(value, str)
        }
        things.append(said)
    return things


async def read_utterance(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    utterance: str,
    asker: Asker,
    model: str,
    now: datetime,
) -> Understood:
    """One sentence, read against this tenant's jobs, with the bill written down.

    The bill, and not the sentence: there is no column for an operator's words
    about their own warehouse, and the row exists for the cap and the spend
    line, neither of which needs them.

    A row is written on every reading, a refusal included -- that is the case
    that matters, because it is then the only record left of a call that cost
    money and returned nothing. `now` is the caller's clock rather than one
    read here, so a test can move it.
    """
    workflows = list(await uow.workflows.known(tenant_id))
    # The mails behind each job, read off the gestures they cite. One query for
    # every job the tenant holds, before the model call rather than per job:
    # the alternative is a round trip per workflow on the door an operator
    # waits at.
    cited = await uow.gestures.gestures_for(
        tenant_id, ids=tuple(sorted({one for w in workflows for s in w.steps for one in s.cites}))
    )
    by_id = {gesture.id: gesture for gesture in cited}
    asked_by = {w.id: texts(mails_behind(w, by_id)) for w in workflows}
    got = await understand(
        utterance, workflows, asker, model, {w: said for w, said in asked_by.items() if said}
    )
    answer = got.answer
    await uow.chats.record(
        ChatReading(
            id=new_chat_id(),
            tenant=tenant_id.value,
            at=now.isoformat(),
            # What the offer came to, which is None when the model named a job
            # nobody holds. The sentence it read is not here and has nowhere to
            # go: `ChatReading` has no field for it.
            workflow_id=got.workflow_id,
            in_tokens=answer.in_tokens,
            out_tokens=answer.out_tokens,
            thought_tokens=answer.thought_tokens,
            cost_usd=answer.cost_usd,
            unpriced=answer.unpriced,
            error=answer.error,
        )
    )
    await uow.commit()
    return got
