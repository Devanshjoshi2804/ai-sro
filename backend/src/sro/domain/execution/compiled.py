from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit

from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.belts import confirming_read, expected_statuses
from sro.domain.execution.compose import alias_map, field_of, normal
from sro.domain.execution.evidence import locators_for, primary_gesture, recorded_call, writes
from sro.domain.execution.field_classes import FieldClass, field_classes, labelled
from sro.domain.execution.lanes import Broken, Lane, accepts, lanes_for
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import body_key_set
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.learned import demanded
from sro.domain.skill.tabs import undecided, unresolved
from sro.domain.skill.workflow import Step, Workflow, field_key


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
    fields: tuple[FieldClass, ...] = ()


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
    values: Mapping[str, str] | None = None,
    from_step: int = 0,
    declared: Mapping[str, int] = MappingProxyType({}),
) -> Compiled:
    reasons: list[Reason] = []
    warnings: list[Reason] = []
    filled = {name for step in workflow.steps for name in step.parameters}
    said = alias_map(aliases)
    fields = field_classes(workflow, by_id, learned, declared)
    for parameter in workflow.parameters:
        name = parameter.get("name")
        if not isinstance(name, str) or not demanded(parameter):
            continue
        aliased = labelled(normal(said.get(normal(name), "")), fields)
        if name not in filled and (aliased is None or aliased.name not in filled):
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
        if field_key(workflow, step):
            name = step.parameters[0]
            if (values or {}).get(name, "").strip() and field_of(workflow, by_id, step) is None:
                reasons.append(
                    Reason(
                        "field_gone",
                        step.order,
                        f"the form its save shows has no {name} field any more",
                    )
                )
        elif primary is None:
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
                "tab": step.role,
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

    if undecided(workflow.steps):
        warnings.append(
            Reason(
                "tab_roles_undecided",
                None,
                "which tab each step acts in is not decided yet; every step runs in the first tab",
            )
        )
    else:
        reasons += [
            Reason("tab_role_unresolved", order, "the tab it acts in is opened by no earlier step")
            for order in unresolved(workflow.steps)
        ]

    def listed(found: list[Reason]) -> list[dict[str, object]]:
        return [{"code": one.code, "step": one.step, "detail": one.detail} for one in found]

    reasons = [one for one in reasons if one.step is None or one.step >= from_step]
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
        "fields": [
            {
                "name": one.name,
                "kind": one.kind,
                "labels": list(one.labels),
                "max_length": one.limits.max_length,
                "options": list(one.limits.options) if one.limits.options is not None else None,
                "required_on_screen": one.limits.required_on_screen,
            }
            for one in fields
        ],
    }
    return Compiled(not reasons, tuple(reasons), view, tuple(warnings), fields)
