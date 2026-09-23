from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).resolve().parents[4] / "migrations" / "versions"


@dataclass(frozen=True, slots=True)
class SchemaVersion:
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
    if not directory.is_dir():
        return frozenset()
    revisions: set[str] = set()
    parents: set[str] = set()
    for script in directory.glob("*.py"):
        text_ = script.read_text(encoding="utf-8", errors="replace")
        for line, into in (("revision", revisions), ("down_revision", parents)):
            for raw in text_.splitlines():
                stripped = raw.strip()
                if stripped.startswith(f"{line} ") or stripped.startswith(f"{line}:"):
                    _, _, value = stripped.partition("=")
                    named = value.strip().strip("\"'")
                    if named and named != "None":
                        into.add(named)
                    break
    return frozenset(revisions - parents)


async def schema_version(session: AsyncSession) -> SchemaVersion:
    try:
        applied = await session.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError:
        return SchemaVersion(applied="", expected=_heads(), reachable=False)
    return SchemaVersion(applied=applied or "", expected=_heads(), reachable=True)


def announce(version: SchemaVersion) -> None:
    if version.current:
        logger.info("database schema %s", version.says())
    else:
        logger.error("database schema %s", version.says())
