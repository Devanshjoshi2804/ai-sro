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

    values: dict[str, str | None]


class ReadDoings:
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
                found.setdefault(name, value)
            break
    return found


def _unify(plan: NetworkPlan, request: CapturedRequest) -> dict[str, str | None] | None:
    from_url = _slots(str(plan.url), request.url)
    if from_url is None:
        return None

    body = plan.body
    if body is None:
        return from_url
    from_body = _slots(str(body), request.request_text or "")
    return {**from_url, **(from_body or {})}


def _slots(template: str, actual: str) -> dict[str, str | None] | None:
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
        return {} if template == actual else None

    fitted = re.match("".join(pattern), actual, re.DOTALL)
    if fitted is None:
        return None
    return {name: _read(value) for name, value in zip(names, fitted.groups(), strict=True)}


def _read(raw: str) -> str | None:
    value = raw.strip()
    if value in ("", "null", '""', "None"):
        return None
    if len(value) > 1 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value
