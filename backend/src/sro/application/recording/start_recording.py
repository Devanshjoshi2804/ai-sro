"""Open a browser session and the Recording that will collect its frames."""

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
    """The debugger URL points somewhere this deployment will not connect.

    ``attach_to`` arrives in the request body and is dialled by the backend, so
    without a bound it reaches anything the backend can: another tenant's
    container, an internal service, a cloud metadata endpoint. The browser being
    attached to is the operator's own, which is on this machine.
    """

    code = "browser_not_attachable"


class NoSessionForSystem(DomainError):
    """This system is known but nobody is signed in to it.

    Raised before a browser opens, because the alternative is what used to
    happen: the operator gets a login page inside a live recording and teaches
    signing in, which is a different task from the one they meant to teach.
    """

    code = "no_session_for_system"


@dataclass(frozen=True, slots=True)
class StartedRecording:
    recording_id: RecordingId
    live_view_url: str

    debugger_url: str = ""
    """CDP endpoint for the capture adapter. Never put on the wire."""

    browser_session_id: BrowserSessionId | None = None

    target_system: str | None = None
    """The connected system this URL belongs to, if any -- which is how a
    demonstration that names nothing still starts already signed in."""


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

        # Browser first: if it fails nothing is written, so we never accumulate
        # recordings that can only ever be abandoned.
        # Opened blank on purpose. Handing the provider a start URL makes it
        # navigate the moment the session exists -- before the stored session
        # cookies have been restored -- so the operator lands on the identity
        # provider's login page and teaches signing in instead of the task.
        # Capture navigates after restoring them.
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
        """Scheme and host, checked before anything dials it.

        The scheme matters as much as the host: ``file:`` and ``gopher:`` are
        not debugger endpoints, and neither is anything else a URL library will
        happily open on our behalf.
        """
        if urlsplit(attach_to).scheme not in ("http", "https", "ws", "wss"):
            raise BrowserNotAttachable(f"{attach_to} is not a debugger endpoint")
        if host_of(attach_to) not in self._attach_hosts:
            raise BrowserNotAttachable(
                f"this deployment does not attach to browsers on {host_of(attach_to) or attach_to}"
            )
