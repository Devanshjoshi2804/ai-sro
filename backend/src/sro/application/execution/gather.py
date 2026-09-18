"""Go and find the values a job needs, in the mailbox the operator reads.

The gap the live deployment named. A run of `Create a Customer Type` needs a
code and a description; the only source was a person typing them into the
press, so step 1 -- "Open an email requesting a new customer type" -- refused
with *"The open email is for customer type GPDP rather than the requested
ZQ41"*. The run had values and the mailbox had a different request, and nothing
could go and look.

**Propose, execute through a real port, observe, feed that back.** The shape
every other loop here uses, and the one every account of agentic loops agrees
on: gather, act, verify, repeat. What is fed back is a NOTE and never the mail
-- see `gathering.K_NOTE`. The failure modes of a loop like this are context
poisoning, distraction and confusion, and raw accumulation is how you get all
three.

**It refuses rather than guessing.** A parameter nothing could be found for
comes back in `missing`, and the caller asks a person. This is the same rule
`write_plan_for` keeps one layer down, for the same reason: a model's reading
of somebody's mail is not something to put into a warehouse write unasked.

**Every value says which message it came from.** A value read out of a mailbox
is only as good as the message it was read from, and both the person approving
the write and an audit a month later need to be able to go and look.

The mailbox is reached through `ToolCaller`, per operator: each reads their own
mail, and a gather for one person must never see another's. That boundary is
the port's, not this module's -- it takes the tenant and the principal and
passes them down.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.execution.gathering import (
    K_PATIENCE_S,
    K_ROUNDS,
    Found,
    Gathered,
    dropped,
    keep,
    note,
    still_wanted,
)
from sro.domain.shared.prices import Answer

SERVER = "gmail"
"""The connector this looks in. One, named, rather than every connector a
deployment has: a gather that tried them all would be reading systems nobody
asked it to read."""

STEP_SCHEMA: dict[str, object] = {
    "type": "object",
    # action first, why last: decide, then explain.
    "properties": {
        "action": {"type": "string", "enum": ["search", "read", "done"]},
        "query": {"type": "string", "nullable": True},
        "message_id": {"type": "string", "nullable": True},
        "values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "from_message": {"type": "string"},
                    "quoting": {"type": "string"},
                },
                "required": ["name", "value", "from_message"],
            },
        },
        "why": {"type": "string"},
    },
    "required": ["action", "why"],
    "propertyOrdering": ["action", "query", "message_id", "values", "why"],
}

INSTRUCTIONS = """You are finding the values a warehouse job needs, in the operator's mailbox.

You are given the job, the values it still needs, what each has been seen
taking before, and what you have already looked at. Choose ONE action:

- search: a Gmail query. Use it to find candidate messages.
- read: a message id from a previous search, to see its whole body.
- done: you have found values, or you are certain the mailbox does not hold
  them. Put what you found in `values`.

Every value you report must carry `from_message` -- the id of the message you
read it out of -- and `quoting`, the few words it appeared in. A value you
cannot point at a message for is a value you must not report.

Report only the values asked for. Do not invent one, do not carry one over
from an example, and do not report a value you inferred rather than read. If
the mailbox does not hold a value, say `done` and leave it out: somebody will
be asked for it, which is far better than a wrong record in a warehouse.

The value is often NOT in the message that mentions the job. A request may say
"as discussed" or point at an earlier thread, so read the thread rather than
stopping at the first hit."""


class GatherContext:
    """Find a job's values in the mailbox, or say which ones are missing."""

    def __init__(self, tools: ToolCaller, asker: Asker, model: str) -> None:
        self._tools = tools
        self._asker = asker
        self._model = model

    async def execute(
        self,
        ctx: RequestContext,
        *,
        job: str,
        wanted: Sequence[str],
        seen: Mapping[str, Sequence[str]] = MappingProxyType({}),
        because: str = "",
        rounds: int = K_ROUNDS,
        patience: float = K_PATIENCE_S,
    ) -> Gathered:
        """Look, up to `rounds` times, and come back with what was found.

        `seen` is what each parameter has been observed taking across the
        demonstrations -- the same `seen_values` the write plan binds by. It is
        shown to the model as the SHAPE of an answer and never as a value to
        reuse: a gather that copied a demonstrated value would create the
        demonstration's record again, which is the defect the whole replay path
        exists to have fixed.
        """
        found: dict[str, Found] = {}
        # Names the mail offered that this job declares no parameter for. A
        # request asking for a field the job cannot take is a request half
        # done, and silence about the other half is the fault this exists to
        # stop being invisible.
        unasked: set[str] = set()
        looked: list[str] = []
        history: list[str] = []
        spent = Answer()
        # A clock as well as a counter. See `K_PATIENCE_S`: rounds bound how
        # many times this looks, and on the day the model answers a round with
        # a 5xx the retry that follows is measured in minutes.
        until = time.monotonic() + patience

        # The first look is not the model's to choose.
        #
        # Asked to find values with nothing to start from, it answered `done`
        # with no values on round one and never touched the mailbox -- a
        # refusal to look wearing the face of a conclusion. Measured on the
        # deployment 2026-09-16: a run with no values gathered nothing and the
        # connector logged no request at all.
        #
        # So the job's own name is the first query, deterministically, and the
        # model's first decision is made with results in front of it. Cheaper
        # by a call, and it means "the mailbox does not hold this" is always a
        # statement about the mailbox rather than about the prompt.
        opening = because.strip() or job.strip()
        if opening:
            asked, said = await self._search(ctx, opening)
            looked.append(asked)
            history.append(note(asked, said))

        for _ in range(rounds):
            missing = still_wanted(wanted, found)
            if not missing:
                break
            # What is left of the budget, and never more. `K_ROUNDS` bounds
            # how many times this looks; this bounds how long looking may
            # take, which on the day the model answers with a 5xx is a
            # different number by two orders of magnitude.
            left = until - time.monotonic()
            if left <= 0:
                return Gathered(
                    values=found,
                    missing=missing,
                    looked=tuple(looked),
                    unasked=tuple(sorted(unasked)),
                    why=_ran_out(found, missing),
                )
            try:
                answer = await asyncio.wait_for(
                    self._asker.ask(
                        model=self._model,
                        instructions=INSTRUCTIONS,
                        evidence=json.dumps(
                            {
                                "job": job,
                                "asked_for": because,
                                "still_needed": list(missing),
                                "seen_before": {name: list(seen.get(name, ())) for name in missing},
                                "already_looked_at": history,
                            },
                            indent=2,
                            ensure_ascii=False,
                        ),
                        schema=STEP_SCHEMA,
                        effort=None,
                    ),
                    left,
                )
            except TimeoutError:
                # The same answer as a mailbox that holds nothing, because to
                # the run it is the same fact: nobody found the value, so a
                # person is asked. What WAS found is kept -- a code read in the
                # first round is not less true for the second round being slow.
                return Gathered(
                    values=found,
                    missing=still_wanted(wanted, found),
                    looked=tuple(looked),
                    unasked=tuple(sorted(unasked)),
                    why=_ran_out(found, still_wanted(wanted, found)),
                )
            spent = _also(spent, answer)
            if answer.data is None:
                return Gathered(
                    values=found,
                    missing=still_wanted(wanted, found),
                    looked=tuple(looked),
                    unasked=tuple(sorted(unasked)),
                    why=answer.error or "the model returned nothing",
                )

            action = str(answer.data.get("action") or "")
            if action == "done":
                offered = _values_in(answer.data)
                found.update(keep(offered, wanted))
                # What it offered that this job has no parameter for, kept so
                # somebody can be told. See `dropped`.
                unasked |= set(dropped(offered, wanted))
                break

            asked, said = await self._look(ctx, action, answer.data)
            if asked:
                looked.append(asked)
                history.append(note(asked, said))
            else:
                # A round that asked for nothing is a round that cannot be
                # followed by a better one: the history would be identical and
                # so would the next answer. Stopping is cheaper than spending
                # the rest of the budget proving it.
                history.append(note("nothing was asked", str(answer.data.get("why") or "")))
                break

        missing = still_wanted(wanted, found)
        return Gathered(
            values=found,
            missing=missing,
            looked=tuple(looked),
            unasked=tuple(sorted(unasked)),
            why=_sentence(found, missing),
        )

    async def _look(
        self, ctx: RequestContext, action: str, said: Mapping[str, object]
    ) -> tuple[str, str]:
        """One call to the mailbox, as this operator. What was asked, and what
        came back -- both as text, because history is a note and not a payload.

        A connector that refuses is not an exception here: it is an observation
        the next round is told about, exactly as an empty search would be. The
        loop then has a chance to try a different query rather than the whole
        gather failing on one bad call.
        """
        if action == "search":
            query = str(said.get("query") or "").strip()
            if not query:
                return "", ""
            return await self._search(ctx, query)
        if action == "read":
            message = str(said.get("message_id") or "").strip()
            if not message:
                return "", ""
            asked = f"read {message}"
            # `id`, which is what the connector declares. It was `message_id`
            # for one afternoon and every read asked for an empty id, so the
            # loop searched six times against bodies that were never fetched --
            # and refused, correctly, on nothing. An argument name is a
            # contract between two programs;
            # `test_the_gather_asks_for_what_the_connector_declares` holds it.
            tool, arguments = "get_message", {"id": message}
        else:
            return "", ""

        return await self._ask_the_mailbox(ctx, asked, tool, arguments)

    async def _search(self, ctx: RequestContext, query: str) -> tuple[str, str]:
        """One search, by whatever words were chosen for it."""
        return await self._ask_the_mailbox(
            ctx, f"search {query!r}", "search_threads", {"query": query, "limit": "5"}
        )

    async def _ask_the_mailbox(
        self, ctx: RequestContext, asked: str, tool: str, arguments: Mapping[str, str]
    ) -> tuple[str, str]:
        """One call, as this operator. What was asked, and what came back.

        A connector that refuses is an observation the next round is told
        about, not an exception: the loop then has a chance to try a different
        query rather than the whole gather failing on one bad call.
        """
        try:
            answered = await self._tools.call(
                ctx.tenant_id, ctx.principal_id, SERVER, tool, dict(arguments)
            )
        except ToolsUnavailable as gone:
            return asked, f"the mailbox could not be reached: {gone}"
        return asked, answered.text


def _values_in(said: Mapping[str, object]) -> dict[str, Found]:
    """The model's reported values, as far as they are the right shape.

    Anything malformed is dropped rather than raising: one bad row in a list of
    two must not lose the good one, and a value with no message behind it is
    dropped by `keep` a moment later anyway.
    """
    rows = said.get("values")
    if not isinstance(rows, list):
        return {}
    found: dict[str, Found] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, value = row.get("name"), row.get("value")
        origin, quoting = row.get("from_message"), row.get("quoting")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        found[name] = Found(
            value=value,
            from_message=origin if isinstance(origin, str) else "",
            quoting=quoting if isinstance(quoting, str) else "",
        )
    return found


def _ran_out(found: Mapping[str, Found], missing: Sequence[str]) -> str:
    """What happened when the clock beat the mailbox.

    Said as what it is rather than as a failure: the run's next move for a
    value nobody found is to ask a person, and that is the same move it makes
    for a mailbox that genuinely does not hold one.
    """
    had = "found " + ", ".join(sorted(found)) + ", then " if found else ""
    return f"{had}ran out of time looking for " + ", ".join(missing)


def _sentence(found: Mapping[str, Found], missing: Sequence[str]) -> str:
    """What happened, for a person reading the run rather than the code."""
    if not missing:
        return "every value was found in the mailbox" if found else "nothing was needed"
    if not found:
        return "the mailbox holds none of the values this job needs"
    return "the mailbox holds " + ", ".join(sorted(found)) + " but not " + ", ".join(missing)


def _also(running: Answer, answer: Answer) -> Answer:
    """The bill so far. Kept because a loop that can ask six times is a loop
    somebody will want the cost of."""
    return Answer(
        in_tokens=running.in_tokens + answer.in_tokens,
        out_tokens=running.out_tokens + answer.out_tokens,
        thought_tokens=running.thought_tokens + answer.thought_tokens,
        cost_usd=running.cost_usd + answer.cost_usd,
        unpriced=running.unpriced or answer.unpriced,
    )


__all__ = ["GatherContext", "Gathered"]
