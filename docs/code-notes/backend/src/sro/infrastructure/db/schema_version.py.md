# Notes for `backend/src/sro/infrastructure/db/schema_version.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/schema_version.py`](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L1): Docstring

> Whether the database this process is talking to is the one its code expects.
>
> A schema behind the code does not announce itself. It surfaces as whichever
> call happens to touch the missing column first, as a 500 with a traceback the
> caller never sees -- and the operator reads that as the feature being broken.
> This happened here: a database four migrations behind reported itself as an
> extension that could not reach its own backend, because the call that fetches
> a device secret was the one that died, and every diagnosis after that was
> aimed at the wrong half of the system.
>
> So it is asked once at startup, and again on every readiness probe. Neither
> refuses to serve: an operator who has just deployed and not yet migrated wants
> to be told, not locked out, and a probe that reports `degraded` is what a
> deployment already knows how to act on.

## module, [line 13](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L13): Note on the line above

Code: `MIGRATIONS = Path(__file__).resolve().parents[4] / "migrations" / "versions"`

> `src/sro/infrastructure/db/` up to the backend root. Resolved from this
> file rather than from the working directory, because `alembic.ini` names its
> script location relative to wherever alembic was invoked and nothing guarantees
> that is where this process was started.

## `SchemaVersion`, [line 17](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L17): Docstring

> What the database is at, what the code wants, and whether they agree.
>
> `expected` empty means the migration directory could not be read -- a
> layout this file does not know about, which is a reason to say nothing
> rather than to claim a mismatch nobody can act on.

## `_heads`, [line 41](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L41): Docstring

> The revisions nothing else builds on.
>
> Read out of the files rather than through `alembic.script.ScriptDirectory`,
> which wants a `Config` pointed at an ini file this process has no reason to
> know the location of. A head is a revision that appears as nobody's
> `down_revision`, which is the same definition alembic uses.

## `schema_version`, [line 60](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L60): Docstring

> Ask the database which migration it is at, and compare.
>
> An empty `alembic_version` table, or none at all, is a database nobody has
> ever migrated -- reported as a mismatch rather than as unreachable, because
> that is exactly the state this exists to name.

## `announce`, [line 68](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L68): Docstring

> Say it once, at startup, at a level that matches what it means.

## `_heads`, [line 51](../../../../../../../backend/src/sro/infrastructure/db/schema_version.py#L51): Comment

Code: `if stripped.startswith(f"{line} ") or stripped.startswith(f"{line}:"):`

> `revision: str = "0040"` and `revision = "0040"` both appear
> in alembic's templates over the versions it has shipped.
