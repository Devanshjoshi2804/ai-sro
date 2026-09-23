from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import domain_matches
from sro.domain.skill.locator import ControlLocator

QUESTION = "question"

MAX_TERM = 200


class TermField(StrEnum):
    """What a term may be compared against.

    Two headers, deliberately. Both are things an operator can point at in an
    open mail, both are short, and neither is the message. There is no `BODY`
    and adding one is not a small change: it would move correspondence into the
    control plane, which is the line ADR 008 draws.
    """

    SENDER = "sender"
    SUBJECT = "subject"


@dataclass(frozen=True, slots=True)
class Term:
    field: TermField
    contains: str

    def __post_init__(self) -> None:
        text = self.contains.strip()
        if not text:
            raise InvariantViolation(f"a {self.field} term with nothing in it matches every mail")
        if len(text) > MAX_TERM:
            raise InvariantViolation(
                f"a {self.field} term of {len(text)} characters is not a phrase somebody "
                f"pointed at; terms are capped at {MAX_TERM}"
            )
        object.__setattr__(self, "contains", text)

    def matches(self, value: str) -> bool:
        if self.contains.lower() in value.lower():
            return True
        wanted = _words(self.contains)
        return bool(wanted) and wanted <= _words(value)

    def nearly(self, value: str) -> bool:
        wanted = _words(self.contains)
        if not wanted or self.matches(value):
            return False
        return bool(wanted & _words(value))


MIN_WORD = 2


def _words(text: str) -> frozenset[str]:
    found = set()
    for raw in re.split(r"[^a-z0-9]+", text.lower()):
        if len(raw) < MIN_WORD:
            continue
        found.add(_stem(raw))
    return frozenset(found)


def _stem(word: str) -> str:
    for ending in ("ed", "s"):
        if word.endswith(ending) and len(word) - len(ending) >= MIN_WORD + 1:
            stem = word[: -len(ending)]
            if len(stem) > MIN_WORD and stem[-1] == stem[-2] and stem[-1] not in "lsz":
                return stem[:-1]
            return stem
    return word


@dataclass(frozen=True, slots=True)
class ValueAt:
    name: str

    where: ControlLocator

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvariantViolation("a value read out of a mail needs the parameter it fills")


@dataclass(frozen=True, slots=True)
class Watch:
    host: str

    terms: tuple[Term, ...]
    values: tuple[ValueAt, ...] = ()

    sender_at: ControlLocator | None = None
    subject_at: ControlLocator | None = None

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise InvariantViolation("a watch names the host it runs on")
        if not self.terms:
            raise InvariantViolation(
                "a watch with nothing to match on fires on every mail that arrives"
            )
        marks = {TermField.SENDER: self.sender_at, TermField.SUBJECT: self.subject_at}
        for field in sorted({term.field for term in self.terms}):
            if marks[field] is None:
                raise InvariantViolation(
                    f"a term on the {field} with nowhere to read the {field} from never "
                    f"matches: mark it on the mail"
                )
        names = [value.name for value in self.values]
        if len(set(names)) != len(names):
            raise InvariantViolation("two places to read the same parameter from is one too many")

    def matches(self, host: str, *, sender: str, subject: str) -> bool:
        if not domain_matches(host, self.host):
            return False
        against = {TermField.SENDER: sender, TermField.SUBJECT: subject}
        return all(term.matches(against[term.field]) for term in self.terms)

    def nearly(self, host: str, *, sender: str, subject: str) -> tuple[str, ...]:
        if not domain_matches(host, self.host) or self.matches(
            host, sender=sender, subject=subject
        ):
            return ()
        return tuple(
            term.contains
            for term in self.terms
            if term.field is TermField.SUBJECT and term.nearly(subject)
        )

    @property
    def reads(self) -> tuple[str, ...]:
        return tuple(value.name for value in self.values)
