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

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Read:
    answers: bool | None
    value: str = ""
    why: str = ""
    about: str = ""


class IsItAnAnswer:
    def __init__(self, asker: Asker | None, *, model: str) -> None:
        self._asker = asker
        self._model = model

    async def execute(self, ctx: RequestContext, pending: Pending, said: str) -> Read:
        if plainly_a_value(pending, said):
            return Read(answers=True, value=said.strip(), why="one word, and it fits")
        if self._asker is None:
            return Read(answers=None, why="no model to ask")
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
            logger.info("%s: the answer could not be read; asking again", ctx.tenant_id.value)
            return Read(answers=None, why="the reading failed")
        data = answer.data if isinstance(answer.data, dict) else None
        if data is None:
            return Read(answers=None, why="nothing came back")
        answers = bool(data.get("answers"))
        value = str(data.get("value") or "").strip() or said.strip()
        return Read(
            answers=answers,
            value=value if answers else "",
            why=str(data.get("why") or ""),
            about=str(data.get("about") or "") or "the_wait",
        )


__all__ = ["IsItAnAnswer", "Read"]
