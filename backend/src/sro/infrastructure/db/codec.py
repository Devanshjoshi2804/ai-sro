"""Domain objects to JSON and back.

Frames and skill versions are deep, immutable and read as whole documents; a
column-per-field mapping would be a hundred tables and would still lose the
parts of a capture that have no fixed shape. They are stored as JSONB and the
queryable fields are lifted into real columns by the models.

The conversion is derived from the domain's own type annotations. There is no
second definition of the shape to keep in step, and a field added to a domain
dataclass is persisted the moment it exists.
"""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from sro.domain.chat.thread import Message
from sro.domain.observation.batch import RejectedEvent
from sro.domain.observation.candidate import Episode, Join
from sro.domain.observation.grant import HostGrant
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.artifact import MediaArtifact
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.narration import NarrationSegment
from sro.domain.skill.skill import SkillVersion
from sro.domain.trigger.watch import Watch

_FRAMES = TypeAdapter(tuple[ActionFrame, ...])
_ARTIFACTS = TypeAdapter(tuple[MediaArtifact, ...])
_NARRATION = TypeAdapter(tuple[NarrationSegment, ...])
_MESSAGES = TypeAdapter(tuple[Message, ...])
_VERSIONS = TypeAdapter(tuple[SkillVersion, ...])
_REJECTED = TypeAdapter(tuple[RejectedEvent, ...])
_POLICY = TypeAdapter(ObservationPolicy)
_GRANTS = TypeAdapter(tuple[HostGrant, ...])
_EPISODES = TypeAdapter(tuple[Episode, ...])
_JOINS = TypeAdapter(tuple[Join, ...])
_WATCH: TypeAdapter[Watch | None] = TypeAdapter(Watch | None)


def _dump[T](adapter: TypeAdapter[T], value: T) -> Any:
    # ``fallback=dict`` covers the read-only mappings the domain uses to keep
    # captured headers immutable; ``warnings=False`` silences the resulting
    # "expected dict, got mappingproxy" notice, which is exactly what we mean.
    return adapter.dump_python(value, mode="json", fallback=dict, warnings=False)


def dump_frames(frames: tuple[ActionFrame, ...]) -> Any:
    return _dump(_FRAMES, frames)


def load_frames(raw: Any) -> tuple[ActionFrame, ...]:
    return _FRAMES.validate_python(raw or [])


def dump_artifacts(artifacts: tuple[MediaArtifact, ...]) -> Any:
    return _dump(_ARTIFACTS, artifacts)


def load_artifacts(raw: Any) -> tuple[MediaArtifact, ...]:
    return _ARTIFACTS.validate_python(raw or [])


def dump_narration(segments: tuple[NarrationSegment, ...]) -> Any:
    return _dump(_NARRATION, segments)


def load_narration(raw: Any) -> tuple[NarrationSegment, ...]:
    return _NARRATION.validate_python(raw or [])


def dump_messages(messages: tuple[Message, ...]) -> Any:
    return _dump(_MESSAGES, messages)


def load_messages(raw: Any) -> tuple[Message, ...]:
    return _MESSAGES.validate_python(raw or [])


def dump_versions(versions: tuple[SkillVersion, ...]) -> Any:
    return _dump(_VERSIONS, versions)


def load_versions(raw: Any) -> tuple[SkillVersion, ...]:
    return _VERSIONS.validate_python(raw or [])


def dump_rejected(rejected: tuple[RejectedEvent, ...]) -> Any:
    return _dump(_REJECTED, rejected)


def load_rejected(raw: Any) -> tuple[RejectedEvent, ...]:
    return _REJECTED.validate_python(raw or [])


def dump_grants(grants: tuple[HostGrant, ...]) -> Any:
    return _dump(_GRANTS, grants)


def load_grants(raw: Any) -> tuple[HostGrant, ...]:
    return _GRANTS.validate_python(raw or [])


def dump_policy(policy: ObservationPolicy) -> Any:
    return _dump(_POLICY, policy)


def load_policy(raw: Any) -> ObservationPolicy:
    return _POLICY.validate_python(raw or {})


def dump_episodes(episodes: tuple[Episode, ...]) -> Any:
    return _dump(_EPISODES, episodes)


def load_episodes(raw: Any) -> tuple[Episode, ...]:
    return _EPISODES.validate_python(raw or [])


def dump_joins(joins: tuple[Join, ...]) -> Any:
    return _dump(_JOINS, joins)


def load_joins(raw: Any) -> tuple[Join, ...]:
    return _JOINS.validate_python(raw or [])


def dump_watch(watch: Watch | None) -> Any:
    return _dump(_WATCH, watch)


def load_watch(raw: Any) -> Watch | None:
    watch: Watch | None = _WATCH.validate_python(raw)
    return watch
