from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sro.domain.skill.workflow import Step

K_NAME = 80

WORTH_KEEPING = ("sight", "css_path", "text")


@dataclass(frozen=True, slots=True)
class LearnedStep:
    ord: int
    strategy: str
    query: str
    found_by: str

    holds: int | None = None

    @property
    def usable(self) -> bool:
        return bool(self.strategy and self.query)


@dataclass(frozen=True, slots=True)
class Taught:
    ord: int
    about: str
    was: str
    now: str
    by_run: str = ""
    found_by: str = ""

    @property
    def worth_keeping(self) -> bool:
        return self.now.strip() != self.was.strip()


LOCATOR = "locator"
HOLDS = "holds"


def changed_by(
    was: LearnedStep | None, now: LearnedStep, *, by_run: str = ""
) -> tuple[Taught, ...]:
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
    if matched_by not in WORTH_KEEPING or not isinstance(result, dict):
        return None
    control = result.get("control")
    matched = result.get("matched")
    if isinstance(matched, dict) and matched.get("strategy") in WORTH_KEEPING:
        strategy, query = str(matched.get("strategy") or ""), str(matched.get("query") or "")
        if strategy and query:
            return LearnedStep(ord_, strategy, query[:K_NAME], str(matched_by))
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
    holds = {one.ord: one.holds for one in learned if one.holds is not None}
    limits: dict[str, int] = dict(declared)
    for step in steps:
        if (cap := holds.get(step.order)) is None:
            continue
        for name in step.parameters:
            limits[name] = min(cap, limits.get(name, cap))
    return limits


def too_long(values: Mapping[str, str], limits: Mapping[str, int]) -> dict[str, int]:
    return {
        name: limits[name]
        for name, value in values.items()
        if name in limits and isinstance(value, str) and len(value) > limits[name]
    }
