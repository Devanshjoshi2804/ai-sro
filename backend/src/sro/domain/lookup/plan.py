from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from sro.domain.knowledge.entry import EntryKind, KnowledgeEntry

HOW = ("call", "screen")

K_MAX_LOOKUPS = 6


@dataclass(frozen=True, slots=True)
class Lookup:
    system: str
    how: Literal["call", "screen"]
    target: str

    params: dict[str, str] = field(default_factory=dict)
    why: str = ""
    cites: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Asked:
    key: str
    question: str
    options: tuple[str, ...]
    because: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Plan:
    question: str
    lookups: tuple[Lookup, ...] = ()
    asks: Asked | None = None
    why: str = ""

    @property
    def ready(self) -> bool:
        return self.asks is None and bool(self.lookups)


def unknown_targets(lookups: list[Lookup], known: list[KnowledgeEntry]) -> list[str]:
    keys = {entry.key for entry in known}
    return sorted({lookup.target for lookup in lookups if lookup.target not in keys})


def in_declared_slots(lookups: list[Lookup], known: list[KnowledgeEntry]) -> list[Lookup]:
    slots: dict[str, set[str]] = {}
    for entry in known:
        declared = entry.body.get("params") if isinstance(entry.body, dict) else None
        if isinstance(declared, list):
            slots.setdefault(entry.key, set()).update(str(name) for name in declared)
    return [
        replace(
            one,
            params={k: v for k, v in one.params.items() if k in slots.get(one.target, set())},
        )
        for one in lookups
    ]


def uncited(lookups: list[Lookup], known: list[KnowledgeEntry]) -> list[str]:
    keys = {entry.key for entry in known}
    return sorted(
        {lookup.target for lookup in lookups if not any(cite in keys for cite in lookup.cites)}
    )


def open_question_for(asked: str, known: list[KnowledgeEntry]) -> Asked | None:
    words = {_stem(word) for word in asked.split()}
    words.discard("")
    settled = {
        entry.key
        for entry in known
        if entry.kind is EntryKind.QUESTION
        and isinstance(entry.body, dict)
        and entry.body.get("answer")
    }
    for entry in known:
        if entry.kind is not EntryKind.QUESTION or entry.superseded_by:
            continue
        if entry.key in settled:
            continue
        body = entry.body if isinstance(entry.body, dict) else {}
        if not _stops(asked, words, entry.key):
            continue
        return Asked(
            key=entry.key,
            question=str(body.get("question") or entry.title),
            options=_listed(body.get("options")),
            because=_listed(body.get("because")),
        )
    return None


def _stops(asked: str, words: set[str], key: str) -> bool:
    parts = [part for part in key.split("/") if part]
    if len(parts) < 3:
        return False
    entity = {_stem(word) for word in parts[1].split("_")}
    entity.discard("")
    about = parts[2]

    if about == "collection":
        return bool(words & entity)
    if about == "value" and len(parts) > 3:
        return parts[3].lower() in asked.lower()
    return False


def _listed(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(one) for one in value if one)


def _stem(word: str) -> str:
    bare = word.strip(",.?!\"'()[]:;").lower()
    if len(bare) < 4:
        return ""
    return bare[:-1] if bare.endswith("s") and len(bare) > 4 else bare
