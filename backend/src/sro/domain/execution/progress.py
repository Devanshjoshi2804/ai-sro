from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, ordered_cites

MAIN = "main"

K_STEP_HEARTBEAT_S = 30
K_STEP_LIMIT_S = 300
K_BEAT_EVERY_S = 10
K_BUDGET_FLOOR_S = 120
K_BUDGET_PER_STEP_S = 60
K_BUDGET_FACTOR = 4

Wrote = Literal["", "sending", "done", "unknown"]


@dataclass
class StepMark:
    lane: str = ""
    verdict: str = ""
    wrote: Wrote = ""


@dataclass
class Progress:
    step: int = 0
    marks: dict[int, StepMark] = field(default_factory=dict)
    read: dict[str, str] = field(default_factory=dict)
    tabs: dict[str, str] = field(default_factory=dict)
    lease: str = ""
    account: dict[str, str] = field(default_factory=dict)
    start_url: str = ""
    asking: dict[str, str] = field(default_factory=dict)

    @classmethod
    def of(cls, raw: Mapping[str, object] | None) -> Progress:
        if not raw:
            return cls()
        return cls(
            step=int(str(raw.get("step") or 0)),
            marks=_marks(raw.get("marks")),
            read=_strings(raw.get("read")),
            tabs=_strings(raw.get("tabs")),
            lease=str(raw.get("lease") or ""),
            account=_strings(raw.get("account")),
            start_url=str(raw.get("start_url") or ""),
            asking=_strings(raw.get("asking")),
        )

    def as_json(self) -> dict[str, object]:
        out = asdict(self)
        out["marks"] = {str(k): v for k, v in out["marks"].items()}
        return out

    def sending(self, order: int) -> None:
        self.marks.setdefault(order, StepMark()).wrote = "sending"

    def written(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote == "done"

    def in_doubt(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote in ("sending", "unknown")

    def settle(self, order: int, *, lane: str, verdict: str) -> None:
        mark = self.marks.setdefault(order, StepMark())
        mark.lane, mark.verdict = lane, verdict
        if mark.wrote:
            mark.wrote = "done" if verdict == "done" else "unknown" if verdict == "unknown" else ""


_WROTE: dict[str, Wrote] = {"": "", "sending": "sending", "done": "done", "unknown": "unknown"}


def _strings(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(one) for key, one in value.items()}


def _marks(value: object) -> dict[int, StepMark]:
    if not isinstance(value, Mapping):
        return {}
    return {
        int(key): StepMark(
            lane=str(one.get("lane") or ""),
            verdict=str(one.get("verdict") or ""),
            wrote=_WROTE.get(str(one.get("wrote") or ""), ""),
        )
        for key, one in value.items()
        if isinstance(one, Mapping)
    }


def run_budget(workflow: Workflow, by_id: Mapping[str, Gesture]) -> float:
    times = [by_id[one].at for one in ordered_cites(workflow) if one in by_id]
    shown = max(times) - min(times) if len(times) > 1 else 0.0
    return max(
        float(K_BUDGET_FLOOR_S),
        K_BUDGET_FACTOR * shown + K_BUDGET_PER_STEP_S * len(workflow.steps),
    )
