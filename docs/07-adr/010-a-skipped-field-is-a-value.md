# ADR 010 — A skipped field is a value, not a missing step

**Status:** accepted · v0

## Context

Two work areas were created by hand in a real Blue Yonder WMS on 2026-08-27,
watched passively, no demonstration pressed. One operator typed a Delta
Priority; the other left it blank. Both writes carried the same keys — the
skipped field arrived as `deltaPriority: null` rather than being left out of
the body — because the form always posts its full shape.

Induction refused the pair: `align` (`application/induction/diff.py:248`)
compares *gestures*, and one recording has a `type` action on Delta Priority
that the other does not. `_evidential` (`:230`) treats any action that carried
a value as evidence the runs disagree about what the task is, so the pair was
refused with "the runs are not two runs of one task" — even though, at the
level of what changed in the warehouse, these are two doings of one task
differing only in values, one of which happens to be nothing.

This is not an edge case. A form worth automating has thirty fields, and no
two people fill the same subset of them; both still create a correct record.
Refusing every pair that disagrees on which fields were touched refuses
passive observation on any form of realistic size — which is the whole premise
this system is built on. Deliberate demonstration could route around it by
having one operator perform both runs identically; a tab watched over someone's
shoulder cannot.

## Decision

`align` keeps its rule that an unmatched step carrying a value is a
disagreement, with one exception: an unmatched step may be dropped when the
two runs' writes prove the field it filled is optional. Proof means the value
it carried fills a key the *other* run's write also sends, holding nothing at
that key (`jsonutil.is_empty`). A key that appears in only one run's write is
never excused this way — that is a real disagreement about what the task is,
and the pair still refuses. This is what `optional_fills` / `_optional_pointer`
compute (`diff.py:317`, `:349`), and `align` drops exactly the frames they
excuse (`:275`), nothing wider.

The field's absent form — what to send when nobody supplies it — is read from
the run that skipped it, never chosen by the system: `null` for a number the
form nulls, `""` for a text control it empties. `Parameter.absent_as` stores it
verbatim as JSON, and the network body renders it unquoted when that JSON is
not itself a string, so a required-looking `null` doesn't arrive as the string
`"null"` and get rejected by a form expecting a number.

A keystroke binds to the field it filled by comparing the typed text against
the values in that run's own write — not the other run's, and not a value
chosen by the system — after normalisation: stripped, case-folded, a numeric
value read as its digits. A form is allowed to tidy what it was given — a work
area name uppercases as you type, a code field trims — and the comparison has
to see through that or the binding proves nothing. Nothing looser: a value
that merely contains another is not a match.

A value binding to two keys binds to neither, with one exception the design
document did not anticipate and real evidence forced. The two work areas'
own form sends `voiceCode: "1"` beside `deltaPriority: 1`, so the typed `"1"`
matched both keys and the tie left nothing bound — which put the pair right
back in the refusal this decision exists to remove. Where exactly one of the
tied keys is the control's own field name — its `itemId`, its `name`, or the
DOM's own `name` attribute — the control breaks the tie. In the implementer's
words: *a form field is named for the key it posts under, and that is a fact
the page states rather than an inference.* Where none of the tied keys is the
control's own name, or more than one is, the binding still fails and the step
stays unconditional.

The dropped gesture is not discarded. It is emitted back as a step conditional
on the field it filled (`SkillStep.when`), so a WMS with no writable API can
still fill it by clicking. `_perform_in_ui` skips a conditional step when
nothing was supplied for its field, rather than clicking it empty and risking
a validation error the operator never triggered; the vision path inherits the
same skip because it runs through the same guard.

**Rejected: inferring optionality from the page** (a `*` beside the label, an
`x-form-required-field` attribute the recorder already captures). Corroborating
knowledge, not the source of truth — a field the page marks required but that
every demonstration happens to fill is still, correctly, required; a field two
demonstrations prove optional stays optional even if the page never says so.
What was actually done outranks what the page claims.

**Rejected: treating a key absent from one run's write as optional too.**
That would be guessing at a structural disagreement, which is exactly what
ADR 004 exists to prevent. Only a key both writes send, differing in whether
it holds a value, is evidence of optionality.

## Consequences

A form of any size can now induce from passive observation, because two
people filling different subsets of the same form are recognised as one task
rather than two. Two demonstrations of one task no longer have to match
keystroke for keystroke — only the writes have to agree on what the record
becomes.

A key one run's write never sends at all still refuses the pair; that
guarantee is unchanged, and it is what keeps this from being a guess.

The costs, named rather than hidden:

- **A required numeric field is still templated as a quoted string.** The
  unquoted rendering only applies to a parameter with `absent_as` set — an
  optional field, proven by a skipped demonstration. A required field with no
  such evidence still substitutes as `"${name}"`, which ADR 004 already
  recorded as a known gap; this decision narrows it rather than closing it.
- **Loop bounds count raw frame indices while step indices count aligned,
  post-`explode` steps.** Pre-existing, and reproducible independently of a
  conditional step at all — two non-evidential unmatched frames with no
  optional field between them already produce a `first_step`/`last_step` a
  version's own invariant rejects (`skill.py:302`). A conditional step makes
  this more likely to occur, since more misalignment can now survive as far as
  emission, but it did not create the bug.
- This ADR covers Part 1 and Part 2 of
  `docs/superpowers/specs/2026-08-27-fields-nobody-filled-design.md` only —
  a value nobody has ever typed, the pre-flight, the offer, and when asking
  stops (Parts 3–6) are their own decision, not made here.
