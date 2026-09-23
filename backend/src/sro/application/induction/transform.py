from __future__ import annotations

from collections.abc import Iterator

from sro.domain.skill.transform import LOWER, PAD, PREFIX, STRIP, SUFFIX, UPPER, Transform

SHORTEST_SOURCE = 2


def discover(source: str, target: str) -> Transform | None:
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
    return candidate if candidate.apply(source) == target else None


def _locate(core: str, target: str) -> tuple[int, str | None, int | None] | None:
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
