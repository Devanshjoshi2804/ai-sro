"""Liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from sro.config import get_settings
from sro.interface.http.deps import ContainerDep

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    revision: str
    """The commit this process was started from -- not the working tree's.

    Here because the expensive failure is not a process that is down, it is a
    process that is up and old: the answer it gives is a rule that was fixed
    hours ago, and nothing about the answer says so. `make status` reads this."""
    checks: dict[str, bool]


@router.get("/health")
async def health() -> Health:
    """Liveness: the process answers, and says which code it is answering with.

    Still touches no dependency: the revision was resolved once at startup."""
    return Health(status="ok", revision=get_settings().revision, checks={})


@router.get("/ready")
async def ready(container: ContainerDep) -> Health:
    # Two facts, not one. A database that answers and is behind its code is
    # reachable and useless -- which is the state that cost an afternoon of
    # diagnosis aimed at the wrong half of the system. Both come back from one
    # connection: see `Container.readiness`.
    checks = await container.readiness()
    return Health(
        status="ok" if all(checks.values()) else "degraded",
        revision=container.settings.revision,
        checks=checks,
    )
