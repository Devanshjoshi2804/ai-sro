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

## module, [line 59](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L59): Note on the line above

Code: `K_LOOK = 8`

> How many of the newest messages one look reads.
>
> Bounded because a look somebody is waiting on has to end, and because eight
> cards at once is a panel nobody reads past the third -- not because of what the
> readings cost. Eight covers a morning's arrivals between looks.

## module, [line 69](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L69): Note on the line above

Code: `K_THREAD = 8000`

> How much of one conversation is read back. Long enough for a thread of a
> dozen short mails, short enough that a forwarded chain is not a prompt.
> The oldest is cut (R1 review, I7): the thread is listed oldest first, and
> the newest mail is the one being read. `earlier` is never cut; it is only
> searched, never sent.

## module, [line 71](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L71): Note on the line above

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

## module, [line 73](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L73): Note on the line above

Code: `K_SUBJECT = 120`

> How much of a request's name travels with the offer. A subject line, not a
> forwarded chain of them: `Fwd: Re: Fwd:` prefixes stack, and what a person
> needs is enough to tell this request from the three like it.

## module, [line 75](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L75): Note on the line above

Code: `K_BECAUSE = 400`

> How much of the request the gather is told, so it knows what it is looking
> for. The sentence that asked, not the mailbox.

## module, [line 77](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L77): Note on the line above

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

## module, [line 79](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L79): Note on the line above

Code: `K_TEXT = 2000`

> How much of one message is read against the jobs.
>
> A request states itself at the top: a greeting, the ask, the values. What
> follows is a quoted thread and a signature block, which is where a model finds
> last week's request and offers the job again for a record that already exists.

## `Offered`, [line 86](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L86): Docstring

> One mail, and the job it turned out to ask for.

## `Offered`, [line 93](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L93): Note on the line above

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

## `Offered`, [line 95](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L95): Note on the line above

Code: `unasked: Sequence[str] = ()`

> What the request asked for that this job has no parameter for.
>
> Said on the card, before the press. The run says it after -- `run.unasked`
> -- and after the press is after the record: nobody can consent to a write
> they cannot see, and "I asked for a Department and it made one without
> one" is the fault this closes.

## `Offered`, [line 97](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L97): Note on the line above

Code: `aside: Mapping[str, str] = field(default_factory=dict)`

> What the fields in `unasked` were given.
>
> The names say what this job cannot set; the values are what make that
> sometimes untrue -- a form posts far more fields than a job varies, so
> where the dictionary names the slot the write can fill it after all.

## `Offered`, [line 99](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L99): Note on the line above

Code: `placed: Mapping[str, str] = field(default_factory=dict)`

> The fields this request named that the job has no parameter for, and the
> body key each is posted as.
>
> Named by the dictionary rather than the demonstrations, which is the whole
> of item 4: a job's parameters are what two doings proved VARY and the form
> posts far more than that. A name in here is one this write can fill after
> all -- and the run proves it landed, because nothing demonstrated it.

## `Offered`, [line 101](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L101): Note on the line above

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

## `Offered`, [line 103](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L103): Note on the line above

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

## `Offered`, [line 86](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L86): Note on the line above
## `Offered`, [line 109](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L109): Note on the line above

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

## `Offered`, [line 107](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L107): Note on the line above

Code: `too_long: Mapping[str, int] = field(default_factory=dict)`

> The values this job's boxes will not hold, and what they hold instead.
>
> Known here only because some earlier run found it out the hard way and
> wrote it down. Carried on the OFFER, which is the point: the run already
> refuses a value that will not fit, and refusing at that moment means a
> person pressed, watched half a form fill, and got a question back. The
> limit is known before the press, so it can be said before the press.

## `LookedInTheMail`, [line 121](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L121): Docstring

> What one look through the mailbox came to.

## `FromTheMail`, [line 128](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L128): Docstring

> Read the operator's recent mail, and offer the jobs it asks for.

## `_sentence`, [line 962](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L962): Docstring

> What happened, for a person reading the result rather than the code.

## `_also`, [line 974](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L974): Docstring

> What the readings came to, totalled. Kept because every other loop here
> reports it and the spend line reads it, not as a limit on anything.

## `_told`, [line 987](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L987): Docstring

> One offer, told what its boxes will not hold and what it can write after
> all.
>
> A name the dictionary places is no longer unwritable, so it leaves
> `unasked` and joins the values -- which is what makes the card's "this job
> cannot set Department" true when it is said and absent when it is not.

## `FromTheMail.execute`, [line 156](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L156): Docstring

> One look. Nothing runs, and nothing is written down about the mail.
>
> What reaches storage is an offer in this operator's own thread -- the
> job, the values, what is missing -- and a claimed key per message id.
> The mail's own words are not kept: they were read out of somebody's
> mailbox to decide one thing, and `ChatReading` has no field for them
> for the same reason.

## `FromTheMail._answering`, [line 448](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L448): Docstring
## `FromTheMail._started`, [line 392](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L392): Note

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

## `FromTheMail._was_asked`, [line 525](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L525): Docstring

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

## `FromTheMail._carrying_on`, [line 535](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L535): Docstring

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

## `FromTheMail._answered_by_mail`, [line 577](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L577): Docstring

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

## `FromTheMail._reply_says`, [line 622](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L622): Docstring

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

## `FromTheMail._the_question_is_answered`, [line 650](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L650): Docstring

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

## `FromTheMail._what_will_not_fit`, [line 711](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L711): Docstring

> Each offer, told which of its values its own boxes are too small for.
>
> One read per job rather than per offer: a mailbox holding four requests
> for the same job is the ordinary case, and it is the same answer four
> times.
>
> A job nothing has been learnt about comes back exactly as it went in,
> which is most of them -- a limit exists only where a run has hit one.

## `FromTheMail._recent`, [line 786](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L786): Docstring

> The newest message ids, as this operator. Ids only: what each one
> says is read one at a time below, and a search answer carries a snippet
> that is not enough to decide on.
>
> One page of them. `page` is the connector's `next_page` from the page
> before (Gmail's `pageToken`), and the id list comes back with the next one,
> or `""` when the search is exhausted.

## `FromTheMail._body`, [line 809](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L809): Docstring

> What one message says, the conversation it belongs to, and its name.
>
> The thread beside the words because a request rarely carries what it is
> about: "as discussed" was discussed in the mail above it, and which
> mail that is, is a fact Gmail already knows.
>
> The subject beside both because a conversation about this request has
> to be able to say which request. See `Offered.subject`.

## `FromTheMail._conversation`, [line 835](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L835): Docstring

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

## `FromTheMail._take`, [line 854](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L854): Note

Code: `tenant, kept, reading = ctx.tenant_id, mail_key(message), _reading_key(message)`

> Two keys in the claim ledger. `mail_key(id)` is a mail read and done with,
> written by `_keep` once its outcome is committed and held for `K_REMEMBER`.
> A mail this system sent holds `sent_key` instead, written by
> `send_as_this_system`, and `_read` drops it by its id or marker before
> reading it: not as a request, not as the answer to a value, and not as the
> operator's own reply naming a recipient.
> `reading:{id}` is the hold a look takes before it reads, one insert that
> does nothing on conflict, so the heartbeat look and the poll never read one
> mail at the same time. The hold lapses after `K_LEASE`: a worker killed
> mid-look (every deploy) leaves it, and a later look reads the mail. `None`
> says somebody else holds it right now, which keeps this look from moving
> the cursor past it.

## `K_LEASE`, [line 63](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L63): Note

Code: `K_LEASE = timedelta(minutes=15)`

> How long a hold on a mail being read lasts. Long enough for the slowest
> look -- a reading, a conversation re-read and a gather of three rounds --
> and short enough that a mail a dead worker was holding is read the same
> quarter hour.

## `FromTheMail.__init__`, [line 152](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L152): Comment

Code: `self._clock = clock`

> Only for closing a question a reply has answered, which is the one
> thing this door writes into the operator's own conversation. Optional
> so nothing that builds this for a test has to grow two arguments to
> go on testing what it was testing.

## `FromTheMail.execute`, [line 157](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L157): Comment

Code: `asker = asker_or_refuse(self._asker)`

> The one guard, in the use case rather than in the container: a
> factory that raised would make a deployment with no key unbuildable
> instead of refusing at the one call that actually needs a model.

## `FromTheMail.execute`, [line 160](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L160): Comment

Code: `why = await over_cap(`

> A look spends the tenant's model budget -- a reading per mail, and a gather
> for what the mail did not carry -- so a spent day refuses it before the first
> mail is fetched, as every other door that starts model work does. The metered
> client would refuse each call anyway; asking here gives the operator the 429
> and the reason instead of a look that quietly read nothing.

## `_Look`, [line 915](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L915): Comment

Code: `unsure: int = 0`

> Read, asked for a job, and not sure which. Counted for `_sentence`, and no
> longer dropped: the reading becomes a question ("should our system do it?")
> naming the job it leaned to, so the operator decides rather than nobody.

## `FromTheMail._read`, [line 240](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L240): Comment

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

## `FromTheMail._read`, [line 251](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L251): Comment

Code: `asked = await self._was_asked(ctx, thread)`

> Or a question standing in the conversation that this answers.

## `FromTheMail._read`, [line 262](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L262): Comment

Code: `if got.workflow_id is None:`

> Silence where it is not sure, and where it named no job at all.
> A card about a delivery notice is worse than no card: the person
> stops reading the ones that matter.

## `FromTheMail._read`, [line 266](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L266): Comment

Code: `look.unsure += 1`

> Which other jobs it might have meant, because that is the
> whole of why it said nothing. Measured on the deployment,
> 2026-09-17: this tenant holds TWO workflows called `Create a
> Customer Type` -- one with six steps and sixty-one runs, one
> with two steps and none -- so every mail asking for one named
> both, `sure` went false, and the mail path was silent about
> the job the rig had otherwise learned to do. Nothing anywhere
> said so.

## `FromTheMail._read`, [line 273](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L273): Comment

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

## `FromTheMail.execute`, [line 215](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L215): Comment

Code: `logger.info(`

> What the look CAME TO, not only what it threw away.
>
> The drops have been logged since the sentence was fixed, and nothing
> logged a kept offer -- so "no line for that message" was the only
> evidence an offer had been made, and absence of evidence is not it.
> Twice on 2026-09-17 that reading sent me looking for a card in a
> panel when I had no idea whether one had ever been offered.

## `FromTheMail.execute`, [line 215](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L215): Comment

Code: `logger.info(`

> What the gather came back with, because an offer that names
> nothing and an offer that was never gathered for look the
> same from outside. Names and counts, never a value: this line
> is about whether the mechanism worked.

## `FromTheMail._read`, [line 300](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L300): Comment

Code: `offers=offerable(`

> What the request asked for that this job cannot write,
> said on the card rather than after the press.
> What it could ALSO set, which nothing has to answer.

## `FromTheMail.execute`, [line 195](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L195): Comment

Code: `except (OverCap, ToolsUnavailable, Unread) as stopped:`

> A mail is kept as read only once what came of it is written -- a run
> started, a question asked, an answer given, or a reading that it asks for no
> job. The cap, a mailbox that stopped answering, or a model that gave no
> reading (a 503 is not "no job") release the hold on the mail being read and
> stop the look, so the next look reads it; the mails after it were never
> taken. Any other failure releases it too, and is raised.

## `FromTheMail._answered_by_mail`, [line 612](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L612): Comment

Code: `sure=asked.confirmed,`

> A reply that fills the last value of a question the operator had already
> said yes to (a card press) is a request as sure as a fresh one: `_settle`
> starts it through the one start path, keyed to this mail. A question the
> look asked itself (`unconfirmed`) was never said yes to, so its completed
> request is asked about instead. Nothing here claims a run started: the
> `resume` cue it used to write was acted on by no browser for a mail reply.

## `FromTheMail._the_question_is_answered`, [line 686](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L686): Comment

Code: `speaker=Speaker.ASSISTANT,`

> ASSISTANT either way: this is the thing that decides whether a
> question is still standing, and a SYSTEM note leaves the old
> one to be found by the next sentence somebody types.

## `FromTheMail._the_question_is_answered`, [line 701](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L701): Comment

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

## `FromTheMail._the_question_is_answered`, [line 702](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L702): Comment

Code: `"kind": Said.NOTE,`

> A completed answer closes the question with a note on the same offer (job
> and mail thread), so it stops standing; what comes of the request is
> `_settle`'s to decide.

## `FromTheMail._what_will_not_fit`, [line 716](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L716): Comment

Code: `placeable: dict[str, dict[str, str]] = {}`

> Per job, like the limits: a mailbox holding four requests for one job
> is the ordinary case and it is the same answer four times.

## `FromTheMail._what_will_not_fit`, [line 726](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L726): Comment

Code: `await declared_limits(`

> And what this job's fields are DOCUMENTED to hold, for the
> boxes no run has hit yet. The whole value of asking before
> the press is lost if the first request too long for a field
> still has to be sent to find that out.

## `FromTheMail._what_will_not_fit`, [line 735](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L735): Comment

Code: `asked = sorted(`

> And which of the fields this request named, that the job has no
> parameter for, the form nonetheless posts.
>
> A job's parameters are what two doings proved VARY and the form
> has far more fields than that, so `Department: Inbound` was a
> reasonable request this could only report as unwritable. Where
> the dictionary names the slot, the write can fill it -- and the
> run then proves it landed, because nothing demonstrated it.

## `_sentence`, [line 968](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L968): Comment

Code: `return f"read {read}, and {unsure} asked for a job this tenant holds more than one of"`

> NOT "none of them asks for a job", which is what this said and which
> was false: one of them asked, and the reading could not tell which of
> two jobs it meant. A look that reports the wrong absence is a look
> nobody investigates -- the tenant had two workflows with one name for
> a day, and this sentence is why nobody knew.

## `_told`, [line 997](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L997): Comment

Code: `return replace(`

> Placed fields leave `unasked` -- they are no longer things this job
> cannot set -- and their values join the ones it was given, because the
> write is what fills them and the write reads `values`.

## `FromTheMail._answer_the_run`, [line 490](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L490): Note

Code: `if kind not in ("value", "recipient") or not said:`

> A reply on the conversation a Steel run is waiting on never starts a
> second run from step 0. Mail is untrusted, so it answers only a question
> for a value: it never tells a step to go again or says a write was done,
> and it never carries a password or a one-time code. Any other question
> stands in the panel for the operator.
>
> That includes a field question (X10). Its answer is not a value: it chooses
> where a value goes (a label) or drops it, and the reply text -- subject, body
> and quoted thread in one -- can name the labels of the request it quotes. A
> wrong field on a live write is the harm D5 keeps mail away from.
>
> A recipient question (M2) is answered by mail only from the operator
> themselves: a mail their own mailbox sent (Gmail's SENT label, not a `From`
> anybody can write) on that thread, naming exactly one address in its own text
> (`one_address_in`, told whether the mail is a reply by its In-Reply-To and
> References) -- never the quoted text under it, which carries the draft and the
> asker's words. None, or more than one, and the question stays open. The draft
> path's question, on a stopped run, comes through this same door. A
> third party in the thread never names who a mail goes to (invariant 7), and
> `AnswerRun` still refuses a line that is not an address and an operator who
> did not start the run.

## `FromTheMail._started`, [line 405](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L405): Comment

Code: `if await uow.workflow_runs.started_on(ctx.tenant_id, server=SERVER, thread=one.thread):`

> A thread that already started a run never starts another by itself. A reply
> quotes the request -- "thanks! > please create type GT2" -- and a model reads
> the quote as a fresh, sure, complete request; the run's own reply mail and a
> colleague's reply-all do the same. Whatever the model reads, a later mail on
> that thread is only a card, until resuming versus starting anew is decided.
> Every automatic start passes through here.

## `FromTheMail._started`, [line 399](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L399): Comment

Code: `or one.sent_to`

> A mail the operator sent to other people asks THEM to do the job, so it
> never starts a run by itself. It stays a card that names who it went to and
> asks whether this system should do it (decided 2026-09-26).

## `K_LOOK_PAGES`, [line 61](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L61): Note

Code: `K_LOOK_PAGES = 10`

> How many pages of `K_LOOK` ids one look reads back through before it stops.
> Paging goes back to the newest mail of the last look that finished whole
> (`caught:` in the claim ledger, per operator), or to the end of the search,
> so a look cut short -- a page that failed, the cap, a restart -- is picked
> up by the next one instead of stranding what it did not reach. A quiet
> mailbox costs one search.
>
> ponytail: a ceiling. A look that reaches the page cap stops without moving
> the cursor, and the next one starts again from the newest page; more than
> `K_LOOK * K_LOOK_PAGES` (80) mails between two whole looks for one operator
> leaves the oldest unread. The look logs a warning when it reaches the cap.
> Upgrade path: keep the page token the capped look stopped at and resume
> from it.

## `FromTheMail._unclaimed`, [line 760](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L760): Note

Code: `if await self._caught_up_to(ctx, message, now=now):`

> The one place the search is paged. Each id is taken as it is handed out,
> never ahead, so a look that stops early leaves every message it did not
> reach free for the next look or the other caller. It stops at the last
> whole look's newest mail, and a look is whole only when it got there (or to
> the end of the search) with nothing held by another look along the way.

## `_page_of`, [line 951](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L951): Note

Code: `return more if isinstance(more, str) and K_PAGE_TOKEN.fullmatch(more) else ""`

> Only a page token of the shape the connector hands out is followed; any
> other string ends the paging rather than being sent back as a search.

## `FromTheMail._settle`, [line 323](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L323): Note

Code: `(one,) = await self._what_will_not_fit(ctx, [one], workflows)`

> Each mail is settled as soon as it is read, not after the whole look: its
> run started, or -- for a Steel tenant -- its question asked in the
> operator's conversation (`ask_to_run`). One path for the heartbeat's look and
> the poll, so a mail is a question whichever read it, and the offer comes
> back `asked` so the browser draws no card beside it. A run the cap refuses
> at its start raises out of here, and `execute` releases the mail.

## `FromTheMail._started`, [line 430](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L430): Note

Code: `except OverCap:`

> A cap refusal is not a start that failed: it goes up to `execute`, which
> releases the mail. Every other failure leaves the card standing.

## `FromTheMail._started`, [line 428](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L428): Note

Code: `offer=mail_key(one.message),`

> The mail is the offer a mail-started run answers. If a look dies after the
> run is written and before the mail is kept, the mail is read again once its
> hold lapses, and the store refuses its second run.

## `FromTheMail._started`, [line 419](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L419): Note

Code: `name: one.aside[name]`

> A value the mail asked for that the job has no parameter for rides into the
> run, where `RunSteps` composes it onto the form (X10) or asks about it. The
> job's own values win on a clash, and a credential-named one never rides.

## `FromTheMail._settle`, [line 324](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L324): Comment

Code: `if one.cannot_run and self._asks is not None:`

> The reader sees every job. A mail that names one which cannot run is
> answered in the thread with the reasons and is never started, so it has an
> outcome before it is kept (invariant 6), and nothing is pressed that the
> start would refuse.

## `FromTheMail._read`, [line 254](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L254): Comment

Code: `whole, earlier = await self._conversation(ctx, thread, message) if thread else ("", "")`

> The whole conversation, read once and first (R1). A reply that says "as
> discussed" was discussed in the mail above it; reading the thread is one
> call and no guessing. Before R1 the single mail was read, and the thread
> read again by a second model call only when values were missing: two
> calls for one request, and the second reading could name another job.
> `earlier` is the thread without this mail, which says whether this mail
> brought anything new (`Offered.fresh`).
> A thread that could not be read (an error result, text that is not a
> thread) raises ToolsUnavailable, and the mail is released for the next
> look: "not read" is never "this mail alone", which would make a quoted
> reply fresh and start a run from it (R1 re-review 1, item 2).

## `Offered`, [line 117](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L117): Note on the line above

Code: `fresh: bool = True`

> Whether this mail itself gave a value the thread did not already hold. A
> follow-up on a thread ("have you recived mail", "check now") read with the
> whole thread names the first mail's values again, and nothing in it is new.
> A mail with nothing before it is the request itself, fresh even when the
> job takes no value.

## `FromTheMail._settle`, [line 334](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L334): Comment

Code: `if not one.fresh and await self._started_here(ctx, one.thread):`

> Follow-ups are thread state (amendment 2, item 4): on a thread that already
> started a run, a mail that adds nothing is about that run. It is answered
> with a note, never offered again as a new job. A mail with a new value on
> the same thread is a new request, and `_started` still refuses to start a
> second run from one thread, so it is offered as a question.
>
> A reading that is not fresh never starts a run, whatever the thread holds
> (invariant 7; R1 review, C1): "thanks!" under a request read with the whole
> thread names that request's values again, and on a thread whose offer
> expired or went to others it would start the run nobody pressed. With no
> run on the thread it is only offered.

## `FromTheMail._about_the_run`, [line 368](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L368): Docstring

> The note a follow-up gets. It points at the run's card rather than quoting
> its state: `started_on` says a run exists, and the card already shows where
> it stands. The note is the mail's outcome, so the claim is kept (invariant 6).

## `FromTheMail._reply_says`, [line 635](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L635): Comment

Code: `said, [candidate_of(job, logins=logins)], self._asker, question=question`

> A reply to a standing question is read against the one job the thread
> settled, and told what was asked: before R1 the reader never saw the
> question, so "use GT7" named no field. It carries the recorded logins, so a
> reply that is the operator's sign-in name answers nothing (R1 review, I5).


## `FromTheMail._read`, [line 243](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L243): Note

Code: `if not answers_for(back, ctx.principal_id.value):`

> A reply to a run's question belongs to the run's starter (invariants 5 and
> 6; S1 round 1). The claim is tenant-wide and the poll looks through
> principals in order, so on a shared inbox a colleague reads the reply
> first. `AnswerRun` refuses them, and keeping their claim dropped the answer
> for good. So their look releases it and the starter's own look takes it.
> It also leaves a mark (`elsewhere_key`): if the question is still open when
> the run ends, `SayWhatHappened.answered_elsewhere` tells the starter that an
> answer arrived in a mailbox they cannot read. The look's summary counts the reply as left for
> the starter, and never as "none of them asks for a job".

## `FromTheMail._elsewhere`, [line 471](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L471): Note

Code: `again = await uow.workflow_runs.get(ctx.tenant_id, run.id)`

> The run is read again after the mark commits. `finish` may have ended the
> run and looked for the mark between this look's read and its mark; then
> nobody else will tell the starter, so this look does. Whichever of the two
> forgets the mark tells, so the starter hears it once (S1 round 2).

## `FromTheMail._answer_the_run`, [line 485](../../../../../../../backend/src/sro/application/chat/from_the_mail.py#L485): Note

Code: `await uow.tool_calls.forget(ctx.tenant_id, elsewhere_key(run.id, asking.get("id", "")))`

> The starter's own look took the reply, so a colleague's mark for this
> question is no longer true, whatever comes of the answer: a step or field
> question mail cannot answer, or a value `AnswerRun` refuses, must not end
> with "arrived in a mailbox you cannot read" (S1 round 2, N1).
