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

## module, [line 13](../../../../../../../backend/src/sro/domain/chat/asking.py#L13): Note on the line above

Code: `NEEDS = "needs_values"`

> The decision kind of a question waiting on a value. Named here because two
> sides read it: the door that writes it and the panel that draws it.

## module, [line 15](../../../../../../../backend/src/sro/domain/chat/asking.py#L15): Note on the line above

Code: `JOB = "job"`

> The decision kind of a job this conversation has offered to do. The panel
> builds its card from one; a sentence agreeing with one starts it.

## module, [line 17](../../../../../../../backend/src/sro/domain/chat/asking.py#L17): Note on the line above

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

## module, [line 42](../../../../../../../backend/src/sro/domain/chat/asking.py#L42): Note on the line above

Code: `K_SAID = 200`

> How much of one answer is taken as a value. A parameter is a customer type
> or a description, and a paragraph pasted into the panel is somebody talking,
> not a field. Long enough for a description, short enough that a mail body
> pasted whole cannot become a warehouse record.

## module, [line 44](../../../../../../../backend/src/sro/domain/chat/asking.py#L44): Note on the line above

Code: `LET_GO = frozenset(`

> Answers that are not values. Without this "no" becomes the customer type.
>
> Matched whole and lowercased, never by substring: "no" is a refusal and
> "NORTH DOCK" is a dock. A sentence that merely contains one of these words is
> a value -- an operator who means to stop can say the word by itself, and a run
> refused because a description said "leave it in receiving" is worse than one
> question too many.

## module, [line 205](../../../../../../../backend/src/sro/domain/chat/asking.py#L205): Note on the line above

Code: `K_SHOWN = 90`

> How much of an established value the opening repeats back.
>
> Enough to recognise a request by, not enough to fill the panel: a description
> may hold two thousand characters and a person checking which job this is about
> needs the first line of it.

## `Pending`, [line 61](../../../../../../../backend/src/sro/domain/chat/asking.py#L61): Docstring

> A job that has been said yes to and is short of values.
>
> `values` is everything established so far, `missing` what is still to ask
> about, in the order it will be asked. `items` rides along untouched: a job
> done once per thing in a list is still that job, and the values asked for
> here are the ones shared across all of them.

## `Pending`, [line 68](../../../../../../../backend/src/sro/domain/chat/asking.py#L68): Note on the line above

Code: `can_find: bool = False`

> Whether a run of this job can go and look for what is missing. On an
> offer it decides what a yes means: start it and let the run find them, or
> ask for the first one here.

## `Pending`, [line 70](../../../../../../../backend/src/sro/domain/chat/asking.py#L70): Note on the line above

Code: `mail_thread: str = ""`

> The outside conversation this job was asked for in, where there is one.
>
> Carried so the run an ANSWER starts is findable by a reply to that mail,
> the same as one a press starts. Without it the two doors disagree about
> something a person cannot see: press the card and the run answers to the
> thread, answer the question and it answers to nobody -- and 3.2 exists
> precisely so the person who knows the missing value, who is usually
> whoever sent the request, can say it where they are.

## `Pending`, [line 72](../../../../../../../backend/src/sro/domain/chat/asking.py#L72): Note on the line above

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

## `Pending`, [line 74](../../../../../../../backend/src/sro/domain/chat/asking.py#L74): Note on the line above

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

## `Pending`, [line 76](../../../../../../../backend/src/sro/domain/chat/asking.py#L76): Note on the line above

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

## `Pending`, [line 80](../../../../../../../backend/src/sro/domain/chat/asking.py#L80): Note on the line above

Code: `options: Mapping[str, tuple[str, ...]] = field(default_factory=dict)`

> The choices each asked-for box offers, where the screen showed a list
> (C2's `FieldLimits.options`). Carried beside `limits` so the one
> question can say both for every field it asks (F1), and so an answer
> that is not one of them is refused as R1's reader refuses it.

## `Pending`, [line 82](../../../../../../../backend/src/sro/domain/chat/asking.py#L82): Note on the line above

Code: `dropped: tuple[str, ...] = ()`

> Fields the operator said they do not have in this thread -- "don't
> have X", "skip X", "run with what we have" (F1). Stored on every
> decision this state writes (`asking_state`, the job decision, the
> note), so `still_to_ask` finds it in the thread and X is never asked
> for or offered again there. thr_c563: "i dont have manufature just run
> whatever we have", and the assistant asked for Manufacturer again.

## `Pending`, [line 84](../../../../../../../backend/src/sro/domain/chat/asking.py#L84): Note on the line above

Code: `without: tuple[str, ...] = ()`

> The REQUIRED fields among `dropped`. The job cannot run without them,
> so the ask ends with `cannot_without`'s note instead of a question --
> it never loops -- and `ready` is false while any is named here.

## `Pending`, [line 86](../../../../../../../backend/src/sro/domain/chat/asking.py#L86): Note on the line above

Code: `refused: Mapping[str, str] = field(default_factory=dict)`

> What the last answer offered that R1's checks turned down, and why --
> for the reply that says so. Not state: never written to a decision.

## `question`, [line 114](../../../../../../../backend/src/sro/domain/chat/asking.py#L114): Docstring

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
> reply. Two spellings of one field (`_twins`) are asked for once. Optional
> fields are never here: `also_set` offers them once, in the opening.

## `asks`, [line 130](../../../../../../../backend/src/sro/domain/chat/asking.py#L130): Docstring

> The question's shape as data: every field it asks for, each with its
> limit and options, in the order asked. Carried on the decision as
> `asks`; the panel's one-form drawing (design 3) is drawn from it.

## `asking_state`, [line 141](../../../../../../../backend/src/sro/domain/chat/asking.py#L141): Docstring

> What a NEEDS decision carries beyond the fields every writer already
> wrote: the shape (`asks`), what is still offered (so a later reply can
> still fill it, though it is never offered in words again), what was
> dropped, and the options. Keys empty for this ask are left out, so a
> decision with nothing new reads as it always did.

## `turned_down`, [line 154](../../../../../../../backend/src/sro/domain/chat/asking.py#L154): Docstring

> Why each value in the last reply was not taken, said before the
> question that asks for it again -- R1's own reasons (`request.refusal`).

## `cannot_without`, [line 158](../../../../../../../backend/src/sro/domain/chat/asking.py#L158): Docstring

> The note that ends an ask for a required field the operator does not
> have (F1): says the job cannot run without it, starts nothing, and is
> not a question, so `pending_job` finds nothing waiting and nothing
> loops. It carries `dropped` so the thread keeps the drop.

## `still_to_ask`, [line 173](../../../../../../../backend/src/sro/domain/chat/asking.py#L173): Docstring

> This ask, less what its thread already settled for the same job
> (F1): every name any assistant decision about this job dropped, and
> every optional field it already offered -- offered once in a thread.
> A required name that was dropped moves to `without`. Scoped by
> `workflow_id`: X is a field of a job, and another job's X is another
> field.


## `unusable`, [line 197](../../../../../../../backend/src/sro/domain/chat/asking.py#L197): Docstring

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

## `opening`, [line 208](../../../../../../../backend/src/sro/domain/chat/asking.py#L208): Docstring

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

## `also_set`, [line 238](../../../../../../../backend/src/sro/domain/chat/asking.py#L238): Docstring

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

## `_listed`, [line 249](../../../../../../../backend/src/sro/domain/chat/asking.py#L249): Docstring

> `a`, `a and b`, `a, b and c`. A comma before the last is how a list of
> two reads as a list of three.

## `_last_time`, [line 255](../../../../../../../backend/src/sro/domain/chat/asking.py#L255): Docstring

> What each was last time, where anything was. An offer a person cannot
> answer without going to look at the last record is an offer they decline.

## `shortened`, [line 260](../../../../../../../backend/src/sro/domain/chat/asking.py#L260): Docstring

> One value, trimmed to something a sentence can carry. Named rather than
> private because the mail to the asker renders the same values and must trim
> them the same way -- two answers to "how much of this do we repeat back"
> is how one surface quotes a paragraph and another quotes a line.

## `too_long_for`, [line 269](../../../../../../../backend/src/sro/domain/chat/asking.py#L269): Docstring

> The limit this answer breaks, or None if it fits.
>
> Only for a bare reply: one that names its fields ("X: …") or says what
> it does not have is not one value, and its values are measured one by
> one in `answered`.
>
> Measured on the value as it will be TAKEN -- trimmed and cut to `K_SAID` --
> rather than as it was typed, so the answer this reports on is the one that
> would be sent.

## `pending_job`, [line 317](../../../../../../../backend/src/sro/domain/chat/asking.py#L317): Docstring

> What the conversation is waiting on, or None.
>
> The LAST thing the assistant decided, and only that. Each answer produces a
> new decision carrying the remaining questions, so the most recent one is
> the whole state -- and a thread that went on to talk about something else
> has a newer decision that is not a question, which ends the waiting exactly
> as it should. Reading further back would let a job abandoned twenty minutes
> ago claim the next sentence somebody typed.

## `_pairs`, [line 354](../../../../../../../backend/src/sro/domain/chat/asking.py#L354): Docstring

> The offered fields as the decision stores them: a list of two-item
> lists, because JSON has no tuples. Anything else is nothing -- an offer
> read out of a shape nobody wrote is an offer to fill a field that may not
> exist.

## `_step`, [line 364](../../../../../../../backend/src/sro/domain/chat/asking.py#L364): Docstring

> Which step a stored decision names, or 0. A bool is an int in Python and
> `from_step: true` would otherwise resume a job at its second step.

## `_numbers`, [line 370](../../../../../../../backend/src/sro/domain/chat/asking.py#L370): Docstring

> A decision's limits, as whole numbers. JSON off a row, so anything that
> is not a usable count is not one -- a bool is an int in Python, and
> `limits: {"Code": true}` would otherwise read as a one-character field.

## `_strings`, [line 380](../../../../../../../backend/src/sro/domain/chat/asking.py#L380): Docstring

> A decision's mapping, as strings. A decision is JSON off a row and its
> values are `object` to anything reading it honestly.

## `let_go`, [line 384](../../../../../../../backend/src/sro/domain/chat/asking.py#L384): Docstring

> Whether that answer was somebody calling it off.

## `said_yes`, [line 388](../../../../../../../backend/src/sro/domain/chat/asking.py#L388): Docstring

> Whether that sentence agrees with what was just offered.

## `_plainly`, [line 392](../../../../../../../backend/src/sro/domain/chat/asking.py#L392): Docstring

> One answer, as it is matched: lowercased, without the punctuation
> somebody types around a short word.

## `_items`, [line 396](../../../../../../../backend/src/sro/domain/chat/asking.py#L396): Docstring

> The things a job would be done for, as strings. A decision is JSON off a
> row, so its `items` is `object` to anything reading it honestly.

## `offered_job`, [line 400](../../../../../../../backend/src/sro/domain/chat/asking.py#L400): Docstring

> The job this conversation has just offered to do, if it is still the
> last thing said.
>
> The same reading as `pending_job` and for the same reason: the newest
> assistant decision is the whole state, so a job offered twenty minutes ago
> and talked past cannot claim the next sentence. A question waiting on a
> value is NOT one of these -- `pending_job` owns that, and a sentence there
> is the value rather than a yes.

## module, [line 420](../../../../../../../backend/src/sro/domain/chat/asking.py#L420): Note on the line above

Code: `K_WHAT_WE_HAVE = re.compile(r"(?<!\w)what(?:ever)?\s+(?:we|i)\s+(?:have|got)(?!\w)", re.I)`

> "run with what we have", "whatever we have": everything this ask
> still wants and the reply did not fill is dropped (F1). Read AFTER the
> reply's named values, so "Customer Type: RRF, run with what we have"
> keeps RRF.

## module, [line 422](../../../../../../../backend/src/sro/domain/chat/asking.py#L422): Note on the line above

Code: `K_NOT_HAD = re.compile(`

> "don't have X", "skip X", "leave out X", "without X": the words after
> it, up to the end of the clause, name what is dropped. They drop a
> field only when they ARE one of this ask's names (`_alike`), so a
> description that says "skip the queue" is still a description.

## module, [line 429](../../../../../../../backend/src/sro/domain/chat/asking.py#L429): Note on the line above

Code: `K_LIKE = 0.8`

> How alike a typed name must be to a field's to be that field: thr_c563
> typed "manufature" for Manufacturer (0.91). Stdlib `difflib`, no
> dependency. The ceiling: two fields spelled within a letter or two of
> each other could both match one typo; the upgrade is the alias table
> R2 keeps per job.

## `_named`, [line 439](../../../../../../../backend/src/sro/domain/chat/asking.py#L439): Docstring

> Every "Name: value" (also `=` and `:-`, the form greyorange writes) in
> the reply for a name this ask is about, each value running to the next
> name or the end of its sentence. Names are matched however the form
> spells them: `long_description` and `Long Description` are one name.
> Only names this ask is about: `url: http://…` under a question about
> Address is not a value for Address.

## `named_in`, [line 474](../../../../../../../backend/src/sro/domain/chat/asking.py#L474): Docstring

> Whether the reply names what it answers or what it does not have. Such
> a reply is the operator saying what the sentence is FOR, and nothing
> needs a model to read it -- the way out of a reading that is told to
> refuse when unsure (`Converse._is_it_an_answer`).

## `answered`, [line 483](../../../../../../../backend/src/sro/domain/chat/asking.py#L483): Docstring (debt)

> The same job with this answer in it, and the next question outstanding.
>
> One reply can fill several fields (F1): every named value is taken, each
> checked on its own with R1's checks (quote, limits and options, logins),
> offered fields included. A bare reply fills the first field the question
> listed, which is the one-field case every earlier surface relied on. What
> the reply says it does not have is dropped: out of `missing` and
> `offered`, into `dropped`, and -- where it was required -- into
> `without`. `confirmed` goes back to true as it always did: an answer is
> the press arriving.
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

## `_twins`, [line 519](../../../../../../../backend/src/sro/domain/chat/asking.py#L519): Docstring

> The other names for the field just answered.
>
> `Customer Type` and `customertype-customerType` normalise to `customertype`
> and `customertypecustomertype`, and one ends with the other. Direction
> matters: the body key carries the form's name as a prefix, so the longer
> name ends with the shorter. Nothing matches when neither contains the
> other, which is the ordinary case of two unrelated fields.

## `Pending.asking_for`, [line 89](../../../../../../../backend/src/sro/domain/chat/asking.py#L89): Docstring

> The one value this question is about.

## `opening`, [line 210](../../../../../../../backend/src/sro/domain/chat/asking.py#L210): Comment

Code: `for name in pending.missing:`

> What was supplied and will not fit is a different sentence from what was
> never supplied, and running them together is how somebody re-sends the
> value they already sent.

## `opening`, [line 214](../../../../../../../backend/src/sro/domain/chat/asking.py#L214): Comment

Code: `if also := also_set(pending):`

> What it could also set, once, before the question it must have answered.
>
> Before rather than after, because the question is what the next sentence
> answers and a question buried above an offer gets the offer's answer.

## `answered`, [line 495](../../../../../../../backend/src/sro/domain/chat/asking.py#L495): Comment

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

## `should_we`, [line 223](../../../../../../../backend/src/sro/domain/chat/asking.py#L223): Note

Code: `said.append(f"You sent this to {_listed(list(sent_to))}.")`

> The recipients first, because they are why the request was not simply run:
> the operator asked somebody else to do it, and the question is whether this
> system should do it instead.

## `offered_job`, [line 416](../../../../../../../backend/src/sro/domain/chat/asking.py#L416): Note

Code: `mail_thread=str(decision.get("mail_thread") or ""),`

> Carried so a yes to a request read from mail starts a run a reply on that
> mail's thread can find, as a press on the card would.

## `asked_under`, [line 278](../../../../../../../backend/src/sro/domain/chat/asking.py#L278): Note

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

## `offered_job`, [line 405](../../../../../../../backend/src/sro/domain/chat/asking.py#L405): Note

Code: `if decision.get("resume"):`

> A `resume` decision is a run already started, not an offer: a second "yes"
> under it would start the same job again.

## `waiting_on_mail`, [line 310](../../../../../../../backend/src/sro/domain/chat/asking.py#L310): Note

Code: `return pending_job(messages, last.id.value) if last is not None else None`

> The question a mail reply on `mail_thread` answers: the newest decision
> about that mail conversation, resolved through `asked_under` like any bound
> answer, so a reply answers the question asked on its own thread even when a
> question about another mail came after it.
