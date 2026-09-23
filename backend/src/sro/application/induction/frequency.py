from __future__ import annotations

from enum import StrEnum

from sro.application.induction.diff import Alignment, Parameterisation

PART_OF_THE_TASK = 2 / 3


class Standing(StrEnum):
    ALWAYS = "always"

    CONDITIONAL = "conditional"

    NOISE = "noise"


def standing_of(alignment: Alignment, parameterisation: Parameterisation) -> dict[int, Standing]:
    standing: dict[int, Standing] = {}
    for index, count in alignment.seen.items():
        if count / alignment.doings >= PART_OF_THE_TASK:
            standing[index] = Standing.ALWAYS
        elif parameterisation.conditional_on(index) is not None:
            standing[index] = Standing.CONDITIONAL
        else:
            standing[index] = Standing.NOISE
    return standing
