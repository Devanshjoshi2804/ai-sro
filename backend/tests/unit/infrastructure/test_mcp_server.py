"""The MCP server is built once for the process; a `UnitOfWork` must not be.

`SqlUnitOfWork` mutates its own session in place and is meant to be built once
per request, the way every HTTP router already does by calling
`container.xxx()` fresh inside the handler. This proves the MCP server does
the same thing through a factory, rather than sharing one instance -- and one
session -- across every concurrent tool call for the life of the process.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.read_runs import GetRun
from sro.application.ports.auth import Caller
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.infrastructure.mcp.server import SkillToolServer, _ctx_var
from tests import factories as f
from tests.unit.fakes import FakeDurableExecution, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SKILL_ID = SkillId("skl-1")


class _NoCredentials:
    def verify(self, presented: str) -> Caller:
        raise NotImplementedError("the middleware never runs when called directly")

    def issue(self, caller: Caller, *, lasting_hours: float) -> str:
        raise NotImplementedError("not used by this test")


async def _seeded() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    skill = f.skill(id=SKILL_ID, versions=0)
    version = f.skill_version(
        steps=(
            f.step(
                network_plan=f.network_plan(
                    method="GET", url=Template("https://wms.test/api/health"), body=None
                )
            ),
        ),
        parameters=(),
    )
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    return uow


async def test_list_tools_builds_a_fresh_use_case_every_call() -> None:
    uow = await _seeded()
    calls: list[None] = []

    def list_skills() -> ListSkills:
        calls.append(None)
        return ListSkills(uow)

    server = SkillToolServer(
        credentials=_NoCredentials(),
        list_skills=list_skills,
        get_skill=lambda: GetSkill(uow),
        durable=FakeDurableExecution(),
        get_run=lambda: GetRun(uow),
    )

    token = _ctx_var.set(CTX)
    try:
        await server.list_tools()
        await server.list_tools()
    finally:
        _ctx_var.reset(token)

    assert len(calls) == 2


async def test_call_tool_asks_the_factory_for_its_own_unit_of_work() -> None:
    uow = await _seeded()
    get_run_calls: list[None] = []

    def get_run() -> GetRun:
        get_run_calls.append(None)
        return GetRun(uow)

    # FakeDurableExecution's fallback path names the first run this way.
    await uow.runs.add(
        Run(
            id=RunId("run-started-1"),
            tenant_id=f.TENANT,
            skill_id=SKILL_ID,
            skill_version=1,
            stage=PromotionStage.SHADOW,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=f.at(0),
            status=RunStatus.SUCCEEDED,
        )
    )

    server = SkillToolServer(
        credentials=_NoCredentials(),
        list_skills=lambda: ListSkills(uow),
        get_skill=lambda: GetSkill(uow),
        durable=FakeDurableExecution(),
        get_run=get_run,
    )

    token = _ctx_var.set(CTX)
    try:
        result = await server.call_tool(SKILL_ID.value, {})
    finally:
        _ctx_var.reset(token)

    assert result.is_error is False
    assert len(get_run_calls) == 1
