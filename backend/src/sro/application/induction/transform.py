"""Reading, off two examples, what was done to a value on its way between steps.

The diff finds a data dependency by exact equality: a value the response carried
and the next call sent. Nothing else was ever recognised, so a value that was
reformatted on the way -- `42` answered by the WMS, `LPN-00042` sent to the ERP
-- looked like a value nobody could account for, and became a question for an
operator who has no idea where the number comes from either.

What makes this evidence rather than pattern-matching is where it is used: the
transformation is read off one run and then has to explain the *other* run's
pair as well, from the same place in the same response. Two runs agreeing is the
same standard the rest of the diff holds itself to. See
docs/16-what-others-have-solved.md, and Leno et al. (arXiv:2001.01007) for the
general form of the problem -- theirs searches a space of programs with A*,
which is the right shape once a transformation is worth more than the six this
can express.
"""

from __future__ import annotations

from collections.abc import Iterator

from sro.domain.skill.transform import LOWER, PAD, PREFIX, STRIP, SUFFIX, UPPER, Transform

SHORTEST_SOURCE = 2
"""A single character carried into a longer string is not evidence of anything.
`7` appears inside a hundred values by accident, and a rule read off one of them
would be a confident wrong answer of the kind ADR 004 exists to prevent."""


def discover(source: str, target: str) -> Transform | None:
    """How `source` becomes `target`, if this can say so exactly.

    None where it cannot, which is most of the time and is the point: an
    unexplained value stays a value the operator is asked for, and being asked
    is better than being sent something invented.
    """
    if source == target or len(source.strip()) < SHORTEST_SOURCE or not target:
        return None

    ops: list[tuple[str, ...]] = []
    core = source
    if source.strip() != source:
        ops.append((STRIP,))
        core = source.strip()

    found = _locate(core, target)
    if found is None:
        return None
    at, cased, padded = found

    if cased is not None:
        ops.append((cased,))
        core = core.upper() if cased == UPPER else core.lower()
    if padded is not None:
        ops.append((PAD, str(padded), "0"))
        core = core.rjust(padded, "0")
    if at:
        ops.append((PREFIX, target[:at]))
    if at + len(core) < len(target):
        ops.append((SUFFIX, target[at + len(core) :]))

    candidate = Transform(tuple(ops))
    # Built from the pair, then checked against it. A construction that does not
    # reproduce its own example is a bug, and shipping it would put an invented
    # value in a warehouse write.
    return candidate if candidate.apply(source) == target else None


def _locate(core: str, target: str) -> tuple[int, str | None, int | None] | None:
    """Where this value sits inside the target, and what was done to it there.

    Tried in order of how much is being claimed: as it is, then recased, then
    zero-padded -- so a value that appears verbatim is never explained by a
    longer story about padding.
    """
    for candidate, cased, padded in _candidates(core, target):
        at = _placed(candidate, target)
        if at is not None:
            return at, cased, padded
    return None


def _candidates(core: str, target: str) -> Iterator[tuple[str, str | None, int | None]]:
    yield core, None, None
    if core.upper() != core:
        yield core.upper(), UPPER, None
    if core.lower() != core:
        yield core.lower(), LOWER, None
    if core.isdigit():
        for width in range(len(core) + 1, len(target) + 1):
            yield core.rjust(width, "0"), None, width


def _placed(candidate: str, target: str) -> int | None:
    """The first occurrence that is not part of a longer number.

    `42` occurs inside `LPN-00042`, and reading that as "prefix `LPN-000`"
    reproduces this example and gets the next one wrong: the run where the WMS
    answered `7` would be sent `LPN-0007`. A digit touching a digit is not the
    boundary of the value -- so that occurrence is skipped, and padding is
    found instead, which is what actually happened.
    """
    start = 0
    while (at := target.find(candidate, start)) != -1:
        after = at + len(candidate)
        touching = (at and candidate[0].isdigit() and target[at - 1].isdigit()) or (
            after < len(target) and candidate[-1].isdigit() and target[after].isdigit()
        )
        if not touching:
            return at
        start = at + 1
    return None
