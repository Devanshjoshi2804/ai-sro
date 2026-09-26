# Notes for `backend/src/sro/application/chat/from_the_mail.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/from_the_mail.py`](../../../../../../../backend/src/sro/application/chat/from_the_mail.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L1): Docstring

> A mail that asks for a job, recognised by what it means.
>
> The rung this replaces is a substring. A watch is `subject contains "Short
> ship"` plus locators somebody marked by hand, and it will miss "please set up a
> new client category" for as long as it exists -- not because the rule is badly
> written, but because a rule made of words the operator typed once cannot be a
> statement about meaning.
>
> So the mail goes through the door that already decides what a piece of text
> means: `understand`, which reads it against every job this tenant holds, with
> each job's parameters, the values those have taken, and -- since
> `domain.chat.asked_by` -- the mails the operator acted on before doing it.
> That last part is why this can be a fair reading rather than a model guessing
> from titles: a request rarely uses a job's words, and what a request for this
> job looks like is a thing the demonstrations recorded.
>
> **It offers, and it runs only what is certain.** A fuzzy reading that started
> a run would be an autonomous system nobody opted into, on the strength of a
> model's opinion about somebody's mail. What comes back is an offer the browser
> turns into the card it already draws, with its existing press and the approval
> ladder underneath, and a person still taps. The one exception is a tenant the
> rollout setting puts on Steel: there a mail that names one job with certainty
> and every required value starts the run itself (`FromTheMail._started`),
> because the server, not a person's browser, is what runs it.
>
> **And it writes nothing into the conversation.** The card is browser-held and
> transient, which is the rule the panel already keeps: an offer ends when it is
> pressed, when the operator does the job themselves, when they dismiss it, or
> when their day does -- and the thread is the record of what was DECIDED. A
> conversation that filled up with "a mail asks for X" would be a surface keeping
> history of questions instead of answers, which is exactly the stillness the
> panel is being split to end.
>
> **Silence beats a wrong card.** A reading that is not `sure` writes nothing. A
> mail nobody was asking about is the common case in any mailbox: a card per
> delivery notice is a panel nobody reads by the fourth, and the cost of missing
> one is that the operator types a sentence, which is what they do today anyway.
>
> **Once per message, ever.** A look every few minutes over the same inbox would
> otherwise offer the same mail forty times. The claim ledger `tool_calls` keeps
> is exactly this shape -- a key, claimed once, with a window -- so it is what
> this uses rather than a table of its own.
>
> The key is the message alone, not the operator who read it: two operators on
> one shared inbox read the same message id, and now that a sure mail can start
> a run, a claim per operator would start it once per operator.
>
> Read as the operator, through their own connector grant. `ToolCaller` takes the
> principal and this passes it down: a look that reached another operator's
> mailbox would be the boundary undone one layer up.

## module, [line 44](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L44): Note on the line above

Code: `K_LOOK = 8`

> How many of the newest messages one look reads.
>
> Bounded because a look somebody is waiting on has to end, and because eight
> cards at once is a panel nobody reads past the third -- not because of what the
> readings cost. Eight covers a morning's arrivals between looks.

## module, [line 46](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L46): Note on the line above

Code: `K_THREAD = 8000`

> How much of one conversation is read back. Long enough for a thread of a
> dozen short mails, short enough that a forwarded chain is not a prompt.

## module, [line 48](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L48): Note on the line above

Code: `K_OFFER_ROUNDS = 3`

> How hard a look tries to find the values for an offer.
>
> Fewer than a run gets. This runs on a beat over every arriving mail, and an
> offer that names most of what it is about is worth far more than one that
> takes a minute to name all of it -- the run looks again anyway, with the
> patience the run is allowed.
>
> Three and not two: the first round is not the model's to choose (see
> `GatherContext`), so two rounds is one search the model actually directs, and
> the value is in a sibling mail that has to be found before it can be read.

## module, [line 50](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L50): Note on the line above

Code: `K_SUBJECT = 120`

> How much of a request's name travels with the offer. A subject line, not a
> forwarded chain of them: `Fwd: Re: Fwd:` prefixes stack, and what a person
> needs is enough to tell this request from the three like it.

## module, [line 52](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L52): Note on the line above

Code: `K_BECAUSE = 400`

> How much of the request the gather is told, so it knows what it is looking
> for. The sentence that asked, not the mailbox.

## module, [line 54](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L54): Note on the line above

Code: `K_RECENT = "newer_than:2d -in:chats"`

> What counts as an arrival worth reading.
>
> Two days rather than an hour: a look runs when somebody asks for one, and a
> request that arrived over the weekend is still a request.
>
> **No label filter, and three tries to get there.** The intent was "their own
> outgoing mail is not a request TO them", and every way Gmail offers to say that
> excludes exactly the mail an operator sends themselves -- which is how a person
> forwards themselves something to deal with later, and how every test request on
> this deployment is written. Measured against the real mailbox, 2026-09-16, on a
> self-addressed request sent at 20:34:
>
>     -in:sent -in:chats          does not find it
>     in:inbox -in:chats          does not find it -- Gmail files it under Sent,
>                                 and the thread only APPEARS in the inbox view
>     {to:me cc:me}               does not find it -- `to:me` does not match it
>     newer_than:2d -in:chats     finds it, first row
>
> So the filter is gone. What it was protecting against remains true and is
> smaller than it looked: a mail the operator sent asking somebody ELSE to do the
> work can now produce a card. That card is an offer a person presses, so the
> cost of being wrong is a card they say no to -- and the same write claim that
> stops two runs making one record still stands behind it.
>
> Chats stay out. A chat message is not a request in any sense this reads.

## module, [line 56](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L56): Note on the line above

Code: `K_TEXT = 2000`

> How much of one message is read against the jobs.
>
> A request states itself at the top: a greeting, the ask, the values. What
> follows is a quoted thread and a signature block, which is where a model finds
> last week's request and offers the job again for a record that already exists.

## `Offered`, [line 63](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L63): Docstring

> One mail, and the job it turned out to ask for.

## `Offered`, [line 70](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L70): Note on the line above

Code: `offers: Sequence[tuple[str, str]] = ()`

> Fields this job can fill that the page does not ask for, and what each
> was last time.
>
> On the CARD, because for a mail that supplied everything required there is
> no question and therefore nowhere else to say it. `_ask_for_values` offers
> these when a run comes up short, and a request that came up short of
> nothing never reaches it -- so on the path an operator who works from
> their mailbox actually uses, the optional fields could never be set at
> all. Measured as a gap on 2026-09-22, before it could bite.

## `Offered`, [line 72](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L72): Note on the line above

Code: `unasked: Sequence[str] = ()`

> What the request asked for that this job has no parameter for.
>
> Said on the card, before the press. The run says it after -- `run.unasked`
> -- and after the press is after the record: nobody can consent to a write
> they cannot see, and "I asked for a Department and it made one without
> one" is the fault this closes.

## `Offered`, [line 74](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L74): Note on the line above

Code: `aside: Mapping[str, str] = field(default_factory=dict)`

> What the fields in `unasked` were given.
>
> The names say what this job cannot set; the values are what make that
> sometimes untrue -- a form posts far more fields than a job varies, so
> where the dictionary names the slot the write can fill it after all.

## `Offered`, [line 76](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L76): Note on the line above

Code: `placed: Mapping[str, str] = field(default_factory=dict)`

> The fields this request named that the job has no parameter for, and the
> body key each is posted as.
>
> Named by the dictionary rather than the demonstrations, which is the whole
> of item 4: a job's parameters are what two doings proved VARY and the form
> posts far more than that. A name in here is one this write can fill after
> all -- and the run proves it landed, because nothing demonstrated it.

## `Offered`, [line 78](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L78): Note on the line above

Code: `started: bool = False`

> A run is already going for this one, so there is nothing to offer.
>
> The operator pressed Yes on the request; that press is what sent the mail,
> and the reply filled the one blank the press could not. A card beside the
> run that answer started is the panel offering to do what it is doing.
>
> Carried on the offer rather than by returning nothing, because the look
> still counts what it read and the caller still tells a browser what
> happened -- what changes is that no card is kept.

## `Offered`, [line 80](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L80): Note on the line above

Code: `subject: str = ""`

> What the request was called, so a conversation about it can say which.
>
> A deliberate exception to `MailOfferModel`'s rule that the id travels and
> the words do not, and worth naming as one. That rule is about not echoing
> somebody's mail across a boundary to say what the id already says -- and it
> already bends for `values`, because nobody can consent to a write they
> cannot see. A subject is the same category: with four requests for the same
> job open at once, it is the only thing that tells one from another in a
> thread that is no longer standing next to the card.

## `Offered`, [line 63](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L63): Note on the line above
## `Offered`, [line 86](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L86): Note on the line above

Code: `sure: bool = False`

> True only for a fresh request the reading was sure of. A reply that carries
> on a waiting run, or answers a standing question, is an offer too, but never
> one the look starts by itself (`FromTheMail._started`).


Code: `thread: str = ""`

> The mail conversation this request arrived in.
>
> Carried so the run started from this offer can be found again by a reply to
> it. The person who knows the value a run could not find is usually whoever
> sent the request, and they are not the person with the panel open -- see
> `domain/execution/waiting.py`.

## `Offered`, [line 84](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L84): Note on the line above

Code: `too_long: Mapping[str, int] = field(default_factory=dict)`

> The values this job's boxes will not hold, and what they hold instead.
>
> Known here only because some earlier run found it out the hard way and
> wrote it down. Carried on the OFFER, which is the point: the run already
> refuses a value that will not fit, and refusing at that moment means a
> person pressed, watched half a form fill, and got a question back. The
> limit is known before the press, so it can be said before the press.

## `LookedInTheMail`, [line 92](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L92): Docstring

> What one look through the mailbox came to.

## `FromTheMail`, [line 99](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L99): Docstring

> Read the operator's recent mail, and offer the jobs it asks for.

## `_sentence`, [line 707](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L707): Docstring

> What happened, for a person reading the result rather than the code.

## `_also`, [line 717](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L717): Docstring

> What the readings came to, totalled. Kept because every other loop here
> reports it and the spend line reads it, not as a limit on anything.

## `_told`, [line 730](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L730): Docstring

> One offer, told what its boxes will not hold and what it can write after
> all.
>
> A name the dictionary places is no longer unwritable, so it leaves
> `unasked` and joins the values -- which is what makes the card's "this job
> cannot set Department" true when it is said and absent when it is not.

## `FromTheMail.execute`, [line 127](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L127): Docstring

> One look. Nothing runs, and nothing is written down about the mail.
>
> What reaches storage is an offer in this operator's own thread -- the
> job, the values, what is missing -- and a claimed key per message id.
> The mail's own words are not kept: they were read out of somebody's
> mailbox to decide one thing, and `ChatReading` has no field for them
> for the same reason.

## `FromTheMail._answering`, [line 361](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L361): Docstring
## `FromTheMail._started`, [line 316](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L316): Note

> Starts an offer only when it is a fresh request the reading was `sure` of
> (`Offered.sure`), carries every required value, fits every field and is not
> already running -- and only for a Steel tenant. A reply that carries on a
> waiting run or answers a standing question is never started here: it
> answers something already in flight, and restarting the job from step 0
> would repeat its writes (D5 resumes it instead).
>
> Through the same `StartWorkflowRun` the press uses, so every refusal the
> press makes is made here too. A refusal (a job whose evidence aged out, the
> cap, a value nothing can supply) leaves the offer as a card for a person
> rather than failing the whole look: the mails before it were already
> claimed, and an exception here would lose their offers with it.
>
> `start_on_steel` answers whether Temporal took the run. When it did not, the
> row is closed and the offer stays a card with `started=False` -- the request
> is never lost behind a run that never began. A started run is recorded as an
> attempt, as a press is, so an autonomous live write has an audit row.
>
> Runs after `_what_will_not_fit`, so a value too long for its field is never
> started and placed values ride along.


> The run still waiting to hear back on this conversation, if any.
>
> Still waiting: a run whose patience has run out is not holding this
> open any more, and reading a reply into it would start a write somebody
> asked for a week ago and has long since done by hand. Such an arrival
> falls through to the ordinary reading, which is the right answer for it
> -- a fresh request on an old thread is a fresh request.

## `FromTheMail._was_asked`, [line 395](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L395): Docstring

> A question standing in the operator's conversation about this mail.
>
> The other half of `_answering`, and the half the reply actually lands
> in. A run is only waiting when a RUN went looking and came back short;
> an offer that could not be answered from the mail asks before anything
> starts, so the commonest shape -- a request with a field missing --
> produces a question and no run at all.
>
> Wired only to the run, a reply to that question fell through to the
> ordinary reading, where "the code is GPX" names no job, is dropped, and
> is dropped for good: the message id is claimed before it is read. The
> answer would be lost at the moment it arrived, which is the exact
> failure the whole path exists to prevent.
>
> The operator's own conversation, because that is where the question
> was put and this look runs as them.

## `FromTheMail._carrying_on`, [line 406](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L406): Docstring

> The waiting run's offer again, with whatever the reply added.
>
> Everything that run established rides along, which is the whole point
> of finding it: the operator pressed once, the gather spent its rounds,
> and a second card starting from nothing would ask them to do all of it
> again over one missing word.
>
> What the reply itself says is read by the ordinary gather, against the
> thread it arrived in -- the same call, with the same rounds, now
> looking at a conversation that contains the answer.

## `FromTheMail._answered_by_mail`, [line 448](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L448): Docstring

> The standing question, with whatever the reply answered of it.
>
> **A card and not a run**, and the difference is consent rather than
> caution. Everything a job writes has been on a card the operator read
> before pressing -- that is what `2.8` and the limit work are for, and
> what "the card says what it will write" means. A value that arrives
> AFTER the press has been read by nobody: the operator authorised this
> job with the values they could see, not whatever later turns up in a
> mailbox.
>
> It is the same reasoning the panel's own answer does NOT need. There,
> the person supplying the value is the person who pressed; here they are
> two different people, and the second is outside every system this
> company runs.
>
> So the reply is read, the value is filled in, and the card comes back
> naming it. One press, on something visible.

## `FromTheMail._reply_says`, [line 491](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L491): Docstring

> The values this reply actually states, read out of the reply.
>
> The one thing neither reply path did. A reply is the answer to a
> question this system asked, and both paths handed it to the gather --
> which does not READ it. `because` is a search QUERY there: the words
> somebody wrote are typed into a mailbox search, the search comes back
> with the thread or with nothing, and the value sitting in the sentence
> is never looked at. Measured on the deployment 2026-09-18: a reply
> saying `customer type :- QQI` to a question asking for Customer Type
> was logged `a reply answers the question standing on ... (0 of 1)`, and
> the card came back asking the same thing again.
>
> The job is known here -- the thread settled it -- so the reading is
> given that one job and nothing else to choose between. It is asked for
> values, not for which job this is: re-deciding a settled question on
> two words like `QQI` is how a bare answer ends up read as no job at
> all and dropped.
>
> Empty for every ordinary reason, and the gather still runs after it: a
> reply that says nothing useful is the case the mailbox search exists
> for.

## `FromTheMail._the_question_is_answered`, [line 514](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L514): Docstring

> Close the standing question, because a reply has answered it.
>
> True where the answer started the job, which is the case where nothing
> is left missing.
>
> The card is built and the conversation was left asking. So the panel
> said two things at once -- here is NGSL, press to run it, and also what
> should Customer Type be -- which is a system that does not know what it
> knows. Seen on the deployment 2026-09-18.
>
> `pending_job` reads the last thing the ASSISTANT decided, so what ends
> a question is the assistant deciding something else. Where the reply
> answered everything that was outstanding, that is a note saying so.
> Where it answered some of it, the question that is left is asked again
> with the new values on it, so the thread carries the progress rather
> than repeating its first sentence.
>
> Silent on every failure: a conversation that could not be written to
> is a stale question, and a stale question is not worth losing the card
> that answers it.

## `FromTheMail._what_will_not_fit`, [line 585](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L585): Docstring

> Each offer, told which of its values its own boxes are too small for.
>
> One read per job rather than per offer: a mailbox holding four requests
> for the same job is the ordinary case, and it is the same answer four
> times.
>
> A job nothing has been learnt about comes back exactly as it went in,
> which is most of them -- a limit exists only where a run has hit one.

## `FromTheMail._recent`, [line 621](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L621): Docstring

> The newest message ids, as this operator. Ids only: what each one
> says is read one at a time below, and a search answer carries a snippet
> that is not enough to decide on.

## `FromTheMail._body`, [line 642](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L642): Docstring

> What one message says, the conversation it belongs to, and its name.
>
> The thread beside the words because a request rarely carries what it is
> about: "as discussed" was discussed in the mail above it, and which
> mail that is, is a fact Gmail already knows.
>
> The subject beside both because a conversation about this request has
> to be able to say which request. See `Offered.subject`.

## `FromTheMail._conversation`, [line 667](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L667): Docstring

> Every mail in one conversation, as one piece of text.
>
> The conversation and not a search. A request names no values -- "please
> create the customer type as discussed" -- and the values are in the mail
> it replies to, which Gmail already knows about: it is the same thread.
> Searching the mailbox for it is guessing at something nobody has to
> guess at, and on a mailbox holding seventeen near-identical threads the
> guess came back "the mailbox holds none of the values this job needs"
> about a value sitting one mail away. Measured on the deployment,
> 2026-09-17 at 21:26.

## `FromTheMail._first_time`, [line 690](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L690): Docstring

> Whether this message has been offered before.
>
> The claim ledger rather than a table of its own: this is the shape it
> already keeps -- a key, claimed once, with a window -- and a second
> store for "have I seen this" is a second store to migrate.
>
> Claimed BEFORE the reading, so a look that fails half way through does
> not read the same mail again on the next one. The cost of that is a
> mail nobody was offered after a crash; the cost of the other order is a
> model call per look per message, forever.

## `FromTheMail.__init__`, [line 123](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L123): Comment

Code: `self._clock = clock`

> Only for closing a question a reply has answered, which is the one
> thing this door writes into the operator's own conversation. Optional
> so nothing that builds this for a test has to grow two arguments to
> go on testing what it was testing.

## `FromTheMail.execute`, [line 128](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L128): Comment

Code: `asker = asker_or_refuse(self._asker)`

> The one guard, in the use case rather than in the container: a
> factory that raised would make a deployment with no key unbuildable
> instead of refusing at the one call that actually needs a model.

## `FromTheMail.execute`, [line 131](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L131): Comment

Code: `why = await over_cap(`

> A look spends the tenant's model budget -- a reading per mail, and a gather
> for what the mail did not carry -- so a spent day refuses it before the first
> mail is fetched, as every other door that starts model work does. The metered
> client would refuse each call anyway; asking here gives the operator the 429
> and the reason instead of a look that quietly read nothing.

## `FromTheMail.execute`, [line 161](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L161): Comment

Code: `unsure = 0`

> Read, asked for a job, and dropped because the reading could not tell
> which job. Counted rather than swallowed: see `_sentence`.

## `FromTheMail.execute`, [line 176](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L176): Comment

Code: `back = await self._answering(ctx, thread)`

> A reply to a request this system already acted on, and could not
> finish.
>
> The thread decides the job here, and the model does not get
> asked. Two reasons, and the second is the one that matters: the
> run waiting on this conversation already agreed which job it is,
> so a reading would be re-deciding a settled question -- and a
> bare reply is the exact sentence a reading cannot make anything
> of. Somebody answering "GU9" to "what should the Customer Type
> be?" has written two words with no job in them: `understand`
> answers `sure=False` or nothing at all, the arrival is dropped,
> and the id is already claimed so it is dropped for good. The
> answer would be lost at precisely the moment it arrived.

## `FromTheMail.execute`, [line 187](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L187): Comment

Code: `asked = await self._was_asked(ctx, thread)`

> Or a question standing in the conversation that this answers.

## `FromTheMail.execute`, [line 197](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L197): Comment

Code: `if got.workflow_id is None:`

> Silence where it is not sure, and where it named no job at all.
> A card about a delivery notice is worse than no card: the person
> stops reading the ones that matter.

## `FromTheMail.execute`, [line 201](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L201): Comment

Code: `unsure += 1`

> Which other jobs it might have meant, because that is the
> whole of why it said nothing. Measured on the deployment,
> 2026-09-17: this tenant holds TWO workflows called `Create a
> Customer Type` -- one with six steps and sixty-one runs, one
> with two steps and none -- so every mail asking for one named
> both, `sure` went false, and the mail path was silent about
> the job the rig had otherwise learned to do. Nothing anywhere
> said so.

## `FromTheMail.execute`, [line 202](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L202): Comment

Code: `logger.info(`

> A thread that wandered onto another subject is not
> more evidence about this one.

## `FromTheMail.execute`, [line 209](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L209): Comment

Code: `values, missing = dict(got.values), list(got.missing)`

> The values it is about, before it is offered.
>
> A request rarely carries them: "please create the customer type
> as discussed" is the whole of it, and what to create is in the
> mail before it. So the reading came back with the job and two
> missing values, and the card said "Create a Customer Type -- want
> me to do it?" with nothing to tell one from another. Four of them
> stacked up on the deployment, 2026-09-18, and they were the same
> sentence four times.
>
> Nobody can consent to a write they cannot see. The run gathers
> these anyway, a moment after the press -- this is the same work
> moved to where the decision is actually made, so a wrong reading
> is caught before the record instead of after it.

## `FromTheMail.execute`, [line 210](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L210): Comment

Code: `asked_for_too: set[str] = set()`

> Named by the request and not a parameter of this job, from every
> reading of it. A set, because two readings of one conversation
> name the same field twice.

## `FromTheMail.execute`, [line 212](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L212): Comment

Code: `if missing:`

> The conversation first, because that is where the answer is.
>
> A reply that says "as discussed" was discussed in the mail above
> it. Reading the thread is one call and no guessing; the gather
> below searches the whole mailbox with a query a model writes, and
> on this mailbox that came back empty about a value one mail away.

## `FromTheMail.execute`, [line 213](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L213): Comment

Code: `job_ = titles.get(got.workflow_id, got.workflow_id)`

> Every way this can end, said. It came up short four times
> running on the deployment and each round told me one more
> thing, because each round only one branch of this could
> speak. A step that can fail five ways and reports one of them
> is a step nobody can debug -- which is the lesson the
> execution ladder already learned, in the same week.

## `FromTheMail.execute`, [line 221](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L221): Comment

Code: `logger.info(`

> What the look CAME TO, not only what it threw away.
>
> The drops have been logged since the sentence was fixed, and nothing
> logged a kept offer -- so "no line for that message" was the only
> evidence an offer had been made, and absence of evidence is not it.
> Twice on 2026-09-17 that reading sent me looking for a card in a
> panel when I had no idea whether one had ever been offered.

## `FromTheMail.execute`, [line 228](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L228): Comment

Code: `logger.info(`

> What the gather came back with, because an offer that names
> nothing and an offer that was never gathered for look the
> same from outside. Names and counts, never a value: this line
> is about whether the mechanism worked.

## `FromTheMail.execute`, [line 237](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L237): Comment

Code: `asked_for_too.update(again.unasked)`

> The whole conversation names fields the first
> sentence did not -- "and put it in Inbound" two
> mails up is still something the request asked for
> and this job cannot write.

## `FromTheMail.execute`, [line 274](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L274): Comment

Code: `offers=offerable(`

> What the request asked for that this job cannot write,
> said on the card rather than after the press. `again` is
> the second reading -- the whole conversation -- and it
> names fields the first sentence did not.
> What it could ALSO set, which nothing has to answer.

## `FromTheMail.execute`, [line 282](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L282): Comment

Code: `aside={**got.aside, **said_besides},`

> What those fields were given. The names alone let the
> card say what this job cannot set; the values are what
> make it sometimes untrue.

## `FromTheMail.execute`, [line 287](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L287): Comment

Code: `except OverCap as reached:`

> The cap crossed partway through a look is a refusal, not a mail that asks
> for nothing. The look stops, keeps the offers it already made, says why, and
> forgets the claim on the mail it was reading, so the next look reads it;
> the mails after it were never claimed.

## `FromTheMail._answered_by_mail`, [line 481](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L481): Comment

Code: `started=started,`

> Nothing to press where the run is already going. A card beside a
> run started by the same answer is the panel offering to do what
> it is doing.

## `FromTheMail._the_question_is_answered`, [line 550](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L550): Comment

Code: `speaker=Speaker.ASSISTANT,`

> ASSISTANT either way: this is the thing that decides whether a
> question is still standing, and a SYSTEM note leaves the old
> one to be found by the next sentence somebody types.

## `FromTheMail._the_question_is_answered`, [line 565](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L565): Comment

Code: `else {`

> Nothing missing, so nothing left to ask -- including the
> asking.
>
> A card here is the same permission twice. The operator
> pressed Yes on this request; that press is what sent the
> mail, and the reply filled the one blank the press could
> not. Putting a second card in front of them says the
> system did not understand what it was already told, and
> it is the same reasoning `_answer_the_question` has kept
> since the chat path was built: "they already said yes;
> asking twice for the same permission is how a system
> teaches somebody to stop reading what it asks."
>
> Which is not the write gate. A live run still parks in
> front of a warehouse write until the JOB has earned it --
> three runs whose writes a state belt verified. That gate
> is about the job's track record and this is about one
> person's consent, and neither stands in for the other.

## `FromTheMail._the_question_is_answered`, [line 576](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L576): Comment

Code: `"resume": True,`

> The browser's cue to start without asking again. The
> same field the chat path emits for the same reason.

## `FromTheMail._what_will_not_fit`, [line 590](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L590): Comment

Code: `placeable: dict[str, dict[str, str]] = {}`

> Per job, like the limits: a mailbox holding four requests for one job
> is the ordinary case and it is the same answer four times.

## `FromTheMail._what_will_not_fit`, [line 600](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L600): Comment

Code: `await declared_limits(`

> And what this job's fields are DOCUMENTED to hold, for the
> boxes no run has hit yet. The whole value of asking before
> the press is lost if the first request too long for a field
> still has to be sent to find that out.

## `FromTheMail._what_will_not_fit`, [line 609](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L609): Comment

Code: `asked = sorted(`

> And which of the fields this request named, that the job has no
> parameter for, the form nonetheless posts.
>
> A job's parameters are what two doings proved VARY and the form
> has far more fields than that, so `Department: Inbound` was a
> reasonable request this could only report as unwritable. Where
> the dictionary names the slot, the write can fill it -- and the
> run then proves it landed, because nothing demonstrated it.

## `_sentence`, [line 711](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L711): Comment

Code: `return f"read {read}, and {unsure} asked for a job this tenant holds more than one of"`

> NOT "none of them asks for a job", which is what this said and which
> was false: one of them asked, and the reading could not tell which of
> two jobs it meant. A look that reports the wrong absence is a look
> nobody investigates -- the tenant had two workflows with one name for
> a day, and this sentence is why nobody knew.

## `_told`, [line 740](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L740): Comment

Code: `return replace(`

> Placed fields leave `unasked` -- they are no longer things this job
> cannot set -- and their values join the ones it was given, because the
> write is what fills them and the write reads `values`.

## `FromTheMail._answer_the_run`, [line 374](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L374): Note

Code: `if run.outcome != "running" or asking.get("kind") != "value":`

> A reply on the conversation a Steel run is waiting on never starts a
> second run from step 0. Mail is untrusted, so it answers only a question
> for a value: it never tells a step to go again or says a write was done,
> and it never carries a password or a one-time code. Any other question
> stands in the panel for the operator.
## `FromTheMail._started`, [line 328](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L328): Comment

Code: `if await uow.workflow_runs.started_on(ctx.tenant_id, server=SERVER, thread=one.thread):`

> A thread that already started a run never starts another by itself. A reply
> quotes the request -- "thanks! > please create type GT2" -- and a model reads
> the quote as a fresh, sure, complete request; the run's own reply mail and a
> colleague's reply-all do the same. Whatever the model reads, a later mail on
> that thread is only a card, until resuming versus starting anew is decided.
> Every automatic start passes through here.

## `FromTheMail._started`, [line 322](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L322): Comment

Code: `or one.sent_to`

> A mail the operator sent to other people asks THEM to do the job, so it
> never starts a run by itself. It stays a card that names who it went to and
> asks whether this system should do it (decided 2026-09-26).
