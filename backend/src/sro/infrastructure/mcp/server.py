from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerMiddleware, ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult, TextContent, Tool

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import NotRunnable
from sro.application.execution.read_runs import GetRun
from sro.application.ports.auth import Credentials
from sro.application.ports.durable import DurableExecution
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.domain.execution.run import Run
from sro.domain.execution.verdict import judge
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import Skill

_AUTHENTICATED_METHODS = frozenset({"tools/list", "tools/call"})

_ctx_var: ContextVar[RequestContext | None] = ContextVar("mcp_request_context", default=None)


def _require_context() -> RequestContext:
    ctx = _ctx_var.get()
    if ctx is None:
        raise PermissionError("no credential on this request")
    return ctx


def _authenticator(credentials: Credentials) -> ServerMiddleware[Any]:
    async def authenticate(
        ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        if ctx.method not in _AUTHENTICATED_METHODS:
            return await call_next(ctx)

        headers = getattr(ctx.request, "headers", None)
        authorization = headers.get("authorization") if headers is not None else None
        if not authorization:
            raise PermissionError(
                "this endpoint needs a credential: send `Authorization: Bearer <token>`"
            )
        caller = credentials.verify(authorization)
        token = _ctx_var.set(
            RequestContext(tenant_id=caller.tenant_id, principal_id=caller.principal_id)
        )
        try:
            return await call_next(ctx)
        finally:
            _ctx_var.reset(token)

    return authenticate


def _tool_for(skill: Skill) -> Tool | None:
    version = skill.runnable
    if version is None:
        return None

    properties: dict[str, Any] = {
        parameter.name: {"type": "string", "description": parameter.description or parameter.name}
        for parameter in version.inputs
    }
    if version.changes_the_system:
        properties["authorize"] = {
            "type": "boolean",
            "description": "Set true to confirm this write.",
        }
    return Tool(
        name=skill.id.value,
        title=skill.name,
        description=version.when_to_use or version.summary or skill.name,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": [parameter.name for parameter in version.inputs],
        },
    )


def _summarise(run: Run) -> str:
    verdict = judge(run)
    parts = [f"{verdict.value}: run {run.id.value} finished {run.status.value}."]
    if run.writes_sent:
        parts.append(f"{run.writes_sent} write(s) sent.")
    if run.failure:
        parts.append(run.failure)
    return " ".join(parts)


class SkillToolServer(MCPServer[None]):
    def __init__(
        self,
        *,
        credentials: Credentials,
        list_skills: Callable[[], ListSkills],
        get_skill: Callable[[], GetSkill],
        durable: DurableExecution,
        get_run: Callable[[], GetRun],
    ) -> None:
        super().__init__(
            name="ai-sro",
            instructions="One tool per skill this tenant has taught and promoted past `recorded`.",
            middleware=[_authenticator(credentials)],
        )
        self._list_skills = list_skills
        self._get_skill = get_skill
        self._durable = durable
        self._get_run = get_run

    async def list_tools(self) -> list[Tool]:
        ctx = _require_context()
        skills = await self._list_skills().execute(ctx)
        return [tool for skill in skills if (tool := _tool_for(skill)) is not None]

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context[None, Any] | None = None
    ) -> CallToolResult:
        ctx = _require_context()
        skill_id = SkillId(name)
        skill = await self._get_skill().execute(ctx, skill_id=skill_id)
        version = skill.runnable
        if version is None:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"{skill.name} has not been reviewed yet; promote it past "
                        "`recorded` to run it.",
                    )
                ],
                is_error=True,
            )

        remaining = dict(arguments)
        authorize = bool(remaining.pop("authorize", False))
        try:
            run_id = await self._durable.execute_skill(
                ctx,
                skill_id=skill_id,
                parameters={key: str(value) for key, value in remaining.items()},
                version=version.version,
                authorized_by=ctx.principal_id.value if authorize else None,
                medium="network",
            )
        except NotRunnable as exc:
            return CallToolResult(content=[TextContent(type="text", text=str(exc))], is_error=True)

        run = await self._get_run().execute(ctx, run_id=run_id)
        return CallToolResult(content=[TextContent(type="text", text=_summarise(run))])
