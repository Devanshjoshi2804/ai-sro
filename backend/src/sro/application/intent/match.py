from __future__ import annotations

import re
from dataclasses import dataclass

from sro.application.induction.naming import singular
from sro.domain.skill.skill import Skill, SkillVersion

_WORD = re.compile(r"[^\W_]+", re.UNICODE)

_NOISE = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "can",
        "do",
        "for",
        "from",
        "get",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "the",
        "then",
        "this",
        "to",
        "want",
        "we",
        "with",
        "you",
    }
)

STRUCTURAL_WEIGHT = 3

FLOOR = STRUCTURAL_WEIGHT

TOO_CLOSE = 2


_ASKS = (
    "how many",
    "how much",
    "what is",
    "what are",
    "which",
    "list all",
    "list the",
    "show me all",
    "show all",
    "are there",
    "do we have",
    "is there",
)


def asks(utterance: str) -> bool:
    text = utterance.strip().lower()
    return text.endswith("?") or any(text.startswith(opening) for opening in _ASKS)


def writes(version: SkillVersion) -> bool:
    return any(
        step.network_plan is not None and step.network_plan.is_mutation for step in version.steps
    )


@dataclass(frozen=True, slots=True)
class Candidate:
    skill: Skill
    version: SkillVersion
    score: int
    why: tuple[str, ...]

    unexplained: tuple[str, ...] = ()

    @property
    def confident(self) -> bool:
        return not self.unexplained


def words(text: str) -> frozenset[str]:
    return frozenset(_one(word) for word in _WORD.findall(text.lower()) if word not in _NOISE)


def _one(word: str) -> str:
    return singular(word)


def rank(
    skills: tuple[Skill, ...],
    utterance: str,
    *,
    question: bool | None = None,
    entity: str = "",
) -> tuple[Candidate, ...]:
    asked = words(utterance)
    if not asked:
        return ()

    if question is None:
        question = asks(utterance)
    subject = words(entity) & asked
    scored = [
        candidate
        for skill in skills
        if (candidate := _score(skill, asked)) is not None
        and not (question and writes(candidate.version))
        and not (subject and subject.issubset(candidate.unexplained))
    ]
    return tuple(sorted(scored, key=lambda candidate: -candidate.score))


def ambiguous(candidates: tuple[Candidate, ...]) -> bool:
    return len(candidates) > 1 and candidates[0].score - candidates[1].score < TOO_CLOSE


def _score(skill: Skill, asked: frozenset[str]) -> Candidate | None:
    version = skill.runnable or (skill.latest if skill.versions else None)
    if version is None:
        return None

    key = skill.objective_key
    structural = {
        "system": words(key.target_system),
        "entity": words(key.entity_type),
        "facility": words(key.facility),
        "task": words(key.objective_type),
    }

    score = 0
    why: list[str] = []
    for field, vocabulary in structural.items():
        if hit := asked & vocabulary:
            score += STRUCTURAL_WEIGHT * len(hit)
            why.append(f"{field}: {', '.join(sorted(hit))}")

    if score < FLOOR:
        return None

    described = words(f"{skill.name} {version.summary} {version.when_to_use}")
    if wording := asked & described:
        score += len(wording)
        why.append(f"described as: {', '.join(sorted(wording))}")

    accounted = described.union(*structural.values())
    return Candidate(
        skill=skill,
        version=version,
        score=score,
        why=tuple(why),
        unexplained=tuple(sorted(asked - accounted)),
    )


_REFERRING = frozenset(
    {"them", "these", "those", "they", "it", "that", "this", "same", "again", "ones"}
)


def refers_back(utterance: str) -> bool:
    return bool(set(_WORD.findall(utterance.lower())) & _REFERRING)
