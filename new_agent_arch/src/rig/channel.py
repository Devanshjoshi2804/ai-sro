"""The rig's end of the command channel.

The extension dials out and the rig sends commands down; there is no endpoint
that drives a browser, because one would let a leaked device id reach a browser
that is not the caller's. One command, one answer, correlated by an id this side
mints. The extension answers every command exactly once, including with an
error, and a late answer is discarded rather than applied -- a run that has
already recorded the step as failed must not have it succeed underneath it.

This is the backend's `infrastructure/agent/sockets.py`, single-tenant. It is
written again rather than imported because the rig may not import `sro.*`; the
two must agree on the wire and nothing else.

Held in memory on purpose. A socket does not survive a restart either.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)

K_COMMAND_DEADLINE_S = 20.0
"""How long a browser has to answer one command. The extension's own timeout
is `deadline_ms` off the envelope, so both ends give up together."""

K_MAX_BUSY_WAIT = 0.5
"""How much of a command's own deadline may be spent waiting for the operator
to stop typing, as a fraction. A device that says it is busy is asking for
politeness, not for a veto."""

_DEFAULT_BUSY_S = 5.0


class DeviceUnreachable(Exception):
    """No socket for that device, or it stopped listening mid-send."""


class Socket(Protocol):
    async def send_text(self, text: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Answer:
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        """What went wrong, keeping the kind the extension named. The kind is
        the machine-readable half; dropping it made `focus_not_permitted`
        indistinguishable from a control that was not there."""
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class Channel(Protocol):
    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer: ...

    def online(self) -> list[str]: ...


class DeviceChannel:
    """Which browsers are connected here, and what they owe an answer to."""

    def __init__(self, deadline_s: float = K_COMMAND_DEADLINE_S) -> None:
        self._deadline = deadline_s
        self._sockets: dict[str, Socket] = {}
        self._pending: dict[str, asyncio.Future[Answer]] = {}
        self._busy_until: dict[str, float] = {}

    # -- the route's side ---------------------------------------------------

    def attach(self, device_id: str, socket: Socket) -> None:
        """A second connection for the same device replaces the first: a
        browser that reconnected after a network drop is the same browser."""
        self._sockets[device_id] = socket

    def detach(self, device_id: str, socket: Socket) -> None:
        """Only if it is still the socket we hold. A slow close arriving after
        a reconnect must not unregister the live one."""
        if self._sockets.get(device_id) is socket:
            del self._sockets[device_id]
            self._busy_until.pop(device_id, None)

    def deliver(self, raw: str, device_id: str) -> None:
        """An answer arrived. Unknown ids are dropped, not raised: a reply to a
        command that already timed out is late, not wrong."""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("device %s sent something that is not JSON", device_id)
            return
        if not isinstance(message, dict):
            return
        if message.get("kind") == "busy":
            seconds = _busy_seconds(message.get("for_ms"))
            self._busy_until[device_id] = asyncio.get_running_loop().time() + seconds
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
                error_kind=str(error["kind"]) if error.get("kind") else None,
                error_detail=str(error["detail"]) if error.get("detail") else None,
            )
        )

    # -- the runner's side --------------------------------------------------

    def online(self) -> list[str]:
        return sorted(self._sockets)

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer:
        if device_id not in self._sockets:
            raise DeviceUnreachable(f"{device_id} has no channel open")
        # Not `deadline_s or self._deadline`: that could not express a short
        # deadline near zero, and let a negative one reach the wire as a
        # negative `deadline_ms`.
        deadline = self._deadline if deadline_s is None else deadline_s
        if deadline <= 0:
            return Answer(ok=False, error_kind="timeout", error_detail="a non-positive deadline")
        await self._wait_out_the_operator(device_id, deadline)
        # Read AFTER the wait: a laptop lid in the middle of it has the
        # extension re-dial, and `attach` replaces the entry.
        socket = self._sockets.get(device_id)
        if socket is None:
            raise DeviceUnreachable(f"{device_id} has no channel open")

        command_id = f"cmd_{uuid.uuid4().hex}"
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

    async def _wait_out_the_operator(self, device_id: str, deadline: float) -> None:
        until = self._busy_until.get(device_id)
        if until is None:
            return
        loop = asyncio.get_running_loop()
        remaining = until - loop.time()
        if remaining <= 0:
            self._busy_until.pop(device_id, None)
            return
        await asyncio.sleep(min(remaining, deadline * K_MAX_BUSY_WAIT))


def _busy_seconds(for_ms: object) -> float:
    if isinstance(for_ms, int | float) and not isinstance(for_ms, bool) and for_ms > 0:
        return min(float(for_ms) / 1000.0, 60.0)
    return _DEFAULT_BUSY_S


class FakeChannel:
    """Scripted answers by command kind, and a record of every envelope sent.

    The seam every runner test goes through. An unscripted kind answers
    `not_actionable`, which is what a real extension says to a command it does
    not have -- so a test that forgot to script a kind fails the way a real run
    would rather than hanging.
    """

    def __init__(self, script: dict[str, list[Answer]] | None = None) -> None:
        self.script = {kind: list(answers) for kind, answers in (script or {}).items()}
        self.sent: list[dict[str, Any]] = []

    def online(self) -> list[str]:
        return ["dev_test"]

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer:
        self.sent.append(
            {"device_id": device_id, "kind": kind, "payload": dict(payload), "run_id": run_id}
        )
        queued = self.script.get(kind)
        if queued:
            return queued.pop(0)
        return Answer(
            ok=False, error_kind="not_actionable", error_detail=f"this extension has no {kind}"
        )
