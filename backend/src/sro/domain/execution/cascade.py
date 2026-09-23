from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.evidence import READ_METHODS
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import path_shape

K_SHORTEST = 3


@dataclass(frozen=True, slots=True)
class Flow:
    key: str

    into: str

    made_at: str

    used_at: str


def writes_of(doing: Gesture, ledger: Sequence[VerifiedWrite] = ()) -> list[Call]:
    return [
        call
        for call in doing.requests
        if call.method.upper() not in READ_METHODS
        and (not ledger or verified_write_for(call, tuple(ledger)) is not None)
    ]


def flows_in(doing: Gesture, typed: Mapping[str, float] | None = None) -> list[Flow]:
    found: list[Flow] = []
    minted: list[tuple[str, str, str]] = []
    for call in writes_of(doing):
        where = f"{call.method.upper()} {path_shape(call.url)}"
        sent = _values(call.request_body.text if call.request_body is not None else None)
        for key, value, made_at in minted:
            into = [name for name, said in sent.items() if said == value]
            if into:
                found.append(Flow(key=key, into=into[0], made_at=made_at, used_at=where))
        if call.response_body is None:
            continue
        for key, value in _values(call.response_body.text).items():
            if value in sent.values():
                continue
            if typed is not None and (typed.get(value, float("inf")) <= doing.at):
                continue
            minted.append((key, value, where))
    return found


def _values(text: str | None) -> dict[str, str]:
    if not text:
        return {}
    try:
        document = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(document, dict):
        return {}
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return {
        key: value.strip()
        for key, value in record.items()
        if isinstance(key, str) and isinstance(value, str) and len(value.strip()) >= K_SHORTEST
    }


__all__ = ["K_SHORTEST", "Flow", "flows_in", "writes_of"]
