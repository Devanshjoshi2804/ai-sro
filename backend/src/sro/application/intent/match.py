"""Rank taught skills against a sentence, structurally first.

No model, and not a similarity search. A skill is only a candidate if something
structural matches -- its system, its entity, its facility or its verb -- and
wording only orders the candidates that survived. The failure this is arranged
against is the expensive one: a confident wrong match does the wrong thing
immediately, with no reasoning left in the cached path to catch it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sro.domain.skill.skill import Skill, SkillVersion

_WORD = re.compile(r"[a-z0-9]+")

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
"""Words that carry no warehouse meaning. Deliberately short: a stop list that
grows starts deleting the words the vocabulary is made of."""

STRUCTURAL_WEIGHT = 3
"""A hit on the objective key counts for three wording hits. The key is what the
demonstration proved; the summary is how somebody described it."""

FLOOR = STRUCTURAL_WEIGHT
"""At least one structural hit. Below this nothing is a match -- the answer is a
question or the planner, never the nearest skill."""

TOO_CLOSE = 2
"""Two candidates within this are not ranked, they are offered. Guessing between
them is the wrong-match failure with extra steps."""


@dataclass(frozen=True, slots=True)
class Candidate:
    skill: Skill
    version: SkillVersion
    score: int
    why: tuple[str, ...]
    """Which words matched what. Shown to the operator, and logged: match
    confidence drifting downwards is the first sign a system has changed."""

    unexplained: tuple[str, ...] = ()
    """Words in the sentence this skill accounts for nowhere.

    Measured because the dangerous match is the *partial* one. "Count inventory
    in SG" hits the facility and the entity of an inventory *adjust* skill, and
    scores well, while the only word that says what to do -- "count" -- matches
    nothing. A skill that cannot explain the verb is not a confident answer.
    """

    @property
    def confident(self) -> bool:
        return not self.unexplained


def words(text: str) -> frozenset[str]:
    return frozenset(word for word in _WORD.findall(text.lower()) if word not in _NOISE)


def rank(skills: tuple[Skill, ...], utterance: str) -> tuple[Candidate, ...]:
    """Every skill that structurally matches, best first."""
    asked = words(utterance)
    if not asked:
        return ()

    scored = [candidate for skill in skills if (candidate := _score(skill, asked)) is not None]
    return tuple(sorted(scored, key=lambda candidate: -candidate.score))


def ambiguous(candidates: tuple[Candidate, ...]) -> bool:
    return len(candidates) > 1 and candidates[0].score - candidates[1].score < TOO_CLOSE


def _score(skill: Skill, asked: frozenset[str]) -> Candidate | None:
    version = skill.versions[-1] if skill.versions else None
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
