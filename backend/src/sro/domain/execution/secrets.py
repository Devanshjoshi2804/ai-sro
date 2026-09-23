from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of

SECRET_MARK = "«from the vault»"  # noqa: S105 - a marker written INSTEAD of a password


def field_of(gesture: Gesture) -> str:
    target = gesture.action.target
    component = target.component if target else None
    for name in (
        component.field_label if component else None,
        target.name if target else None,
        component.item_id if component else None,
    ):
        if name and name.strip():
            return _as_key(name)
    return "password"


def _as_key(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")


def secret_key_for(tenant_id: str, gesture: Gesture) -> str:
    system = origin_of(gesture.url or "") or origin_of(gesture.system or "") or "unknown"
    return f"{tenant_id}/{system}/{field_of(gesture)}"


def secret_key_of(tenant_id: str, system: str, field: str) -> str:
    return f"{tenant_id}/{origin_of(system) or system.strip().lower()}/{_as_key(field)}"


def connector_key(tenant_id: str, server: str, principal_id: str) -> str:
    named = hashlib.sha256(principal_id.encode()).hexdigest()[:32]
    return secret_key_of(tenant_id, server, f"mcp-token-{named}")


def needs_a_secret(gesture: Gesture) -> bool:
    target = gesture.action.target
    return bool(target and target.secret)


def without_secrets(payload: Mapping[str, object]) -> dict[str, object]:
    if payload.get("value") is None:
        return dict(payload)
    return {**payload, "value": SECRET_MARK}
