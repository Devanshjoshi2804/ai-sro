# Notes for `backend/src/sro/application/induction/diff.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/diff.py`](../../../../../../../backend/src/sro/application/induction/diff.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/diff.py#L1): Docstring

> Two-run diff: what varies becomes a parameter.
>
> Rationale and the rejected alternatives: docs/07-adr/004-diff-parameterisation.md.

## module, [line 34](../../../../../../../backend/src/sro/application/induction/diff.py#L34): Note on the line above

Code: `_UNREMARKABLE = frozenset({"", "true", "false", "null", "0", "1"})`

> Values too common to be evidence of anything, wherever they turn up.

## module, [line 136](../../../../../../../backend/src/sro/application/induction/diff.py#L136): Note on the line above

Code: `_GENERATED = re.compile(r"\d+")`

> ExtJS numbers its generated ids per page load: the same Save button is
> ``button-1347-btnIconEl`` in one demonstration and ``button-1494-btnIconEl`` in
> the next. Compared verbatim, every unnamed control in this application is a
> different control every session.

## module, [line 172](../../../../../../../backend/src/sro/application/induction/diff.py#L172): Note on the line above

Code: `FILLS = frozenset({"type", "select", "upload"})`

> The gestures that put a value in one place, where doing it twice before
> anything is sent means the second one is what the field held.
>
> The same three `verify._PUTS_A_VALUE` names for the same reason, and kept as
> their own constant rather than imported across the layer: a gesture that can be
> corrected and a gesture that can be wrong in a way nothing else on the page
> would show are two different questions that happen to have one answer today.

## `Difference`, [line 45](../../../../../../../backend/src/sro/application/induction/diff.py#L45): Note on the line above

Code: `absent_as: str | None = None`

> What this field looked like in the run that left it alone -- `"null"`,
> or `""` from a text control nobody focused. Present only when exactly one
> of the two runs filled it, which is what makes the field optional.

## `Difference`, [line 47](../../../../../../../backend/src/sro/application/induction/diff.py#L47): Note on the line above

Code: `filled_as: str | None = None`

> The JSON type of the leaf the run that filled this field actually sent.
>
> Read off the value rather than inferred from the absence beside it: a form
> that nulls an untouched box nulls a text box the same way it nulls a
> number, and `null` says nothing about what goes there when somebody types.
> Only a body leaf has one; a URL segment and a header are text either way.

## `Substitution`, [line 55](../../../../../../../backend/src/sro/application/induction/diff.py#L55): Note on the line above

Code: `unquoted: bool = False`

> Whether this site's placeholder is emitted without the quotes
> `json.dumps` would put round it.
>
> Decided here, per site, rather than per parameter name downstream: one
> parameter can fill a body leaf, a URL segment and a header, and only the
> body leaf is JSON at all.

## `Choice`, [line 59](../../../../../../../backend/src/sro/application/induction/diff.py#L59): Docstring

> A value both demonstrations chose, that either of them could have chosen
> differently.
>
> The operator picked an address off a list and then picked the same one
> again. Nothing in two runs can say whether that address is policy or
> preference -- and both answers are ordinary. Replaying it writes every
> supplier to one address; parameterising it asks a question nobody wanted.
> So it is neither: it is asked.

## `Choice`, [line 61](../../../../../../../backend/src/sro/application/induction/diff.py#L61): Note on the line above

Code: `sites: tuple[Site, ...]`

> Everywhere this call sends the value. One answer settles all of them: the
> address is in the path and in two body fields, and prompting for it three
> times would be three questions about one thing.

## `Choice`, [line 64](../../../../../../../backend/src/sro/application/induction/diff.py#L64): Note on the line above

Code: `field: str`

> What the parameter would be called, if it became one.

## `Choice`, [line 66](../../../../../../../backend/src/sro/application/induction/diff.py#L66): Note on the line above

Code: `seen_at: int`

> The step whose response listed it. The evidence that it was chosen from
> what the screen offered rather than typed out of somebody's head.

## `Parameterisation`, [line 73](../../../../../../../backend/src/sro/application/induction/diff.py#L73): Note on the line above

Code: `choices: tuple[Choice, ...] = ()`

> Constants that were chosen rather than given. Nothing here changes what
> runs -- they are questions for an operator, not parameters.

## `_mutations`, [line 93](../../../../../../../backend/src/sro/application/induction/diff.py#L93): Docstring

> The calls this gesture made that changed something, in the order sent.

## `unfold`, [line 101](../../../../../../../backend/src/sro/application/induction/diff.py#L101): Docstring

> The same split as :func:`explode`, for a run with nothing to pair against.
>
> One demonstration has no second run to line calls up with, so each gesture's
> calls are taken in the order the application sent them.

## `explode`, [line 112](../../../../../../../backend/src/sro/application/induction/diff.py#L112): Docstring

> One step per call, where a single gesture made several.
>
> Clicking Save on the supplier screen sends a POST that creates the supplier
> and a PUT that sets its address. The frame kept both and everything
> downstream read only the "primary" one, so the skill replayed the address
> and never created the supplier -- a task that looks right in review and does
> half the work.
>
> Split after pairing rather than before it, because the pairing is a fact
> about gestures: two runs of the same task click the same Save, and what that
> Save sent is what has to line up underneath it. Splitting first would ask
> the aligner to pair calls whose paths carry the parameter that makes the two
> runs different.

## `_control`, [line 139](../../../../../../../backend/src/sro/application/induction/diff.py#L139): Docstring

> What the gesture acted on, as steadily as the page allows.
>
> The accessible name first, because ExtJS renumbers its generated ids between
> page loads and ``button-1148`` is not the same control tomorrow. Role and
> kind on their own would pair two different text boxes, which is the one
> mistake worth being strict about.
>
> An unnamed control has its generated numbers taken out, which is the same
> point made one level down: ``button-1347-btnIconEl`` and
> ``button-1494-btnIconEl`` are one Save button seen in two sessions.

## `_same`, [line 149](../../../../../../../backend/src/sro/application/induction/diff.py#L149): Docstring

> Whether these two steps are the same step of the same task.
>
> Either signal will do, because each fails on its own. The page renames its
> own controls -- one demonstration reported an accessible name of "Save" and
> the next, of the same button, reported none at all -- so identity alone
> refuses pairs that are plainly the same gesture. And what a step sent is
> absent from every step that only typed into a field, so calls alone would
> pair nothing in a form.
>
> What the step sent is the stronger of the two when both are present: the
> page describes the control, the application describes the call.

## `url_shape`, [line 160](../../../../../../../backend/src/sro/application/induction/diff.py#L160): Docstring

> A path with its identifiers taken out, so two runs of one task agree.
>
> ``/addresses/A00022791`` and ``/addresses/A00022812`` are the same step of
> the same task. Which record it was is what the diff exists to find; here it
> would only stop the two steps being recognised as each other.
>
> Public because mining asks the same question of a day's observed traffic:
> two episodes are the same task when their calls have the same shapes, and a
> second opinion about that would cluster what induction then refuses to
> align.

## `_evidential`, [line 164](../../../../../../../backend/src/sro/application/induction/diff.py#L164): Docstring

> Whether dropping this step would lose something the skill needs.
>
> A gesture that changed the system, or carried a value into it, is evidence.
> A click that fetched nothing and typed nothing is the operator finding their
> way -- focusing a field, opening a panel to look, clicking a label twice.

## `settled`, [line 175](../../../../../../../backend/src/sro/application/induction/diff.py#L175): Docstring

> A run with the operator's corrections taken out.
>
> People mistype. They type a code, look at it, clear it and type it again --
> two `type` frames on one control, one value that was ever really submitted.
> `align` pairs one of them and then finds the other unpaired, carrying a
> value, and refuses the whole pair: "the second run did something the other
> did not: type on Warehouse Equipment Type".
>
> That refusal is what an operator sees as *"I've watched this a few times
> but the doings differ too much"*. On this deployment it was every pair of
> four doings of one task -- 0 and 1, 0 and 2, 0 and 3, 1 and 2, 1 and 3, 2
> and 3 -- so a task done four times taught nothing, and doing it a fifth
> time would have refused the same way.
>
> Only what was superseded before anything was sent. A later typing on the
> same control with no write in between replaces the earlier one, because
> the field only ever held the last of them by the time the form went. A
> typing on either side of a write is two different things being submitted
> -- a row added twice, a search run again -- and both are kept.
>
> Never a credential. A password re-typed is still one password, but it
> carries no value to be superseded BY, and the run that types it twice is
> a run that failed to sign in once; `domain/skill/passwords` makes that
> judgement with the evidence to make it.
>
> The same for a dropdown and a file. Picking the wrong option and picking
> again, or attaching the wrong document and attaching the right one, is one
> field filled once by the time the form goes -- and a run that replayed both
> picks would do the work of the mistake before the work of the correction.
> A click is deliberately not in this set: two clicks on one control are two
> presses of a button, which `_evidential` already lets through as
> exploration when they changed nothing and which really are two actions
> when they did.

## `_wrote_something`, [line 191](../../../../../../../backend/src/sro/application/induction/diff.py#L191): Docstring

> Whether this step sent a mutation the application acted on. Background
> traffic is not one -- a keep-alive that lands between two typings would
> otherwise make a correction look like a second submission.

## `align`, [line 197](../../../../../../../backend/src/sro/application/induction/diff.py#L197): Docstring

> Pair the steps the two runs share, and say why they cannot be paired.
>
> The first demonstration of anything contains looking around: a field clicked
> twice, a panel opened to check a code, a grid sorted before the row is found.
> Demanding identical step counts made the exploration part of the task and
> refused the pair -- for two runs whose writes were byte-identical.
>
> So the runs are aligned rather than counted, on the longest sequence of
> gestures they share. What only one run did is dropped, but only when
> dropping it loses nothing: a step that changed the system or carried a value
> is never silently discarded, because that is a genuine disagreement about
> what the task is and guessing there is what ADR 004 exists to prevent.

## `Alignment`, [line 227](../../../../../../../backend/src/sro/application/induction/diff.py#L227): Docstring

> One run chosen to speak for all of them, and how many did what it says.
>
> ``reference`` is that run's steps, in order -- extended with anything a
> minority did that the majority did not, so a step nobody but one doing
> made is present rather than silently gone. ``seen`` counts, by position in
> ``reference``, how many of the runs handed to :func:`align_all` contained
> a match for that step. What a count of one versus a count matching every
> run *means* -- keep it, drop it, ask about it -- is a later decision; this
> only refuses to throw the evidence away before that decision is made.

## `Alignment`, [line 231](../../../../../../../backend/src/sro/application/induction/diff.py#L231): Note on the line above

Code: `doings: int`

> How many runs were aligned -- the denominator every count in ``seen`` is
> a share of.
>
> Recorded rather than inferred, and the inference it replaces is the reason
> the field exists. ``max(seen.values())`` is the run count only where some
> step is universal, and a batch where none is -- two operators who wandered
> off, ten doings of a screen that grew a confirm dialog partway through the
> month -- reads low. Low here is not a soft failure. Every share is divided
> by it, so a denominator short by two turns "six of ten made this" into
> "six of eight", and a step over two thirds that neither demonstration in
> the pair made is not quietly kept: `induce_skill._extra_steps` *refuses*
> the whole induction where such a step carries a value or a request,
> because a step the counts call the task and nothing diffed is exactly the
> disagreement `align` will not paper over. Guessing the denominator low
> therefore does not cost a reviewer a question, it costs them the skill.

## `align_all`, [line 234](../../../../../../../backend/src/sro/application/induction/diff.py#L234): Docstring

> Align every occurrence of a task against one reference, and count them.
>
> :func:`align` pairs two runs and stops there: everything past the second
> goes to :func:`parameterise` as ``others``, read only for whether some
> doing left a field empty, never for a step. Four demonstrations of one
> task -- filled out differently, one of them with a whole address lookup
> the rest skipped -- go through this as one pair and three histories, and
> the address lookup's steps are discarded along with the run that made
> them. Its *value* survives regardless, because ``others`` still sees it:
> the induced skill came out with a ``cod_address_id`` parameter and no step
> that could ever fill it. This is the fix -- every run's steps reach here,
> not just the two that happened to be first.
>
> Reading every run against one fixed reference, rather than pairing every
> run against every other, is the same trade :func:`_longest_common`'s own
> docstring makes, applied once more: a run is a handful of steps, so its
> quadratic table costs nothing next to the code that would avoid it. That
> holds once per pair; asking it to hold between every pair of N runs turns
> "a handful of steps, squared" into "a handful of runs, squared, each
> already squared". *This* step -- aligning every run against the reference
> once it is chosen -- pays the quadratic cost N times, against one
> reference, rather than N-squared times against each other.
>
> Choosing that reference is a separate cost, and it is not N -- see
> :func:`_pick_reference`, which is all-pairs on purpose and says so.
>
> The reference is the run whose steps recur most across the others,
> judged by :func:`_longest_common` against each one -- not the longest run
> and not the most recently recorded. The longest run may be the one where
> somebody wandered, and rewarding length would make wandering the way to
> author the reference; the most recent is an accident of upload order and
> says nothing about what the task is. See :func:`_pick_reference` for how
> a tie between equally-agreed-with runs is broken.
>
> Every other run is then aligned against that reference with
> :func:`_longest_common`, the same pairing :func:`align` uses for two.
> Where a run's step matches one already in the reference, that position's
> count goes up. Where a run made a step :func:`_evidential` -- the same
> test :func:`align` already uses to refuse silently dropping one -- and the
> reference has nothing there yet, the reference gains it, at the position
> the alignment says it belongs, counted once for the run that made it. A
> step only one operator demonstrated is not noise to be voted out here; it
> is one occurrence out of however many, and whether one occurrence is
> enough to keep is a question for whoever calls this, not for the counting.
>
> How many runs there were is recorded alongside the counts rather than left
> to be read back out of them -- see :attr:`Alignment.doings`. It is the one
> number this function knows for certain and nothing downstream can recover.
>
> Refuses on no input at all: an alignment of nothing is not a task with
> zero steps, it is the absence of anything demonstrated to align.

## `_pick_reference`, [line 267](../../../../../../../backend/src/sro/application/induction/diff.py#L267): Docstring (debt)

> The run the others agree with most, on the strength of shared steps.
>
> Scored by summing :func:`_longest_common` against every other run in the
> batch -- every occurrence gets a say in the score, not just whichever two
> runs a naive pairing would have compared first. Ties go to the shortest
> candidate: a run tied on agreement with a longer one agrees on exactly the
> same steps, and the longer one's extra length is exactly the part nothing
> else here corroborates -- the wandering :func:`align_all`'s own docstring
> warns against rewarding.
>
> ponytail: this scores every run against every other run, so choosing the
> reference is O(N^2) in the number of runs even though aligning against it
> afterward is only O(N). A few dozen occurrences pay that cheaply; a
> thousand do not. Cheaper here would be scoring each run against a sample
> of the others, or clustering first and picking a reference per cluster --
> worth designing on its own once occurrence counts make this measurably
> slow, not improvised inline.

## `OptionalFill`, [line 279](../../../../../../../backend/src/sro/application/induction/diff.py#L279): Docstring

> A gesture only one run made, that only filled a field the other left alone.
>
> What :func:`align` drops. Dropping it costs nothing the *pairing* needs --
> both runs created the record -- but it is the only gesture in either
> recording that fills that field, so a skill built from the pairs alone can
> never fill it by clicking. On a system with no writable API that means never
> at all.

## `OptionalFill`, [line 281](../../../../../../../backend/src/sro/application/induction/diff.py#L281): Note on the line above

Code: `pointer: str`

> Where in the write the typed value landed. The parameter is named from
> this pointer, never from the keystroke.

## `OptionalFill`, [line 283](../../../../../../../backend/src/sro/application/induction/diff.py#L283): Note on the line above

Code: `at: int`

> How many aligned steps come before it, so it can be put back in its place
> in the order rather than at the end of it.

## `optional_fills`, [line 286](../../../../../../../backend/src/sro/application/induction/diff.py#L286): Docstring

> The gestures :func:`align` drops, with enough to place them again.
>
> Beside `align` rather than inside it: what it returns is the pairs, and the
> steps and the diff are both addressed by position in them. A caller that
> wants the dropped ones asks for them separately and decides what to do with
> them, which for induction is to emit each as a step conditional on the field
> it filled.
>
> Either run's, because which recording was taught first is an accident of
> storage order: whichever operator filled the field, the skill that comes out
> has to be able to fill it.

## `_optional_pointer`, [line 306](../../../../../../../backend/src/sro/application/induction/diff.py#L306): Docstring

> Where this unmatched step's typed value landed, when it landed in a field
> the other run left alone. None when it did not, and the step is a genuine
> disagreement about what the task is.
>
> Two people filling one form fill different subsets of it, and both create
> the record. Such a step is not a refusal, because the field it filled is
> about to become an optional parameter -- and keeping the refusal means a
> form of any size never induces at all.
>
> Everything here is read from the writes. The field must be one *both* runs
> sent, or the two are different requests and the refusal stands.

## `describe_step`, [line 323](../../../../../../../backend/src/sro/application/induction/diff.py#L323): Docstring

> A step named the way an operator would recognise it.

## `_longest_common`, [line 331](../../../../../../../backend/src/sro/application/induction/diff.py#L331): Docstring

> Classic LCS over control identity. Runs are a handful of steps, so the
> quadratic table is smaller than the code to avoid it.

## `differences`, [line 355](../../../../../../../backend/src/sro/application/induction/diff.py#L355): Docstring

> What varies between these two runs, and what the rest of the history
> says about emptiness.
>
> ``others`` are further doings of the same task, read for one thing only:
> whether some doing left a field empty. They are never aligned, never
> diffed, and never a source of a step or a value -- the pair still proves
> every parameter, exactly as ADR 004 says. What they can add is an absent
> form to a parameter the pair already found, because whether a field may be
> left out is a fact about the whole history of a task and not about the last
> two times somebody did it. Two people who both happened to fill Absolute
> Priority prove nothing about the third who did not.

## `_absences`, [line 368](../../../../../../../backend/src/sro/application/induction/diff.py#L368): Docstring

> Every key some doing sent holding nothing, and what nothing looked like.
>
> Keyed by the call as well as the pointer, because a pointer on its own is
> not a field: two writes in one task can both send `/name`, and one of them
> leaving it empty says nothing about the other. Same method, same endpoint
> shape, same pointer -- the same three things `_same` and the diff already
> use to decide two calls are the same call.
>
> A key a doing never sent at all contributes nothing here. That is the line
> ADR 010 draws and this does not move it: an absent key is a divergence, and
> only a key that was sent holding nothing is evidence of an optional field.

## `_absence_elsewhere`, [line 384](../../../../../../../backend/src/sro/application/induction/diff.py#L384): Docstring

> The absent form some other doing sent at this key, where exactly one
> form was seen.
>
> Never chosen: what goes in the slot when nobody supplies the field is what
> a doing actually sent there. Where two doings disagree about it -- one
> `null`, one `""` -- there is no single form to send and the field stays
> required, which is what the evidence supports.

## `parameterise`, [line 391](../../../../../../../backend/src/sro/application/induction/diff.py#L391): Docstring

> Diff, classify as input or derived, name, and address every substitution.
>
> ``ask_for`` names the fields an operator has since said they want to choose
> per run -- values both demonstrations happened to agree on. Their answer,
> not our inference: without it these stay exactly as they were demonstrated.
>
> ``also`` adds candidates the diff cannot find on its own. A single
> demonstration has nothing to disagree with, so the values a person typed are
> offered from there -- still gated by ``ask_for``, still never invented.
>
> ``others`` are the rest of the doings of this task, read only for whether
> some doing left a field empty. See :func:`differences`.

## `typed_values`, [line 499](../../../../../../../backend/src/sro/application/induction/diff.py#L499): Docstring

> Values a person typed, and where the calls afterwards carried them.
>
> Only for a demonstration with no partner. Two runs settle this by
> disagreeing: what changed is a parameter, what held is literal. One run
> cannot disagree with anything, so every value it sent looked equally fixed --
> including the supplier number an operator had just typed into a box labelled
> "What is the supplier number?". Replaying that creates the same supplier
> again.
>
> Typing is not an inference: the frame records that a human entered this
> value, and the control records what it was called. Everything else the call
> carried stays exactly as demonstrated, because nothing says it varies.
>
> ``taken`` is the names the rest of the induction has already handed out.
> This used to pass an empty set, so a typed value whose control suggested a
> name a parameter already had either merged the two into one -- one box
> filling another box's value -- or collided outright and failed the whole
> induction with "parameter names must be unique".

## `_chosen_constants`, [line 533](../../../../../../../backend/src/sro/application/induction/diff.py#L533): Docstring

> The record a write addressed, where the operator picked it off a screen.
>
> Narrow on purpose. A create copies twenty fields off the record it was
> given -- the address line, the city, the postcode -- and every one of them
> was "chosen" in the sense that it came from a list. Asking about all twenty
> is worse than asking about none: fifteen questions arrived for one task and
> nobody would answer any of them.
>
> What actually matters is which *record* the call acts on, and that is in the
> URL path: `PUT /wm/addresses/A000144886`. Answer that one and the fields
> that carry the same value are settled with it, because they are not separate
> decisions -- they are the same address written down three times.

## `_collections_read`, [line 576](../../../../../../../backend/src/sro/application/induction/diff.py#L576): Docstring

> Every path the demonstration called, so a record can be told from a route.
>
> `/data/WM/wm/addresses/A000144886` and `/data/WM/wm/suppliers` both end in a
> segment that is constant across the runs, and only one of them is a record
> somebody picked: the demonstration also called `/data/WM/wm/addresses`, and
> never called `/data/WM/wm`. A path whose parent was fetched as a collection
> is addressing one of its members.

## `_name_for`, [line 592](../../../../../../../backend/src/sro/application/induction/diff.py#L592): Docstring

> The call's own name for this value, preferring the payload's.
>
> `/wm/addresses/A000144886` names it `addresse_id` by position; the body
> calls it `addressId`. The body is the system's own vocabulary and does not
> depend on how the path happens to be pluralised.

## `_listed_before`, [line 601](../../../../../../../backend/src/sro/application/induction/diff.py#L601): Docstring

> The step whose read offered this value, or False if none did.
>
> Matched against the values a response carried, never its text: `data` and
> `suppliers` appear in the body of every JSON payload ever sent, and matching
> text asked the operator whether the word "data" in the endpoint's own path
> was a choice they had made.

## `_link_produced_values`, [line 611](../../../../../../../backend/src/sro/application/induction/diff.py#L611): Docstring

> Values an earlier call in this same task minted, bound to where they came from.
>
> The diff only sees what varies, so a record id the server assigned during
> the demonstration is invisible to it: both runs sent whatever that run's
> server said, and the value that reached the next call was different in each
> -- but only because the runs are different runs, not because an operator
> chose anything. Left alone it becomes a literal, and every replay writes to
> the record the demonstration happened to create.
>
> So a value is bound to the response that produced it when three things hold:
> both runs' responses carried it at the same pointer, the step that used it
> came later, and nobody in either run had that value in their hands before
> that response arrived. The last one is what separates a server-minted id
> from a facility code the operator picked on the first screen: a value that
> was already being sent was not produced by anything.

## `_find_produced`, [line 655](../../../../../../../backend/src/sro/application/induction/diff.py#L655): Docstring

> The earlier response that produced this value, if one demonstrably did.
>
> Stricter than the diff's own source-finding, because there is no variation
> here to corroborate anything: an unvarying value matches by luck all the
> time. A list of forty addresses contains "CAN" and "SUP" and a dozen true
> flags, and binding a supplier's country to row 44 of a lookup would be a
> confident wrong answer of exactly the kind ADR 004 exists to prevent.
>
> So the value has to be unique in the response -- one pointer, not one of
> forty rows -- at the same pointer in both runs, and where the place it is
> later sent has a name, the response has to use that same name for it. The
> system's own vocabulary is the evidence; agreement on it is not luck.
>
> And deliberately no reformatting here, unlike `_find_source`. A rewriting is
> read off one pair and believed because it also explains the other; here both
> runs carry the same value, so the second pair is the first one again and a
> rule would only ever be checked against itself.

## `_key_of`, [line 679](../../../../../../../backend/src/sro/application/induction/diff.py#L679): Docstring

> What the call calls this value, where it calls it anything.

## `_constant_sites`, [line 687](../../../../../../../backend/src/sro/application/induction/diff.py#L687): Docstring

> Every addressable value this call sent that both runs sent identically.

## `_held_before`, [line 713](../../../../../../../backend/src/sro/application/induction/diff.py#L713): Docstring

> Whether anybody in this run had the value before that step answered.
>
> Typed, or sent in a URL or a body. The step that produced it is included:
> a call that sends an id in its own path did not learn that id from its own
> response, whatever the response repeats back.

## `_names_it`, [line 723](../../../../../../../backend/src/sro/application/induction/diff.py#L723): Docstring

> Which of the places this value appears should name it.
>
>     The call's own field name, wherever there is one. A screen labels the field
>     "Supplier*
> What is the supplier number?" and the payload calls the same
>     value `supplierNumber` -- and naming it after the label produced
>     `supplier_what_is_the_supplier_number`, which is not only ugly: the model
>     asked to fill it in refused to bind "ACMETEST9" to it, so the skill could
>     not be run from a sentence at all. The system's own vocabulary is shorter,
>     stabler, and already what every other part of this reads.
>     

## `_where`, [line 780](../../../../../../../backend/src/sro/application/induction/diff.py#L780): Docstring

> Name every place this value appears, not just how many.
>
> A parameter is one value, and one value can sit under several field names:
> Blue Yonder's adjust payload sends the detail number as both `lpn` and
> `detailNumber`, so the group is named after whichever site was seen first
> and the plan reads `"lpn": "${detail_number}"`. That is faithful, and it
> looks exactly like a mis-binding to anybody reviewing it -- it cost an
> afternoon of mine. Saying where the value appears is the difference between
> a reviewer trusting the plan and re-deriving it.

## `_diff_headers`, [line 836](../../../../../../../backend/src/sro/application/induction/diff.py#L836): Docstring

> Headers that carry meaning and varied between the runs.
>
> Restricted to replayable headers on purpose. Everything else varies for
> reasons that have nothing to do with the task: a trace id is new per call, a
> cookie per session, a Referer per page. Diffing those would produce
> parameters no operator could answer.
>
> A header present in one run and missing in the other is left alone rather
> than treated as a difference -- browsers add and drop `sec-*` headers on
> their own, and a missing header has no value to parameterise.

## `_is_a_clock`, [line 899](../../../../../../../backend/src/sro/application/induction/diff.py#L899): Docstring

> Whether these two values differ only because time passed.
>
> Ext JS appends ``_dc=<epoch millis>`` to every request to defeat caching,
> and jQuery's ``_`` does the same. Both runs of a task therefore disagree
> there, always -- and the diff dutifully reported a parameter, so a skill
> asked its operator for a number that means "now". Two parameters out of four
> on the first real task taught were this.
>
> Detected by what the values are rather than by the key's name, because the
> name differs per framework and the shape does not: milliseconds since the
> epoch, recently, and different in the two runs.

## `_group_left_empty`, [line 960](../../../../../../../backend/src/sro/application/induction/diff.py#L960): Docstring

> Why a group one run filled and the other emptied is refused.
>
> `same_shape` admits the pair -- `"lines": [{"sku": "ABC"}]` against
> `"lines": null` is one request with a different value in it -- but nothing
> here can express what comes out. The absent form of an *ancestor* is not
> the absent form of the leaves under it: handing the group's `null` to each
> leaf individually emitted `{"lines":[{"sku":${sku},"qty":${qty}}]}`, and a
> run supplying neither sent `{"lines":[{"sku":null,"qty":null}]}` -- a blank
> line item neither demonstration sent, which a WMS that accepts one turns
> into a blank order line.
>
> The honest alternative is one optional parameter holding the whole group,
> whose absence sends the ancestor's own form. That is a parameter whose
> value is an object, and every rule that keeps a supplied value from writing
> the rest of the body -- `Parameter.rejects`, `_check_runnable` -- is written
> for scalars. Refusing costs a pair nobody has demonstrated yet; guessing
> costs a warehouse a record it never asked for.

## `renders_unquoted`, [line 969](../../../../../../../backend/src/sro/application/induction/diff.py#L969): Docstring

> Whether this site's placeholder is emitted without quotes round it.
>
> The absent form decides it, and only the absent form: the slot has to be
> able to render what the demonstration that skipped the field sent, and a
> quoted slot can only ever render a string. `null` there is a JSON null and
> `""` is an empty string, so a field the form empties keeps its quotes and
> a field the form nulls loses them.
>
> What a *supplied* value has to look like in that slot is a different
> question, answered by `filled_as` -- deciding the quotes from that instead
> unquotes a slot whose absent form is `""` and renders `{"qty":}`.

## `_absent_form`, [line 977](../../../../../../../backend/src/sro/application/induction/diff.py#L977): Docstring

> The empty exactly as it was sent. `json.dumps` rather than `str`,
> because a form that nulls a number wants `null` and not `None`.

## `_find_source`, [line 981](../../../../../../../backend/src/sro/application/induction/diff.py#L981): Docstring

> Find an earlier response producing this value in *both* runs.
>
> Requiring both is what separates a real data dependency from a coincidence.
> A coincidence promoted to DERIVED leaves a parameter nothing can populate.
>
> Verbatim first, everywhere, before any reformatting is considered: a value
> handed over unchanged is the ordinary case and must never be explained by a
> story about padding that happens to fit.
>
> An empty side is never a dependency. Requiring *both* runs to match is the
> only thing separating a data path from a coincidence, and an empty leaf
> matches every empty leaf there is -- so the moment one of the two values is
> empty that check carries no information and the pair is decided by the other
> run alone. A difference always has two unequal values, so this can only ever
> fire where exactly one run left the field alone: the optional field. Calling
> that DERIVED is the worst reading available -- every run would fill it from
> a response leaf, including the runs an operator wanted blank, and the
> keystroke `align` excused would come back as nothing at all. Read as an
> optional input it stays fillable by hand, with the absent form the run that
> skipped it actually sent.

## `Parameterisation.unquoted_sites`, [line 78](../../../../../../../backend/src/sro/application/induction/diff.py#L78): Docstring

> The sites in this step whose placeholder loses its quotes.

## `Parameterisation.conditional_on`, [line 81](../../../../../../../backend/src/sro/application/induction/diff.py#L81): Docstring

> The optional parameter this step's keystroke fills, if it fills one.
>
> A step that types an optional field only happens when somebody supplies
> it. That was already true of the gesture `align` dropped -- one run
> filled the box and the other did not, so the step comes back
> conditional. It is just as true of a gesture both runs made, where what
> proves the field optional is some third doing that left it empty: with
> nothing supplied there is nothing to type, and typing empty into a box
> the demonstration always filled is how a form raises a validation error
> nobody triggered.
>
> The keystroke only. The write that carries the field is not conditional
> on it -- that call goes out either way, carrying the absent form.
>
> One, and `next` rather than an arbitrary pick from several: a step has
> at most one keystroke site, because `_diff_action` yields at most one
> `ActionValueSite` difference per step and nothing else in this module
> ever builds a substitution on one -- every other source of sites is
> `_constant_sites`, which reads URLs, queries and bodies. So the answer
> here is determined by the evidence and not by the order the
> substitutions happen to sit in.
>
> If that ever stopped holding -- a gesture whose typing filled two
> fields that some doing each left empty -- this would be the wrong
> shape, and so would `SkillStep.when`, which is a single `str | None`.
> A step gated on two supplied values cannot be expressed by one `when`
> at all, and picking either one would run the step when half its
> condition held. Whoever wires this up meets that as a refusal to
> design, not as a silent choice made here.

## `_evidential`, [line 167](../../../../../../../backend/src/sro/application/induction/diff.py#L167): Comment

Code: `return any(`

> Background traffic is not what a step did. A keep-alive fires on a timer
> and lands on whichever gesture happens to be open, so counting it made
> clicking a paragraph of help text "evidence" -- and one operator reading
> the screen for a moment longer than the other refused the whole pair.

## `settled`, [line 180](../../../../../../../backend/src/sro/application/induction/diff.py#L180): Comment

Code: `latest.clear()`

> A write settles everything typed before it. What comes after is
> a fresh fill of the same form, not a correction of the old one.

## `align`, [line 205](../../../../../../../backend/src/sro/application/induction/diff.py#L205): Comment

Code: `excused = {id(fill.frame) for fill in optional_fills(run_a, run_b)}`

> Which dropped gestures are excused is asked once, of the function that
> also hands them back to be emitted, rather than decided here as well
> where the two answers could drift. Excused is the wider of the two:
> induction emits only those it can name an optional parameter for, and a
> gesture excused here that nothing emits is the field quietly becoming
> unfillable -- which is the whole reason the excusing exists.

## `align_all`, [line 247](../../../../../../../backend/src/sro/application/induction/diff.py#L247): Comment

Code: `cursor = 0`

> A single forward-scanning cursor into `reference`, rather than
> looking each matched frame's position up by value: `reference` grows
> under this loop as evidential steps are spliced in, and ActionFrame
> compares by field equality, not identity -- two distinct steps that
> happen to carry equal fields would make `.index()` find the wrong
> one. The cursor only ever moves forward, because `paired` preserves
> both runs' original order, so a plain identity scan is enough.

## `parameterise`, [line 399](../../../../../../../backend/src/sro/application/induction/diff.py#L399): Comment

Code: `pairs = align(run_a, run_b)`

> Every index below -- a difference's step, a parameter's source -- counts
> paired steps, not the steps of either recording. Handing the raw runs to
> _find_source would look up "step 4" in a run whose step 4 is somebody's
> second click on a label.

## `parameterise`, [line 403](../../../../../../../backend/src/sro/application/induction/diff.py#L403): Comment

Code: `groups: dict[tuple[str, str, str | None, Site | None], list[Difference]] = {}`

> Grouped by value pair: an order number in the URL, the body and a
> confirmation field is one parameter with three sites, not three that agree.
>
> Verbatim between one site and another. Tidying exists to join a keystroke
> to the site it filled -- a form is allowed to change what it was given on
> the way out, so `twoTEST` typed and `TWOTEST` sent are one value -- and
> between two body sites there is no keystroke and nothing to see through.
> Both texts are what the system stored. Case-folded, they merged fields the
> demonstrations proved differ: a `workArea` sent `TWOTEST` beside a `slug`
> sent `twotest` became one parameter, and the skill then sent `NEWAREA` as
> the slug both runs showed lowercased.
>
> Keyed on the absent form too, because two fields nobody filled look
> identical without it: both tidy to `""`, so a Delta Priority the form
> nulls and a Distance Threshold it empties became one parameter with one
> absent form -- whichever site came first -- and the other field was then
> sent that form, unquoted, on every run. An absence is not a value, and
> two sites that disagree about what theirs looks like are not one value.
>
> And keyed on the site itself wherever there is an absent form, which is
> to say wherever only one run filled the field. Two body keys really can
> hold one value -- Blue Yonder's adjust payload sends the detail number as
> both `lpn` and `detailNumber` -- and what says so is both runs agreeing at
> both keys, twice, with two different values. An optional field agrees only
> once: the other side of its pair is an absence, and every skipped field's
> absence looks the same. So a Delta Priority and a Distance Threshold that
> both happened to carry 1 in the run that filled them, and null in the run
> that did not, matched on the whole key and became one parameter --
> supplying 7 wrote 7 to both fields and typed it into both boxes, on the
> strength of one coincidence.

## `parameterise`, [line 414](../../../../../../../backend/src/sro/application/induction/diff.py#L414): Comment

Code: `for formless in [`

> Keying on the site, though, splits one field that is sent in two places:
> a form that puts Delta Priority in the query string *and* the body sends
> `?deltaPriority=1` beside `{"deltaPriority":1}`, and only the body leaf
> carries an absent form -- a query string has no way to say `null`. Split,
> the URL site became a second, *required* parameter, and supplying 7 sent
> `?deltaPriority=7` with a body still carrying `"deltaPriority":null`.
>
> So a site with no form of its own rejoins the one that has one, when they
> agree on both values verbatim and there is exactly one such candidate.
> Verbatim because between two non-keystroke sites there is no form tidying
> anything, and exactly one because two candidates is real ambiguity.
>
> And when they name the same field. Agreeing on the value pair says only
> that two sites carried the same two values; `?deltaPriority=1` beside a
> body `{"distanceThreshold":1}`, nulled in the other run, agrees on both
> and names two different fields, so the rejoin welded them into one
> parameter and supplying 7 wrote 7 to a field nobody supplied. Where the
> names differ -- or where a site names nothing at all, a path segment or a
> whole text body -- there is no join, and the URL half comes out required
> for a field the body half calls optional. That trade is deliberate:
> refusing to merge costs an operator one extra prompt, merging wrongly
> writes to a field nobody asked about.

## `parameterise`, [line 417](../../../../../../../backend/src/sro/application/induction/diff.py#L417): Comment

Code: `named = {_key_of(difference.site) for difference in groups[formless]}`

> A set because a formless group can already hold several sites -- two
> body keys the runs proved hold one value -- and a group that spans
> two field names has none to match on.

## `parameterise`, [line 429](../../../../../../../backend/src/sro/application/induction/diff.py#L429): Comment

Code: `for typed_key in [key for key in groups if isinstance(key[3], ActionValueSite)]:`

> And here is where tidying is spent: a keystroke joins the one site whose
> value it tidies to. It has to be exactly one -- typing that fits two
> fields fits neither, the same rule `binding` already holds itself to.
>
> Joined rather than keyed together, because a keystroke carries no absent
> form -- only a body leaf does -- and keying on that alone separated the
> typing that fills a field from the body site it fills: the field came out
> twice, required on the gesture path and optional on the network path, two
> answers for the one thing this whole decision exists to get right.

## `parameterise`, [line 445](../../../../../../../backend/src/sro/application/induction/diff.py#L445): Comment

Code: `value_a, value_b = named_by.value_a, named_by.value_b`

> The values the site that names the parameter saw. Whatever the form
> did to the keystroke, what the system stored is what this value is.

## `typed_values`, [line 520](../../../../../../../backend/src/sro/application/induction/diff.py#L520): Comment

Code: `name = deduplicate(suggest_name(site, url=request.url, field_label=label), already)`

> Not added to ``taken`` afterwards: two sites that suggest the
> same name are the same box, and merging them is the point.

## `_chosen_constants`, [line 556](../../../../../../../backend/src/sro/application/induction/diff.py#L556): Comment

Code: `listed = _listed_before(run_a, value, index)`

> Either run showing it on screen is enough. The second operator
> may have had the panel open already, or reached it by a route
> whose response the first one never fetched -- and a question that
> changes nothing until it is answered is cheap to ask and
> expensive to skip.

## `_inside_a_collection`, [line 588](../../../../../../../backend/src/sro/application/induction/diff.py#L588): Comment

Code: `return False`

> Routes have segments after them; a record is the end of the address.

## `_name_for`, [line 594](../../../../../../../backend/src/sro/application/induction/diff.py#L594): Comment

Code: `segments = url_path_segments(url)`

> Among several, the one named after the collection: an address record
> carries both `resourceId` and `addressId`, and only one of those means
> anything to somebody being asked which address to use.

## `_link_produced_values`, [line 618](../../../../../../../backend/src/sro/application/induction/diff.py#L618): Comment

Code: `named: dict[tuple[str, int, str], str] = {}`

> One value is one parameter, however many places the call sends it: an id
> in the path and the same id in the body is one thing the system produced.

## `_find_produced`, [line 669](../../../../../../../backend/src/sro/application/induction/diff.py#L669): Comment

Code: `continue`

> Row 44 of a lookup list. Position in a collection is not stable
> between one run and the next, so a value read from one was never
> a dependency -- it is the same value happening to sit in a list
> somebody scrolled past.

## `_build_parameter`, [line 739](../../../../../../../backend/src/sro/application/induction/diff.py#L739): Comment

Code: `is_the_body = any(isinstance(site.site, TextBodySite) for site in sites)`

> A body that is not JSON is parameterised whole, and a value going into
> one is the body rather than something inside it: nothing round it to
> escape into, and nothing round it to break out of either. Every other
> site kind here is a value inside something, which is the safe default.

## `_build_parameter`, [line 743](../../../../../../../backend/src/sro/application/induction/diff.py#L743): Comment

Code: `return Parameter(`

> Filled in one demonstration and left alone in the other: proof the
> field is optional, not just proof it varies. The empty side is not
> a second observed value -- nobody observed it, the form supplied it.

## `_build_parameter`, [line 750](../../../../../../../backend/src/sro/application/induction/diff.py#L750): Comment

Code: `observed_values=tuple(value for value in (value_a, value_b) if value),`

> Whichever sides were actually filled. An absence is not an
> observed value -- nobody observed it, the form supplied it --
> but where the pair both filled the field and a third doing is
> what proves it optional, both of theirs are real.

## `_build_parameter`, [line 752](../../../../../../../backend/src/sro/application/induction/diff.py#L752): Comment

Code: `unquoted_as=next(`

> What the run that filled it actually sent, carried through to
> execution: an unquoted slot holds JSON, so a value going into
> one has to be the type the demonstration proved it holds.

## `_build_parameter`, [line 767](../../../../../../../backend/src/sro/application/induction/diff.py#L767): Comment

Code: `described += f", {rewrite.said_plainly()}"`

> Said in the description because a reviewer approving a write has to be
> able to disagree with it: "produced by step 0" reads as verbatim, and
> a value silently reformatted on the way is exactly the kind of thing
> somebody should be able to catch by eye.

## `_diff_request`, [line 814](../../../../../../../backend/src/sro/application/induction/diff.py#L814): Comment

Code: `lonely = request_a or request_b`

> One run fetched something the other did not. Whether that matters
> depends entirely on what it was.

## `_diff_request`, [line 811](../../../../../../../backend/src/sro/application/induction/diff.py#L811): Comment

Code: `return []`

> A read. The second demonstration of a task does not refetch what
> the browser still has, and refusing the pair over a cache made
> the operator record the whole task again to no purpose -- the
> writes were identical both times. The step is kept; there is
> simply nothing to diff at it.

## `_is_a_clock`, [line 900](../../../../../../../backend/src/sro/application/induction/diff.py#L900): Inline

Code: `recent = range(1_600_000_000_000, 4_000_000_000_000)`

> 2020 to 2096, in millis

## `_diff_body`, [line 925](../../../../../../../backend/src/sro/application/induction/diff.py#L925): Comment

Code: `return [Difference(step_index=index, site=TextBodySite(), value_a=body_a, value_b=body_b)]`

> Form-encoded or plain text: the whole body becomes one parameter.
> Coarse, but better than a confident mis-parse of a format we do not model.

## `_diff_body`, [line 941](../../../../../../../backend/src/sro/application/induction/diff.py#L941): Comment

Code: `continue`

> `null` in one run and `""` in the other: two spellings of nobody
> filling the field, whose string forms differ, so the test above
> let them through. Nothing varies here. Called a difference, this
> became a required parameter with two empty observed values --
> nothing an operator could sensibly supply, and refusing every run
> that left it out, which is every honest run.

## `_diff_body`, [line 949](../../../../../../../backend/src/sro/application/induction/diff.py#L949): Comment

Code: `value_a="" if empty_a else str(leaf_a),`

> An absence is not a value, so it is not offered as one: the
> side that filled the field is what an operator is shown.

## `_diff_body`, [line 951](../../../../../../../backend/src/sro/application/induction/diff.py#L951): Comment

Code: `absent_as=_absent_form(leaf_a if empty_a else leaf_b)`

> From the pair where the pair shows it, and otherwise from
> whichever other doing of this task left the field empty.
> Either way it is read off a write that actually sent it.

## `_find_source`, [line 993](../../../../../../../backend/src/sro/application/induction/diff.py#L993): Comment

Code: `leaves_b = {pointer: str(leaf) for pointer, leaf in _response_leaves(run_b[step_index])}`

> Every call the gesture made, not its "primary" one: a Save that
> created a record and then addressed it answers twice, and the id
> the next step needs is in whichever of those the frame did not
> rank first.

## `_find_source`, [line 1002](../../../../../../../backend/src/sro/application/induction/diff.py#L1002): Comment

Code: `rewrite = discover(source_a, value_a)`

> Read off this run, then required to explain the other one --
> from the same place in the same response. A rule that fits one
> pair fits a great many pairs; a rule that fits both, where the
> two runs sent different values, is what the task does.
