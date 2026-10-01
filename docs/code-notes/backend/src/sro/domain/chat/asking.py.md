# Notes for `backend/src/sro/domain/chat/asking.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/asking.py`](../../../../../../../backend/src/sro/domain/chat/asking.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/asking.py#L1): Docstring

> Asking for what a job still needs, one question at a time.
>
> A job is offered as a decision: *"Create a Customer Type — want me to do it?"*
> The press means yes, and after it the run goes and looks for whatever nobody
> typed -- in the mail that asked for the job, and in time in the systems
> themselves. Mostly it finds them. When it does not, the run has a choice
> between two bad answers and this module is the third one.
>
> The two bad answers, both of which this system has shipped:
>
> **Boxes on the card.** One text input per declared parameter, drawn before
> anybody knows whether a value is needed at all, and the press disabled until
> they are full. It asks everybody for what it usually finds by itself, and on
> `Create a Customer Type` it asked four times for two values, because that job
> declares each field twice -- the label a person reads and the body key a form
> posts.
>
> **Stopping.** "nobody gave a value for X, and your mail does not say either."
> True, and the end of it: the operator starts over, and the run that knew
> everything except one word is gone.
>
> So the third answer is a conversation. The run ends, and what it could not
> find becomes a question in the operator's own thread -- one question, for one
> value, in words. They answer, the next question comes, and when the last one
> lands the job runs with the full set and the press they already gave.
>
> **The state is the thread.** Not a session, not a row: every question carries
> what is established so far and what is still missing, so the answer to it is
> readable off the last thing the assistant said. An operator who answers two
> questions over five minutes does not depend on a process staying up, and a
> second browser reading the same thread sees the same state.
>
> Pure: given the messages, say what is being waited on. Nothing here reads a
> clock, a repository or a model.

## module, [line 17](../../../../../../../backend/src/sro/domain/chat/asking.py#L17): Note on the line above

Code: `NEEDS = "needs_values"`

> The decision kind of a question waiting on a value. Named here because two
> sides read it: the door that writes it and the panel that draws it.

## module, [line 19](../../../../../../../backend/src/sro/domain/chat/asking.py#L19): Note on the line above

Code: `JOB = "job"`

> The decision kind of a job this conversation has offered to do. The panel
> builds its card from one; a sentence agreeing with one starts it.

## module, [line 21](../../../../../../../backend/src/sro/domain/chat/asking.py#L21): Note on the line above

Code: `SAID_YES = frozenset(`

> Answers that mean "the thing you just offered".
>
> Measured on the deployment, 2026-09-17 at 03:17. The assistant said "Create a
> Customer Type does that -- say the word and I will run it", the operator said
> "pls do", and the reply was "Nothing has been taught for that": the sentence
> went to the skills resolver, which had never heard of it, because nothing was
> holding on to what had just been offered. A system that asks for a word and
> then does not know the word is worse than one that never asked.
>
> Matched whole and lowercased, like `LET_GO`. "do it" is a yes; "do it for the
> red ones instead" is a new sentence and is placed as one.

## module, [line 46](../../../../../../../backend/src/sro/domain/chat/asking.py#L46): Note on the line above

Code: `K_SAID = 200`

> How much of one answer is taken as a value. A parameter is a customer type
> or a description, and a paragraph pasted into the panel is somebody talking,
> not a field. Long enough for a description, short enough that a mail body
> pasted whole cannot become a warehouse record.

## module, [line 48](../../../../../../../backend/src/sro/domain/chat/asking.py#L48): Note on the line above

Code: `LET_GO = frozenset(`

> Answers that are not values. Without this "no" becomes the customer type.
>
> Matched whole and lowercased, never by substring: "no" is a refusal and
> "NORTH DOCK" is a dock. A sentence that merely contains one of these words is
> a value -- an operator who means to stop can say the word by itself, and a run
> refused because a description said "leave it in receiving" is worse than one
> question too many.

## module, [line 266](../../../../../../../backend/src/sro/domain/chat/asking.py#L266): Note on the line above

Code: `K_SHOWN = 90`

> How much of an established value the opening repeats back.
>
> Enough to recognise a request by, not enough to fill the panel: a description
> may hold two thousand characters and a person checking which job this is about
> needs the first line of it.

## `Pending`, [line 65](../../../../../../../backend/src/sro/domain/chat/asking.py#L65): Docstring

> A job that has been said yes to and is short of values.
>
> `values` is everything established so far, `missing` what is still to ask
> about, in the order it will be asked. `items` rides along untouched: a job
> done once per thing in a list is still that job, and the values asked for
> here are the ones shared across all of them.

## `Pending`, [line 72](../../../../../../../backend/src/sro/domain/chat/asking.py#L72): Note on the line above

Code: `can_find: bool = False`

> Whether a run of this job can go and look for what is missing. On an
> offer it decides what a yes means: start it and let the run find them, or
> ask for the first one here.

## `Pending`, [line 74](../../../../../../../backend/src/sro/domain/chat/asking.py#L74): Note on the line above

Code: `mail_thread: str = ""`

> The outside conversation this job was asked for in, where there is one.
>
> Carried so the run an ANSWER starts is findable by a reply to that mail,
> the same as one a press starts. Without it the two doors disagree about
> something a person cannot see: press the card and the run answers to the
> thread, answer the question and it answers to nobody -- and 3.2 exists
> precisely so the person who knows the missing value, who is usually
> whoever sent the request, can say it where they are.

## `Pending`, [line 76](../../../../../../../backend/src/sro/domain/chat/asking.py#L76): Note on the line above

Code: `offered: tuple[tuple[str, str], ...] = ()`

> Fields this job can fill that the page does not ask for, and what each
> held last time.
>
> Since 2026-09-22 an optional field no longer stops a run -- see
> `LearnedParameter.required` -- and the step that fills it is skipped where
> nothing was given for it. Skipping it silently is the other half of the
> old mistake: the operator is never told the job could have set Department,
> so a field they DID want goes unfilled and nothing on the screen says it
> was ever possible.
>
> Said once, in the opening, with what it was last time so the offer is
> answerable without going to look. Not asked for one at a time: they are
> optional, and four questions nobody has to answer is how a person learns
> to type "no" without reading.
>
> An answer arrives through the door that already exists -- "Department: IN"
> is taken by the same path that takes any named value -- so nothing here
> needs a new kind of reply.

## `Pending`, [line 78](../../../../../../../backend/src/sro/domain/chat/asking.py#L78): Note on the line above

Code: `from_step: int = 0`

> Which step of the job the run that asked this had reached.
>
> A run that comes up short ENDS -- it must, because a write with a blank in
> it is a wrong record -- and the answer starts another one. Starting that
> one at step 0 re-walks everything the first one did: on `Create a Customer
> Type` it re-opens the mail, re-navigates, presses Add again and re-types
> both fields, to reach the box it stopped in front of.
>
> So the run says where it stopped and the next one begins there. Safe by
> construction rather than by hope: `run.needs` is set only at the two
> truncation stops and by a gather that came back short, and all three
> happen BEFORE the step's command goes out. The step named here is one that
> did not complete, every step under it did, and every step over it never
> ran -- which is exactly what `from_step` means.
>
> Zero for a question asked about an OFFER, which has no run behind it yet
> and nothing to resume.

## `Pending`, [line 80](../../../../../../../backend/src/sro/domain/chat/asking.py#L80): Note on the line above

Code: `limits: Mapping[str, int] = field(default_factory=dict)`

> What the box behind a name will hold, where anything knows.
>
> Carried so the question can say WHY it is being asked. A person sent a
> value, it will not fit, and "What should Customer Type be?" gets the same
> ten characters back -- they have no way to know the box takes four, because
> the browser truncates in silence and nothing else has said so.
>
> It is also what makes the asking a loop rather than one question: an answer
> that still will not fit is not an answer, and `answered` keeps asking.
> Empty for every name nothing has measured or documented, which is most.

## `Pending`, [line 84](../../../../../../../backend/src/sro/domain/chat/asking.py#L84): Note on the line above

Code: `options: Mapping[str, tuple[str, ...]] = field(default_factory=dict)`

> The choices each asked-for box offers, where the screen showed a list
> (C2's `FieldLimits.options`). Carried beside `limits` so the one
> question can say both for every field it asks (F1), and so an answer
> that is not one of them is refused as R1's reader refuses it.

## `Pending`, [line 86](../../../../../../../backend/src/sro/domain/chat/asking.py#L86): Note on the line above

Code: `dropped: tuple[str, ...] = ()`

> Fields the operator said they do not have in this thread -- "don't
> have X", "skip X", "run with what we have" (F1). Stored on every
> decision this state writes (`asking_state`, the job decision, the
> note), so `still_to_ask` finds it in the thread and X is never asked
> for or offered again there. thr_c563: "i dont have manufature just run
> whatever we have", and the assistant asked for Manufacturer again.

## `Pending`, [line 88](../../../../../../../backend/src/sro/domain/chat/asking.py#L88): Note on the line above

Code: `without: tuple[str, ...] = ()`

> The REQUIRED fields among `dropped`. The job cannot run without them,
> so the ask ends with `cannot_without`'s note instead of a question --
> it never loops -- and `ready` is false while any is named here.

## `Pending`, [line 90](../../../../../../../backend/src/sro/domain/chat/asking.py#L90): Note on the line above

Code: `refused: Mapping[str, str] = field(default_factory=dict)`

> What the last answer offered that R1's checks turned down, and why --
> for the reply that says so. Not state: never written to a decision.

## `question`, [line 143](../../../../../../../backend/src/sro/domain/chat/asking.py#L143): Docstring

> The question, in words rather than as a field name and a box.
>
> The name as the job declares it, because that is the word the operator
> will see again on the form and in the record. A prettier rendering of
> `customertype-longDescription` would be this system choosing a name for a
> field somebody else named.
>
> And the limit where there is one, because the two things that bring a job
> here want two different questions. A value nobody could find is "what
> should X be?". A value that will not fit is a person who HAS an answer and
> has been given no reason to change it: asked the first way they send the
> same ten characters back, and the loop is one nobody can get out of.
>
> Every missing REQUIRED field in ONE question, each with its limits and
> options (F1; greyorange QA 2026-09-27: 44% of assistant turns asked for a
> value one field at a time). One field keeps the short form every earlier
> surface used; several are listed together with how to name each in one
> reply. Optional
> fields are never here: `also_set` offers them once, in the opening.

## `asks`, [line 169](../../../../../../../backend/src/sro/domain/chat/asking.py#L169): Docstring

> The question's shape as data: every field it asks for, each with its
> limit and options, in the order asked. Carried on the decision as
> `asks`; the panel's one-form drawing (design 3) is drawn from it.

## `asking_state`, [line 180](../../../../../../../backend/src/sro/domain/chat/asking.py#L180): Docstring

> What a NEEDS decision carries beyond the fields every writer already
> wrote: the shape (`asks`), what is still offered (so a later reply can
> still fill it, though it is never offered in words again), what was
> dropped, and the options. Keys empty for this ask are left out, so a
> decision with nothing new reads as it always did.

## `turned_down`, [line 196](../../../../../../../backend/src/sro/domain/chat/asking.py#L196): Docstring

> Why each value in the last reply was not taken, said before the
> question that asks for it again -- R1's own reasons (`request.refusal`).

## `cannot_without`, [line 212](../../../../../../../backend/src/sro/domain/chat/asking.py#L212): Docstring

> The note that ends an ask for a required field the operator does not
> have (F1): says the job cannot run without it and how to start it again
> ("ask for … again"), and is not a question, so `pending_job` finds
> nothing waiting and nothing loops. It keeps the values the ask had so far
> (F1 round 1, M1) and `dropped`.
>
> `ran`: said by the run's own ask (`StartWorkflowRun.ask_for_values`),
> where a run DID start and stopped -- "stopped — it needs X to run" --
> rather than "nothing was started", which would be false there (I4).

## `still_to_ask`, [line 233](../../../../../../../backend/src/sro/domain/chat/asking.py#L233): Docstring

> The run's own ask, continued from the ask whose answer started that run
> -- and from no other (F1 round 1, I3: a drop is final for THIS ask
> only). The link is structural: the thread's latest decision about this
> job is a `resume` job decision holding exactly the values the run was
> started with. Then that ask's drops hold (a required one moves to
> `without`) and nothing is offered again: it was offered once, in that
> ask's opening. Anything else -- a card press, a "yes", a new request, a
> run with other values -- is a fresh ask, and returns `pending` as it is.
>
> ponytail: the run-to-ask attribution is by values, because the run row
> carries no link to the ask whose answer started it. Ceiling: a run started
> outside this thread with byte-identical values, while that ask's `resume`
> decision is still the thread's latest about the job, inherits that ask's
> drops (it is not offered the optional fields again, and a dropped field it
> needs ends with the note). Upgrade path: carry the answer's offer id (the
> `resume` decision's `offer`) onto the run when a migration is next allowed,
> and match on it here instead of on values.

## `unusable`, [line 258](../../../../../../../backend/src/sro/domain/chat/asking.py#L258): Docstring

> Names holding a value the box will not take, in the order given.
>
> A value that will not fit is not a value. It is as outstanding as a name
> nobody supplied at all -- more so, because the person believes they have
> already answered it -- and the only difference is what the question has to
> say to get a usable answer back.
>
> The run path has always folded these together: `_too_long_for` puts the
> names on `run.needs` beside the ones nothing could find, and one question
> loop handles both. This is the same rule for an offer, which has not run
> and so has no `needs` of its own to put them on.

## `opening`, [line 269](../../../../../../../backend/src/sro/domain/chat/asking.py#L269): Docstring

> The first thing said when a job is taken up but cannot yet run.
>
> The question alone is `Customer Type takes 4 characters. What should it
> be?`, and in a conversation that is a sentence with no subject. The card it
> came from said which request it was about, what had been read out of the
> mail, and what would not fit -- and then handed over to a thread that knew
> none of it. Somebody who steps away for a minute comes back to a bare
> question about a field, with four identical-looking ones above it.
>
> So the opening carries what the card carried: which job, which request
> where there is one to name, what is already established, and what is being
> asked for -- and then the question itself, which every answer after this
> one gets on its own.
>
> `about` is what the request was called. Empty for a job nobody named --
> a press on a page rather than a mail -- and the sentence simply does not
> claim one.

## `also_set`, [line 333](../../../../../../../backend/src/sro/domain/chat/asking.py#L333): Docstring

> What this job could ALSO fill, which nothing has to answer.
>
> Public because two doors ask the same question in different words and both
> have to make the same offer: `opening` for a job taken up from an offer,
> and `ask_for_values` for a run that got half way and came up short. A
> sentence written twice is a sentence that drifts, and the drift here would
> be one door telling an operator about Department and the other not.
>
> Empty where there is nothing to offer, so a caller can append it without
> asking.

## `_listed`, [line 344](../../../../../../../backend/src/sro/domain/chat/asking.py#L344): Docstring

> `a`, `a and b`, `a, b and c`. A comma before the last is how a list of
> two reads as a list of three.

## `_last_time`, [line 350](../../../../../../../backend/src/sro/domain/chat/asking.py#L350): Docstring

> What each was last time, where anything was. An offer a person cannot
> answer without going to look at the last record is an offer they decline.

## `shortened`, [line 355](../../../../../../../backend/src/sro/domain/chat/asking.py#L355): Docstring

> One value, trimmed to something a sentence can carry. Named rather than
> private because the mail to the asker renders the same values and must trim
> them the same way -- two answers to "how much of this do we repeat back"
> is how one surface quotes a paragraph and another quotes a line.

## `too_long_for`, [line 364](../../../../../../../backend/src/sro/domain/chat/asking.py#L364): Docstring

> The limit this answer breaks, or None if it fits.
>
> Only for a bare reply: one that names its fields ("X: …") or says what
> it does not have is not one value, and its values are measured one by
> one in `answered`.
>
> Measured on the value as it will be TAKEN -- trimmed and cut to `K_SAID` --
> rather than as it was typed, so the answer this reports on is the one that
> would be sent.

## `pending_job`, [line 478](../../../../../../../backend/src/sro/domain/chat/asking.py#L478): Docstring

> What the conversation is waiting on, or None.
>
> The LAST thing the assistant decided, and only that. Each answer produces a
> new decision carrying the remaining questions, so the most recent one is
> the whole state -- and a thread that went on to talk about something else
> has a newer decision that is not a question, which ends the waiting exactly
> as it should. Reading further back would let a job abandoned twenty minutes
> ago claim the next sentence somebody typed.

## `_pairs`, [line 521](../../../../../../../backend/src/sro/domain/chat/asking.py#L521): Docstring

> The offered fields as the decision stores them: a list of two-item
> lists, because JSON has no tuples. Anything else is nothing -- an offer
> read out of a shape nobody wrote is an offer to fill a field that may not
> exist.

## `_step`, [line 531](../../../../../../../backend/src/sro/domain/chat/asking.py#L531): Docstring

> Which step a stored decision names, or 0. A bool is an int in Python and
> `from_step: true` would otherwise resume a job at its second step.

## `_numbers`, [line 537](../../../../../../../backend/src/sro/domain/chat/asking.py#L537): Docstring

> A decision's limits, as whole numbers. JSON off a row, so anything that
> is not a usable count is not one -- a bool is an int in Python, and
> `limits: {"Code": true}` would otherwise read as a one-character field.

## `_strings`, [line 547](../../../../../../../backend/src/sro/domain/chat/asking.py#L547): Docstring

> A decision's mapping, as strings. A decision is JSON off a row and its
> values are `object` to anything reading it honestly.

## `let_go`, [line 551](../../../../../../../backend/src/sro/domain/chat/asking.py#L551): Docstring

> Whether that answer was somebody calling it off.

## `said_yes`, [line 555](../../../../../../../backend/src/sro/domain/chat/asking.py#L555): Docstring

> Whether that sentence agrees with what was just offered.

## `_plainly`, [line 559](../../../../../../../backend/src/sro/domain/chat/asking.py#L559): Docstring

> One answer, as it is matched: lowercased, without the punctuation
> somebody types around a short word.

## `_items`, [line 563](../../../../../../../backend/src/sro/domain/chat/asking.py#L563): Docstring

> The things a job would be done for, as strings. A decision is JSON off a
> row, so its `items` is `object` to anything reading it honestly.

## `offered_job`, [line 567](../../../../../../../backend/src/sro/domain/chat/asking.py#L567): Docstring

> The job this conversation has just offered to do, if it is still the
> last thing said.
>
> The same reading as `pending_job` and for the same reason: the newest
> assistant decision is the whole state, so a job offered twenty minutes ago
> and talked past cannot claim the next sentence. A question waiting on a
> value is NOT one of these -- `pending_job` owns that, and a sentence there
> is the value rather than a yes.

## module, [line 587](../../../../../../../backend/src/sro/domain/chat/asking.py#L587): Note on the line above

Code: `K_WITH_WHAT_WE_HAVE = re.compile(`

> "run with what we have", "go with whatever we've got": everything this
> ask still wants and the reply did not fill is dropped (F1). A verb must
> come first: "let me check what we have" and "also check what I have in
> stock" are not drops (F1 round 1, C1). Read after the reply's named
> values, so "Customer Type: RRF, run with what we have" keeps RRF.

## module, [line 592](../../../../../../../backend/src/sro/domain/chat/asking.py#L592): Note on the line above

Code: `K_DROP = re.compile(`

> The only drop phrases (F1 round 1, C1): "don't have X", "skip X",
> "without X". Searched inside one clause; X is the rest of that clause,
> cut at "just", "but", "so", "then" (`K_WHAT_ENDS`). X drops a field only
> when `_field` names one plainly; where it could be several fields, the
> operator is asked which (`which`). A phrase naming no field drops
> nothing, so "skip the queue at dock 4" is still a description -- except
> a bare pronoun ("skip it"), which is a holding reply, not a value.

## module, [line 620](../../../../../../../backend/src/sro/domain/chat/asking.py#L620): Note on the line above

Code: `K_LIKE = 0.8`

> How alike a typed name must be to a field's name to be that field, word
> by word (`_score`): thr_c563 typed "manufature" for Manufacturer (0.91).
> It holds only when exactly one field scores this high and beats the
> runner-up by `K_MARGIN` (F1 round 1, C2); a tie is asked about. Word by
> word, so "ship from code" is never Ship To Code (one word differs), and a
> name with a different number of words never matches -- "code" is not Zip
> Code. Stdlib `difflib`, no dependency.

## `_read`, [line 750](../../../../../../../backend/src/sro/domain/chat/asking.py#L750): Docstring

> The reply, clause by clause, with every value cut from the ORIGINAL text by
> position (F1 round 2, item 9). A clause ends at a comma, semicolon, full
> stop or " and " (`K_CLAUSE`), but a named value is never cut silently: the
> next clause ends it only when that clause starts something of THIS ask
> (`_starts`) -- a label `_field` resolves to one of its fields, a drop
> phrase naming one, or "run with what we have". Otherwise the clause is
> joined back onto the value with its separator, so "black and white",
> "12 Main St, Springfield", "5 St. Louis Ave" and "Retail, wholesale and
> export" stay whole.
>
> One rule decides the join (F1 round 3, items 7-9): `_starts` is true
> whenever this function would act on the clause -- a label `_label_of`
> resolves OR finds near, a drop naming a field, a holding / not-ready
> phrase ("i don't have X yet"), or "with what we have". Such a clause is
> never joined onto the value before it.
>
> Inside a named value only a first-person "don't have X" (`K_FIRST_PERSON`)
> ends it and drops X ("Customer Type: RRF i dont have manufacturer"). A
> "skip X" / "without X" there that names a field of this ask EXACTLY is
> asked about once -- "Did you mean to skip X, or is it part of the
> value?" (item 10a): the value is not written, X is remembered on the ask
> (`doubted`), and the same words again are the value. Naming no field
> ("sold without labels"), it is simply the value. A "Name:"
> label counts only at a clause start (M3). A label is asked about only when
> it is close to a field of this ask or names another field of the job
> (`_label_of`, item 12); any other "Word:" is text, so with one field open
> "Attn: Bob, 5 Main St" is that field's value. Names resolve through the
> job's labels and R2's aliases first (`request.field_of`, via
> `Pending.known`; I1). A question is read by nothing here: it goes to the
> reader.

## `named_in`, [line 823](../../../../../../../backend/src/sro/domain/chat/asking.py#L823): Docstring

> Whether the reply says what it is: a named value, a drop, "run with what
> we have", or a label to ask about. Such a reply needs no model to read it
> (`Converse._is_it_an_answer`). Anything else -- another task, a lookup,
> "don't know", "let me check" -- goes to the reader (F1 round 1, C1).

## `answered`, [line 840](../../../../../../../backend/src/sro/domain/chat/asking.py#L840): Docstring

> The same job with this answer in it, and the next question outstanding.
>
> One reply can fill several fields (F1): every named value is taken, each
> checked on its own with R1's checks (quote, limits and options, logins),
> offered fields included. A bare reply fills the one field asked for; with
> several missing it is taken only when it is an allowed option of exactly
> one of them, and is otherwise asked about with names (F1 round 1, C3). A
> holding reply ("don't know", "not yet", "let me check", "skip it") takes
> nothing. What the reply says it does not have is dropped: out of
> `missing` and `offered`, into `dropped`, and -- where it was required --
> into `without`. `confirmed` goes back to true as it always did.
>
> The old twin rule (a name filling every name that ends with it) is gone
> (F1 round 1, C2): it let "Code: 123" fill Zip Code. A job still carrying
> two names for one field is asked for both.

## `Pending.asking_for`, [line 105](../../../../../../../backend/src/sro/domain/chat/asking.py#L105): Docstring

> The one value this question is about.

## `opening`, [line 271](../../../../../../../backend/src/sro/domain/chat/asking.py#L271): Comment

Code: `for name in pending.missing:`

> What was supplied and will not fit is a different sentence from what was
> never supplied, and running them together is how somebody re-sends the
> value they already sent.

## `opening`, [line 275](../../../../../../../backend/src/sro/domain/chat/asking.py#L275): Comment

Code: `if also := also_set(pending):`

> What it could also set, once, before the question it must have answered.
>
> Before rather than after, because the question is what the next sentence
> answers and a question buried above an offer gets the offer's answer.

## `answered`, [line 857](../../../../../../../backend/src/sro/domain/chat/asking.py#L857): Comment

Code: `if (why := refusal(one, value, _limits(pending, name), logins))`

> Each value in the reply is checked on its own (invariant 14): the one
> refused stays missing, with its reason in `refused`, and the others are
> taken. An answer the box still will not hold, is not one of its options,
> or is the operator's own recorded sign-in name, leaves that field's
> question standing. The reader's own check
> (`request.refusal`), so a bare "RKUCHIYAGM" typed under a pending Address
> question is refused in chat as it is in a mail (thr_163b; R1 review, I5).
>
> The alternative is accepting it and stopping the run in front of the
> form, which is the whole of what asking here was meant to replace: the
> person is at the keyboard, and telling them NOW costs one more sentence
> where telling them later costs the job.

## `should_we`, [line 284](../../../../../../../backend/src/sro/domain/chat/asking.py#L284): Note

Code: `said.append(f"You sent this to {_listed(list(sent_to))}.")`

> The recipients first, because they are why the request was not simply run:
> the operator asked somebody else to do it, and the question is whether this
> system should do it instead.

## `offered_job`, [line 583](../../../../../../../backend/src/sro/domain/chat/asking.py#L583): Note

Code: `mail_thread=str(decision.get("mail_thread") or ""),`

> Carried so a yes to a request read from mail starts a run a reply on that
> mail's thread can find, as a press on the card would.

## `asked_under`, [line 373](../../../../../../../backend/src/sro/domain/chat/asking.py#L373): Note

Code: `def asked_under(messages: Sequence[Message], answering: str | None = None) -> Message | None:`

> The one lookup `pending_job` and `offered_job` share: the question an answer
> is bound to. With no id -- a sentence typed into the box -- it is the newest
> assistant decision, as it always was, so a conversation that moved on is not
> waiting on anything. With an id -- a press under a question -- it is that
> message, and only while it is still open: a later assistant decision on the
> same offer (same job, same mail thread: an answer, a re-ask, a run started or
> a question left) closes it. So a press under an older question acts on that
> question's offer, never on the newest one, and a press under a closed
> question resolves to nothing, which the door refuses.

## `offered_job`, [line 572](../../../../../../../backend/src/sro/domain/chat/asking.py#L572): Note

Code: `if decision.get("resume"):`

> A `resume` decision is a run already started, not an offer: a second "yes"
> under it would start the same job again.

## `waiting_on_mail`, [line 411](../../../../../../../backend/src/sro/domain/chat/asking.py#L411): Note

Code: `return pending_job(messages, last.id.value) if last is not None else None`

> The question a mail reply on `mail_thread` answers: the newest decision
> about that mail conversation, resolved through `asked_under` like any bound
> answer, so a reply answers the question asked on its own thread even when a
> question about another mail came after it.

## `of_the_offer`, [line 290](../../../../../../../backend/src/sro/domain/chat/asking.py#L290): Docstring

> What a standing offer is waiting on, for a person who asked about it rather
> than answering it (F2). Words only: the conversation route writes it with no
> decision, so the offer it describes is still the last thing asked and a yes
> still lands in it. Only offers: a standing question is answered about by
> `Converse.execute` asking it again, before anything reaches here.


## `the_request`, [line 450](../../../../../../../backend/src/sro/domain/chat/asking.py#L450): Docstring

> The operator's own words for the run a chat offer started (S4): the chain of
> assistant messages that led to this run's offer (`WorkflowRun.offer`) -- each
> a `job` or `needs_values` decision for this workflow with no mail thread,
> whose id is in the chain or whose `offer` points into it, following each
> `offer` back to the fresh offer that has none -- and the operator line
> directly before each: the request, answers to its questions, the yes.
>
> Anchored on the offer, never on the panel's `resume` flag (S4 round 1, I4):
> an older offer for the same job that nobody answered, pressed on a card, or
> walked past links to nothing here, so its words -- last week's, naming
> somebody else -- never join this run's request. Every continuation Converse
> writes carries the `offer` it continues (`_chained`).
>
> An offer that came from mail carries its `mail_thread`, and a run the mail
> door started records a mail key as its offer, so neither has a request here:
> a request relayed from mail is never the operator speaking.
