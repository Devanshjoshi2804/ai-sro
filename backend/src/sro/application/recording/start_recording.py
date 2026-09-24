from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.capture.identity import host_of, system_of
from sro.application.connection.browsers import Browsers
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId
from sro.domain.shared.objective import ObjectiveKey


class BrowserNotAttachable(DomainError):
    code = "browser_not_attachable"


class NoSessionForSystem(DomainError):
    code = "no_session_for_system"


@dataclass(frozen=True, slots=True)
class StartedRecording:
    recording_id: RecordingId
    live_view_url: str

    debugger_url: str = ""

    browser_session_id: BrowserSessionId | None = None

    target_system: str | None = None


class StartRecording:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        clock: Clock,
        ids: IdFactory,
        browsers: Browsers,
        attach_hosts: tuple[str, ...] = (),
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._browsers = browsers
        self._clock = clock
        self._ids = ids
        self._attach_hosts = attach_hosts

    async def execute(
        self,
        ctx: RequestContext,
        *,
        objective_key: ObjectiveKey | None = None,
        start_url: str | None = None,
        label: str | None = None,
        attach_to: str | None = None,
    ) -> StartedRecording:
        if attach_to:
            self._refuse_unless_allowed(attach_to)

        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        system = (
            objective_key.target_system
            if objective_key
            else system_of(connections, start_url, attach_to)
        )

        session = (
            await self._browsers.attach(ctx, attach_to)
            if attach_to
            else await self._browsers.open(ctx)
        )

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            objective_key=objective_key,
            demonstrator=ctx.principal_id,
            started_at=self._clock.now(),
            label=label,
        )
        recording.attach_browser_session(session.id)

        async with self._uow as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        return StartedRecording(
            recording_id=recording.id,
            live_view_url=session.live_view_url,
            debugger_url=session.debugger_url,
            browser_session_id=session.id,
            target_system=system,
        )

    def _refuse_unless_allowed(self, attach_to: str) -> None:
        if urlsplit(attach_to).scheme not in ("http", "https", "ws", "wss"):
            raise BrowserNotAttachable(f"{attach_to} is not a debugger endpoint")
        if host_of(attach_to) not in self._attach_hosts:
            raise BrowserNotAttachable(
                f"this deployment does not attach to browsers on {host_of(attach_to) or attach_to}"
            )
