"""The write-safety ledger, read off the knowledge base's own index.

`index/write-endpoints.json` is a research project's record of which
`(method, path)` pairs on the real Blue Yonder deployment have been
individually watched succeed -- edit, verify on a separate read, revert --
and are therefore safe to send directly rather than only through a click.
Reading it is this module's whole job; the rule that decides what a call may
do with it is `sro.domain.execution.verified_writes`, which is pure and knows
nothing about files.

Same root as `infrastructure.knowledge.ingest`'s, and the same reason: no
``blue-yonder-sce`` subdirectory, ``index/`` sits directly under
``knowledge-base/``. Missing entirely -- a deployment shipped without the
research project beside it -- is not an error here: it is an empty ledger,
which is the same as one that has verified nothing yet.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from sro.domain.execution.verified_writes import VerifiedWrite

logger = logging.getLogger(__name__)

PROVEN = frozenset({"round-trip", "observed"})
"""The `proof` values that mean somebody watched this endpoint succeed.

An allowlist and not a denylist of the refusals, for this module's own rule:
a malformed or unrecognised entry has to narrow what is verified, never widen
it. A `proof` this file has never heard of -- a new vocabulary word, a typo,
the field missing entirely -- is not a claim that anything was watched.

The lower two ranks of `knowledge.entry.EvidenceLevel` by name and not by
import: this ledger is a research project's hand-kept JSON with its own
spelling (`round-trip`, not `round_trip`), and pretending the two vocabularies
are one would be a mapping nobody maintains."""

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base"


@lru_cache(maxsize=8)
def load_verified_writes(root: Path = _DEFAULT_ROOT) -> tuple[VerifiedWrite, ...]:
    """Every entry the ledger itself marks ``verified: true``, once each.

    Cached: the file is a research artifact edited by hand between sessions,
    not a request-scoped read, and a run planning fifty steps is fifty cache
    hits rather than fifty file reads of a file that never changes mid-run.
    """
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
            # `is not True` on purpose, not a truthiness test: this ledger is
            # hand-edited between sessions, and the string "false" is
            # truthy. A typo in the file must narrow what gets verified, not
            # accidentally verify the one entry someone meant to disable.
            continue
        if entry.get("proof") not in PROVEN:
            # Marked verified, but by its own account never watched succeed.
            continue
        method, pattern = entry.get("method"), entry.get("pathPattern")
        if not isinstance(method, str) or not isinstance(pattern, str):
            continue
        if not pattern or not pattern.startswith("/"):
            # An empty pattern splits to zero segments, matching every path
            # of zero segments -- the site root -- and a pattern missing its
            # leading slash is not a path at all, just a template fragment
            # that happens to split the same way a real one would.
            continue
        key = (method.upper(), pattern)
        if key in seen:
            continue
        seen.add(key)
        verified.append(VerifiedWrite(method=method, path_pattern=pattern))
    return tuple(verified)
