"""What a skill does, in a sentence, and when to reach for it.

Composed from the evidence rather than written by a model: the objective, the
call the skill writes with, the parameters the diff found, and — where the
operator narrated — their own closing sentence, quoted rather than paraphrased.

These two fields are not decoration. They are what an operator's sentence is
matched against when they ask for work later, so a skill nobody can find is a
skill that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.skill import SkillStep


@dataclass(frozen=True, slots=True)
class Description:
    summary: str
    when_to_use: str


def compose(
    objective: ObjectiveKey,
    steps: tuple[SkillStep, ...],
    parameters: tuple[Parameter, ...],
) -> Description:
    action = objective.objective_type.replace("_", " ")
    subject = objective.entity_type.replace("_", " ")
    where = f"{objective.facility} on {objective.target_system}"
    inputs = [p.name for p in parameters if p.kind is ParameterKind.INPUT]

    summary = f"{_sentence_case(action)} {subject} at {where}."
    summary += f" {len(steps)} step{'' if len(steps) == 1 else 's'}"
    write = _write(steps)
    summary += f", writing {write}." if write else ", reading only."

    spoken = _closing_words(steps)
    if spoken:
        # The operator's own words outrank ours: they describe the task as the
        # warehouse describes it, which is the vocabulary a request will use.
        summary += f' In the demonstrator\'s words: "{spoken}"'

    when = f"Use to {action} {subject} at {objective.facility} in {objective.target_system}."
    if inputs:
        when += f" Needs {', '.join(inputs)}."
    if any(step.requires_human for step in steps):
        when += " One step needs a human."
    hints = [step.branch_hint for step in steps if step.branch_hint]
    if hints:
        when += f" Not covered: {hints[0]}"

    return Description(summary=summary, when_to_use=when)


def _write(steps: tuple[SkillStep, ...]) -> str | None:
    """The mutating call the skill exists to make, named by method and path."""
    for step in steps:
        plan = step.network_plan
        if plan is not None and plan.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            return f"{plan.method} {urlsplit(str(plan.url)).path}"
    return None


def _closing_words(steps: tuple[SkillStep, ...]) -> str | None:
    """What the operator said last. It is usually what the task was for."""
    for step in reversed(steps):
        if step.narration.strip():
            return " ".join(step.narration.split())[:200]
    return None


def _sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text
