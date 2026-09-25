from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal

from sro.application.ports.page import PageDriver
from sro.application.runtime.sight_lane import SightLane
from sro.application.runtime.step import LaneContext
from sro.application.runtime.ui_lane import K_UI_WAIT_S
from sro.domain.execution.compose import Composed, normal
from sro.domain.execution.evidence import primary_gesture
from sro.domain.execution.lanes import Lane
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.skill.workflow import Step


@dataclass(frozen=True, slots=True)
class Filled:
    lane: Lane | None
    asks: Literal["", "no_field", "ambiguous", "no_option"] = ""
    options: tuple[str, ...] = ()
    learned: Mapping[str, str] = field(default_factory=dict)
    detail: str = ""


class FillField:
    def __init__(
        self, driver: PageDriver, sight: SightLane | None, *, wait_s: float = K_UI_WAIT_S
    ) -> None:
        self._driver = driver
        self._sight = sight
        self._wait_s = wait_s

    async def fill(
        self,
        composed: Composed,
        value: str,
        write: Step,
        ctx: LaneContext,
        *,
        learned: LearnedStep | None = None,
    ) -> Filled:
        held = ctx.held
        primary = primary_gesture(write, ctx.by_id)
        if held is None or primary is None:
            return Filled(None, detail="no page, or no recorded write to fill the field for")
        target = primary.action.target
        frame_path = (
            None
            if primary.action.frame_path is None
            else [asdict(hop) for hop in primary.action.frame_path]
        )
        locator = (
            {"strategy": learned.strategy, "query": learned.query}
            if learned is not None and learned.usable
            else None
        )
        payload: dict[str, object] = {
            "action": composed.action,
            "value": value,
            "write": False,
            "target": {
                "role": composed.role,
                "name": composed.label,
                "landmarks": [] if target is None else [asdict(one) for one in target.landmarks],
            },
            "frame_path": frame_path,
            "learned": locator,
        }
        ctx.check_stop()
        found = await self._driver.resolve(held.session, held.target_id, payload)
        if found.candidates > 1 or found.error_kind == "frame_ambiguous":
            return Filled(None, "ambiguous")
        if found.candidates != 1 or found.matched_by == "repair":
            return Filled(None, "no_field")
        if composed.action == "select":
            live = await self._driver.outline(held.session, held.target_id, frame_path)
            options = _options(live, composed)
            if options and all(normal(one) != normal(value) for one in options):
                return Filled(None, "no_option", options=options)
        ctx.check_stop()
        answer = await self._driver.act(held.session, held.target_id, payload)
        check = {**payload, "expect": {"value": value}}
        if (
            answer.ok
            and not answer.repaired
            and await self._driver.wait_for(
                held.session, held.target_id, {**check, "pin": answer.pin}, self._wait_s
            )
        ):
            return Filled(
                Lane.UI,
                learned=locator
                or {"strategy": "role_and_name", "query": f"{composed.role}|{composed.label}"},
            )
        why = answer.detail or "the control did not take the value"
        if self._sight is None:
            return Filled(None, detail=why)
        result = await self._sight.fill(f"Set {composed.label} to {value}", write, ctx, check)
        if result.verdict == "done":
            return Filled(Lane.SIGHT, learned=result.learned)
        return Filled(None, detail=result.reason or why)


def _options(live: Mapping[str, object] | None, composed: Composed) -> tuple[str, ...]:
    fields = live.get("fields") if live else None
    for one in fields if isinstance(fields, list) else []:
        if (
            isinstance(one, dict)
            and one.get("role") == composed.role
            and normal(str(one.get("label") or "")) == normal(composed.label)
            and isinstance(one.get("options"), list)
        ):
            return tuple(str(option) for option in one["options"])
    return ()
