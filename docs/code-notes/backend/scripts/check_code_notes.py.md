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
> named symbol, and every anchor whose symbol can no longer be found or
> resolved. Exits non-zero if anything was found. It does not check whether a
> source file is missing a note file -- `docs/code-notes/README.md` asks for
> one only where the source once carried a comment, and nothing in the
> current file says whether it ever did.
>
> `--fix`: rewrite the stale line numbers to where the symbol sits now, found
> by name with `ast` -- including a dotted qualname like `Class.method`. Note
> text is never touched, and an anchor that cannot be resolved cleanly is
> left alone and reported instead of guessed at. Run once, after every merge
> -- not by the branches that cause the drift.

## `HEADING_RE`, [line 11](../../../../backend/scripts/check_code_notes.py#L11): Constant

> One pattern for every anchor heading this repository generates, e.g.
> `` ## `Container.claim_the_runs`, [line 255](...#L255): Comment ``. The
> `name`/`module` split is `docs/code-notes/README.md`'s own two spellings --
> a real symbol in backticks, or the bare word `module` for a note about the
> file itself. `prefix`, `mid` and `suffix` are captured whole so `--fix` can
> rebuild the line byte-for-byte around the two numbers it changes, rather
> than reconstructing Markdown it might get subtly wrong.
>
> A few headings in this repository have no `line N` at all -- e.g.
> `` ## `FromTheMail.execute`: Comment ``. `HEADING_RE` simply does not match
> them; `parse_anchors` below is what turns that non-match into a reported
> finding instead of a silent skip.

## `resolve_symbol`, [line 112](../../../../backend/scripts/check_code_notes.py#L112): Function

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

## `evaluate_anchor`, [line 134](../../../../backend/scripts/check_code_notes.py#L134): Function

> Where one anchor's line should be, without yet trusting position to settle
> a tie -- that needs every anchor's `"certain"` result gathered first (see
> `order_violations` below), so this only ever returns one of three
> answers: `"certain"` (a symbol-only anchor's own `lineno`, a single hit, or
> the stated line itself when it's one of several hits -- a quote matching
> more than one line is not an error by itself, only an unconfirmed one is),
> `"dead"` (the symbol or the quoted code cannot be found at all), or
> `"ambiguous"` (more than one hit, and the stated line isn't among them).
>
> The search for a `Code:`-quoted line is exact and whitespace-trimmed, and
> scoped to the named symbol's own line range (the whole file, for a
> `module` anchor) -- never the whole tree, which is what keeps `import json`
> in one function from resolving a note written about `import json` in
> another.

## `order_violations`, [line 175](../../../../backend/scripts/check_code_notes.py#L175): Function

> The rule `resolve_note_file` relies on to break an `"ambiguous"` tie --
> the notes for one symbol are written in source order, so the next one's
> line should never resolve *before* the previous one's -- is an assumption
> about how these files were written, not a law, so it is checked here
> against real evidence before anything downstream trusts it: only the
> `"certain"` resolutions, per symbol, per file, in heading order. Those
> never depended on position to resolve, so they can't beg the question they
> are being used to answer.
>
> A symbol found out of order here is not guessed through anywhere in this
> file again -- every `"ambiguous"` note under it is reported instead
> (`resolve_note_file` below). Measured on this repository: most of the
> symbols this flags never actually had an ambiguous note under them, so
> flagging them costs nothing; the ones that did (e.g. `FromTheMail.execute`,
> whose six identical `logger.info(` lines cannot be told apart once its
> notes are known to be out of order) are exactly the reports this rule
> exists to produce instead of a wrong guess.

## `resolve_note_file`, [line 201](../../../../backend/scripts/check_code_notes.py#L201): Function

> One note file, anchor by anchor, in heading order. `"certain"` results
> feed `last_resolved` outright; an `"ambiguous"` one is resolved the same
> way *if* its symbol is not in `broken` -- the first hit strictly after
> `last_resolved`'s line for that symbol (or the symbol's own start line, for
> its first note) -- and left as a dead report otherwise: no hit past that
> floor, or the symbol's own notes already proven out of order.
>
> `last_resolved` is updated by every resolution, `"certain"` or
> structurally resolved alike, because the rule it enforces --
> next-note-after-previous-note -- does not care which way a line was
> confirmed, only that it was.

## `run`, [line 265](../../../../backend/scripts/check_code_notes.py#L265): Function

> One pass over every note file. A note file is rewritten once, in place,
> only if at least one of its anchors resolved to a line different from the
> one stated -- an anchor `resolve_note_file` could not resolve is reported
> and left exactly as written, on this run and on `--fix` alike.
