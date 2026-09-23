from __future__ import annotations

_BACKGROUND_MARKERS = (
    "keepalive",
    "keep-alive",
    "heartbeat",
    "beacon",
    "telemetry",
    "analytics",
    "performanceentries",
    "/rum",
    "perftrace",
)


def is_background_traffic(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return any(marker in path for marker in _BACKGROUND_MARKERS)
