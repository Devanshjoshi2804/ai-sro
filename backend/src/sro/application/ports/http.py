from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    text: str

    @property
    def succeeded(self) -> bool:
        return 200 <= self.status_code < 300


class HttpCaller(Protocol):
    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse: ...


class TargetUnreachable(Exception):
    code = "target_unreachable"


class MalformedRequest(TargetUnreachable): ...
