"""Ask the model whether a sentence answers the question standing in the thread.

One question, the words that were actually said, and no jobs to choose between:
which job this is about was settled when the question was asked, and handing a
reading a decision that is already made is how a settled question gets
re-opened by two words.

Refuses by saying "this is an answer", never by silence. A deployment with no
model, a day's cap spent, a door that raised -- all of them mean this system
behaves exactly as it did before this existed, which is a question that takes
the next sentence. That is the wrong default and it is the SAFE one to fall
back to: the alternative is a panel that silently stops accepting answers the
moment a model is unreachable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.domain.chat.asking import Pending, question
from sro.domain.chat.is_it_an_answer import (
    HOW_TO_READ,
    IS_IT_AN_ANSWER_SCHEMA,
    plainly_a_value,
)
from sro.domain.shared.prices import Answer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Read:
    """What the sentence turned out to be."""

    answers: bool
    value: str = ""
    why: str = ""
    spent: Answer | None = None


class IsItAnAnswer:
    """Whether to take this sentence as the value the conversation asked for."""

    def __init__(self, asker: Asker | None, *, model: str) -> None:
        self._asker = asker
        self._model = model

    async def execute(self, ctx: RequestContext, pending: Pending, said: str) -> Read:
        """Read it, or say it plainly is one without spending anything."""
        if plainly_a_value(pending, said):
            return Read(answers=True, value=said.strip(), why="one word, and it fits")
        if self._asker is None:
            return Read(answers=True, value=said.strip(), why="no model to ask")
        try:
            answer = await self._asker.ask(
                model=self._model,
                instructions=HOW_TO_READ,
                evidence=json.dumps(
                    {"asked": question(pending), "field": pending.asking_for, "typed": said},
                    indent=2,
                    ensure_ascii=False,
                ),
                schema=IS_IT_AN_ANSWER_SCHEMA,
            )
        except Exception:
            logger.info("%s: the answer could not be read; taking it", ctx.tenant_id.value)
            return Read(answers=True, value=said.strip(), why="the reading failed")
        data = answer.data if isinstance(answer.data, dict) else None
        if data is None:
            return Read(answers=True, value=said.strip(), why="nothing came back", spent=answer)
        answers = bool(data.get("answers"))
        # The value the reading pulled out, and the whole sentence where it
        # named none. A reading that says "this answers" and then hands back
        # nothing has not read anything, and the sentence is what was said.
        value = str(data.get("value") or "").strip() or said.strip()
        return Read(
            answers=answers,
            value=value if answers else "",
            why=str(data.get("why") or ""),
            spent=answer,
        )


__all__ = ["IsItAnAnswer", "Read"]
