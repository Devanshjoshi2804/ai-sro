"""What a step's frequency says about whether it is part of the task.

Rationale and the rejected alternatives:
docs/07-adr/015-a-step-is-decided-by-how-often-it-happens.md.
"""

from __future__ import annotations

from enum import StrEnum

from sro.application.induction.diff import Alignment, Parameterisation

PART_OF_THE_TASK = 2 / 3
"""What share of the doings has to contain a step before it is the task itself
rather than an exception to it.

A share, never a count, so it means the same at four doings and at four
thousand: a step three doings made is the task when there were four of them and
a rounding error when there were four thousand, and a threshold counted in
doings would quietly change its mind about a skill as the task got more popular.

Two in three rather than a bare majority, because at the counts this actually
sees a majority is one person's habit. Four doings is the real case -- somebody
demonstrating a task they do -- and there the difference between half and a
majority is a single operator filling a field they usually skip. A rule that
flips on one doing is not a rule. Two in three is the smallest share that
survives one dissenter at four, which is the smallest batch anyone is going to
hand this.

It is not a precise number and does not pretend to be. It decides only what
happens to a step nothing else explains: a rare step with a supplied value
behind it is kept whatever this says, because that is a branch and not a
frequency question at all.
"""


class Standing(StrEnum):
    """What a step's place in the task is, once the doings have been counted."""

    ALWAYS = "always"
    """Part of the task. Runs every time."""

    CONDITIONAL = "conditional"
    """Part of the task, on a condition the doings named: it happens when
    somebody supplies a particular value and is skipped when nobody does. This
    is `SkillStep.when` -- the field already exists for exactly this and names
    the parameter whose presence decides whether the step happens at all."""

    NOISE = "noise"
    """Not part of the task. A mis-click, a field typed and corrected, a panel
    opened to look at -- the accidents union would have learned."""


def standing_of(alignment: Alignment, parameterisation: Parameterisation) -> dict[int, Standing]:
    """Decide each aligned step's place in the task, by reference-frame index.

    No model decides this, and ADR 004 is why: identity -- what a step *is*,
    what a value *means* -- is settled by evidence or not settled at all. So
    this reads two things and nothing else. How many of the doings contained
    the step, which :func:`align_all` counted; and which parameter, if any, the
    step's own keystroke fills, which the diff already worked out from what the
    demonstrations sent. Both are facts somebody could check by re-reading the
    recordings. A model asked "is this step really part of the task?" would
    produce a confident answer to a question the counts already answer, and
    would produce one just as confidently where they do not.

    Rarity on its own drops nothing. A step below the threshold whose presence
    tracks a supplied value is a branch, however rare: every doing that made it
    was a doing where somebody supplied that field, and one in a hundred is the
    rate a real branch runs at, not evidence against it. Dropping it is how a
    skill silently stops handling the case somebody needed it for -- which is
    exactly what happened to the address lookup. A rare step with nothing
    explaining it is a fumble, and that is the only thing rarity decides.

    The keystroke, specifically, via
    :meth:`Parameterisation.conditional_on` -- not "this step mentions an
    optional parameter". The write that carries the field goes out either way,
    carrying the absent form the demonstration sent, so a rare write is a
    fumble however many nullable fields it happens to fill in.
    """
    # How many doings there were. Not carried on `Alignment`, and read off the
    # counts instead: a step every doing contained is counted once per doing,
    # so the largest count is the number of doings whenever the task has one
    # step everybody made -- which every task with a write does, since the
    # write is the task. Where no step at all is universal this reads low, the
    # shares come out high, and steps are kept that a true count would have
    # called noise. That is the direction `align_all` already errs in, and the
    # cheap way out of it -- keeping a step nobody can explain -- costs a
    # reviewer a question, where the other direction costs the branch.
    #
    # ponytail: exact would be `align_all` recording `len(runs)` on the
    # `Alignment` it returns. One field, worth adding the day a caller has a
    # batch of doings with nothing in common -- not before.
    doings = max(alignment.seen.values(), default=0)
    if not doings:
        return {}

    standing: dict[int, Standing] = {}
    for index, count in alignment.seen.items():
        if count / doings >= PART_OF_THE_TASK:
            standing[index] = Standing.ALWAYS
        elif parameterisation.conditional_on(index) is not None:
            standing[index] = Standing.CONDITIONAL
        else:
            standing[index] = Standing.NOISE
    return standing
