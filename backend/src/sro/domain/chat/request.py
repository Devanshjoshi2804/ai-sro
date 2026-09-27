from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sro.domain.execution.compose import normal
from sro.domain.execution.field_classes import FieldClass
from sro.domain.prompts.record import quoted_in

K_CANDIDATES = 8

K_A_LOGIN = "a sign-in name, never a job's value"


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    title: str
    fields: tuple[FieldClass, ...]
    aliases: Mapping[str, str]
    seen: Mapping[str, tuple[str, ...]]
    asked_by: tuple[str, ...] = ()
    logins: frozenset[str] = frozenset()

    @property
    def parameters(self) -> tuple[str, ...]:
        return tuple(one.name for one in self.fields if one.kind != "never")

    @property
    def required(self) -> frozenset[str]:
        return frozenset(one.name for one in self.fields if one.kind == "required")


@dataclass
class Read:
    job: str | None
    sure: bool = False
    values: dict[str, str] = field(default_factory=dict)
    aside: dict[str, str] = field(default_factory=dict)
    items: list[dict[str, str]] = field(default_factory=list)
    also: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    refused: dict[str, str] = field(default_factory=dict)


def field_of(said: str, candidate: Candidate) -> tuple[str, bool] | None:
    key = normal(said)
    aliased = candidate.aliases.get(key)
    if aliased is not None:
        return aliased, aliased in candidate.parameters
    for one in candidate.fields:
        if key in {normal(label) for label in (one.name, *one.labels)}:
            return one.name, one.kind != "never"
    return None


def _names(quote: str, candidate: Candidate) -> set[str]:
    said = normal(quote)
    wordings = [
        *((label, one.name) for one in candidate.fields for label in (one.name, *one.labels)),
        *candidate.aliases.items(),
    ]
    return {
        name
        for label, name in wordings
        if normal(label) and re.search(rf"(?<!\w){re.escape(normal(label))}(?!\w)", said)
    }


def _entries(raw: object) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)] if isinstance(raw, list) else []


def _placed(raw: object, job: Candidate, thread: str, read: Read) -> tuple[dict[str, str], bool]:
    values: dict[str, str] = {}
    clean = True
    limits = {one.name: one.limits for one in job.fields}
    for one in _entries(raw):
        said, value, quote = (str(one.get(key) or "") for key in ("field", "value", "quote"))
        if not value.strip() or not quoted_in(quote, thread) or not quoted_in(value, quote):
            clean = False
            continue
        placed = field_of(said, job)
        login = normal(value) in job.logins
        if placed is None or not placed[1]:
            if not login:
                read.aside[said if placed is None else placed[0]] = value
            continue
        name = placed[0]
        named = _names(quote, job)
        why = (
            K_A_LOGIN
            if login
            else f"its quote names {', '.join(sorted(named))}"
            if named and name not in named
            else limits[name].refuses(value)
        )
        if why:
            read.refused[name] = why
            continue
        values[name] = value
    return values, clean


def _fills(job: Candidate, named: set[str]) -> bool:
    return job.required <= named


def read_of(data: Mapping[str, object], candidates: Sequence[Candidate], thread: str) -> Read:
    by_id = {one.id: one for one in candidates}
    job = by_id.get(str(data.get("job") or ""))
    if job is None:
        return Read(None)
    read = Read(job.id)
    read.values, clean = _placed(data.get("values"), job, thread, read)
    things: list[dict[str, str]] = []
    for one in _entries(data.get("items")):
        thing, fine = _placed(one.get("values"), job, thread, read)
        clean = clean and fine
        things.append(thing)
    read.items = [one for one in things if one]
    also = data.get("also")
    read.also = [
        one
        for one in (also if isinstance(also, list) else [])
        if isinstance(one, str) and one in by_id and one != job.id
    ]
    named = set(read.values) | {name for one in read.items for name in one}
    settled = (
        bool(read.also)
        and _fills(job, named)
        and not any(_fills(by_id[one], named) for one in read.also)
    )
    if settled:
        read.also = []
    supplied = [{**read.values, **one} for one in things] or [read.values]
    read.missing = sorted(
        name
        for name in job.required | set(read.refused)
        if any(name not in one for one in supplied)
    )
    read.sure = (data.get("sure") is True or settled) and clean and not read.also
    return read


__all__ = ["K_A_LOGIN", "K_CANDIDATES", "Candidate", "Read", "field_of", "read_of"]
