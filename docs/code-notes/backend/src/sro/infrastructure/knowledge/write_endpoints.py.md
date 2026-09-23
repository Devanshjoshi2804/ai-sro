# Notes for `backend/src/sro/infrastructure/knowledge/write_endpoints.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/knowledge/write_endpoints.py`](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L1): Docstring

> The write-safety ledger, read off the knowledge base's own index.
>
> `index/write-endpoints.json` is a research project's record of which
> `(method, path)` pairs on the real Blue Yonder deployment have been
> individually watched succeed -- edit, verify on a separate read, revert --
> and are therefore safe to send directly rather than only through a click.
> Reading it is this module's whole job; the rule that decides what a call may
> do with it is `sro.domain.execution.verified_writes`, which is pure and knows
> nothing about files.
>
> Same root as `infrastructure.knowledge.ingest`'s, and the same reason: no
> ``blue-yonder-sce`` subdirectory, ``index/`` sits directly under
> ``knowledge-base/``. Missing entirely -- a deployment shipped without the
> research project beside it -- is not an error here: it is an empty ledger,
> which is the same as one that has verified nothing yet.

## module, [line 12](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L12): Note on the line above

Code: `PROVEN = frozenset({"round-trip", "observed"})`

> The `proof` values that mean somebody watched this endpoint succeed.
>
> An allowlist and not a denylist of the refusals, for this module's own rule:
> a malformed or unrecognised entry has to narrow what is verified, never widen
> it. A `proof` this file has never heard of -- a new vocabulary word, a typo,
> the field missing entirely -- is not a claim that anything was watched.
>
> The lower two ranks of `knowledge.entry.EvidenceLevel` by name and not by
> import: this ledger is a research project's hand-kept JSON with its own
> spelling (`round-trip`, not `round_trip`), and pretending the two vocabularies
> are one would be a mapping nobody maintains.

## `load_verified_writes`, [line 18](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L18): Docstring

> Every entry the ledger itself marks ``verified: true``, once each.
>
> Cached: the file is a research artifact edited by hand between sessions,
> not a request-scoped read, and a run planning fifty steps is fifty cache
> hits rather than fifty file reads of a file that never changes mid-run.

## `load_verified_writes`, [line 34](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L34): Comment

Code: `continue`

> `is not True` on purpose, not a truthiness test: this ledger is
> hand-edited between sessions, and the string "false" is
> truthy. A typo in the file must narrow what gets verified, not
> accidentally verify the one entry someone meant to disable.

## `load_verified_writes`, [line 36](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L36): Comment

Code: `continue`

> Marked verified, but by its own account never watched succeed.

## `load_verified_writes`, [line 39](../../../../../../../backend/src/sro/infrastructure/knowledge/write_endpoints.py#L39): Comment

Code: `continue`

> An empty pattern splits to zero segments, matching every path
> of zero segments -- the site root -- and a pattern missing its
> leading slash is not a path at all, just a template fragment
> that happens to split the same way a real one would.
