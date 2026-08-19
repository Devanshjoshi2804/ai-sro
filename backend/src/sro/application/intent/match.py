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

from sro.application.induction.naming import singular
from sro.domain.skill.skill import Skill, SkillVersion

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
"""Letters and digits in any alphabet. ``[a-z0-9]+`` split "zürich" into "z"
and "rich", so a facility, a supplier or a customer whose name is not plain
ASCII was matched on fragments of itself -- and "rich" is a word that turns
up elsewhere."""

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
"""Openings that make a sentence a question rather than an instruction.

Phrases, not words, and matched at the start: single words are how this goes
wrong. "count" reads like a question and is one of the most consequential tasks
in a warehouse; "show" appears in "show me how to create one". A question is
recognised by how it opens, or by ending in a question mark.

Deliberately incomplete. A question this misses is treated as an instruction and
still has to pass every other check, which is the safe direction to be wrong in;
an instruction misread as a question would refuse to do work somebody asked for.
"""


def asks(utterance: str) -> bool:
    """Whether this sentence wants to be told something rather than have it done."""
    text = utterance.strip().lower()
    return text.endswith("?") or any(text.startswith(opening) for opening in _ASKS)


def writes(version: SkillVersion) -> bool:
    """Whether performing this skill changes the target system."""
    return any(
        step.network_plan is not None
        and step.network_plan.method.upper() not in {"GET", "HEAD", "OPTIONS"}
        for step in version.steps
    )


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
    """The meaningful words of a sentence, in one number.

    Singular and plural are the same word here. "How many suppliers are there"
    shares no token with an objective key that says `supplier`, so the sentence
    every operator types to ask for a count matched nothing at all and went to
    the planner while the taught skill sat one row away. Counting is asked for
    in the plural; things are named in the singular. That is not two subjects.
    """
    return frozenset(_one(word) for word in _WORD.findall(text.lower()) if word not in _NOISE)


def _one(word: str) -> str:
    """See :func:`naming.singular`. Shared with induction on purpose: the words
    a skill is named after and the words a sentence is matched on have to be
    reduced the same way, or the match fails on spelling."""
    return singular(word)


def rank(
    skills: tuple[Skill, ...],
    utterance: str,
    *,
    question: bool | None = None,
    entity: str = "",
) -> tuple[Candidate, ...]:
    """Every skill that structurally matches, best first.

    A question never matches a skill that writes. "How many transport modes are
    in the list" shares every noun with the skill that *creates* one, scores
    well on all of them, and the only honest answer to matching it is a form
    asking which transport mode to create -- which is the wrong-task failure
    wearing the face of a helpful prompt.

    Ranking a writer lower would not do: the question that asks for a count and
    the instruction that asks for a creation are not two points on one scale.

    ``entity`` is what the sentence says it is about, where that was read. A
    skill that accounts for the verb and not the subject is not a candidate:
    "give me list of clients" matched three skills on the word "list" alone and
    offered suppliers, addresses and transport modes -- three answers about the
    wrong thing, from a matcher that had already recorded "clients" as a word it
    could not explain.
    """
    asked = words(utterance)
    if not asked:
        return ()

    # The reading, where there is one. "Show me one supplier in detail" opens
    # with none of the phrases this recognises and ends in no question mark, so
    # it was taken for an instruction and the skill that *creates* a supplier
    # was offered as one of two things it might have meant.
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
    # The newest *runnable* one, falling back to the newest there is. A
    # second demonstration lands at RECORDED, so always taking the newest
    # took a working skill offline the moment somebody re-taught it -- while
    # a skill that has only ever been recorded must still be found, and
    # refused with a reason, rather than reading as never taught.
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
"""Words that point at something already said rather than naming it.

A follow-up is recognised by referring, not by failing to match. "Release the
wave" names a different task and matches nothing taught; carrying the previous
subject into it produced a confident offer to list transport modes, which is
the wrong-task failure arriving through the back door.
"""


def refers_back(utterance: str) -> bool:
    """Whether this sentence leans on the one before it for its subject.

    Read off the raw words rather than the filtered ones: "it" and "this" are
    noise when matching a skill and are the whole signal here, so "run it" would
    otherwise never be recognised as referring to anything.
    """
    return bool(set(_WORD.findall(utterance.lower())) & _REFERRING)
