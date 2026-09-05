"""A workflow the rig mined, as a version this system can review and run.

`from_rig` turns a mined step into `UiPlan`s -- what a driver would do. This is
the rest of the journey: a `SkillVersion`, which is what `/v1/runs`, the
promotion ladder and the console all actually take. The gap between the two is
not mechanical, and the interesting part of this module is what it refuses to
invent rather than what it builds.

**What it will not supply.** A `Skill` needs an `ObjectiveKey` -- objective
type, target system, entity type, facility, direction -- and the rig produces
none of those. It knows a title, the systems a job touched, and a shape key.
Deriving "this is an inbound receipt against BLR1" from `Create Work Area
NEWTESTS` would be a guess wearing the clothes of a finding, which is the exact
move the citation requirement exists to stop. So this builds the version and
the objective stays a person's decision, which is where it belongs: naming what
a job is FOR is the reviewer's half of induction.

**What it will not fake.** `Provenance.recording_ids` must be non-empty, and
the rig has no `Recording`. Its nearest equivalent is the capture stream a
gesture arrived on, which lives in a column of the gestures table rather than
in the gesture itself -- so the caller passes it and this refuses without it.
Minting an id from something to hand would satisfy the invariant and lie to
`from_one_demonstration`, a live safety rule: it decides whether a write
skill's values were ever diffed.

That rule also decides the direction this errs in. Two doings of one job inside
a single capture stream report as ONE recording, so a version whose parameters
were genuinely proven can still read as `from_one_demonstration` -- and that
answer is the strict one. `values_are_fixed` follows it, and promotion asks
more of a skill nobody diffed. Understating the evidence costs a reviewer's
time; overstating it promotes something on a diff that never happened.

Every version comes out at `RECORDED`. Nothing about a mined workflow has been
reviewed by anybody, and the stage is the one field that says so.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sro.application.skill.from_rig import plans_for_workflow
from sro.domain.shared.identifiers import PrincipalId, RecordingId
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind
from sro.domain.skill.skill import Provenance, SkillStep, SkillVersion


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def parameters_from_rig(workflow: Mapping[str, object]) -> tuple[Parameter, ...]:
    """The rig's parameters as the domain's, with the evidence they actually have.

    PROVEN where two doings disagreed, which is the only thing `parameters_across`
    ever reports -- it returns a control precisely when its value CHANGED between
    occurrences, so a rig parameter is a fact rather than a reading. That is a
    stronger footing than the induction path's own PROPOSED, which is one
    demonstration plus a model's opinion.

    A parameter carrying fewer than two distinct values is downgraded rather
    than trusted. It should not exist -- nothing in the rig produces one -- and
    if the store ever holds one, the honest reading is that whatever made it did
    not do the diff this evidence level claims.
    """
    parameters = workflow.get("parameters")
    found: list[Parameter] = []
    for entry in parameters if isinstance(parameters, list) else ():
        if not isinstance(entry, Mapping):
            continue
        name = _text(entry.get("name"))
        if not name:
            continue
        raw = entry.get("seen_values")
        values = tuple(
            text for value in (raw if isinstance(raw, list) else ()) if (text := _text(value))
        )
        found.append(
            Parameter(
                name=name,
                kind=ParameterKind.INPUT,
                # Named after the control it was typed into, which is what the
                # rig names it: `activityCode` says what it is, `TEST1` says
                # what it was once.
                description=f"what the operator typed into {name}",
                observed_values=values,
                evidence=Evidence.PROVEN if len(set(values)) > 1 else Evidence.PROPOSED,
            )
        )
    return tuple(found)


def version_from_rig(
    workflow: Mapping[str, object],
    gestures: Mapping[str, Mapping[str, object]],
    *,
    recordings: Sequence[str],
    induced_by: str,
    induced_at: datetime,
    version: int = 1,
) -> SkillVersion | None:
    """One mined workflow as a reviewable version, or None where it is not one.

    None rather than a version with no steps: a workflow whose citations all
    name evidence this store does not have describes a job nobody can perform,
    and an empty `SkillVersion` would sit in a library looking runnable.

    A rig step is prose over several gestures, and a `SkillStep` performs one
    thing -- the same convention `emit_step` follows on the induction path. So a
    step citing three gestures becomes three steps, each carrying the operator-
    level prose it came from. The prose repeats on purpose: those three gestures
    really were one described step, and renaming them apart would invent a
    distinction the evidence does not make.
    """
    if not recordings:
        return None

    steps: list[SkillStep] = []
    for step, plans in plans_for_workflow(workflow, gestures):
        says = _text(step.get("says")) or "perform the step"
        for plan in plans:
            steps.append(SkillStep(index=len(steps), intent=says, ui_plan=plan))
    if not steps:
        return None

    return SkillVersion(
        version=version,
        steps=tuple(steps),
        parameters=parameters_from_rig(workflow),
        provenance=Provenance(
            recording_ids=tuple(dict.fromkeys(RecordingId(r) for r in recordings)),
            induced_at=induced_at,
            induced_by=PrincipalId(induced_by),
            note=_text(workflow.get("narrative")) or "",
        ),
        summary=_text(workflow.get("title")) or "",
        # What the recorder saw on the frame the first action happened on. Only
        # from one stream: two demonstrations that began on different screens
        # are saying the screen is not part of the task, and this cannot tell
        # which case it is holding, so it speaks only for the single-recording
        # one.
        starts_on=_starts_on(workflow, gestures) if len(set(recordings)) == 1 else None,
        systems=tuple(text for s in _as_list(workflow.get("systems")) if (text := _text(s))),
    )


def _as_list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _starts_on(
    workflow: Mapping[str, object], gestures: Mapping[str, Mapping[str, object]]
) -> str | None:
    """The url of the first gesture any step cites, in workflow order."""
    for step, _ in plans_for_workflow(workflow, gestures):
        cites = step.get("cites")
        for cited in cites if isinstance(cites, list) else ():
            gesture = gestures.get(_text(cited) or "")
            if gesture is not None and (url := _text(gesture.get("url"))):
                return url
    return None
