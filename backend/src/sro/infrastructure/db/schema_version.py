"""Whether the database this process is talking to is the one its code expects.

A schema behind the code does not announce itself. It surfaces as whichever
call happens to touch the missing column first, as a 500 with a traceback the
caller never sees -- and the operator reads that as the feature being broken.
This happened here: a database four migrations behind reported itself as an
extension that could not reach its own backend, because the call that fetches
a device secret was the one that died, and every diagnosis after that was
aimed at the wrong half of the system.

So it is asked once at startup, and again on every readiness probe. Neither
refuses to serve: an operator who has just deployed and not yet migrated wants
to be told, not locked out, and a probe that reports `degraded` is what a
deployment already knows how to act on.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).resolve().parents[4] / "migrations" / "versions"
"""`src/sro/infrastructure/db/` up to the backend root. Resolved from this
file rather than from the working directory, because `alembic.ini` names its
script location relative to wherever alembic was invoked and nothing guarantees
that is where this process was started."""


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    """What the database is at, what the code wants, and whether they agree.

    `expected` empty means the migration directory could not be read -- a
    layout this file does not know about, which is a reason to say nothing
    rather than to claim a mismatch nobody can act on.
    """

    applied: str
    expected: frozenset[str]
    reachable: bool

    @property
    def current(self) -> bool:
        if not self.expected or not self.reachable:
            return True
        return self.applied in self.expected

    def says(self) -> str:
        if not self.reachable:
            return "the database could not be asked which migration it is at"
        if not self.expected:
            return f"at {self.applied or 'no revision'}; the migrations directory was not readable"
        if self.current:
            return f"at {self.applied}, which is head"
        return (
            f"at {self.applied or 'no revision'}, but this code expects "
            f"{'/'.join(sorted(self.expected))} — run `alembic upgrade head`"
        )


def _heads(directory: Path = MIGRATIONS) -> frozenset[str]:
    """The revisions nothing else builds on.

    Read out of the files rather than through `alembic.script.ScriptDirectory`,
    which wants a `Config` pointed at an ini file this process has no reason to
    know the location of. A head is a revision that appears as nobody's
    `down_revision`, which is the same definition alembic uses.
    """
    if not directory.is_dir():
        return frozenset()
    revisions: set[str] = set()
    parents: set[str] = set()
    for script in directory.glob("*.py"):
        text_ = script.read_text(encoding="utf-8", errors="replace")
        for line, into in (("revision", revisions), ("down_revision", parents)):
            for raw in text_.splitlines():
                stripped = raw.strip()
                # `revision: str = "0040"` and `revision = "0040"` both appear
                # in alembic's templates over the versions it has shipped.
                if stripped.startswith(f"{line} ") or stripped.startswith(f"{line}:"):
                    _, _, value = stripped.partition("=")
                    named = value.strip().strip("\"'")
                    if named and named != "None":
                        into.add(named)
                    break
    return frozenset(revisions - parents)


async def schema_version(session: AsyncSession) -> SchemaVersion:
    """Ask the database which migration it is at, and compare.

    An empty `alembic_version` table, or none at all, is a database nobody has
    ever migrated -- reported as a mismatch rather than as unreachable, because
    that is exactly the state this exists to name.
    """
    try:
        applied = await session.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError:
        return SchemaVersion(applied="", expected=_heads(), reachable=False)
    return SchemaVersion(applied=applied or "", expected=_heads(), reachable=True)


def announce(version: SchemaVersion) -> None:
    """Say it once, at startup, at a level that matches what it means."""
    if version.current:
        logger.info("database schema %s", version.says())
    else:
        logger.error("database schema %s", version.says())
