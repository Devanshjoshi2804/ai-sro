"""Builders for domain objects.

Each returns something valid with no arguments and takes keyword overrides, so a
test names only the fields it is about.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sro.domain.observation.device import AgentDevice
from sro.domain.recording.artifact import ArtifactKind, MediaArtifact
from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import (
    Body,
    CapturedRequest,
    Cookie,
    Initiator,
    InitiatorKind,
)
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import (
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
)
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import NetworkPlan, UiPlan
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion
from sro.domain.skill.template import Template

T0 = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
TENANT = TenantId("acme")
OPERATOR = PrincipalId("clerk@acme.test")


def at(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


def objective(**overrides: Any) -> ObjectiveKey:
    defaults: dict[str, Any] = {
        "objective_type": "resolve_short_ship",
        "target_system": "blue_yonder",
        "entity_type": "shipment",
        "facility": "DC01",
        "direction": Direction.OUTBOUND,
    }
    return ObjectiveKey(**{**defaults, **overrides})


def fingerprint(**overrides: Any) -> ElementFingerprint:
    defaults: dict[str, Any] = {
        "node_id": "ax-1",
        "role": "button",
        "accessible_name": "Release wave",
        "css_path": "form > button.primary",
        "tag": "button",
    }
    return ElementFingerprint(**{**defaults, **overrides})


def cookie(**overrides: Any) -> Cookie:
    defaults: dict[str, Any] = {
        "name": "JSESSIONID",
        "value": "abc123",
        "domain": "wms.test",
        "secure": True,
        "http_only": True,
    }
    return Cookie(**{**defaults, **overrides})


def request(**overrides: Any) -> CapturedRequest:
    defaults: dict[str, Any] = {
        "request_id": "req-1",
        "method": "POST",
        "url": "https://wms.test/api/shipments/12345/release",
        "resource_type": "xhr",
        "started_at": at(10),
        "request_headers": {
            "Authorization": "Bearer live-token",
            "X-CSRF-Token": "csrf-abc",
            "Content-Type": "application/json",
            "X-Facility": "DC01",
            "User-Agent": "Mozilla/5.0",
        },
        "request_body": Body(
            text='{"shipmentId": "12345", "reason": "short"}',
            size_bytes=42,
            mime_type="application/json",
        ),
        "cookies_sent": (cookie(),),
        "status": 200,
        "status_text": "OK",
        "response_body": Body(
            text='{"ok": true, "waveId": "W-777"}', size_bytes=30, mime_type="application/json"
        ),
        "initiator": Initiator(kind=InitiatorKind.SCRIPT),
        "protocol": "h2",
        "duration_ms": 120,
    }
    return CapturedRequest(**{**defaults, **overrides})


def frame(index: int = 0, **overrides: Any) -> ActionFrame:
    defaults: dict[str, Any] = {
        "index": index,
        "occurred_at": at(10 + index),
        "action": InputAction(kind=ActionKind.CLICK, target=fingerprint()),
        "ax_graph": AxGraph(
            taken_at=at(10 + index), url="https://wms.test/shipments/12345", nodes=(fingerprint(),)
        ),
        "requests": (request(),),
    }
    return ActionFrame(**{**defaults, **overrides})


def recording(*, frames: int = 1, sealed: bool = False, **overrides: Any) -> Recording:
    defaults: dict[str, Any] = {
        "id": RecordingId("rec-1"),
        "tenant_id": TENANT,
        "objective_key": objective(),
        "demonstrator": OPERATOR,
        "started_at": T0,
        "label": "run 1",
    }
    rec = Recording(**{**defaults, **overrides})
    for i in range(frames):
        rec.append_frame(frame(i))
    if sealed:
        rec.seal(at(300))
    return rec


def artifact(kind: ArtifactKind = ArtifactKind.VIDEO, **overrides: Any) -> MediaArtifact:
    defaults: dict[str, Any] = {
        "kind": kind,
        "uri": f"s3://sro-artifacts/acme/rec-1/{kind.value}",
        "content_type": "video/webm",
        "size_bytes": 2048,
        "created_at": at(300),
    }
    return MediaArtifact(**{**defaults, **overrides})


def body(text: str) -> Body:
    return Body(text=text, size_bytes=len(text), mime_type="application/json")


def network_plan(**overrides: Any) -> NetworkPlan:
    defaults: dict[str, Any] = {
        "method": "POST",
        "url": Template("https://wms.test/api/shipments/${shipment_id}/release"),
        "body": Template('{"shipmentId": "${shipment_id}"}'),
        "expected_status": 200,
    }
    return NetworkPlan(**{**defaults, **overrides})


def ui_plan(**overrides: Any) -> UiPlan:
    defaults: dict[str, Any] = {"action": ActionKind.CLICK, "target": fingerprint()}
    return UiPlan(**{**defaults, **overrides})


def step(index: int = 0, **overrides: Any) -> SkillStep:
    defaults: dict[str, Any] = {
        "index": index,
        "intent": "release the wave",
        "network_plan": network_plan(),
        "ui_plan": ui_plan(),
    }
    return SkillStep(**{**defaults, **overrides})


def parameter(**overrides: Any) -> Parameter:
    defaults: dict[str, Any] = {
        "name": "shipment_id",
        "kind": ParameterKind.INPUT,
        "observed_values": ("12345", "67890"),
    }
    return Parameter(**{**defaults, **overrides})


def device(**overrides: Any) -> AgentDevice:
    defaults: dict[str, Any] = {
        "id": DeviceId("dev-1"),
        "tenant_id": TENANT,
        "principal_id": OPERATOR,
        "label": "laptop",
        "extension_version": "0.1.0",
        "registered_at": at(0),
        "last_seen_at": at(0),
        "secret": "what-this-browser-proves-itself-with",
    }
    return AgentDevice(**{**defaults, **overrides})


def provenance(**overrides: Any) -> Provenance:
    defaults: dict[str, Any] = {
        "recording_ids": (RecordingId("rec-1"), RecordingId("rec-2")),
        "induced_at": at(600),
        "induced_by": OPERATOR,
    }
    return Provenance(**{**defaults, **overrides})


def skill_version(**overrides: Any) -> SkillVersion:
    defaults: dict[str, Any] = {
        "version": 1,
        "steps": (step(),),
        "parameters": (parameter(),),
        "provenance": provenance(),
    }
    return SkillVersion(**{**defaults, **overrides})


def skill(*, versions: int = 1, **overrides: Any) -> Skill:
    defaults: dict[str, Any] = {
        "id": SkillId("skill-1"),
        "tenant_id": TENANT,
        "objective_key": objective(),
        "name": "Resolve a short ship",
        "created_at": T0,
    }
    result = Skill(**{**defaults, **overrides})
    for n in range(1, versions + 1):
        result.add_version(skill_version(version=n))
    return result


# re-exported so a test can build a payload without importing the domain twice
Body = Body
