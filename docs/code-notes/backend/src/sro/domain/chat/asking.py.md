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

## module, [line 8](../../../../../../../backend/src/sro/domain/chat/asking.py#L8): Note on the line above

Code: `NEEDS = "needs_values"`

> The decision kind of a question waiting on a value. Named here because two
> sides read it: the door that writes it and the panel that draws it.

## module, [line 10](../../../../../../../backend/src/sro/domain/chat/asking.py#L10): Note on the line above

Code: `JOB = "job"`

> The decision kind of a job this conversation has offered to do. The panel
> builds its card from one; a sentence agreeing with one starts it.

## module, [line 12](../../../../../../../backend/src/sro/domain/chat/asking.py#L12): Note on the line above

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

## module, [line 37](../../../../../../../backend/src/sro/domain/chat/asking.py#L37): Note on the line above

Code: `K_SAID = 200`

> How much of one answer is taken as a value. A parameter is a customer type
> or a description, and a paragraph pasted into the panel is somebody talking,
> not a field. Long enough for a description, short enough that a mail body
> pasted whole cannot become a warehouse record.

## module, [line 39](../../../../../../../backend/src/sro/domain/chat/asking.py#L39): Note on the line above

Code: `LET_GO = frozenset(`

> Answers that are not values. Without this "no" becomes the customer type.
>
> Matched whole and lowercased, never by substring: "no" is a refusal and
> "NORTH DOCK" is a dock. A sentence that merely contains one of these words is
> a value -- an operator who means to stop can say the word by itself, and a run
> refused because a description said "leave it in receiving" is worse than one
> question too many.

## module, [line 98](../../../../../../../backend/src/sro/domain/chat/asking.py#L98): Note on the line above

Code: `K_SHOWN = 90`

> How much of an established value the opening repeats back.
>
> Enough to recognise a request by, not enough to fill the panel: a description
> may hold two thousand characters and a person checking which job this is about
> needs the first line of it.

## `Pending`, [line 56](../../../../../../../backend/src/sro/domain/chat/asking.py#L56): Docstring

> A job that has been said yes to and is short of values.
>
> `values` is everything established so far, `missing` what is still to ask
> about, in the order it will be asked. `items` rides along untouched: a job
> done once per thing in a list is still that job, and the values asked for
> here are the ones shared across all of them.

## `Pending`, [line 63](../../../../../../../backend/src/sro/domain/chat/asking.py#L63): Note on the line above

Code: `can_find: bool = False`

> Whether a run of this job can go and look for what is missing. On an
> offer it decides what a yes means: start it and let the run find them, or
> ask for the first one here.

## `Pending`, [line 65](../../../../../../../backend/src/sro/domain/chat/asking.py#L65): Note on the line above

Code: `mail_thread: str = ""`

> The outside conversation this job was asked for in, where there is one.
>
> Carried so the run an ANSWER starts is findable by a reply to that mail,
> the same as one a press starts. Without it the two doors disagree about
> something a person cannot see: press the card and the run answers to the
> thread, answer the question and it answers to nobody -- and 3.2 exists
> precisely so the person who knows the missing value, who is usually
> whoever sent the request, can say it where they are.

## `Pending`, [line 67](../../../../../../../backend/src/sro/domain/chat/asking.py#L67): Note on the line above

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

## `Pending`, [line 69](../../../../../../../backend/src/sro/domain/chat/asking.py#L69): Note on the line above

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

## `Pending`, [line 71](../../../../../../../backend/src/sro/domain/chat/asking.py#L71): Note on the line above

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

## `question`, [line 82](../../../../../../../backend/src/sro/domain/chat/asking.py#L82): Docstring

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

## `unusable`, [line 90](../../../../../../../backend/src/sro/domain/chat/asking.py#L90): Docstring

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

## `opening`, [line 101](../../../../../../../backend/src/sro/domain/chat/asking.py#L101): Docstring

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

## `also_set`, [line 120](../../../../../../../backend/src/sro/domain/chat/asking.py#L120): Docstring

> What this job could ALSO fill, which nothing has to answer.
>
> Public because two doors ask the same question in different words and both
> have to make the same offer: `opening` for a job taken up from an offer,
> and `_ask_for_values` for a run that got half way and came up short. A
> sentence written twice is a sentence that drifts, and the drift here would
> be one door telling an operator about Department and the other not.
>
> Empty where there is nothing to offer, so a caller can append it without
> asking.

## `_listed`, [line 131](../../../../../../../backend/src/sro/domain/chat/asking.py#L131): Docstring

> `a`, `a and b`, `a, b and c`. A comma before the last is how a list of
> two reads as a list of three.

## `_last_time`, [line 137](../../../../../../../backend/src/sro/domain/chat/asking.py#L137): Docstring

> What each was last time, where anything was. An offer a person cannot
> answer without going to look at the last record is an offer they decline.

## `shortened`, [line 142](../../../../../../../backend/src/sro/domain/chat/asking.py#L142): Docstring

> One value, trimmed to something a sentence can carry. Named rather than
> private because the mail to the asker renders the same values and must trim
> them the same way -- two answers to "how much of this do we repeat back"
> is how one surface quotes a paragraph and another quotes a line.

## `too_long_for`, [line 151](../../../../../../../backend/src/sro/domain/chat/asking.py#L151): Docstring

> The limit this answer breaks, or None if it fits.
>
> Measured on the value as it will be TAKEN -- trimmed and cut to `K_SAID` --
> rather than as it was typed, so the answer this reports on is the one that
> would be sent.

## `pending_job`, [line 158](../../../../../../../backend/src/sro/domain/chat/asking.py#L158): Docstring

> What the conversation is waiting on, or None.
>
> The LAST thing the assistant decided, and only that. Each answer produces a
> new decision carrying the remaining questions, so the most recent one is
> the whole state -- and a thread that went on to talk about something else
> has a newer decision that is not a question, which ends the waiting exactly
> as it should. Reading further back would let a job abandoned twenty minutes
> ago claim the next sentence somebody typed.

## `_pairs`, [line 185](../../../../../../../backend/src/sro/domain/chat/asking.py#L185): Docstring

> The offered fields as the decision stores them: a list of two-item
> lists, because JSON has no tuples. Anything else is nothing -- an offer
> read out of a shape nobody wrote is an offer to fill a field that may not
> exist.

## `_step`, [line 195](../../../../../../../backend/src/sro/domain/chat/asking.py#L195): Docstring

> Which step a stored decision names, or 0. A bool is an int in Python and
> `from_step: true` would otherwise resume a job at its second step.

## `_numbers`, [line 201](../../../../../../../backend/src/sro/domain/chat/asking.py#L201): Docstring

> A decision's limits, as whole numbers. JSON off a row, so anything that
> is not a usable count is not one -- a bool is an int in Python, and
> `limits: {"Code": true}` would otherwise read as a one-character field.

## `_strings`, [line 211](../../../../../../../backend/src/sro/domain/chat/asking.py#L211): Docstring

> A decision's mapping, as strings. A decision is JSON off a row and its
> values are `object` to anything reading it honestly.

## `let_go`, [line 215](../../../../../../../backend/src/sro/domain/chat/asking.py#L215): Docstring

> Whether that answer was somebody calling it off.

## `said_yes`, [line 219](../../../../../../../backend/src/sro/domain/chat/asking.py#L219): Docstring

> Whether that sentence agrees with what was just offered.

## `_plainly`, [line 223](../../../../../../../backend/src/sro/domain/chat/asking.py#L223): Docstring

> One answer, as it is matched: lowercased, without the punctuation
> somebody types around a short word.

## `_items`, [line 227](../../../../../../../backend/src/sro/domain/chat/asking.py#L227): Docstring

> The things a job would be done for, as strings. A decision is JSON off a
> row, so its `items` is `object` to anything reading it honestly.

## `offered_job`, [line 231](../../../../../../../backend/src/sro/domain/chat/asking.py#L231): Docstring

> The job this conversation has just offered to do, if it is still the
> last thing said.
>
> The same reading as `pending_job` and for the same reason: the newest
> assistant decision is the whole state, so a job offered twenty minutes ago
> and talked past cannot claim the next sentence. A question waiting on a
> value is NOT one of these -- `pending_job` owns that, and a sentence there
> is the value rather than a yes.

## `answered`, [line 251](../../../../../../../backend/src/sro/domain/chat/asking.py#L251): Docstring (debt)

> The same job with this answer in it, and the next question outstanding.
>
> The answer fills the name that was asked about **and every name that is
> that same field under another spelling**. `Create a Customer Type` declares
> `Customer Type` and `customertype-customerType`, which is one value and two
> parameters, and asking twice for one word is the form this conversation
> exists to replace.
>
> ponytail: the twin rule is a suffix match on the normalised names, and the
> defect behind it is fixed -- mining records every name a control answers to
> and folds the entries a job already has (`domain/skill/learned.py`). This
> stays for the jobs whose fold has not happened yet: a job is repaired by
> the next pass that recognises it, and until then its offer still carries
> two names for one field. Delete it once no stored job has a pair.

## `_twins`, [line 272](../../../../../../../backend/src/sro/domain/chat/asking.py#L272): Docstring

> The other names for the field just answered.
>
> `Customer Type` and `customertype-customerType` normalise to `customertype`
> and `customertypecustomertype`, and one ends with the other. Direction
> matters: the body key carries the form's name as a prefix, so the longer
> name ends with the shorter. Nothing matches when neither contains the
> other, which is the ordinary case of two unrelated fields.

## `Pending.asking_for`, [line 74](../../../../../../../backend/src/sro/domain/chat/asking.py#L74): Docstring

> The one value this question is about.

## `opening`, [line 110](../../../../../../../backend/src/sro/domain/chat/asking.py#L110): Comment

Code: `for name in pending.missing:`

> What was supplied and will not fit is a different sentence from what was
> never supplied, and running them together is how somebody re-sends the
> value they already sent.

## `opening`, [line 114](../../../../../../../backend/src/sro/domain/chat/asking.py#L114): Comment

Code: `if also := also_set(pending):`

> What it could also set, once, before the question it must have answered.
>
> Before rather than after, because the question is what the next sentence
> answers and a question buried above an offer gets the offer's answer.

## `answered`, [line 255](../../../../../../../backend/src/sro/domain/chat/asking.py#L255): Comment

Code: `if too_long_for(pending, said) is not None:`

> An answer the box still will not hold leaves the question standing.
>
> The alternative is accepting it and stopping the run in front of the
> form, which is the whole of what asking here was meant to replace: the
> person is at the keyboard, and telling them NOW costs one more sentence
> where telling them later costs the job.
