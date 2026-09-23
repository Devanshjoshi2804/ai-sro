from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_WHOSE: ContextVar[dict[str, str | int] | None] = ContextVar("sro_whose", default=None)

KNOWN = (
    "tenant",
    "principal",
    "request",
    "device",
    "run",
    "step",
    "workflow",
    "thread",
    "pass_id",
    "command",
)


def whose() -> dict[str, str | int]:
    return dict(_WHOSE.get() or {})


@contextmanager
def about(**ids: str | int | None) -> Iterator[None]:
    unknown = sorted(set(ids) - set(KNOWN))
    if unknown:
        raise ValueError(f"not something a line can be attributed to: {', '.join(unknown)}")
    given = {key: value for key, value in ids.items() if value is not None}
    fresh = {**(_WHOSE.get() or {}), **given}
    token = _WHOSE.set(fresh)
    try:
        yield
    finally:
        _WHOSE.reset(token)


def attribute(**ids: str | int | None) -> None:
    unknown = sorted(set(ids) - set(KNOWN))
    if unknown:
        raise ValueError(f"not something a line can be attributed to: {', '.join(unknown)}")
    given = {key: value for key, value in ids.items() if value is not None}
    _WHOSE.set({**(_WHOSE.get() or {}), **given})


class Louder(logging.Filter):
    def __init__(self, floor: int, loud: frozenset[str]) -> None:
        super().__init__()
        self._floor = floor
        self._loud = loud

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= self._floor:
            return True
        mine = getattr(record, "whose", None) or whose()
        return str(mine.get("tenant", "")) in self._loud


class Attribution(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.whose = whose()
        return True


class Plainly(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        said = super().format(record)
        mine = getattr(record, "whose", {})
        if not mine:
            return said
        return f"{said}  [{' '.join(f'{key}={mine[key]}' for key in KNOWN if key in mine)}]"


class AsJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        said: dict[str, Any] = {
            "at": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "said": record.getMessage(),
            **getattr(record, "whose", {}),
        }
        if record.exc_info:
            said["blew_up"] = self.formatException(record.exc_info)
        return json.dumps(said, ensure_ascii=False, default=str)


__all__ = [
    "KNOWN",
    "AsJson",
    "Attribution",
    "Louder",
    "Plainly",
    "about",
    "attribute",
    "whose",
]
