from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sro.application.skill.from_rig import (
    bindings_for,
    declared_parameters,
    plan_for_gesture,
    plans_for_workflow,
)
from sro.application.skill.network_from_rig import network_plan_for_gesture
from sro.domain.shared.identifiers import PrincipalId, RecordingId
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind
from sro.domain.skill.skill import Provenance, SkillStep, SkillVersion


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def parameters_from_rig(workflow: Mapping[str, object]) -> tuple[Parameter, ...]:
    return tuple(
        Parameter(
            name=name,
            kind=ParameterKind.INPUT,
            description=f"what the operator typed into {label}",
            observed_values=values,
            evidence=Evidence.PROVEN if len(set(values)) > 1 else Evidence.PROPOSED,
        )
        for name, (label, values) in declared_parameters(workflow).items()
    )


def version_from_rig(
    workflow: Mapping[str, object],
    gestures: Mapping[str, Mapping[str, object]],
    *,
    recordings: Sequence[str],
    induced_by: str,
    induced_at: datetime,
    version: int = 1,
    requests: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    facility: str = "",
    target_system: str = "",
) -> SkillVersion | None:
    named = tuple(
        dict.fromkeys(one for r in recordings if isinstance(r, str) and (one := r.strip()))
    )
    if not named:
        return None

    bindings = bindings_for(workflow)
    steps: list[SkillStep] = []
    for step in _ordered(workflow):
        says = _text(step.get("says")) or "perform the step"
        cites = step.get("cites")
        for cited in cites if isinstance(cites, list) else ():
            gesture = gestures.get(_text(cited) or "")
            if not isinstance(gesture, Mapping):
                continue
            ui = plan_for_gesture(gesture, bindings)
            network = (
                network_plan_for_gesture(
                    gesture,
                    requests.get(_text(cited) or "", ()),
                    target_system=target_system,
                    facility=facility,
                    bindings=bindings,
                )
                if requests is not None and facility
                else None
            )
            if ui is None and network is None:
                continue
            steps.append(SkillStep(index=len(steps), intent=says, ui_plan=ui, network_plan=network))
    if not steps:
        return None

    return SkillVersion(
        version=version,
        steps=tuple(steps),
        parameters=parameters_from_rig(workflow),
        provenance=Provenance(
            recording_ids=tuple(RecordingId(r) for r in named),
            induced_at=induced_at,
            induced_by=PrincipalId(induced_by),
            note=_text(workflow.get("narrative")) or "",
        ),
        summary=_text(workflow.get("title")) or "",
        starts_on=_starts_on(workflow, gestures),
        systems=tuple(text for s in _as_list(workflow.get("systems")) if (text := _text(s))),
    )


def _ordered(workflow: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [step for step, _ in plans_for_workflow(workflow, {})]


def _as_list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _starts_on(
    workflow: Mapping[str, object], gestures: Mapping[str, Mapping[str, object]]
) -> str | None:
    for step in _ordered(workflow):
        cites = step.get("cites")
        for cited in cites if isinstance(cites, list) else ():
            gesture = gestures.get(_text(cited) or "")
            if gesture is not None and (url := _text(gesture.get("url"))):
                return url
    return None
