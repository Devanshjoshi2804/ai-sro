"""One demonstration to a usable skill.

The two-run diff is still the better instrument, and where two runs exist it is
what runs. This is for the ordinary case the diff cannot serve: a task nobody
can perform twice identically, or a task somebody only had time to do once.

The split is the point. **The calls are evidence and are untouched.** The
narrative -- what each step was for, what the whole thing accomplishes, which
values look like inputs -- is a model reading the same evidence, and every part
of it is marked as read rather than proven. A candidate parameter that cannot be
found in a captured payload is dropped: a parameter nobody can point at in the
evidence is a hallucination with a name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.application.capture.identity import (
    derive_objective_key,
    system_of,
    systems_touched,
)
from sro.application.context import RequestContext
from sro.application.induction import narration as narration_alignment
from sro.application.induction.assertions import StepEvidence
from sro.application.induction.diff import (
    Parameterisation,
    Substitution,
    typed_values,
    unfold,
)
from sro.application.induction.emit import emit_step
from sro.application.induction.errors import InductionFailed
from sro.application.induction.sites import (
    ActionValueSite,
    JsonBodySite,
    Site,
    UrlQuerySite,
    url_query_pairs,
)
from sro.application.ports.interpretation import Reading, WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import Verdict

_MAX_EVIDENCE_CHARS = 60_000


@dataclass(frozen=True, slots=True)
class Understood:
    skill_id: SkillId
    version: int
    step_count: int
    proposed_parameter_count: int
    caveat: str


class UnderstandRecording:
    def __init__(
        self,
        uow: UnitOfWork,
        interpreter: WorkflowInterpreter,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._uow = uow
        self._interpreter = interpreter
        self._clock = clock
        self._ids = ids

    async def execute(
        self, ctx: RequestContext, *, recording_id: RecordingId, name: str | None = None
    ) -> Understood:
        now = self._clock.now()

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            if recording.status is not RecordingStatus.SEALED:
                raise InductionFailed(
                    f"recording {recording.id} is {recording.status}; seal it first"
                )
            if not recording.frames:
                raise InductionFailed("this demonstration captured nothing to learn from")
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)

        objective = recording.objective_key or derive_objective_key(
            recording.frames,
            system=system_of(
                connections,
                *(f.primary_request.url for f in recording.frames if f.primary_request),
            ),
        )
        if objective is None:
            raise InductionFailed(
                "nothing this demonstration did says what task it was; name it and try again"
            )

        reading = (
            await self._interpreter.read(as_evidence(recording))
            if self._interpreter.available
            else Reading(
                caveat="no interpreter is configured; the steps are described mechanically"
            )
        )

        # Typed first, and they win. A frame recording that a human entered a
        # value is stronger evidence than a model's reading of the same text --
        # and it is the value most certain to want a different answer next run.
        entered = _entered(recording.frames)
        proposed = entered | _believable(reading, recording.frames, claimed=entered)
        steps = _steps(recording, reading, proposed)
        parameters = tuple(
            Parameter(
                name=name_,
                kind=ParameterKind.INPUT,
                description=description,
                observed_values=(value,),
                evidence=Evidence.PROPOSED,
            )
            for name_, (value, description) in proposed.items()
        )

        async with self._uow as uow:
            skill = await uow.skills.find_by_objective(ctx.tenant_id, objective)
            if skill is None:
                skill = Skill(
                    id=self._ids.new_skill_id(),
                    tenant_id=ctx.tenant_id,
                    objective_key=objective,
                    name=name
                    or reading.title
                    or objective.objective_type.replace("_", " ").title(),
                    created_at=now,
                )
                await uow.skills.add(skill)

            version = SkillVersion(
                version=skill.next_version_number(),
                steps=steps,
                parameters=parameters,
                provenance=Provenance(
                    recording_ids=(recording.id,),
                    # `_steps` builds every step from this one recording's
                    # frames -- the whole point of the single-run path -- so
                    # this is exactly the case the default `()` must not be
                    # left to stand in for.
                    aligned_recording_ids=(recording.id,),
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=(
                        "read from one demonstration: the calls are evidence, the values the "
                        "operator typed are recovered from the frames, and the description is "
                        "a model's reading of the rest"
                    ),
                ),
                summary=reading.summary
                or f"{objective.objective_type} on {objective.target_system}",
                when_to_use=reading.when_to_use,
                # Read here as well as on the two-run path: a workflow taught
                # from a single occurrence is still a workflow, and a version
                # that does not say so is one no breaker guards and no rule
                # binds to a browser.
                systems=systems_touched(
                    await uow.connections.list_for_tenant(ctx.tenant_id), recording
                ),
            )
            skill.add_version(version)
            # Straight to rehearsing, once it is attached: a version is added at
            # RECORDED and cannot be run there, so it could never earn the rung
            # that lets it run. Nothing is sent at the next one -- the request is
            # built and withheld for somebody to read, and withholding it from
            # the operator too is not caution, just a skill nobody can review.
            version.earn(Verdict.WITHHELD, now)
            await uow.skills.save(skill)
            await uow.commit()

        return Understood(
            skill_id=skill.id,
            version=version.version,
            step_count=len(steps),
            proposed_parameter_count=len(parameters),
            caveat=reading.caveat,
        )


def as_evidence(recording: Recording) -> str:
    """The demonstration as text a model can read.

    Bodies are included because they are where the values are, and they have
    already had credentials removed at capture time -- this sends what is
    stored, and what is stored never held a password.

    URLs are cleaned here rather than at capture, because the URL is the
    evidence: which endpoint was called is the whole point of keeping it. What
    a hosted model has no use for is the query string's values, and a system
    that puts a session key or a one-time token in one -- several do -- was
    sending it to Google in full.
    """
    lines: list[str] = []
    for frame in recording.frames:
        action = frame.action
        target = action.target.describe() if action.target else ""
        value = "«secret»" if action.secret else (action.value or "")
        lines.append(f"[{frame.index}] {action.kind} {target} {value}".rstrip())
        for request in _calls(frame):
            lines.append(f"     {request.method} {_clean(request.url)} -> {request.status}")
            if request.request_text:
                lines.append(f"     sent: {request.request_text[:600]}")
            if request.response_text:
                lines.append(f"     back: {request.response_text[:600]}")
    for segment in recording.narration:
        lines.append(f"said: {segment.text}")
    return "\n".join(lines)[:_MAX_EVIDENCE_CHARS]


def _clean(url: str) -> str:
    """The URL with any credential-shaped query value taken out."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = [
        (key, "«redacted»" if is_secret_field(key) else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(pairs, safe="${}"), parts.fragment)
    )


def _calls(frame: ActionFrame) -> tuple[CapturedRequest, ...]:
    """Every call this gesture made. Not the "primary" one: reading only that
    hid the call that created the record from the model doing the reading."""
    return tuple(r for r in frame.requests if not is_background_traffic(r.url))


TYPED_IN = "typed by the operator, and carried by a later call"


def _entered(frames: tuple[ActionFrame, ...]) -> dict[str, tuple[str, str]]:
    """Values a person typed that the calls afterwards carried.

    Not an inference, and not a model's: the frame records that a human entered
    this value and the control records what it was called. Without this, one
    demonstration has nothing to disagree with, so the supplier code somebody
    had just typed into a box looked as fixed as the endpoint -- and replaying it
    creates that same supplier again.

    The two-run path has recovered these since the day it was written. This one
    is the path a mined candidate takes, which is now most of them.
    """
    entered: dict[str, tuple[str, str]] = {}
    for choice in typed_values(frames):
        if choice.field.isidentifier() and choice.value.strip():
            entered[choice.field] = (choice.value, TYPED_IN)
    return entered


def _believable(
    reading: Reading,
    frames: tuple[ActionFrame, ...],
    *,
    claimed: dict[str, tuple[str, str]] | None = None,
) -> dict[str, tuple[str, str]]:
    """Candidates whose value actually appears in what was captured.

    The check that keeps this honest: a model can name any parameter it likes,
    and only the ones pointing at a literal in the evidence survive.

    A value already recovered from a typed box is skipped whatever the model
    called it: two names for one value would put two placeholders at one site,
    and the second would quietly win.
    """
    haystack = _as_text(frames)
    spoken_for = {value for value, _ in (claimed or {}).values()}
    kept: dict[str, tuple[str, str]] = {}
    for candidate in reading.parameters:
        value = candidate.value.strip()
        if not value or value not in haystack or value in spoken_for:
            continue
        name = candidate.name.strip()
        if not name.isidentifier() or name in kept or name in (claimed or {}):
            continue
        kept[name] = (value, candidate.description)
    return kept


def _as_text(frames: tuple[ActionFrame, ...]) -> str:
    parts: list[str] = []
    for frame in frames:
        if frame.action.value and not frame.action.secret:
            parts.append(frame.action.value)
        for request in _calls(frame):
            parts.append(request.url)
            parts.append(request.request_text or "")
            parts.append(request.response_text or "")
    return "\n".join(parts)


def _steps(
    recording: Recording, reading: Reading, proposed: dict[str, tuple[str, str]]
) -> tuple[SkillStep, ...]:
    """Steps built from the evidence, described by the reading."""
    said = narration_alignment.align(recording.frames, recording.narration)
    read_by_index = {step.index: step for step in reading.steps}

    steps: list[SkillStep] = []
    # Unfolded, so a Save that created a record and then addressed it becomes
    # two steps rather than one step that replays half the task.
    for position, frame in enumerate(unfold(recording.frames)):
        step = emit_step(
            position,
            frame,
            _substitutions(frame, proposed),
            _no_assertions(frame),
            recording.objective_key,  # type: ignore[arg-type]
            None,
            said.get(frame.index),
        )
        if (heard := read_by_index.get(frame.index)) is not None and heard.what.strip():
            # The model's sentence is a better label than "click button#x". It
            # is a label only: the plans underneath are untouched.
            step = SkillStep(
                index=step.index,
                intent=heard.what.strip()[:200],
                network_plan=step.network_plan,
                ui_plan=step.ui_plan,
                assertions=step.assertions,
                requires_human=step.requires_human,
                narration=step.narration or heard.why,
                branch_hint=step.branch_hint,
            )
        steps.append(step)
    return tuple(steps)


def _substitutions(frame: ActionFrame, proposed: dict[str, tuple[str, str]]) -> Parameterisation:
    """This step's placeholders, in the shape the emitter already understands."""
    sites = _replacements(frame, proposed)
    return Parameterisation(
        parameters=(),
        substitutions={
            frame.index: tuple(
                Substitution(site=site, parameter=text.strip("${}")) for site, text in sites.items()
            )
        },
    )


def _replacements(frame: ActionFrame, proposed: dict[str, tuple[str, str]]) -> dict[Site, str]:
    """Where each candidate value sits in this step, so the plan carries a
    placeholder rather than one run's literal."""
    found: dict[Site, str] = {}
    request = frame.primary_request
    for name, (value, _) in proposed.items():
        placeholder = f"${{{name}}}"
        if frame.action.value == value and not frame.action.secret:
            found[ActionValueSite()] = placeholder
        if request is None:
            continue
        for key, query_value in url_query_pairs(request.url):
            if query_value == value:
                found[UrlQuerySite(key)] = placeholder
        for pointer in _pointers_to(request.request_text, value):
            found[JsonBodySite(pointer)] = placeholder
    return found


def _pointers_to(body: str | None, value: str) -> list[str]:
    if not body:
        return []
    try:
        document = json.loads(body)
    except ValueError:
        return []

    found: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{path}/{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}/{index}")
        elif str(node) == value:
            found.append(path)

    walk(document, "")
    return found


def _no_assertions(frame: ActionFrame) -> StepEvidence:
    """What a single run can assert: the status the system actually answered.

    Deliberately thin. The read-back comparison that a pair produces is not
    available here, and inventing a richer assertion from one observation is how
    a verifier starts failing correct runs.
    """
    request = frame.primary_request
    if request is None or request.status is None:
        return StepEvidence(assertions=(), wait_for=None)
    return StepEvidence(
        assertions=(
            Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template(str(request.status))),
        ),
        wait_for=None,
    )
