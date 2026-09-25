# Notes for `backend/src/sro/domain/execution/verified_writes.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/verified_writes.py`](../../../../../../../backend/src/sro/domain/execution/verified_writes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/verified_writes.py#L1): Docstring

> Which recorded calls may be sent straight to the API, not through a click.
>
> `planning.unreplayable` says a call is safe to send byte-for-byte. This says
> something narrower and harder: a call whose bytes are NOT safe to replay
> (Blue Yonder's writes carry a `CSRF-ENCRYPT-TOKEN` the recorder correctly
> redacts) may still be sent directly, but only for a `(method, path)` this
> deployment has individually watched succeed against the real system --
> edit, verify on a separate read, revert. `knowledge-base/index/write-
> endpoints.json` is that ledger, in the research project that keeps it; this
> module is the one rule that reads it, and the rule is deliberately narrow.
>
> Membership, not resemblance. A path that merely looks like a verified one is
> exactly the mistake the ledger's own notes warn against: "never by assuming
> a documented-looking path behaves like a tested one." So the match is exact
> on the templated shape -- a `{id}`-style segment matches any single path
> segment, every other segment matches literally -- and nothing here tries to
> be clever about near misses.

## `_is_traversal_segment`, [line 24](../../../../../../../backend/src/sro/domain/execution/verified_writes.py#L24): Docstring

> Whether this segment, once decoded, is not really one segment at all.
>
> `_segments` splits the RAW path on "/" before this ever runs, which is
> exactly why a segment can still lie: `..`, `%2e%2e`, and
> `..%2f..%2fadmin%2fwipe` are each one segment by that split, but decode
> to `..` or to something carrying its own `/`. Blue Yonder runs on Tomcat,
> which decodes `%2f` before it routes -- so the segment this module
> matched as `{id}` and the segment the server actually walked to are not
> the same string, and the gap between them is exactly a path traversal.
> Decode once and reject anything that is not a single, literal segment.

## `learned_pattern`, [line 42](../../../../../../../backend/src/sro/domain/execution/verified_writes.py#L42): Docstring

> The pattern to remember a write under, from a path this run just made.
>
> A deployment that has watched its own write succeed knows something the
> hand-kept ledger cannot: `Delete a Customer Type` had run eight times here
> and the ninth run still clicked Save, because the only ledger is a JSON
> file a human edits between sessions. What it watched is strictly better
> evidence than what the file asserts -- the call went out, the server
> answered, and a read-back confirmed the record.
>
> **Which segment is the identifier is known, not guessed.** A run typed
> `GZ5` into Customer Type and the path ends `/customerTypes/GZ5`, so that
> segment is the id and the pattern is `/customerTypes/{id}` -- learnt from
> what this run supplied rather than from what a segment looks like. The
> shape heuristic (`path_shape`'s digits rule) is kept as the second source
> for ids no value names: a numeric row id nobody typed is still an id.
>
> Everything else stays literal. The ledger's own note is the rule here:
> "never by assuming a documented-looking path behaves like a tested one".
> A pattern wider than the evidence is a licence to send a call nobody
> watched.

## `verified_write_for`, [line 63](../../../../../../../backend/src/sro/domain/execution/verified_writes.py#L63): Docstring

> The ledger entry this call is proven under, or None.
>
> The query string is never part of the match: every entry in the ledger is
> a resource path, and a write does not become a different, unverified
> endpoint because the operator's recording happened to carry
> `?siteId=SG`.

## `learned_pattern`, [line 52](../../../../../../../backend/src/sro/domain/execution/verified_writes.py#L52): Comment

Code: `if was is None:`

> With the recorded call's URL (`recorded`), each segment is compared,
> percent-decoded, with the recording's segment at the same place. A segment
> the recording holds the same is fixed and never templated: with
> `Decision: approve`, `/orders/42/approve` stays `/orders/{id}/approve`,
> not `/orders/{id}/{id}`. A segment the recording held differently is the
> identifier when it holds one of this run's values (decoded, so
> `Acme%20Corp` matches "Acme Corp") or looks like an id -- in any position,
> so an email in an earlier segment is templated and never stored. With no
> recording (or one of another length) only the rule below holds:

> The LAST segment only, for the value rule. A run value is any string
> somebody typed, and a short one collides with route words: with
> `Department: wm` a create became `/data/{id}/{id}/customerTypes`,
> which matches paths nobody has ever watched -- the exact licence
> this module's opening note refuses. A REST identifier is the last
> segment; the resource is not.
