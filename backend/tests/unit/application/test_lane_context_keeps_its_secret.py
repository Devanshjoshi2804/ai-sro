import asyncio

from sro.application.runtime.step import LaneContext
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Workflow


def test_the_repr_of_a_lane_context_never_shows_the_secret() -> None:
    ctx = LaneContext(
        tenant_id=TenantId("t1"),
        principal_id=PrincipalId("p1"),
        workflow=Workflow(id="wf_1", tenant="t1", title="t", narrative="n"),
        by_id={},
        learned={},
        ledger=(),
        held=None,
        stop=asyncio.Event(),
        secret="hunter2",  # noqa: S106 -- the value under test, not a credential
    )

    assert "hunter2" not in repr(ctx)
