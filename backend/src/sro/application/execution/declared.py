from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.field_notes import keys_named, limits_named
from sro.domain.knowledge.entry import EntryKind
from sro.domain.shared.hosts import screen_of
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Workflow

K_EVERY_FIELD = 800

K_EVERY_FORM = 400


async def declared_limits(
    uow: UnitOfWork, tenant_id: TenantId, names: Sequence[str], screen: str = ""
) -> dict[str, int]:
    if not names:
        return {}
    async with uow as opened:
        fields = await opened.knowledge.search(
            tenant_id, kinds=(EntryKind.FIELD,), limit=K_EVERY_FIELD
        )
        forms = (
            await opened.knowledge.search(tenant_id, kinds=(EntryKind.FORM,), limit=K_EVERY_FORM)
            if screen.strip()
            else ()
        )
    return limits_named(
        names,
        _slots(forms, screen),
        {one.key: one.body for one in fields if isinstance(one.body, Mapping)},
    )


async def declared_keys(
    uow: UnitOfWork, tenant_id: TenantId, names: Sequence[str], screen: str = ""
) -> dict[str, str]:
    if not names:
        return {}
    async with uow as opened:
        fields = await opened.knowledge.search(
            tenant_id, kinds=(EntryKind.FIELD,), limit=K_EVERY_FIELD
        )
        forms = (
            await opened.knowledge.search(tenant_id, kinds=(EntryKind.FORM,), limit=K_EVERY_FORM)
            if screen.strip()
            else ()
        )
    return keys_named(
        names,
        _slots(forms, screen),
        {one.key: one.body for one in fields if isinstance(one.body, Mapping)},
    )


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


def names_of(workflow: Workflow) -> list[str]:
    return [
        name
        for parameter in workflow.parameters
        if isinstance(name := parameter.get("name"), str) and name.strip()
    ]


async def screen_for(uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow) -> str:
    cites = tuple(sorted({one for step in workflow.steps if step.parameters for one in step.cites}))
    if not cites:
        return ""
    async with uow as opened:
        gestures = await opened.gestures.gestures_for(tenant_id, ids=cites)
    return screen_of([one.page_url or one.url for one in gestures]) or ""


__all__ = ["declared_limits", "names_of", "screen_for"]
