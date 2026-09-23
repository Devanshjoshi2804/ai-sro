from __future__ import annotations

import asyncio
import json
import logging
import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sro.application.ports.agent import DeviceUnreachable
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.telemetry.otel import doing
from sro.whose import about

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0

_DEFAULT_BUSY = 5.0

K_REDIAL = 8.0

K_LOOK_AGAIN = 0.25

MAX_BUSY_WAIT = 0.5


class Socket(Protocol):
    async def send_text(self, text: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Answer:
    ok: bool
    result: Mapping[str, object] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class DeviceSockets:
    def __init__(self, *, timeout_s: float = DEFAULT_TIMEOUT, redial_s: float = K_REDIAL) -> None:
        self._timeout = timeout_s
        self._redial = redial_s
        self._sockets: dict[tuple[str, str], Socket] = {}
        self._pending: dict[str, asyncio.Future[Answer]] = {}
        self._busy: dict[tuple[str, str], float] = {}

    def attach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        self._sockets[_key(tenant_id, device_id)] = socket

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        key = _key(tenant_id, device_id)
        self._busy.pop(key, None)
        return self._sockets.pop(key, None) is not None

    def detach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        key = _key(tenant_id, device_id)
        if self._sockets.get(key) is socket:
            del self._sockets[key]
            self._busy.pop(key, None)

    def deliver(
        self, raw: str, tenant_id: TenantId | None = None, device_id: DeviceId | None = None
    ) -> None:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("a device sent something that is not JSON")
            return
        if not isinstance(message, dict):
            return

        if message.get("kind") == "busy" and tenant_id is not None and device_id is not None:
            seconds = _busy_seconds(message.get("for_ms"))
            if seconds is not None:
                self._busy[_key(tenant_id, device_id)] = asyncio.get_running_loop().time() + seconds
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
        source: str = "backend",
    ) -> Answer:
        key = _key(tenant_id, device_id)
        if await self._dialling_back(key) is None:
            raise DeviceUnreachable(f"{device_id} has no channel open")

        command_id = f"cmd_{uuid.uuid4().hex}"
        deadline = timeout_s or self._timeout
        await self._wait_out_the_operator(key, deadline)

        socket = await self._dialling_back(key)
        if socket is None:
            raise DeviceUnreachable(f"{device_id} has no channel open")
        waiting: asyncio.Future[Answer] = asyncio.get_running_loop().create_future()
        self._pending[command_id] = waiting

        try:
            await socket.send_text(
                json.dumps(
                    {
                        "command_id": command_id,
                        "kind": kind,
                        "run_id": run_id,
                        "source": source,
                        "deadline_ms": int(deadline * 1000),
                        "payload": dict(payload),
                    }
                )
            )
        except Exception as broken:
            self._pending.pop(command_id, None)
            raise DeviceUnreachable(f"{device_id} stopped listening") from broken

        try:
            with about(command=command_id), doing("browser.command", command=command_id) as span:
                span.set_attribute("kind", kind)
                return await asyncio.wait_for(waiting, timeout=deadline)
        except TimeoutError:
            return Answer(
                ok=False,
                error_kind="timeout",
                error_detail=f"the browser did not answer within {deadline:.0f}s",
            )
        finally:
            self._pending.pop(command_id, None)

    def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None:
        key = _key(tenant_id, device_id)
        busy_until = self._busy.get(key)
        if busy_until is None:
            return None
        remaining = busy_until - asyncio.get_running_loop().time()
        if remaining <= 0:
            self._busy.pop(key, None)
            return None
        return min(remaining, self._timeout * MAX_BUSY_WAIT)

    async def _dialling_back(self, key: tuple[str, str]) -> Socket | None:
        socket = self._sockets.get(key)
        if socket is not None or self._redial <= 0:
            return socket
        loop = asyncio.get_running_loop()
        until = loop.time() + self._redial
        while loop.time() < until:
            await asyncio.sleep(K_LOOK_AGAIN)
            socket = self._sockets.get(key)
            if socket is not None:
                logger.info("%s dialled back in; the command goes down the new socket", key[1])
                return socket
        return None

    async def _wait_out_the_operator(self, key: tuple[str, str], deadline: float) -> None:
        busy_until = self._busy.get(key)
        if busy_until is None:
            return
        remaining = busy_until - asyncio.get_running_loop().time()
        if remaining <= 0:
            self._busy.pop(key, None)
            return
        await asyncio.sleep(min(remaining, deadline * MAX_BUSY_WAIT))


def _busy_seconds(for_ms: object) -> float | None:
    if for_ms is None:
        return _DEFAULT_BUSY
    if isinstance(for_ms, bool) or not isinstance(for_ms, int | float):
        return None
    seconds = float(for_ms) / 1000
    if not math.isfinite(seconds) or seconds <= 0:
        return None
    return min(seconds, 30.0)


def _key(tenant_id: TenantId, device_id: DeviceId) -> tuple[str, str]:
    return tenant_id.value, device_id.value
