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
import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sro.application.ports.agent import DeviceUnreachable
from sro.domain.shared.identifiers import DeviceId, TenantId

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0

_DEFAULT_BUSY = 5.0
"""What a `busy` with no window of its own asks for."""

MAX_BUSY_WAIT = 0.5
"""How much of a command's own deadline may be spent waiting for the operator
to stop typing, as a fraction of it. A device that says it is busy is asking for
politeness, not for a veto: a run that waited out every keystroke would be a run
that never happened on a busy morning."""


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
        """What went wrong, keeping the kind the extension named.

        The detail alone used to win whenever both were sent, which threw away
        the only machine-readable half. `focus_not_permitted` with a sentence
        beside it arrived as the sentence, so a run that politely declined to
        steal the operator's screen was indistinguishable from one that could
        not find a control. Every device failure passes through here, so naming
        the kind once covers all of them.
        """
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class DeviceSockets:
    """Which browsers are connected here, and what they owe an answer to."""

    def __init__(self, *, timeout_s: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout_s
        self._sockets: dict[tuple[str, str], Socket] = {}
        self._pending: dict[str, asyncio.Future[Answer]] = {}
        self._busy: dict[tuple[str, str], float] = {}

    # -- the router's side ---------------------------------------------------

    def attach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        """A device is connected. A second connection for the same device
        replaces the first: a browser that reconnected after a network drop is
        the same browser, and the stale socket will never answer anything."""
        self._sockets[_key(tenant_id, device_id)] = socket

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        """Forget whatever socket this device holds: it is offline from here
        on, whether or not the browser has noticed.

        The one caller is a tenant revoking a browser, and a revoked browser
        that still read as connected would be an audit line nobody could
        trust.
        """
        key = _key(tenant_id, device_id)
        self._busy.pop(key, None)
        return self._sockets.pop(key, None) is not None

    def detach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:
        """Only if it is still the socket we hold. A slow close arriving after
        a reconnect must not unregister the live one."""
        key = _key(tenant_id, device_id)
        if self._sockets.get(key) is socket:
            del self._sockets[key]
            # A browser that said it was busy and then closed the lid is not
            # busy any more, and its entry would otherwise sit here for the
            # life of the process waiting for a send that never comes.
            self._busy.pop(key, None)

    def deliver(
        self, raw: str, tenant_id: TenantId | None = None, device_id: DeviceId | None = None
    ) -> None:
        """An answer arrived. Unknown ids are dropped, not raised: a reply to a
        command that already timed out is late, not wrong.

        The device is named by the router rather than by the message, because a
        browser saying which device it is would be a browser that could say it
        was another one. It is only needed for the unsolicited messages -- an
        answer carries its own command id and needs nothing else.
        """
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("a device sent something that is not JSON")
            return
        if not isinstance(message, dict):
            return

        if message.get("kind") == "busy" and tenant_id is not None and device_id is not None:
            # Self-expiring, and short. A browser that says it is busy and then
            # closes its laptop must not leave a device nothing can be sent to
            # until the process restarts, so the pause carries its own end
            # rather than waiting for an "idle" that may never come.
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
        key = _key(tenant_id, device_id)
        if key not in self._sockets:
            # Keyed by tenant as well as device, so another tenant's id is not
            # a device that exists and refuses -- it is a device that is not
            # there, which is the same answer as one that never existed.
            raise DeviceUnreachable(f"{device_id} has no channel open")

        command_id = f"cmd_{uuid.uuid4().hex}"
        deadline = timeout_s or self._timeout
        await self._wait_out_the_operator(key, deadline)

        # Read *after* the wait, not before it. That wait can be seconds long,
        # and a laptop lid or a wifi hop in the middle of it has the extension
        # re-dial: `attach` replaces the registry entry, and a command sent
        # down the socket this call was holding fails as an unreachable device
        # against a browser that is in fact connected.
        socket = self._sockets.get(key)
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

    def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None:
        """How much longer this browser has asked to be left alone.

        Clamped to what `_wait_out_the_operator` will actually honour, so a
        console counting down from this never promises longer than the backend
        intends to wait. The expired entry is dropped here as well as there:
        two readers of one dict disagreeing about whether a pause is over is a
        bug waiting for a quiet morning.
        """
        key = _key(tenant_id, device_id)
        busy_until = self._busy.get(key)
        if busy_until is None:
            return None
        remaining = busy_until - asyncio.get_running_loop().time()
        if remaining <= 0:
            self._busy.pop(key, None)
            return None
        return min(remaining, self._timeout * MAX_BUSY_WAIT)

    async def _wait_out_the_operator(self, key: tuple[str, str], deadline: float) -> None:
        """Hold a command back while the operator is using their own browser.

        Typing into a field a moment before a replay clicks it is how a run and
        a person fight over the same form. Bounded by a fraction of the
        command's own deadline: politeness that could stall a run indefinitely
        would be a browser deciding whether work happens.
        """
        busy_until = self._busy.get(key)
        if busy_until is None:
            return
        remaining = busy_until - asyncio.get_running_loop().time()
        if remaining <= 0:
            self._busy.pop(key, None)
            return
        await asyncio.sleep(min(remaining, deadline * MAX_BUSY_WAIT))


def _busy_seconds(for_ms: object) -> float | None:
    """How long a device is asking to be left alone, or `None` for a message
    that does not say anything usable.

    Absent is the documented default. Present and not a real number of
    milliseconds is ignored outright rather than rounded into a default: a
    browser that sends nonsense has not asked for anything in particular.

    `json.loads` accepts a bare `NaN`, which passes an `isinstance` check and
    survives `min()` -- and `asyncio.sleep(nan)` raises. Stored, that made every
    later command to the device raise the same way, so one malformed frame from
    one browser took that device offline until the process restarted.
    """
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
