"""What each demonstration put in each field.

A version stores the *two* doings it diffed -- that is what proves a field
varies -- and reads the rest for one thing only, whether some field was left
empty. So a screen asked to show ten doings side by side has values for two of
them and nothing for the other eight.

Nothing is missing, though: the version holds the call it sends as a template
with ``$name`` in the slots, and every doing holds the call it actually made.
Laying one over the other reads the value straight back out. That is a
measurement, not an inference -- the same rule as everywhere else here. Where
the template does not fit what a doing sent, this says so rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import SkillVersion

_PLACEHOLDER = re.compile(r"\$(?:\{(\w+)\}|(\w+))")


@dataclass(frozen=True, slots=True)
class Doing:
    recording_id: RecordingId
    started_at: datetime
    demonstrator: PrincipalId
    frames: int
    diffed: bool
    """Whether this is one of the two the induction actually diffed. The other
    doings are evidence read back here, and a reviewer should be able to tell
    which is which."""

    values: dict[str, str | None]
    """The value this doing put in each parameter it can be read for. ``None``
    means it sent the field holding nothing -- the absent form -- which is the
    evidence behind an optional field. A name missing from the mapping is a
    field this doing does not answer for, and the screen says so."""


class ReadDoings:
    """Every demonstration behind a version, and what each one filled in."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, skill_id: SkillId, version: int | None = None
    ) -> tuple[Doing, ...]:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            chosen = _version(skill.versions, version)
            doings: list[Doing] = []
            for position, recording_id in enumerate(chosen.provenance.recording_ids):
                try:
                    recording = await uow.recordings.get(ctx.tenant_id, recording_id)
                except NotFound:
                    # Purged by retention. The version still cites it -- a
                    # skill's provenance is never rewritten to hide a gap --
                    # so the doing is simply not among the ones that can be
                    # read back.
                    continue
                doings.append(
                    Doing(
                        recording_id=recording_id,
                        started_at=recording.started_at,
                        demonstrator=recording.demonstrator,
                        frames=len(recording.frames),
                        diffed=position < 2,
                        values=values_in(chosen, recording.frames),
                    )
                )
        return tuple(doings)


def _version(versions: tuple[SkillVersion, ...], wanted: int | None) -> SkillVersion:
    if wanted is None:
        return versions[-1]
    for version in versions:
        if version.version == wanted:
            return version
    return versions[-1]


def values_in(version: SkillVersion, frames: tuple[ActionFrame, ...]) -> dict[str, str | None]:
    """Read this version's parameters out of one doing's traffic.

    Matched by call rather than by step number: only the two diffed doings
    have frames the induction aligned, and an older doing may have taken a
    different route to the same writes. Same method, same endpoint shape --
    the rule the diff itself uses to decide two calls are the same call.
    """
    sent = [
        request
        for frame in frames
        for request in frame.requests
        if request.is_mutation and request.succeeded and not is_background_traffic(request.url)
    ]

    found: dict[str, str | None] = {}
    for step in version.steps:
        plan = step.network_plan
        if plan is None:
            continue
        for request in sent:
            if request.method.upper() != plan.method.upper():
                continue
            read = _unify(plan, request)
            if read is None:
                continue
            for name, value in read.items():
                # First reading wins: a task that sends the same call twice in
                # one doing gets the value from the first, which is the one the
                # step was induced from.
                found.setdefault(name, value)
            break
    return found


def _unify(plan: NetworkPlan, request: CapturedRequest) -> dict[str, str | None] | None:
    """The slot values this request holds, or ``None`` if it is not this call.

    The URL decides whether it is the same call at all; only then is the body
    read. A template that does not fit the body of a call that is otherwise
    the right one yields the URL's slots and nothing else -- a doing whose
    payload changed shape still tells you which record it acted on.
    """
    from_url = _slots(str(plan.url), request.url)
    if from_url is None:
        return None

    body = plan.body
    if body is None:
        return from_url
    from_body = _slots(str(body), request.request_text or "")
    return {**from_url, **(from_body or {})}


def _slots(template: str, actual: str) -> dict[str, str | None] | None:
    """What each ``$name`` in ``template`` stands over in ``actual``.

    A regex built from the template's literals, with a non-greedy group per
    placeholder. Non-greedy because two slots in one JSON body are separated
    by punctuation the template carries verbatim; greedy matching would let
    the first slot swallow the second.

    ``None`` when the literals do not fit, which is this function's whole
    value: it is how a doing that sent something else is reported as unread
    rather than as a wrong value.
    """
    names: list[str] = []
    pattern: list[str] = ["\\A"]
    position = 0
    for match in _PLACEHOLDER.finditer(template):
        pattern.append(re.escape(template[position : match.start()]))
        pattern.append("(.*?)")
        names.append(match.group(1) or match.group(2))
        position = match.end()
    pattern.append(re.escape(template[position:]))
    pattern.append("\\Z")

    if not names:
        # A literal call. It identifies itself or it does not; either way it
        # carries no values.
        return {} if template == actual else None

    fitted = re.match("".join(pattern), actual, re.DOTALL)
    if fitted is None:
        return None
    return {name: _read(value) for name, value in zip(names, fitted.groups(), strict=True)}


def _read(raw: str) -> str | None:
    """A slot's contents as a person would read them.

    ``None`` for the absent forms -- a JSON ``null``, an empty string, an
    emptied slot -- because "this doing left it out" is the fact behind every
    optional field, and rendering it as the four characters ``null`` hides
    exactly the thing a reviewer is looking for.
    """
    value = raw.strip()
    if value in ("", "null", '""', "None"):
        return None
    if len(value) > 1 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value
