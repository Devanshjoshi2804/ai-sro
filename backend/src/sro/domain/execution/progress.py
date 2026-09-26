from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal, cast, get_args

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, ordered_cites

MAIN = "main"

K_STEP_HEARTBEAT_S = 30
K_STEP_LIMIT_S = 300
K_BEAT_EVERY_S = 10
K_BUDGET_FLOOR_S = 120
K_BUDGET_PER_STEP_S = 60
K_BUDGET_FACTOR = 4
K_BUDGET_MARGIN_S = 600

Wrote = Literal["", "sending", "done", "unknown"]


@dataclass
class StepMark:
    lane: str = ""
    verdict: str = ""
    wrote: Wrote = ""
    expired: bool = False


@dataclass
class Account:
    origin: str = ""
    username: str = ""


@dataclass
class Progress:
    step: int = 0
    marks: dict[int, StepMark] = field(default_factory=dict)
    read: dict[str, str] = field(default_factory=dict)
    tabs: dict[str, str] = field(default_factory=dict)
    lease: str = ""
    account: Account = field(default_factory=Account)
    start_url: str = ""
    asking: dict[str, str] = field(default_factory=dict)
    composed: list[dict[str, object]] = field(default_factory=list)
    filled: dict[str, str] = field(default_factory=dict)

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
            account=_account(raw.get("account")),
            start_url=str(raw.get("start_url") or ""),
            asking=_strings(raw.get("asking")),
            composed=_composed(raw.get("composed")),
            filled=_strings(raw.get("filled")),
        )

    def as_json(self) -> dict[str, object]:
        out = asdict(self)
        out["marks"] = {str(k): v for k, v in out["marks"].items()}
        return out

    def sending(self, order: int, lane: str) -> None:
        mark = self.marks.setdefault(order, StepMark())
        if mark.wrote == "done":
            return
        mark.lane, mark.wrote = lane, "sending"

    def written(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote == "done"

    def in_doubt(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote in ("sending", "unknown")

    def settle(
        self,
        order: int,
        *,
        lane: str,
        verdict: str,
        never_left: bool = False,
        expired: bool = False,
    ) -> None:
        mark = self.marks.setdefault(order, StepMark())
        if mark.wrote == "done":
            return
        mark.lane, mark.verdict = lane, verdict
        if not mark.wrote:
            return
        if verdict == "done":
            mark.wrote = "done"
        elif verdict == "failed" and never_left:
            mark.wrote = ""
        else:
            mark.wrote, mark.expired = "unknown", expired


def _strings(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(one) for key, one in value.items()}


def _composed(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(one, Mapping) for one in value):
        raise ValueError(f"progress.composed is not a list of fields: {value!r:.80}")
    return [dict(one) for one in value]


def _account(value: object) -> Account:
    found = _strings(value)
    return Account(origin=found.get("origin", ""), username=found.get("username", ""))


def _marks(value: object) -> dict[int, StepMark]:
    if not isinstance(value, Mapping):
        return {}
    return {
        int(key): StepMark(
            lane=str(one.get("lane") or ""),
            verdict=str(one.get("verdict") or ""),
            wrote=_wrote(str(one.get("wrote") or "")),
            expired=one.get("expired") is True,
        )
        for key, one in value.items()
        if isinstance(one, Mapping)
    }


def _wrote(value: str) -> Wrote:
    return cast(Wrote, value) if value in get_args(Wrote) else ""


def run_budget(workflow: Workflow, by_id: Mapping[str, Gesture]) -> float:
    times = [by_id[one].at for one in ordered_cites(workflow) if one in by_id]
    shown = max(times) - min(times) if len(times) > 1 else 0.0
    return max(
        float(K_BUDGET_FLOOR_S),
        K_BUDGET_FACTOR * shown + K_BUDGET_PER_STEP_S * len(workflow.steps),
    )
