from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from sro.domain.execution.verified_writes import VerifiedWrite

logger = logging.getLogger(__name__)

PROVEN = frozenset({"round-trip", "observed"})

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base"


@lru_cache(maxsize=8)
def load_verified_writes(root: Path = _DEFAULT_ROOT) -> tuple[VerifiedWrite, ...]:
    path = root / "index" / "write-endpoints.json"
    if not path.is_file():
        logger.warning("no write-endpoints ledger at %s; verifying nothing", path)
        return ()
    try:
        entries = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("write-endpoints ledger at %s could not be read", path)
        return ()
    if not isinstance(entries, list):
        return ()
    seen: set[tuple[str, str]] = set()
    verified: list[VerifiedWrite] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("verified") is not True:
            continue
        if entry.get("proof") not in PROVEN:
            continue
        method, pattern = entry.get("method"), entry.get("pathPattern")
        if not isinstance(method, str) or not isinstance(pattern, str):
            continue
        if not pattern or not pattern.startswith("/"):
            continue
        key = (method.upper(), pattern)
        if key in seen:
            continue
        seen.add(key)
        verified.append(VerifiedWrite(method=method, path_pattern=pattern))
    return tuple(verified)
