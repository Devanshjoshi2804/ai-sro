from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sro.domain.chat.asking import NOTHING_NEW, shortened
from sro.domain.chat.thread import Message
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import read_wait, still_waiting
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.recording.sensitivity import is_secret_field

_OUTCOME = {
    "held": "has finished",
    "stopped": "has stopped",
    "refused": "was refused",
    "aborted": "was aborted",
    "failed": "did not finish",
}


def last_run(messages: Sequence[Message]) -> str | None:
    for message in reversed(messages):
        run_id = (message.decision or {}).get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id
    return None


def stands(run: WorkflowRun, now: datetime) -> bool:
    return run.outcome == "running" or still_waiting(read_wait(run.awaiting), now)


def of_the_run(run: WorkflowRun, title: str, now: datetime) -> str:
    progress = Progress.of(run.progress)
    if run.outcome != "running":
        said = [f"{title} {_OUTCOME.get(run.outcome, run.outcome)}."]
    elif run.doing.strip():
        said = [f"{title} is running — {run.doing.strip()}."]
    else:
        said = [f"{title} is running, at step {progress.step + 1}."]
    if asked := progress.asking.get("text", "").strip():
        said.append(f"It is waiting for your answer: {asked}")
    if still_waiting(read_wait(run.awaiting), now):
        said.append("No reply has answered it yet in the mail it is waiting on.")
    if run.needs:
        said.append(f"It still needs {', '.join(run.needs)}.")
    held = [
        f"{name}: {shortened(value)}{' (from the mail)' if name in run.gathered else ''}"
        for name, value in run.values.items()
        if value.strip() and not is_secret_field(name)
    ]
    if held:
        said.append("I have " + "; ".join(held) + ".")
    said.append(NOTHING_NEW)
    return " ".join(said)


__all__ = ["last_run", "of_the_run", "stands"]
