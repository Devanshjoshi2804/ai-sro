"""Which recorded calls may be sent straight to the API, not through a click.

`planning.unreplayable` says a call is safe to send byte-for-byte. This says
something narrower and harder: a call whose bytes are NOT safe to replay
(Blue Yonder's writes carry a `CSRF-ENCRYPT-TOKEN` the recorder correctly
redacts) may still be sent directly, but only for a `(method, path)` this
deployment has individually watched succeed against the real system --
edit, verify on a separate read, revert. `knowledge-base/index/write-
endpoints.json` is that ledger, in the research project that keeps it; this
module is the one rule that reads it, and the rule is deliberately narrow.

Membership, not resemblance. A path that merely looks like a verified one is
exactly the mistake the ledger's own notes warn against: "never by assuming
a documented-looking path behaves like a tested one." So the match is exact
on the templated shape -- a `{id}`-style segment matches any single path
segment, every other segment matches literally -- and nothing here tries to
be clever about near misses.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Call


@dataclass(frozen=True, slots=True)
class VerifiedWrite:
    method: str
    path_pattern: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())


def _segments(path: str) -> tuple[str, ...]:
    return tuple(segment for segment in path.split("/") if segment)


def _matches_path(path: str, pattern: str) -> bool:
    path_segments, pattern_segments = _segments(path), _segments(pattern)
    if len(path_segments) != len(pattern_segments):
        return False
    return all(
        (pattern_segment.startswith("{") and pattern_segment.endswith("}"))
        or pattern_segment == path_segment
        for path_segment, pattern_segment in zip(path_segments, pattern_segments, strict=True)
    )


def verified_write_for(call: Call, verified: tuple[VerifiedWrite, ...]) -> VerifiedWrite | None:
    """The ledger entry this call is proven under, or None.

    The query string is never part of the match: every entry in the ledger is
    a resource path, and a write does not become a different, unverified
    endpoint because the operator's recording happened to carry
    `?siteId=SG`.
    """
    method = call.method.upper()
    path = urlsplit(call.url).path
    for entry in verified:
        if entry.method == method and _matches_path(path, entry.path_pattern):
            return entry
    return None
