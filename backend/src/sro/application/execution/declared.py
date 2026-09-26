from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.field_notes import keys_named, limits_named
from sro.domain.knowledge.entry import EntryKind, KnowledgeEntry
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import screen_of
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Workflow

K_EVERY_FIELD = 800

K_EVERY_FORM = 400

KbRows = tuple[Sequence[KnowledgeEntry], Sequence[KnowledgeEntry]]


async def kb_rows(uow: UnitOfWork, tenant_id: TenantId) -> KbRows:
    async with uow as opened:
        fields = await opened.knowledge.search(
            tenant_id, kinds=(EntryKind.FIELD,), limit=K_EVERY_FIELD
        )
        forms = await opened.knowledge.search(
            tenant_id, kinds=(EntryKind.FORM,), limit=K_EVERY_FORM
        )
    return fields, forms


def limits_from_rows(
    names: Sequence[str],
    fields: Sequence[KnowledgeEntry],
    forms: Sequence[KnowledgeEntry],
    screen: str,
) -> dict[str, int]:
    label = _screen_label(forms, screen)
    return limits_named(names, _slots(forms, screen), _on_its_screen(fields, label))


def keys_from_rows(
    names: Sequence[str],
    fields: Sequence[KnowledgeEntry],
    forms: Sequence[KnowledgeEntry],
    screen: str,
) -> dict[str, str]:
    label = _screen_label(forms, screen)
    return keys_named(names, _slots(forms, screen), _on_its_screen(fields, label))


async def declared_limits(
    uow: UnitOfWork, tenant_id: TenantId, names: Sequence[str], screen: str = ""
) -> dict[str, int]:
    if not names:
        return {}
    fields, forms = await kb_rows(uow, tenant_id)
    return limits_from_rows(names, fields, forms, screen)


async def declared_keys(
    uow: UnitOfWork, tenant_id: TenantId, names: Sequence[str], screen: str = ""
) -> dict[str, str]:
    if not names:
        return {}
    fields, forms = await kb_rows(uow, tenant_id)
    return keys_from_rows(names, fields, forms, screen)


def _slots(forms: Sequence[object], screen: str) -> dict[str, dict[str, object]]:
    slots: dict[str, dict[str, object]] = {}
    for entry in forms:
        route = str(getattr(entry, "key", "") or "").rstrip("/")
        body = getattr(entry, "body", None)
        if not route or route not in screen or not isinstance(body, Mapping):
            continue
        fields = body.get("fields")
        for one in fields if isinstance(fields, list) else ():
            if not isinstance(one, Mapping) or not isinstance(slot := one.get("field"), str):
                continue
            said: dict[str, object] = {"observed": True}
            if isinstance(one.get("label"), str):
                said["labels"] = [one["label"]]
            if isinstance(cap := one.get("maxLength"), int) and not isinstance(cap, bool):
                said["max_length"] = cap
            slots.setdefault(slot, {}).update(said)
    return slots


def _screen_label(forms: Sequence[object], screen: str) -> str | None:
    for entry in forms:
        route = str(getattr(entry, "key", "") or "").rstrip("/")
        body = getattr(entry, "body", None)
        if not route or route not in screen or not isinstance(body, Mapping):
            continue
        label = body.get("label")
        if isinstance(label, str) and label.strip():
            return label
    return None


def _on_its_screen(fields: Sequence[object], label: str | None) -> dict[str, Mapping[str, object]]:
    found: dict[str, Mapping[str, object]] = {}
    for entry in fields:
        key = getattr(entry, "key", None)
        body = getattr(entry, "body", None)
        if not isinstance(key, str) or not isinstance(body, Mapping):
            continue
        screens = body.get("screens")
        if isinstance(screens, list) and screens and label not in screens:
            continue
        found[key] = body
    return found


def names_of(workflow: Workflow) -> list[str]:
    return [
        name
        for parameter in workflow.parameters
        if isinstance(name := parameter.get("name"), str) and name.strip()
    ]


def _cites_with_params(workflow: Workflow) -> tuple[str, ...]:
    return tuple(sorted({one for step in workflow.steps if step.parameters for one in step.cites}))


def screen_of_loaded(by_id: Mapping[str, Gesture], workflow: Workflow) -> str:
    cites = _cites_with_params(workflow)
    if not cites:
        return ""
    return (
        screen_of([g.page_url or g.url for one in cites if (g := by_id.get(one)) is not None]) or ""
    )


async def screen_for(uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow) -> str:
    cites = _cites_with_params(workflow)
    if not cites:
        return ""
    async with uow as opened:
        gestures = await opened.gestures.gestures_for(tenant_id, ids=cites)
    return screen_of([one.page_url or one.url for one in gestures]) or ""


__all__ = [
    "declared_limits",
    "kb_rows",
    "limits_from_rows",
    "names_of",
    "screen_for",
    "screen_of_loaded",
]
