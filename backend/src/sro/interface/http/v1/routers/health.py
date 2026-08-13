"""Liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from sro.interface.http.deps import ContainerDep

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    checks: dict[str, bool]


@router.get("/health")
async def health() -> Health:
    """Liveness: the process answers. Deliberately touches no dependency."""
    return Health(status="ok", checks={})


@router.get("/ready")
async def ready(container: ContainerDep) -> Health:
    checks = {"database": await container.database_reachable()}
    return Health(status="ok" if all(checks.values()) else "degraded", checks=checks)
