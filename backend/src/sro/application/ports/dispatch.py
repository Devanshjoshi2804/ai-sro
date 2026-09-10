"""Starting a run in a process that is not this one.

There is exactly one reason this exists: the channel to an operator's browser is
held by whichever process the extension connected to, and the scheduler's worker
is not that process. A run bound to a device is therefore asked for rather than
performed here.

Deliberately the same authority a person has -- start this taught skill, with
these values -- and not "send this browser a command". An interface that could
say the latter would be a way to drive somebody's signed-in session anywhere,
which no taught skill can do.
"""

from __future__ import annotations

from typing import Protocol

from sro.application.context import RequestContext
from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import DeviceId, SkillId


class RunDispatcher(Protocol):
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
        """Ask whoever holds that browser to run this, and answer with the run.

        ``may_take_focus`` travels with it because the process that holds the
        socket is not the process that read the trigger, and whether an
        operator's screen may be taken is the trigger's decision rather than
        either process's.
        """
        ...


class DispatchFailed(Exception):
    """The other process refused or could not be reached."""

    code = "dispatch_failed"
