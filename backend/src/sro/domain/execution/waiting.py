from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sro.domain.execution.mail_job import MAIL_BODY
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import WorkflowRun

K_PATIENCE = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class Awaiting:
    server: str

    thread: str
    until: str


def waiting_on(
    server: str, thread: str, *, now: datetime, patience: timedelta = K_PATIENCE
) -> Awaiting | None:
    if not server.strip() or not thread.strip():
        return None
    return Awaiting(
        server=server.strip(),
        thread=thread.strip(),
        until=(now + patience).isoformat(),
    )


def still_waiting(awaiting: Awaiting | None, now: datetime) -> bool:
    if awaiting is None:
        return False
    try:
        until = datetime.fromisoformat(awaiting.until)
    except ValueError:
        return False
    return (until if until.tzinfo else until.replace(tzinfo=UTC)) > now


def asks_a_person(run: WorkflowRun) -> bool:
    asking = Progress.of(run.progress).asking
    return (
        bool(run.needs)
        or (run.outcome == "running" and bool(asking.get("id")))
        or (run.outcome == "stopped" and asking.get("kind") in ("recipient", MAIL_BODY))
    )


def as_said(awaiting: Awaiting | None) -> dict[str, str] | None:
    if awaiting is None:
        return None
    return {"server": awaiting.server, "thread": awaiting.thread, "until": awaiting.until}


def read_wait(said: object) -> Awaiting | None:
    if not isinstance(said, Mapping):
        return None
    server, thread, until = (
        str(said.get("server") or ""),
        str(said.get("thread") or ""),
        str(said.get("until") or ""),
    )
    if not server.strip() or not thread.strip() or not until.strip():
        return None
    return Awaiting(server=server, thread=thread, until=until)


__all__ = [
    "K_PATIENCE",
    "Awaiting",
    "as_said",
    "asks_a_person",
    "read_wait",
    "still_waiting",
    "waiting_on",
]
