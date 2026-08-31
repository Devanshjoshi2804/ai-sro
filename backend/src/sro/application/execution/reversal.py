"""Whether what a run made can be taken back, and by which skill.

A visible undo is the strongest thing an agentic surface has, because trust is
knowing you can recover from a mistake. It is also where this design could most
easily begin guessing, so it does not: an undo is offered on three facts or not
at all.

  - the run's write was a POST to some resource shape, and
  - a runnable skill in this tenant's library DELETEs that same shape, and
  - the run read back the identifier that skill needs.

`url_shape` answers the middle one and is the same function induction uses to
decide two calls are the same call. Nothing here is proposed as a reverse
because it looked like one.

Most tasks will have no undo for a long time, because nobody demonstrates
deleting things. That is honest: the fallback is the operator fixing it while
we watch, which is what they were going to do anyway.
"""

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
    parameters: dict[str, str]


def reversal_for(run: Run, skills: Sequence[Skill]) -> Reversal | None:
    """The skill that would undo what this run made, or ``None``.

    The first skill in the tenant's library that answers all three facts wins.
    Two skills that both delete the same shape is not a case this refuses to
    handle by picking the first -- it is a case nobody has produced yet.
    """
    made = _what_it_made(run)
    if made is None:
        return None

    for skill in skills:
        version = skill.runnable
        if version is None:
            # `runnable` is the one place "may this skill actually be asked to
            # run" is answered. Offering a version it would refuse teaches an
            # operator that the button lies.
            continue
        for step in version.steps:
            plan = step.network_plan
            if plan is None or plan.method.upper() != "DELETE":
                continue
            if _collection(plan.url.raw) != made:
                continue
            wanted = {p.name for p in version.inputs}
            if not wanted or not wanted <= run.derived.keys():
                # Either the delete needs nothing identifiable (so it is not
                # addressing the one record this run made), or it needs
                # something this run never read back. A button that cannot
                # name what it would remove is worse than no button.
                continue
            return Reversal(
                skill_id=skill.id,
                parameters={name: run.derived[name] for name in wanted},
            )
    return None


def _what_it_made(run: Run) -> str | None:
    """The shape of the one resource this run created, if it created one."""
    urls = [
        step.url
        for step in run.steps
        if step.method is not None and step.method.upper() == "POST" and step.url is not None
    ]
    if len(urls) != 1:
        # Nothing written, or several things. A run that made two records is
        # not one this can offer to unmake with a single press.
        return None
    return url_shape(urls[0])


def _collection(url: str) -> str:
    """The resource a call acts on, with its trailing identifier set aside.

    A DELETE addresses one record -- `.../workOperations/$operation_id` -- and
    what has to match the shape of a bare `POST .../workOperations` is the
    collection the record belongs to, not the record's own address. The
    identifier segment is dropped before `url_shape` runs rather than after:
    `url_shape` only recognises an identifier by the digits in it, and a
    skill's own placeholder -- `$operation_id` -- carries none.
    """
    return url_shape(url.rsplit("/", 1)[0])
