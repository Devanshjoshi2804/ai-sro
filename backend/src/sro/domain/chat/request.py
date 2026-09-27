from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sro.domain.execution.compose import normal
from sro.domain.execution.field_classes import FieldClass, FieldLimits, labelled
from sro.domain.prompts.record import quoted_in
from sro.domain.skill.signing_in import Logins

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
    logins: Logins = field(default_factory=Logins)
    systems: frozenset[str] = frozenset()

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


def _aliased(label: str, candidate: Candidate) -> tuple[str, bool]:
    one = labelled(normal(label), candidate.fields)
    return (label, False) if one is None else (one.name, one.kind != "never")


def field_of(said: str, candidate: Candidate) -> tuple[str, bool] | None:
    aliased = candidate.aliases.get(normal(said))
    if aliased is not None:
        return _aliased(aliased, candidate)
    one = labelled(normal(said), candidate.fields)
    return None if one is None else (one.name, one.kind != "never")


def _says(said: str, wording: str) -> bool:
    key = normal(wording)
    return bool(key) and re.search(rf"(?<!\w){re.escape(key)}(?!\w)", normal(said)) is not None


def _rest(value: str, quote: str) -> str | None:
    spaced = " ".join(quote.split())
    whole = rf"(?<!\w){re.escape(' '.join(value.split()))}(?!\w)"
    rest, found = re.subn(whole, " ", spaced, count=1)
    return rest if found else None


def _wordings(candidate: Candidate) -> list[tuple[str, str]]:
    return [
        *((label, one.name) for one in candidate.fields for label in (one.name, *one.labels)),
        *((wording, _aliased(label, candidate)[0]) for wording, label in candidate.aliases.items()),
    ]


def _names(said: str, candidate: Candidate) -> set[str]:
    return {name for label, name in _wordings(candidate) if _says(said, label)}


def _signing(value: str, thread: str, job: Candidate, own: frozenset[str]) -> bool:
    """A recorded username, or a value the thread states right after a sign-in
    box name of the job's own system: "user: X", "user X"."""
    spoken = re.escape(normal(value))
    said = normal(thread)
    return normal(value) in job.logins.names or any(
        re.search(rf"(?<!\w){re.escape(label)}[\s:=-]+{spoken}(?!\w)", said) is not None
        for system, label in job.logins.labels
        if system in job.systems and label not in own
    )


def refusal(
    value: str,
    quote: str,
    limits: FieldLimits,
    logins: Logins,
) -> str:
    if _rest(value, quote) is None:
        return "not in what was said"
    return K_A_LOGIN if normal(value) in logins.names else limits.refuses(value)


def _entries(raw: object) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)] if isinstance(raw, list) else []


def _placed(raw: object, job: Candidate, thread: str, read: Read) -> tuple[dict[str, str], bool]:
    values: dict[str, str] = {}
    clean = True
    limits = {one.name: one.limits for one in job.fields}
    own = frozenset(normal(label) for label, _ in _wordings(job))
    for one in _entries(raw):
        said, value, quote = (str(one.get(key) or "") for key in ("field", "value", "quote"))
        rest = _rest(value, quote)
        if not value.strip() or not quoted_in(quote, thread) or rest is None:
            clean = False
            continue
        placed = field_of(said, job)
        signing = _signing(value, thread, job, own)
        if placed is None or not placed[1]:
            if not signing:
                read.aside[said if placed is None else placed[0]] = value
            continue
        name = placed[0]
        named = _names(rest, job)
        why = (K_A_LOGIN if signing else refusal(value, quote, limits[name], job.logins)) or (
            f"its quote names {', '.join(sorted(named))}" if named and name not in named else ""
        )
        if why:
            read.refused[name] = why
            continue
        values[name] = value
    return values, clean


def _fills(job: Candidate, named: set[str]) -> bool:
    return bool(named) and named <= set(job.parameters) and job.required <= named


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
    read.missing = sorted(name for name in job.required if any(name not in one for one in supplied))
    read.sure = (data.get("sure") is True or settled) and clean and not read.also
    return read


__all__ = ["K_A_LOGIN", "K_CANDIDATES", "Candidate", "Read", "field_of", "read_of", "refusal"]
