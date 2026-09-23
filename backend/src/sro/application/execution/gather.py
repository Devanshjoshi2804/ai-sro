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

STEP_SCHEMA: dict[str, object] = {
    "type": "object",
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
    def __init__(self, tools: ToolCaller, asker: Asker, model: str) -> None:
        self._tools = tools
        self._asker = asker
        self._model = model

    @property
    def tools(self) -> ToolCaller:
        return self._tools

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
        found: dict[str, Found] = {}
        unasked: set[str] = set()
        looked: list[str] = []
        history: list[str] = []
        spent = Answer()
        until = time.monotonic() + patience

        opening = because.strip() or job.strip()
        if opening:
            asked, said = await self._search(ctx, opening)
            looked.append(asked)
            history.append(note(asked, said))

        for _ in range(rounds):
            missing = still_wanted(wanted, found)
            if not missing:
                break
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
                unasked |= set(dropped(offered, wanted))
                break

            asked, said = await self._look(ctx, action, answer.data)
            if asked:
                looked.append(asked)
                history.append(note(asked, said))
            else:
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
            tool, arguments = "get_message", {"id": message}
        else:
            return "", ""

        return await self._ask_the_mailbox(ctx, asked, tool, arguments)

    async def _search(self, ctx: RequestContext, query: str) -> tuple[str, str]:
        return await self._ask_the_mailbox(
            ctx, f"search {query!r}", "search_threads", {"query": query, "limit": "5"}
        )

    async def _ask_the_mailbox(
        self, ctx: RequestContext, asked: str, tool: str, arguments: Mapping[str, str]
    ) -> tuple[str, str]:
        try:
            answered = await self._tools.call(
                ctx.tenant_id, ctx.principal_id, SERVER, tool, dict(arguments)
            )
        except ToolsUnavailable as gone:
            return asked, f"the mailbox could not be reached: {gone}"
        return asked, answered.text


def _values_in(said: Mapping[str, object]) -> dict[str, Found]:
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
    had = "found " + ", ".join(sorted(found)) + ", then " if found else ""
    return f"{had}ran out of time looking for " + ", ".join(missing)


def _sentence(found: Mapping[str, Found], missing: Sequence[str]) -> str:
    if not missing:
        return "every value was found in the mailbox" if found else "nothing was needed"
    if not found:
        return "the mailbox holds none of the values this job needs"
    return "the mailbox holds " + ", ".join(sorted(found)) + " but not " + ", ".join(missing)


def _also(running: Answer, answer: Answer) -> Answer:
    return Answer(
        in_tokens=running.in_tokens + answer.in_tokens,
        out_tokens=running.out_tokens + answer.out_tokens,
        thought_tokens=running.thought_tokens + answer.thought_tokens,
        cost_usd=running.cost_usd + answer.cost_usd,
        unpriced=running.unpriced or answer.unpriced,
    )


__all__ = ["GatherContext", "Gathered"]
