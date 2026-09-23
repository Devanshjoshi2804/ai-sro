from __future__ import annotations

import json
from collections.abc import Mapping


def once_each(payload: bytes) -> bytes:
    seen: set[str] = set()
    kept: list[bytes] = []
    dropped = False
    for line in payload.splitlines():
        call = _request_id(line)
        if call is not None:
            if call in seen:
                dropped = True
                continue
            seen.add(call)
        kept.append(line)
    return b"\n".join(kept) if dropped else payload


def _request_id(line: bytes) -> str | None:
    try:
        event = json.loads(line)
    except ValueError:
        return None
    if not isinstance(event, Mapping) or event.get("kind") != "request":
        return None
    request = event.get("request")
    if not isinstance(request, Mapping):
        return None
    call = request.get("request_id")
    return call if isinstance(call, str) and call else None
