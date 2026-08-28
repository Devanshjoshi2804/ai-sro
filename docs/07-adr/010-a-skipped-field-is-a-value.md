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
verbatim as JSON.

Two facts decide how that field renders, and reading both off one of them was
wrong in both directions. Whether the body template keeps the quotes
`json.dumps` puts round a placeholder is the *absent form's* business: a quoted
slot can only ever render a string, so a field the form nulls loses its quotes
— a required-looking `null` must not arrive as the string `"null"` and be
rejected by a form expecting a number — and a field the form empties to `""`
keeps them. What a *supplied* value has to be is the business of the type the
other demonstration actually filled: `Difference.filled_as`, read off the leaf
where `_diff_body` already has it, carried to `Parameter.unquoted_as`. Deciding
both from the absent form unquotes a text box whose form nulls it, and
`check dock 9` goes out as `{"note":check dock 9}`; deciding both from the
filled type unquotes a number box whose form empties it, and every run that
skips it renders `{"qty":}`. A value going into an unquoted *text* slot is
JSON-encoded on its way into the body, and only into the body — the same value
in a URL segment is text.

Which sites lose their quotes is decided per site, at parameterisation time,
and carried on `Substitution`. One parameter can fill a body leaf here and a
URL segment there, and only the body leaf is JSON at all; a set of parameter
*names* handed to `substitute_body` cannot tell those apart. The `\x00` marker
that finds the leaf again afterwards is keyed on its pointer and stays a local
detail of the one function that writes it.

A value is not only a value. A template substitutes as text and
`ExecutionRequest.parameters` is a free-form dict off an HTTP request, so a
quantity supplied as `2,"approved":true` renders a valid body carrying a field
no demonstration ever sent — and unquoting made that free where a quoted slot
at least needs a `"` to get out of. `Parameter.rejects` says, in a sentence,
why a value cannot go in its slot: a bare number slot takes a JSON number or
the absent form the demonstration itself sent, a quoted slot takes text that
cannot end its own string, an unquoted text slot is encoded and takes anything.
It is asked in two places, because the values arrive from two. `_check_runnable`
refuses what an operator supplied before the run starts, since a job whose
fourth step carries the bad value has already written three times by the time
rendering sees it; and rendering asks again for the values `_check_runnable`
cannot see — a value an earlier response produced, or the thing a loop is on
this time round. A run that refuses is better than a run that writes something
nobody demonstrated.

Whether a field may be left out is not stored beside all this. `optional`
derives from `absent_as`, because they were never two facts: what makes a field
optional is one demonstration having left it alone, and the absent form is what
that demonstration sent instead. Held separately they could disagree —
`Parameter(absent_as="null", optional=False)` was legal — and the two sides
read different predicates: emission unquoted the slot on the strength of the
absent form, execution declined to fill it on the strength of the flag, and the
write left as `{"deltaPriority":}`.

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
- **A value carrying a `"` or a `\` is refused wherever it was headed.** The
  quoted-slot rule is asked of every parameter, because nothing on a
  `Parameter` says which of its sites is a JSON body leaf and which is a URL
  segment — so a form-encoded body parameterised whole, or a search term with
  a quotation mark in it, is refused rather than sent. A false refusal names
  the field and the character; the alternative is a body somebody else's
  quotation marks helped write. Narrow it by carrying the site kinds a
  parameter fills, the day a real value needs one of those characters.
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
