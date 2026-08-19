"""What may be retried after the healer repairs a session.

The diagnosis reads a 302 as proof the request was turned away at a login page
before the application saw it. Sometimes it is. It is also exactly what a
successful form POST answers with -- POST, redirect, GET -- and the two are
indistinguishable from the executor's side.

So the diagnosis does not decide this. The attempt does: a status code means the
application answered, and an answered POST that is sent again is one create
becoming two, in a warehouse, with the run reporting a clean single write.
"""

from __future__ import annotations

import pytest

from sro.application.execution.execute_skill import _may_be_retried
from sro.domain.execution.run import Medium, StepDisposition, StepOutcome
from sro.domain.skill.plan import Template
from tests import factories as f


def _outcome(status: int | None) -> StepOutcome:
    return StepOutcome(
        index=0,
        medium=Medium.NETWORK,
        disposition=StepDisposition.PERFORMED,
        intent="create the client",
        method="POST",
        status_code=status,
    )


@pytest.mark.parametrize("status", [200, 201, 302, 401, 500])
def test_a_write_the_system_answered_is_never_sent_again(status: int) -> None:
    write = f.step(index=0, network_plan=f.network_plan(method="POST"))

    assert not _may_be_retried(write, _outcome(status))


def test_a_write_that_never_reached_the_wire_may_be() -> None:
    """No status: the step refused before the request was built -- a header it
    holds no live value for. Nothing landed, so nothing can land twice."""
    write = f.step(index=0, network_plan=f.network_plan(method="POST"))

    assert _may_be_retried(write, _outcome(None))


@pytest.mark.parametrize("status", [200, 302, 500, None])
def test_a_read_may_always_be(status: int | None) -> None:
    read = f.step(
        index=0,
        network_plan=f.network_plan(
            method="GET", url=Template("https://wms.test/api/clients"), body=None
        ),
    )

    assert _may_be_retried(read, _outcome(status))
