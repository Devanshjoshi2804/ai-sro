"""Every activity the run workflow calls is registered on the runs worker.

`run.answered` was defined and called but never registered: every answer to a
Steel run's question (a password, a value, a mail) failed with "not registered
on this worker" and the run never heard it (QA, 2026-10-01).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from temporalio import activity

from sro.container import Container
from sro.infrastructure.temporal import workflows
from sro.infrastructure.temporal.activities import RunActivities


def _names(functions: list[Callable[..., Any]]) -> set[str]:
    return {str(activity._Definition.must_from_callable(one).name) for one in functions}


def test_the_runs_worker_registers_every_activity_the_run_workflow_calls() -> None:
    called = set(re.findall(r'"(run\.[a-z_]+)"', Path(workflows.__file__).read_text()))

    registered = _names(RunActivities(cast(Container, None)).registered())

    assert called and called <= registered, f"called but not registered: {called - registered}"
    assert "run.answered" in registered
