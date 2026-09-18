"""What a run found out about a step, kept for the next one.

`mark_stale` is this module's negative twin: a step that only the weakest rung
could find is recorded as about to break. Nothing recorded what the rung
actually FOUND, so the discovery lived for one command and the next run climbed
the same ladder to reach the same control.

Measured on the deployment, 2026-09-17. `Create a Customer Type` step 2 clicks
a tab whose recorded identity no longer matches anything: three runs in one
afternoon paid for two model calls each, worked out that the control is called
"Customer Types", and wrote it into a log line. At the end of the afternoon the
job knew exactly what it knew at the start. That is not a system that learns --
it is one that repeats.

**What is kept is a locator, not a point.** A point is where a control was on
one screen at one size; a name is what it is. The rung that looks at a picture
is the expensive one and the only one that can recover from a page that moved,
so its answer is the one worth keeping -- as `text=Customer Types`, which every
run after it can try first for the price of a DOM query.

**A run may write this and may not write the workflow.** The workflow is what a
mining pass produces from evidence; this is what one run observed, and the two
are kept apart so neither rewrites the other. Same reason the stale table
exists, and the same shape: one row per step, the last answer winning.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # a domain type used in a signature, imported for the checker only
    from sro.domain.skill.workflow import Step

K_NAME = 80
"""How much of a control's name is kept. A button's accessible name is a few
words; eighty characters is a label, and anything longer is a paragraph that
happens to sit in a `<div>`."""

WORTH_KEEPING = ("sight", "css_path", "text")
"""The rungs whose answer is worth writing down.

`component` and `test_id` are the job's own recorded identity -- when they
match, the job is right and there is nothing to learn. These three are what a
run falls back to when it is not, and `sight` is the one that costs a model
call and a picture.
"""


@dataclass(frozen=True, slots=True)
class LearnedStep:
    """One step, and the locator that last worked for it."""

    ord: int
    strategy: str
    query: str
    found_by: str
    """Which rung produced it, so a reader can tell a name a picture found from
    one a css path did."""

    holds: int | None = None
    """How many characters this step's box will take, where a run found out.

    A field truncates in the browser, before the request, and the only moment
    the difference exists is between the value the step was given and the value
    the box ends up holding. Catching that every time is repeating; this is the
    half that makes it learning.

    None until a run has been told otherwise -- which is every step that does
    not type, and every typing step whose value has always fitted."""

    @property
    def usable(self) -> bool:
        return bool(self.strategy and self.query)


@dataclass(frozen=True, slots=True)
class Taught:
    """One thing a job changed its mind about, and what it changed from.

    A learned fact is stored as one row per step with the last answer winning,
    which is right for the question a run asks -- what should I try first --
    and leaves nothing behind. A locator learned from a screenshot that quietly
    replaced one learned from a component is a job that drifted, and the only
    record of it was the difference between two runs nobody compared.

    So a change is a thing with a shape: what it was about, what it was, what
    it became, which run taught it and how. A confirmation is not a change --
    see `changed_by` -- because four hundred rows saying "the same locator
    again" bury the four that matter.
    """

    ord: int
    about: str
    was: str
    now: str
    by_run: str = ""
    found_by: str = ""

    @property
    def worth_keeping(self) -> bool:
        """Whether this is a change at all.

        A run that found what the run before it found has taught nothing. And
        the FIRST answer is worth keeping: `was` empty and `now` set is a job
        learning something it never knew, which is the row somebody reads to
        find out where a locator nobody demonstrated came from.
        """
        return self.now.strip() != self.was.strip()


LOCATOR = "locator"
HOLDS = "holds"
"""What a change can be about. Two constants rather than two tables: they are
the same event -- a job changed its mind about a step -- and a reader wants
them in one order."""


def changed_by(
    was: LearnedStep | None, now: LearnedStep, *, by_run: str = ""
) -> tuple[Taught, ...]:
    """What this step just learned that it did not already know.

    Both halves in one pass, because a run can change both at once: the rung
    that found a control by picture also measured what its box would hold.

    A locator is compared as `strategy=query`, which is what makes it the same
    locator: the two together are the answer, and the rung that produced it is
    recorded beside the change rather than folded into the comparison -- the
    same query found twice is the same answer however it was found the second
    time, and a row per rung would say a job had drifted when nothing moved.
    """
    changes = [
        Taught(
            ord=now.ord,
            about=LOCATOR,
            was=_as_locator(was),
            now=_as_locator(now),
            by_run=by_run,
            found_by=now.found_by,
        ),
        Taught(
            ord=now.ord,
            about=HOLDS,
            was="" if was is None or was.holds is None else str(was.holds),
            now="" if now.holds is None else str(now.holds),
            by_run=by_run,
            found_by=now.found_by,
        ),
    ]
    return tuple(one for one in changes if one.worth_keeping)


def _as_locator(step: LearnedStep | None) -> str:
    if step is None or not step.usable:
        return ""
    return f"{step.strategy}={step.query}"


def learned_from(ord_: int, matched_by: str | None, result: object) -> LearnedStep | None:
    """What this step's reply is worth keeping, or None.

    Nothing is kept for a step the job's own identity found: that is the
    ordinary case and writing it down would be the job telling itself what it
    already says. Nothing is kept from a reply that names no control either --
    a run cannot pass on what it did not learn.
    """
    if matched_by not in WORTH_KEEPING or not isinstance(result, dict):
        return None
    control = result.get("control")
    matched = result.get("matched")
    # The locator that worked, where the browser named one: a css path that
    # matched is a css path worth trying first next time.
    if isinstance(matched, dict) and matched.get("strategy") in WORTH_KEEPING:
        strategy, query = str(matched.get("strategy") or ""), str(matched.get("query") or "")
        if strategy and query:
            return LearnedStep(ord_, strategy, query[:K_NAME], str(matched_by))
    # Otherwise the control the point turned out to be, named. This is the
    # sight rung's answer turned into something cheap.
    if isinstance(control, dict):
        name = str(control.get("name") or "").strip()
        item_id = str(control.get("item_id") or "").strip()
        if item_id:
            return LearnedStep(ord_, "component", item_id[:K_NAME], str(matched_by))
        if name:
            return LearnedStep(ord_, "text", name[:K_NAME], str(matched_by))
    return None


def limits_for(
    steps: Sequence[Step],
    learned: Iterable[LearnedStep],
    declared: Mapping[str, int] = MappingProxyType({}),
) -> dict[str, int]:
    """What the boxes behind a job's parameter names will hold, by name.

    A limit is learnt about a STEP, because a step is what typed into the box.
    Everything that wants to use it ahead of time -- the question asked of
    somebody whose value was too long, the card asked before the press -- knows
    a parameter's name and not which step fills it. This is that translation,
    in one place, because two copies of it drift the day a job fills one name
    at two steps.

    Which is the case the `min` is for. A name typed at two steps has two
    limits and only the smaller one is true of the run: a value that fits the
    first box and not the second still stops the job, and a card that promised
    otherwise lied to the person who pressed.

    `declared` is the same rule applied to a second kind of source. What a run
    LEARNT is a measurement and what the vendor's dictionary and the captured
    form DECLARE is a claim, and neither gets to overrule the other here: a
    limit is a ceiling, so every ceiling anything names applies and the lowest
    one binds. Being wrong low asks somebody to shorten a value further than
    they had to. Being wrong high sends `NEWSROTEST`, keeps `NEWS`, and answers
    201 -- see `application/execution/declared.py`.

    Empty by default, which is every caller that has only ever had the
    measurements and behaves exactly as it did.
    """
    holds = {one.ord: one.holds for one in learned if one.holds is not None}
    limits: dict[str, int] = dict(declared)
    for step in steps:
        if (cap := holds.get(step.order)) is None:
            continue
        for name in step.parameters:
            limits[name] = min(cap, limits.get(name, cap))
    return limits


def too_long(values: Mapping[str, str], limits: Mapping[str, int]) -> dict[str, int]:
    """The values that will not fit, and what their box actually takes.

    The limit and not a flag: "this will not fit" sends somebody back with a
    value that does not fit either, and they have no way to know why -- the
    browser truncates in silence and says nothing at all. What a person needs
    in order to answer once is the number.
    """
    return {
        name: limits[name]
        for name, value in values.items()
        if name in limits and isinstance(value, str) and len(value) > limits[name]
    }
