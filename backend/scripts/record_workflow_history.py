from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from temporalio.client import (
    Client,
    Interceptor,
    OutboundInterceptor,
    StartWorkflowInput,
    WorkflowHandle,
)

from sro.infrastructure.temporal.workflows import RunWorkflow

HISTORIES = Path(__file__).resolve().parents[1] / "tests" / "replay" / "histories"
VERSION = hashlib.sha256(inspect.getsource(RunWorkflow).encode()).hexdigest()[:8]


class Recording(Interceptor):
    def __init__(self) -> None:
        self.started: list[str] = []

    def intercept_client(self, outbound: OutboundInterceptor) -> OutboundInterceptor:
        return _Starts(outbound, self.started)


class _Starts(OutboundInterceptor):
    def __init__(self, outbound: OutboundInterceptor, started: list[str]) -> None:
        super().__init__(outbound)
        self._started = started

    async def start_workflow(self, start: StartWorkflowInput) -> WorkflowHandle[Any, Any]:
        self._started.append(start.id)
        return await super().start_workflow(start)


async def save(client: Client, started: list[str], name: str) -> None:
    for n, workflow_id in enumerate(started):
        history = await client.get_workflow_handle(workflow_id).fetch_history()
        recorded = json.loads(history.to_json(), object_hook=_without_stack_traces)
        (HISTORIES / f"{VERSION}-{name}-{n}.json").write_text(json.dumps(recorded, indent=1))


def _without_stack_traces(node: dict[str, Any]) -> dict[str, Any]:
    return {key: "" if key == "stackTrace" else value for key, value in node.items()}
