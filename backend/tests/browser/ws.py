"""Enough of RFC 6455 for the stub to hold one channel open.

The extension dials the same origin it uploads to, so the stub that answers
`/v1/observations` has to be the thing that answers the WebSocket upgrade too --
one port, one server. `websockets` would mean a second server on a second port
and an extension told a different URL than the one a real deployment gives it,
which is the part of this worth testing.

Server to client is never masked, client to server always is. Nothing here
fragments, and neither does Chrome for messages this size.
"""

from __future__ import annotations

import base64
import hashlib
import json
import queue
import struct
import threading
from io import BufferedIOBase
from typing import Any

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def accept_key(client_key: str) -> str:
    digest = hashlib.sha1(f"{client_key}{_GUID}".encode(), usedforsecurity=False).digest()
    return base64.b64encode(digest).decode()


def encode(payload: bytes) -> bytes:
    """One unmasked text frame."""
    head = bytearray([0x81])
    size = len(payload)
    if size < 126:
        head.append(size)
    elif size < 1 << 16:
        head.append(126)
        head += struct.pack(">H", size)
    else:
        head.append(127)
        head += struct.pack(">Q", size)
    return bytes(head) + payload


def decode(stream: BufferedIOBase) -> tuple[int, bytes]:
    """The next frame's opcode and payload, unmasked. Blocks."""
    header = stream.read(2)
    if len(header) < 2:
        return 8, b""
    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    size = header[1] & 0x7F
    if size == 126:
        size = struct.unpack(">H", stream.read(2))[0]
    elif size == 127:
        size = struct.unpack(">Q", stream.read(8))[0]
    mask = stream.read(4) if masked else b""
    payload = bytearray(stream.read(size))
    if masked:
        for index in range(len(payload)):
            payload[index] ^= mask[index % 4]
    return opcode, bytes(payload)


class Channel:
    """One open socket, as the test drives it: send a command, read what the
    extension answered. Unsolicited messages -- `hello`, the keepalive -- go on
    the same queue and are stepped past by `answer`."""

    def __init__(self, stream: BufferedIOBase) -> None:
        self._out = stream
        self._lock = threading.Lock()
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()

    def send(self, message: dict[str, Any]) -> None:
        with self._lock:
            self._out.write(encode(json.dumps(message).encode()))
            self._out.flush()

    def command(self, command_id: str, kind: str, payload: dict[str, Any], **envelope: Any) -> None:
        self.send(
            {
                "command_id": command_id,
                "kind": kind,
                "run_id": envelope.get("run_id"),
                "deadline_ms": envelope.get("deadline_ms", 15_000),
                "payload": payload,
            }
        )

    def answer(self, command_id: str, timeout: float = 20.0) -> dict[str, Any]:
        """The answer to one command, ignoring everything else on the wire."""
        deadline = timeout
        while deadline > 0:
            step = min(deadline, 5.0)
            message = self.messages.get(timeout=step)
            deadline -= step
            if message.get("command_id") == command_id:
                return message
        raise AssertionError(f"no answer to {command_id} within {timeout}s")

    def saw(self, kind: str, timeout: float = 10.0) -> dict[str, Any]:
        """The next unsolicited message of this kind."""
        deadline = timeout
        while deadline > 0:
            step = min(deadline, 5.0)
            message = self.messages.get(timeout=step)
            deadline -= step
            if message.get("kind") == kind:
                return message
        raise AssertionError(f"the extension never sent {kind} within {timeout}s")
