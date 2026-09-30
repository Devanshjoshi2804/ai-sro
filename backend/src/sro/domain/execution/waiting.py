from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sro.domain.execution.mail_job import DRAFT_QUESTIONS
from sro.domain.execution.progress import K_BUDGET_MARGIN_S, Progress
from sro.domain.execution.workflow_run import WorkflowRun

K_PATIENCE = timedelta(days=7)

STUCK = "the run stopped responding and was closed after its time ran out"

Durably = Literal["open", "closed", "unknown"]


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
        or (run.outcome == "stopped" and asking.get("kind") in DRAFT_QUESTIONS)
    )


def standing_question(run: WorkflowRun) -> str:
    asking = Progress.of(run.progress).asking
    if run.outcome != "running" or not asking.get("id") or asking.get("answered"):
        return ""
    return asking.get("text", "")


def stuck(run: WorkflowRun, *, budget_s: float, now: datetime, durable: Durably) -> bool:
    if run.outcome != "running" or durable == "open":
        return False
    if durable == "closed":
        return True
    if asks_a_person(run) or any(step.verdict == "awaiting" for step in run.steps):
        return False
    started = datetime.fromisoformat(run.started_at)
    allowed = budget_s * max(1, len(run.items)) + K_BUDGET_MARGIN_S
    return now >= started + timedelta(seconds=allowed)


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
    "STUCK",
    "Awaiting",
    "Durably",
    "as_said",
    "asks_a_person",
    "read_wait",
    "still_waiting",
    "stuck",
    "waiting_on",
]
