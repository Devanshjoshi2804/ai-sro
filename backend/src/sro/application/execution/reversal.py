from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sro.application.induction.diff import url_shape
from sro.domain.execution.run import Run
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import Skill


@dataclass(frozen=True, slots=True)
class Reversal:
    skill_id: SkillId
    version: int

    removes: str

    parameters: dict[str, str]


def reversal_for(run: Run, skills: Sequence[Skill]) -> Reversal | None:
    made = _what_it_made(run)
    if made is None:
        return None

    for skill in skills:
        version = skill.runnable
        if version is None:
            continue
        for step in version.steps:
            plan = step.network_plan
            if plan is None or plan.method.upper() != "DELETE":
                continue
            if made not in _shapes_for(plan.url.raw):
                continue
            wanted = {p.name for p in version.inputs}
            if not wanted or not wanted <= run.derived.keys():
                continue
            return Reversal(
                skill_id=skill.id,
                version=version.version,
                removes=step.intent,
                parameters={name: run.derived[name] for name in wanted},
            )
    return None


def _what_it_made(run: Run) -> str | None:
    urls = [
        step.url
        for step in run.steps
        if step.method is not None and step.method.upper() == "POST" and step.url is not None
    ]
    if len(urls) != 1:
        return None
    return url_shape(urls[0])


def _shapes_for(delete_url: str) -> tuple[str, str]:
    shape = url_shape(delete_url)
    return shape, shape.rsplit("/", 1)[0]
