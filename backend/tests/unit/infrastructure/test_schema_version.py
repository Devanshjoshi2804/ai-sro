"""The check that names a database older than the code talking to it.

Written because the failure it catches actually happened: a local database four
migrations behind reported itself as an extension that could not reach its own
backend, because the call fetching a device secret was the one that died first.
Nothing in the system said the schema was old, so the diagnosis went to the
wrong half of it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from sro.infrastructure.db.schema_version import (
    MIGRATIONS,
    SchemaVersion,
    _heads,
    schema_version,
)


class _Answers:
    """A session that answers `SELECT version_num` with whatever it was given."""

    def __init__(self, applied: str | None = None, raises: bool = False) -> None:
        self._applied = applied
        self._raises = raises

    async def scalar(self, _statement: object) -> str | None:
        if self._raises:
            raise OperationalError("SELECT version_num", {}, Exception("no such table"))
        return self._applied


def test_the_real_migrations_directory_has_exactly_one_head() -> None:
    """The check is worth nothing if it cannot read this repository's own
    migrations -- and a second head would mean two branches of history nobody
    merged, which is a real fault this notices for free."""
    assert MIGRATIONS.is_dir(), f"the migrations directory moved: {MIGRATIONS}"
    heads = _heads()
    assert len(heads) == 1, f"expected one head, found {sorted(heads)}"


async def test_a_database_at_head_is_current() -> None:
    (head,) = _heads()
    version = await schema_version(_Answers(applied=head))
    assert version.current
    assert "which is head" in version.says()


async def test_a_database_behind_its_code_is_named_with_both_revisions() -> None:
    # The whole point: the message has to carry what the database is at, what
    # the code wants, and the command that closes the gap. An operator reading
    # a log line should not have to look any of the three up.
    version = await schema_version(_Answers(applied="0036"))
    (head,) = _heads()
    assert not version.current
    said = version.says()
    assert "0036" in said
    assert head in said
    assert "alembic upgrade head" in said


async def test_a_database_nobody_ever_migrated_is_a_mismatch_not_an_outage() -> None:
    # No `alembic_version` table at all raises, and it would be easy to file
    # that as "cannot ask" -- but it is precisely the state this exists to
    # name, and reporting it as unreachable would hide it behind the database
    # check that is already there.
    version = await schema_version(_Answers(raises=True))
    assert not version.reachable
    assert "could not be asked" in version.says()


def test_an_unreadable_migrations_directory_claims_nothing() -> None:
    # A deployment laid out differently from this checkout must not be told its
    # schema is wrong on the strength of a path that did not resolve. Silence
    # is the honest answer; a false alarm here is worse than no alarm, because
    # it is the alarm that would be ignored next time.
    assert _heads(Path("/nonexistent/migrations/versions")) == frozenset()
    version = SchemaVersion(applied="0036", expected=frozenset(), reachable=True)
    assert version.current
    assert "not readable" in version.says()


@pytest.mark.parametrize("applied", ["0040", ""])
def test_a_head_that_cannot_be_read_never_fails_a_deployment(applied: str) -> None:
    assert SchemaVersion(applied=applied, expected=frozenset(), reachable=True).current
