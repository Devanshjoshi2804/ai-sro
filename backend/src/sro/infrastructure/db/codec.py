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

from sro.domain.recording.artifact import MediaArtifact
from sro.domain.recording.events import ActionFrame
from sro.domain.skill.skill import SkillVersion

_FRAMES = TypeAdapter(tuple[ActionFrame, ...])
_ARTIFACTS = TypeAdapter(tuple[MediaArtifact, ...])
_VERSIONS = TypeAdapter(tuple[SkillVersion, ...])


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


def dump_versions(versions: tuple[SkillVersion, ...]) -> Any:
    return _dump(_VERSIONS, versions)


def load_versions(raw: Any) -> tuple[SkillVersion, ...]:
    return _VERSIONS.validate_python(raw or [])
