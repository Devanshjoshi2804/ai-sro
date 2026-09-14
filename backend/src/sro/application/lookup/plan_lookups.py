"""One question, turned into where to go and look for the answer.

The read half of this system. `read_chat` resolves a sentence against the jobs
an operator was seen DOING; this resolves one against what the systems KNOW,
which is a different question with a different answer and no overlap in the
vocabulary. A job is mined from evidence; a lookup is planned from knowledge.

Nothing here touches a system. The plan says where the answer lives and stops;
executing it is the next seam, and keeping them apart is what lets a plan be
read by a person before anything is asked of anybody's warehouse.

**Structural retrieval first, similarity second**, which is `Retrieve`'s own
rule and its argument: a nearest neighbour over the whole store returns another
system's endpoint with total confidence, and a confident fast wrong answer is
what this design is arranged against. So the planner is shown endpoints,
screens, fields and quirks -- filtered by kind -- and the model orders what
survived rather than choosing from everything.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap
from sro.domain.knowledge.entry import EntryKind, KnowledgeEntry
from sro.domain.lookup.plan import (
    INSTRUCTIONS,
    K_MAX_LOOKUPS,
    LOOKUP_SCHEMA,
    Lookup,
    Plan,
    open_question_for,
    uncited,
    unknown_targets,
)
from sro.domain.shared.prices import Answer

logger = logging.getLogger(__name__)

WHAT_TO_SHOW = (
    EntryKind.ENDPOINT,
    EntryKind.SCREEN,
    EntryKind.FIELD,
    EntryKind.QUIRK,
    EntryKind.QUESTION,
)
"""The kinds a lookup can be built from, and one that stops it.

`QUESTION` is in the list precisely because it is not knowledge the plan may
use: an unanswered one is where the next confident answer would be a guess, and
it has to be retrieved to be noticed. `STATUS` and `FORM` are left out -- what a
code means and how a form is shaped matter when reading an answer, not when
deciding where to ask.
"""

K_SHOWN = 40
"""How much knowledge the planner sees.

Wide enough to hold the endpoint and the screen for two systems with their
fields; narrow enough that the model is choosing rather than searching. The
store holds 7,985 entries and a prompt carrying them would be a prompt nobody
has read."""


@dataclass(frozen=True, slots=True)
class Planned:
    plan: Plan
    answer: Answer | None = None
    """What the reading cost. Beside the plan rather than inside it: a plan is
    a domain object and a bill is not, and `MineResult` learned that the hard
    way when three workflows from one call summed to three times its cost."""

    refused: str | None = None


class PlanLookups:
    """Where to look, for one question, over one tenant's knowledge."""

    def __init__(
        self,
        uow: UnitOfWork,
        retrieve: Retrieve,
        asker: Asker | None,
        *,
        model: str,
        clock: Clock,
        cap_usd: float,
    ) -> None:
        self._uow = uow
        self._retrieve = retrieve
        # `Asker | None` rather than through `asker_or_refuse` at construction,
        # for `ReadChat`'s reason: a factory that raised would make a
        # deployment with no key unbuildable rather than refusing the one call
        # that needs a model.
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap = cap_usd

    async def execute(
        self, ctx: RequestContext, *, question: str, system: str | None = None
    ) -> Planned:
        asked = question.strip()
        if not asked:
            return Planned(Plan(question=""), refused="a question with nothing in it")

        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap)
        if why:
            # Before the retrieval and long before the call, which is where
            # `mining_pass` checks it: a cap read after the work is a cap that
            # has already paid for what it stops.
            raise OverCap(why)

        known = list(
            await self._retrieve.execute(
                ctx,
                Question(text=asked, system=system, kinds=WHAT_TO_SHOW, limit=K_SHOWN),
            )
        )
        if not known:
            return Planned(
                Plan(question=asked, why="this deployment knows nothing about these systems"),
                refused="nothing retrieved",
            )

        stopped = open_question_for(asked, known)
        if stopped is not None:
            # Asked once, and not answered here. The operator settles it and
            # the answer supersedes the question, so the next reading of the
            # same word reads the answer instead of asking again.
            return Planned(Plan(question=asked, asks=stopped, why=stopped.question))

        answer = await asker.ask(
            model=self._model,
            instructions=INSTRUCTIONS,
            evidence=_shown(asked, known),
            schema=LOOKUP_SCHEMA,
        )
        if answer.error or not isinstance(answer.data, dict):
            return Planned(Plan(question=asked), answer=answer, refused=answer.error or "no answer")

        lookups = _read(answer.data)
        if unknown := unknown_targets(lookups, known):
            # A path that looks like the others is the failure this refuses.
            # Refused whole rather than filtered: a plan that quietly drops one
            # of its systems answers a narrower question than the one asked,
            # and says nothing about having done so.
            return Planned(
                Plan(question=asked),
                answer=answer,
                refused=f"named {', '.join(unknown)}, which nothing here has seen",
            )
        if bare := uncited(lookups, known):
            return Planned(
                Plan(question=asked),
                answer=answer,
                refused=f"{', '.join(bare)} cites nothing it was shown",
            )

        return Planned(
            Plan(
                question=asked,
                lookups=tuple(lookups[:K_MAX_LOOKUPS]),
                why=str(answer.data.get("why") or ""),
            ),
            answer=answer,
        )


def _read(data: dict[str, object]) -> list[Lookup]:
    """The model's answer as lookups, dropping anything malformed.

    Dropped rather than refused: a shape the schema should have caught is the
    model failing to answer, and the refusals above are about what it SAID.
    Losing one malformed lookup out of four still leaves a plan somebody can
    read; the count is what `unknown_targets` and `uncited` then judge.
    """
    raw = data.get("lookups")
    if not isinstance(raw, list):
        return []
    found: list[Lookup] = []
    for one in raw:
        if not isinstance(one, dict):
            continue
        how = one.get("how")
        target = str(one.get("target") or "").strip()
        if how not in ("call", "screen") or not target:
            continue
        params = one.get("params")
        cites = one.get("cites")
        found.append(
            Lookup(
                system=str(one.get("system") or ""),
                how=how,
                target=target,
                params=(
                    {str(k): str(v) for k, v in params.items()} if isinstance(params, dict) else {}
                ),
                why=str(one.get("why") or ""),
                cites=tuple(str(c) for c in cites if c) if isinstance(cites, list) else (),
            )
        )
    return found


def _shown(question: str, known: list[KnowledgeEntry]) -> str:
    """What the planner is given, grouped by kind.

    Grouped because the kinds answer different questions -- an endpoint is a
    place to ask, a quirk is a reason to distrust the answer -- and a flat list
    makes the model sort them before it can use them. The key is first on every
    line, because the key is what a citation has to name.
    """
    lines = [f"QUESTION: {question}", ""]
    for kind in WHAT_TO_SHOW:
        of_kind = [entry for entry in known if entry.kind is kind]
        if not of_kind:
            continue
        lines.append(f"{kind.value.upper()}S THIS DEPLOYMENT HAS SEEN")
        for entry in of_kind:
            lines.append(f"  {entry.key} :: {entry.title}")
            body = entry.body if isinstance(entry.body, dict) else {}
            if params := body.get("params"):
                lines.append(f"      params: {params}")
            if routes := body.get("seen_on_routes"):
                shown = routes[:6] if isinstance(routes, list) else routes
                lines.append(f"      seen on: {shown}")
        lines.append("")
    return "\n".join(lines)
