"""The open channels to operators' browsers, and the commands sent down them.

One command, one answer, correlated by an id this side mints. The extension
must answer every command exactly once, including with an error, and a late
answer is discarded rather than applied -- a run that has already recorded the
step as failed must not have it succeed underneath it.

Held in memory on purpose. A socket does not survive a restart either, so a
durable record of which browser was connected would only ever be a record of
which browser used to be connected.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sro.application.ports.agent import DeviceUnreachable
from sro.domain.shared.identifiers import DeviceId, TenantId

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0


class Socket(Protocol):
    """What the router hands over. Narrow so this file never imports a web
    framework, and so a test can be a list."""

    async def send_text(self, text: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Answer:
    ok: bool
    result: Mapping[str, object] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        return self.error_detail or self.error_kind or ""


class DeviceSockets:
    """Which browsers are connected here, and what they owe an answer to."""

    def __init__(self, *, timeout_s: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout_s
        self._sockets: dict[tuple[str, str], Socket] = {}
        self._pending: dict[str, asyncio.Future[Answer]] = {}

    # -- the router's side ---------------------------------------------------

    def attach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        """A device is connected. A second connection for the same device
        replaces the first: a browser that reconnected after a network drop is
        the same browser, and the stale socket will never answer anything."""
        self._sockets[_key(tenant_id, device_id)] = socket

    def detach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        """Only if it is still the socket we hold. A slow close arriving after
        a reconnect must not unregister the live one."""
        key = _key(tenant_id, device_id)
        if self._sockets.get(key) is socket:
            del self._sockets[key]

    def deliver(self, raw: str) -> None:
        """An answer arrived. Unknown ids are dropped, not raised: a reply to a
        command that already timed out is late, not wrong."""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("a device sent something that is not JSON")
            return
        if not isinstance(message, dict):
            return

        waiting = self._pending.pop(str(message.get("command_id", "")), None)
        if waiting is None or waiting.done():
            return

        error = message.get("error")
        error = error if isinstance(error, dict) else {}
        result = message.get("result")
        waiting.set_result(
            Answer(
                ok=bool(message.get("ok")),
                result=result if isinstance(result, dict) else {},
                error_kind=str(error.get("kind")) if error.get("kind") else None,
                error_detail=str(error.get("detail")) if error.get("detail") else None,
            )
        )

    # -- the driver's side ---------------------------------------------------

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return tuple(
            DeviceId(device) for tenant, device in self._sockets if tenant == tenant_id.value
        )

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        timeout_s: float | None = None,
    ) -> Answer:
        socket = self._sockets.get(_key(tenant_id, device_id))
        if socket is None:
            # Keyed by tenant as well as device, so another tenant's id is not
            # a device that exists and refuses -- it is a device that is not
            # there, which is the same answer as one that never existed.
            raise DeviceUnreachable(f"{device_id} has no channel open")

        command_id = f"cmd_{uuid.uuid4().hex}"
        deadline = timeout_s or self._timeout
        waiting: asyncio.Future[Answer] = asyncio.get_running_loop().create_future()
        self._pending[command_id] = waiting

        try:
            await socket.send_text(
                json.dumps(
                    {
                        "command_id": command_id,
                        "kind": kind,
                        "run_id": run_id,
                        "deadline_ms": int(deadline * 1000),
                        "payload": dict(payload),
                    }
                )
            )
        except Exception as broken:
            self._pending.pop(command_id, None)
            raise DeviceUnreachable(f"{device_id} stopped listening") from broken

        try:
            return await asyncio.wait_for(waiting, timeout=deadline)
        except TimeoutError:
            return Answer(
                ok=False,
                error_kind="timeout",
                error_detail=f"the browser did not answer within {deadline:.0f}s",
            )
        finally:
            self._pending.pop(command_id, None)


def _key(tenant_id: TenantId, device_id: DeviceId) -> tuple[str, str]:
    return tenant_id.value, device_id.value
