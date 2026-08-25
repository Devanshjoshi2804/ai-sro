# ADR 004 — Parameters come from a two-run diff, not from a model

**Status:** accepted · v1

## Context

A demonstration contains literals: order `12345`, dock door `7`. Turning
`type "12345"` into `type ${order_number}` is where naive capture systems break.

The obvious approach is to ask a language model which parts of a payload are
parameters. It will be right most of the time. The times it is wrong are
invisible in review — the recipe looks plausible — and surface later as the wrong
order being actioned.

## Decision

Record the same task **twice**, with different values, and diff the runs.

| Observation | Conclusion |
|---|---|
| Changed between runs | `input` parameter |
| Identical in both runs | Structure. Leave it alone. |
| Changed, but the value appeared in an earlier response of the same run | `derived` — never prompt a human |

"Record it twice" is a mandatory part of the capture protocol, not an
optimisation.

No model is involved anywhere in induction.

### Derived detection requires both runs

A value is classified `derived` only if it appears at the **same JSON pointer** of
the **same earlier response** in **both** runs. A match in one run alone is a
coincidence, and a coincidence promoted to `derived` leaves a parameter nothing
can ever populate.

This matters because session tokens, generated LPNs and server-assigned ids all
change between runs. A naive "it changed, so ask the user" rule would prompt an
operator for a value only the server can know.

### A value reformatted on the way is still derived, if both runs say so

**Amended, v1.** Equality was the only recognised link between a response and a
later call, so a value the task *reformats* — `42` answered by the WMS, sent to
the ERP as `LPN-00042` — was not derived at all. It became an `input`: a
question put to an operator who does not know where the number comes from
either. That is the ordinary shape of work that crosses two systems, and it is
now the ordinary shape of a skill (`docs/15`, `TeachWorkflow`).

So a link may also be a small reformatting — trimmed, recased, zero-padded, a
constant prefix or suffix — under exactly the standard the rest of this ADR
holds: the rewriting is read off one run and must then explain the **other**
run's pair, from the same pointer of the same earlier response. Rules always fit
one pair. A rule that fits both, where the two runs carried different values, is
what the task does.

What keeps this from being the inference this ADR exists to prevent:

- **Verbatim wins, everywhere, first.** A value handed over unchanged is never
  explained by a longer story about padding that happens to fit — including
  when an *earlier* step could be reformatted into it and a later one carries it
  outright.
- **A single character is not evidence.** `7` occurs inside a hundred values by
  accident, so the source has to contribute at least two characters.
- **A digit touching a digit is not a boundary.** `42` occurs inside `LPN-00042`;
  reading that as the prefix `LPN-000` reproduces the example and gets the next
  run wrong. Those occurrences are skipped, and the padding that actually
  happened is found instead.
- **Six operations, and no search.** Anything a person cannot check by eye
  against two examples is not expressible. The general form of this problem is
  program synthesis by example (Leno et al., arXiv:2001.01007, searching with
  A*); that is the right shape when a transformation is worth more than these
  six, and it is a decision to take then rather than now.
- **The reviewer is told.** The parameter's description says what was done —
  *"produced by step 0 response at /data/waveId, padded to 5 with '0', then
  prefixed with 'LPN-'"* — because a value silently reformatted on its way into
  another company's system is exactly what somebody approving a write should be
  able to disagree with.

### Structural disagreement is an error, not a guess

Different step counts, different action kinds, different endpoint shapes,
different query keys, differently-shaped JSON bodies — all raise `InductionFailed`
naming the step and the disagreement. The answer is to re-record, not to
reconcile. Fuzzy alignment here would be a guess at the point where guessing
costs the most.

### Substitution is by address, not by string replacement

Values are replaced at known **sites** — a URL path index, a query key, a JSON
pointer, the typed value. Replacing every occurrence of the changed string would
eventually swap a quantity of `3` where a page number shared the value, and
review would not catch it.

### Naming comes from the payload

A JSON key, a query key, the path segment before an id (`/shipments/12345` →
`shipment_id`), or the field's accessible name. The captured payload already uses
the vocabulary of the system being automated; invented names would not match it.

Distinct value pairs that collide on a name get a `_2` suffix rather than being
merged — merging would silently couple two fields.

### Placeholder syntax is `$name`

`string.Template`, not `{name}`. Recorded payloads are mostly JSON and JSON is
made of braces; a brace syntax needs every captured body escaped, and one missed
escape turns a literal into a phantom parameter.

## Consequences

- Induction is deterministic and reproducible. The same recordings always produce
  the same skill.
- Every parameter shows its evidence — the two observed values — so review is
  real rather than a rubber stamp.
- Cost per skill is zero LLM tokens.
- Operators must record twice. This is friction, and it is the point.
- A JSON numeric leaf becomes the string `"${name}"` after substitution. Harmless
  while nothing executes; typed substitution is a change to rendering, not to the
  address scheme. Marked `# ponytail:` in `sites.py`.

## Headers are diffed too, but not all of them

A header that carries meaning and varied between the two runs is a parameter,
exactly like a path segment or a body field. Replaying run one's warehouse id
when the operator asked for a different warehouse is the same failure as
replaying run one's wave id.

Only **replayable** headers are diffed. Everything else varies for reasons that
have nothing to do with the task -- a session cookie per session, a trace id per
call, a Referer per page -- and diffing those would produce parameters no
operator could answer. So each header ends up in one of four states, and a
reviewer can see which:

| State | Shown as | Why |
|---|---|---|
| Credential | `<blue_yonder/DC01/authorization>` | resolved from the vault at run time |
| Minted | `<minted per run>` | the captured value is stale by construction |
| Client-managed | `<set by the client>` | Host, Content-Length, Referer, the sec-* family |
| Semantic | `DC01` or `${warehouse_id}` | literal if it held, parameter if it varied |

**The limit of two runs.** A header called `X-Trace` carrying a fresh random
value on every call is indistinguishable, by diffing alone, from a value the
task genuinely varies. Both simply differ. Rather than inspect values and guess
-- which is the inference this ADR exists to avoid -- classification is extended
by *name*: `trace`, `nonce`, `request-id`, `correlation`, `idempotency`,
`timestamp`. Naming is a decision the system being automated already made, and
reading it is not the same as guessing at data.

That leaves a real residue: a per-call value under a name nobody would guess
becomes a parameter. The reviewer sees it, with both observed values, before
anything is promoted. Two demonstrations cannot do better than that, and a third
run would narrow it further -- which is a change to make when someone has a case
that needs it, not before.
