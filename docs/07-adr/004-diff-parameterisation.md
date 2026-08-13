# ADR 004 — Parameters come from a two-run diff, not from a model

**Status:** accepted · v0

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
