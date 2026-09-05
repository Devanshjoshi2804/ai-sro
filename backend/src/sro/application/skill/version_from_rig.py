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

    Names and collisions come from `declared_parameters`, the same reader
    `bindings_for` uses, so what a version DECLARES and what its steps
    REFERENCE cannot drift apart.
    """
    return tuple(
        Parameter(
            name=name,
            kind=ParameterKind.INPUT,
            # The control's own label, kept because sanitising the name throws
            # away how the operator would recognise the field: `Username or
            # email` becomes `Username_or_email`, and a reviewer should still
            # see what they typed into.
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
    # Blank and non-string ids are dropped before the emptiness check, not
    # after. `if not recordings` passed a list of empty strings straight
    # through to `RecordingId`, which refuses one and raises -- and `stream_id`
    # comes out of a column, so a blank is a database's answer rather than a
    # caller's mistake. `str(r)` was worse than raising: a JSON null became the
    # literal id "None", which is exactly the minting this module says it
    # refuses to do. A version with no readable provenance is refused.
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
            # A Mapping, not merely present. Everything here came off
            # `json.loads` out of a column, and a citation naming a string or a
            # null gave `AttributeError` from `.get` -- a traceback where the
            # module's whole contract is that it refuses.
            if not isinstance(gesture, Mapping):
                continue
            # Both recipes for the same gesture, which is what ADR 005 means by
            # dual: the network plan is how a run performs it without a
            # browser, the UI plan is how it performs it when the call no
            # longer works. Iterated here rather than through
            # `plans_for_workflow` because a network plan belongs to a specific
            # gesture and that function returns plans without saying which.
            ui = plan_for_gesture(gesture, bindings)
            network = (
                network_plan_for_gesture(
                    gesture,
                    requests.get(_text(cited) or "", ()),
                    target_system=target_system,
                    facility=facility,
                    bindings=bindings,
                )
                # Gated on the FACILITY alone. `target_system` is now derived
                # per call from the host it went to, so requiring it here left
                # a caller that correctly declined to name one system for a
                # cross-system job with no network recipe at all.
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
        # What the recorder saw on the frame the first action happened on. Only
        # from one stream: two demonstrations that began on different screens
        # are saying the screen is not part of the task, and this cannot tell
        # which case it is holding, so it speaks only for the single-recording
        # one.
        starts_on=_starts_on(workflow, gestures) if len(named) == 1 else None,
        systems=tuple(text for s in _as_list(workflow.get("systems")) if (text := _text(s))),
    )


def _ordered(workflow: Mapping[str, object]) -> list[Mapping[str, object]]:
    """The workflow's steps in the order it gives them.

    `plans_for_workflow` already sorts by `order` with the guard that stops a
    quoted number crashing the sort; this reuses that rather than repeating
    the rule, and throws away the plans it builds along the way.
    """
    return [step for step, _ in plans_for_workflow(workflow, {})]


def _as_list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _starts_on(
    workflow: Mapping[str, object], gestures: Mapping[str, Mapping[str, object]]
) -> str | None:
    """The url of the first gesture any step cites, in workflow order."""
    for step in _ordered(workflow):
        cites = step.get("cites")
        for cited in cites if isinstance(cites, list) else ():
            gesture = gestures.get(_text(cited) or "")
            if gesture is not None and (url := _text(gesture.get("url"))):
                return url
    return None
