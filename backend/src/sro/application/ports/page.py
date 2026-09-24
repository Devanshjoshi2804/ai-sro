from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionRef:
    steel_session_id: str
    cdp_url: str
