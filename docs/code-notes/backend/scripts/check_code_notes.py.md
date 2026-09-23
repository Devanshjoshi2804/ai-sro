# Notes for `backend/scripts/check_code_notes.py`

Comments and docstrings moved out of [`backend/scripts/check_code_notes.py`](../../../../backend/scripts/check_code_notes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/check_code_notes.py#L1): Docstring

> Do the anchors in `docs/code-notes/` still point at the code they name?
>
> Every note there names a function, class or constant and the line it sits
> on today (`docs/code-notes/README.md`). Every edit to the source moves
> lines under notes that were not touched, and nothing else in this
> repository re-checks that.
>
> `check` (the default): report every anchor whose line no longer matches its
> named symbol, every anchor whose symbol can no longer be found (or is
> ambiguous), and every non-trivial backend source file with no note file at
> all. Exits non-zero if anything was found.
>
> `--fix`: rewrite the stale line numbers to where the symbol sits now, found
> by name with `ast` -- including a dotted qualname like `Class.method`. Note
> text is never touched, and an anchor that cannot be resolved cleanly
> (missing or ambiguous) is left alone and reported instead of guessed at.
> Run once, after every merge -- not by the branches that cause the drift.

## `EXEMPT_FROM_NOTES`, [line 10](../../../../backend/scripts/check_code_notes.py#L10): Constant

Code: `EXEMPT_FROM_NOTES = ("backend", "src", "sro", "interface", "http")`

> `docs/code-notes/README.md`'s one exemption: a source file under
> `interface/http/` may keep its own docstrings, because they become the
> OpenAPI document. A file entirely covered by that exemption legitimately
> has nothing left to move out, so `requires_note` does not flag it for
> having no note file. It can still get one -- most files there do, for
> their non-docstring comments -- this only excuses the directory from the
> "must have a note" rule, not from carrying one.

## `EXCLUDED_DIR_PARTS`, [line 12](../../../../backend/scripts/check_code_notes.py#L12): Constant

Code: `EXCLUDED_DIR_PARTS = {"tests", "migrations", "__pycache__", ".venv"}`

> Not backend source in the sense the README means: generated Alembic
> migrations, the test suite, and anything not checked in.

## `HEADING_RE`, [line 14](../../../../backend/scripts/check_code_notes.py#L14): Constant

> One pattern for every anchor heading this repository generates, e.g.
> `` ## `Container.claim_the_runs`, [line 255](...#L255): Comment ``. The
> `name`/`module` split is `docs/code-notes/README.md`'s own two spellings --
> a real symbol in backticks, or the bare word `module` for a note about the
> file itself. `prefix`, `mid` and `suffix` are captured whole so `--fix` can
> rebuild the line byte-for-byte around the two numbers it changes, rather
> than reconstructing Markdown it might get subtly wrong.
>
> Three headings in this repository today have no `line N` at all --
> `` ## `FromTheMail.execute`: Comment `` and two others. `HEADING_RE` simply
> does not match them; `parse_anchors` below is what turns that non-match
> into a reported finding instead of a silent skip.

## `requires_note`, [line 56](../../../../backend/scripts/check_code_notes.py#L56): Function

> Whether `docs/code-notes/README.md`'s rules say this source file should
> have a note file.
>
> An empty file never carried a comment worth moving -- an empty
> `__init__.py` has no note anywhere in this tree, a one-line one does. That
> is the whole test: not "is this file trivial" by any deeper measure, just
> "is there anything in it at all" once whitespace is stripped.

## `resolve_symbol`, [line 129](../../../../backend/scripts/check_code_notes.py#L129): Function

> A dotted name (`Container`, `Container.claim_the_runs`, a bare module-level
> constant like `LATCH_AT`) walked one segment at a time through direct
> child statements only -- a class or function body, never a deep search.
> That is enough for every qualname this repository's notes actually use,
> and it is the reason a rename anywhere else in the file cannot produce a
> false match: `_find_in_body` only ever looks at the one scope the dotted
> path says to look in.
>
> `None, "missing"` and `None, "ambiguous"` are the two cases a caller must
> never guess through -- a deleted symbol and a redefined one read the same
> to a name-only lookup, and both get reported rather than resolved to
> whichever match happened to come first.

## `resolve_target_line`, [line 142](../../../../backend/scripts/check_code_notes.py#L142): Function

> Where one anchor's line should be today.
>
> A `Docstring`/`Class`/`Function`/`Constant`-style anchor (no `Code:` line
> in the note) names the symbol itself; its target is that symbol's own
> `lineno` -- the `class`/`def` line, or the assignment's line for a bare
> constant. Every other kind quotes the exact source line it was written
> against, and the target is wherever that literal text sits today, searched
> only inside the named symbol's own line range (or the whole file, for a
> `module` anchor) -- never the whole tree, which is what keeps `import json`
> in one function from resolving a note written about `import json` in
> another.
>
> ponytail: the search is an exact, whitespace-trimmed line match, not a
> structural one. A method that calls `await self._session.execute(` more
> than once reads as ambiguous here and is reported rather than guessed --
> matching on the statement's AST shape (or which argument follows) would
> resolve more of these, and is not worth building before real duplicates,
> not just repeated boilerplate, show up as noise in `check`'s output.

## `run`, [line 190](../../../../backend/scripts/check_code_notes.py#L190): Function

> One pass over every note file, plus one pass over every source file.
>
> The first pass is where `--fix` writes: a note file is rewritten once, in
> place, only if at least one of its anchors resolved cleanly to a different
> line -- an anchor this pass could not resolve is reported and left as-is,
> on this run and on `--fix` alike. The second pass is the other direction:
> a source file `requires_note` and has no matching note file at all, which
> a per-anchor pass over existing notes could never find by construction.
