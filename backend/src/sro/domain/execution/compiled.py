from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.belts import confirming_read, expected_statuses
from sro.domain.execution.compose import alias_map, normal
from sro.domain.execution.evidence import locators_for, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import Broken, Lane, accepts, lanes_for
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import body_key_set
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.learned import demanded
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class Reason:
    code: str
    step: int | None
    detail: str


@dataclass(frozen=True, slots=True)
class Compiled:
    runnable: bool
    reasons: tuple[Reason, ...]
    view: dict[str, object]
    warnings: tuple[Reason, ...] = ()


def why_not(reasons: Iterable[Reason]) -> list[str]:
    return list(
        dict.fromkeys(
            one.detail if one.step is None else f"Step {one.step}: {one.detail}" for one in reasons
        )
    )


def _ladder(
    step: Step, by_id: Mapping[str, Gesture], ledger: Sequence[VerifiedWrite]
) -> tuple[Lane, ...]:
    tool = sends_mail(step, by_id)
    call = recorded_call(step, by_id)
    api = not tool and call is not None and verified_write_for(call, tuple(ledger)) is not None
    browser = not tool and primary_gesture(step, by_id) is not None
    return lanes_for(step.order, tool=tool, api=api, browser=browser, broken=())


def compile_job(
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
    *,
    learned: Mapping[int, LearnedStep],
    ledger: Sequence[VerifiedWrite],
    broken: Collection[Broken],
    aliases: Sequence[JobAlias] = (),
) -> Compiled:
    reasons: list[Reason] = []
    warnings: list[Reason] = []
    filled = {name for step in workflow.steps for name in step.parameters}
    said = alias_map(aliases)
    for parameter in workflow.parameters:
        name = parameter.get("name")
        if not isinstance(name, str) or not demanded(parameter):
            continue
        if name not in filled and said.get(normal(name)) not in filled:
            reasons.append(
                Reason("unbound_parameter", None, f"{name} is required and no step fills it")
            )
    steps: list[dict[str, object]] = []
    for step in sorted(workflow.steps, key=lambda one: one.order):
        mine = learned.get(step.order)
        primary = primary_gesture(step, by_id)
        ladder = (
            ()
            if primary is None or only_reads_the_mail(step, by_id)
            else _ladder(step, by_id, ledger)
        )
        call = recorded_call(step, by_id)
        found = [
            f"{one.strategy}:{one.query}" for one in (locators_for(primary) if primary else [])
        ]
        if mine is not None and mine.usable:
            found.insert(0, f"{mine.strategy}:{mine.query} (learned by {mine.found_by})")
        if primary is None:
            reasons.append(
                Reason("no_lane", step.order, f"has no evidence a browser can act on: {step.says}")
            )
        if Lane.UI in ladder and not found:
            reasons.append(
                Reason("no_locator", step.order, "nothing recorded or learned finds its control")
            )
        statuses = sorted(expected_statuses(step, by_id))
        writing = call is not None and writes(step, by_id)
        if writing and not any(accepts(one, ()) for one in statuses):
            reasons.append(
                Reason("unproven_write", step.order, "no recorded status proves its write was done")
            )
        if (
            writing
            and not workflow.parameters
            and call is not None
            and body_key_set(call.request_body)
        ):
            warnings.append(
                Reason(
                    "fixed_values",
                    step.order,
                    "its write sends the values captured when it was recorded, the same every run",
                )
            )
        dead = {one.lane for one in broken if one.step == step.order}
        if ladder and set(ladder) <= dead:
            warnings.append(
                Reason(
                    "every_lane_broken",
                    step.order,
                    "every lane that could run it failed lately; each is tried after a cool-down",
                )
            )
        read = confirming_read(step, by_id)
        steps.append(
            {
                "order": step.order,
                "says": step.says,
                "lanes": [lane.value for lane in ladder],
                "broken": sorted(lane.value for lane in dead),
                "locators": found,
                "proof": None
                if call is None or not writing
                else {
                    "call": f"{call.method.upper()} {urlsplit(call.url).path}",
                    "statuses": statuses,
                    "read_back": None if read is None else urlsplit(read.url).path,
                },
            }
        )

    def listed(found: list[Reason]) -> list[dict[str, object]]:
        return [{"code": one.code, "step": one.step, "detail": one.detail} for one in found]

    view: dict[str, object] = {
        "job": workflow.id,
        "title": workflow.title,
        "runnable": not reasons,
        "reasons": listed(reasons),
        "warnings": listed(warnings),
        "parameters": [
            {"name": p.get("name"), "required": demanded(p)} for p in workflow.parameters
        ],
        "aliases": [{"wording": one.wording, "field": one.field} for one in aliases],
        "steps": steps,
    }
    return Compiled(not reasons, tuple(reasons), view, tuple(warnings))
