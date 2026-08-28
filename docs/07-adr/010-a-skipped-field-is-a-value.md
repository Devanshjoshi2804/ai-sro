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

*Amended.* Optionality is a fact about the whole history of a task, not about
the last two times somebody did it. The pair is still what proves a parameter
and still decides identity -- ADR 004 stands, nothing here is inferred from a
run nothing was diffed against -- but a key that *any* recorded doing left
empty is optional, and a key filled in every doing there is stays required,
because nothing has shown the task works without it.

The evidence: an operator created the same kind of work area three times, all
accepted. The first sent only `workArea`, `workAreaDescription` and
`warehouseId`; the two after it also filled `absolutePriority`,
`homeWorkAreaAbsolutePriority` and `voiceCode`. `TeachCandidate` built
recordings from the two most recent episodes only, so nothing induction looked
at had ever seen those three fields empty and the skill demanded all three --
while the doing that proves the warehouse takes them empty sat unopened in the
evidence plane.

So `TeachCandidate` builds a recording from every episode it can, hands the
two freshest to `InduceSkill` as the pair -- the rule about the freshest doing
being the one most likely to still find its controls is a rule about the pair
that gets *diffed*, and it has not changed -- and passes the rest as `others`.
`differences` reads them for one thing: whether some write sent a key holding
nothing (`diff._absences`, `_absence_elsewhere`). They are never aligned, never
diffed, and no step or value comes out of them. Every doing the induction read
is named in the version's provenance, because a reviewer asked why a field is
optional has to be able to go and look at the doing that proves it.

Keyed by method, endpoint shape and pointer, not by pointer alone: a pointer is
not a field, two writes in one task can both send `/name`, and one of them
being empty says nothing about the other. Those are the same three things
`_same` already uses to decide two calls are the same call.

Two rules do not move. The absent form is still read off a doing that actually
sent it, never chosen -- and where two doings disagree about it, one `null` and
one `""`, there is no single form to send and the field stays required. And a
key no doing sent at all is still a divergence: a doing read only for emptiness
cannot say anything about a key it never sent, so nothing about it reaches the
field.

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
the absent form the demonstration itself sent, and nothing else does.

*Amended.* A quoted slot used to be a third rule — text that cannot end its own
string — and that was the wrong half of the asymmetry to keep. A quoted body
slot holds text inside a JSON string, exactly as the unquoted string slot beside
it does, and that one is `json.dumps`-encoded on its way in and takes anything.
So the quoted slot is encoded too: one `json.dumps` in `execute_skill._perform`
serves both, its own quotes carried where the slot has none and stripped where
the template already wrote them, and for a value with neither a quote nor a
backslash in it nothing on the wire changes. What is refused is what encoding
cannot fix — the bare slot's JSON type, and a control character wherever the
value is not itself the body, since the same value is substituted as text into
headers and URLs and neither can carry one.

Either way it is asked in two places, because the values arrive from two.
`_check_runnable` refuses what an operator supplied before the run starts, since a job whose
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
still fill it by clicking. *Amended:* being conditional is not a property of
having been dropped. Where the history is what proves the field optional, both
diffed runs typed into the box and the gesture is an ordinary aligned step --
which still only happens when somebody supplies the value, because typing empty
into a box every demonstration filled is how a form raises a validation error
nobody triggered. So the question is asked of every step in `emit_step`: a
keystroke whose value is an optional parameter is conditional on it, wherever
that step came from. The keystroke only -- the write that carries the field is
not conditional on it, since that call goes out either way carrying the absent
form. `_perform_in_ui` skips a conditional step when
nothing was supplied for its field, rather than clicking it empty and risking
a validation error the operator never triggered; the vision path inherits the
same skip because it runs through the same guard.

**Rejected: inferring optionality from the page** (a `*` beside the label, an
`x-form-required-field` attribute the recorder already captures). Corroborating
knowledge, not the source of truth — a field the page marks required but that
every demonstration happens to fill is still, correctly, required; a field two
demonstrations prove optional stays optional even if the page never says so.
What was actually done outranks what the page claims.

**Rejected: treating a key absent from any doing's write as optional too.**
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

A field an operator left empty once, three visits ago, is optional in the
skill induced today -- without the two doings that get diffed having to be the
two that happened to disagree about it.


The costs, named rather than hidden:

- **A required numeric field is still templated as a quoted string.** The
  unquoted rendering only applies to a parameter with `absent_as` set — an
  optional field, proven by a skipped demonstration. A required field with no
  such evidence still substitutes as `"${name}"`, which ADR 004 already
  recorded as a known gap; this decision narrows it rather than closing it.
- ~~**A value carrying a `"` or a `\` is refused wherever it was headed.**~~
  *Closed.* A whole-body parameter — SOAP, XML — carries a `"` on every single
  run, so this was not a false refusal at the margin: it made such a task
  permanently unrunnable. Closed the way this predicted, by carrying the one
  site kind that matters: `Parameter.is_the_body` says whether the value *is*
  a body rather than a value inside one. It is the body only for a body that
  is not JSON, which is parameterised whole; everything else is escaped into
  the JSON string it lands in, which is the safe default and so also what
  every parameter stored before the field existed does.
- **A control character is still refused, including in a body leaf that could
  escape it.** `json.dumps` would encode a newline perfectly well, but a
  parameter's value is substituted as text into headers and URLs too — a `\r`
  ends a header value and starts a second header — and `is_the_body` is not
  fine-grained enough to separate a body leaf from a header. Refusing costs a
  multi-line value in a JSON field; no form control an operator fills in
  produces one. Narrow it the day one does, by carrying the rest of the site
  kinds.
- **A value can still add a query parameter the demonstration never sent.** A
  URL slot substitutes raw text: supplying `X&limit=9999` for a query
  parameter renders `?name=X&limit=9999&limit=25`, and `a/b` for a path
  segment adds a segment. The same class as the JSON injection, in a different
  syntax, and untouched by this decision — encoding on the way in is the fix
  and it is not one line, because `substitute_url` records query values
  decoded (`parse_qsl`) and path segments encoded (`url_path_segments` never
  unquotes), so one uniform rule double-encodes half of them. Its own change.
- **Loop bounds count raw frame indices while step indices count aligned,
  post-`explode` steps.** Pre-existing, and reproducible independently of a
  conditional step at all — two non-evidential unmatched frames with no
  optional field between them already produce a `first_step`/`last_step` a
  version's own invariant rejects (`skill.py:302`). A conditional step makes
  this more likely to occur, since more misalignment can now survive as far as
  emission, but it did not create the bug.

- **A form that nulls a whole nested block refuses to induce.** Everything
  above is written for leaves: what proves a field optional is a key both
  writes send, one holding a value and the other holding nothing, and the
  absent form is read off that leaf. An *ancestor* left empty --
  `"lines": [{"sku": "ABC"}]` in one run against `"lines": null` in the other
  -- is admitted by `same_shape`, and nothing here can say what comes out of
  it. The group's `null` is not the absent form of the leaves under it: handed
  down to each of them it emitted `{"lines":[{"sku":${sku},"qty":${qty}}]}`,
  and a run supplying neither sent a blank line item neither demonstration
  sent, which a WMS that accepts one turns into a blank order line. The honest
  alternative is one optional parameter holding the whole group, whose value is
  an object -- and every rule that keeps a supplied value from writing the rest
  of the body, `Parameter.rejects` and `_check_runnable`, is written for
  scalars. So the pair is refused, naming the pointer and asking for that group
  filled in both runs. This is the more reachable of the two refusals recorded
  here, because a form with a nested block nulls the block rather than each
  leaf inside it; it costs a pair nobody has demonstrated yet, where guessing
  costs a warehouse a record it never asked for.

- **A loop and a skipped field in one pair is refused.** Built, the pair proved
  worse than the bounds question that prompted looking for it: a loop's
  substitutions are keyed by raw frame, the diff's by aligned step, and
  `_make_room` moves every key it is handed -- so the conditional step moved
  the loop's own `${line_id}` one place past the step that sends it, and the
  skill posted `/api/lines/1/adjust` once per line the order had. Nothing
  complained; the version passed its own invariants. Reconciling the two spaces
  means deciding they agree once every dropped gesture is back, which holds
  only while every unmatched frame before the block is one of them. That is a
  guess, so induction refuses the combination and names the demonstration to do
  again. The bounds are still not remapped, and with the refusal in place there
  is nothing that could reach the remapping.
- **A field the pair agreed on is not made a parameter by a doing that left
  it empty.** Optionality is read from the history; identity and
  parameterisation are not, and ADR 004 is the reason. Two runs that both sent
  `voiceCode: "1"` produce a constant, and an older doing that sent `""` there
  cannot turn that constant into an optional parameter -- nothing in the pair
  says the value varies, and inventing a parameter from a run nothing was
  diffed against is exactly the guess that decision forbids. It costs a skill
  that always sends `"1"` where it could have offered a box. The demonstration
  that fixes it is one where the two freshest doings disagree.
- **Teaching now reads every episode of a candidate, not two.** A candidate
  seen fifty times reads fifty batches out of the blob store and stores fifty
  recordings on one teach. Bounded in practice by how often a task is watched
  before somebody teaches it, and unbounded in principle; the day that bites,
  the cheap fix is to read the older doings' writes without sealing them as
  recordings, which costs the provenance line that names them.
- **`TeachWorkflow` still hands over two.** Two candidates taught as one job
  draw their pair from occurrences and spend an episode per side, so "the rest
  of the history" there is a different thing to compute. Unchanged rather than
  half-done: a workflow's optional fields are still decided by its pair.
- This ADR covers Part 1 and Part 2 of
  `docs/superpowers/specs/2026-08-27-fields-nobody-filled-design.md` only —
  a value nobody has ever typed, the pre-flight, the offer, and when asking
  stops (Parts 3–6) are their own decision, not made here.
