"""Asking the process that holds a browser to run something.

The channel to an operator's Chrome is held by whichever process the extension
connected to, and the scheduler's worker is not that one. So a scheduled run
bound to a device is *asked for* over the same public endpoint a person uses,
with a short-lived credential minted for the trigger's own principal.

Deliberately that endpoint and no other. An internal "send this browser a
command" route would be a way to drive somebody's signed-in session anywhere,
which no taught skill can do; this can only start a skill that was taught, with
values a trigger already recorded.
"""

from __future__ import annotations

import json
import logging

import httpx

from sro.application.context import RequestContext
from sro.application.ports.auth import Caller, Credentials
from sro.application.ports.dispatch import DispatchFailed, RunDispatcher
from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import DeviceId, SkillId

logger = logging.getLogger(__name__)

CREDENTIAL_HOURS = 0.05
"""Three minutes. Long enough to make one call, short enough that a copy of it
found in a log later is worth nothing."""


class ApiRunDispatcher(RunDispatcher):
    def __init__(
        self, base_url: str, credentials: Credentials, *, timeout_s: float = 120.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._credentials = credentials
        self._timeout = timeout_s

    async def start(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        version: int | None = None,
        authorized_by: bool = False,
        medium: Medium = Medium.NETWORK,
        may_take_focus: bool = False,
    ) -> RunId:
        token = self._credentials.issue(
            Caller(tenant_id=ctx.tenant_id, principal_id=ctx.principal_id),
            lasting_hours=CREDENTIAL_HOURS,
        )
        body = {
            "parameters": parameters,
            "version": version,
            "medium": medium.value,
            "device_id": device_id.value,
            "may_take_focus": may_take_focus,
            # The API turns this into the principal on the credential above --
            # which is the trigger's authoriser, because that is who the
            # credential was minted for.
            "authorized_by": ctx.principal_id.value if authorized_by else None,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/skills/{skill_id.value}/runs",
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as unreachable:
            raise DispatchFailed(
                f"the run could not be handed to {self._base_url}: {unreachable}"
            ) from unreachable

        if response.status_code >= 400:
            raise DispatchFailed(_why(response))

        run_id = response.json().get("id")
        if not run_id:
            raise DispatchFailed("the run was started but came back without an id")
        return RunId(str(run_id))


def _why(response: httpx.Response) -> str:
    """The problem document's own sentence, when there is one. A status code on
    its own sends whoever reads the log to the wrong place."""
    try:
        problem = response.json()
    except (json.JSONDecodeError, ValueError):
        return f"the run was refused with {response.status_code}"
    detail = problem.get("detail") if isinstance(problem, dict) else None
    return f"the run was refused: {detail or response.status_code}"
