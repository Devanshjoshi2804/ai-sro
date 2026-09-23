# Notes for `backend/src/sro/application/chat/about_an_offer.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/about_an_offer.py`](../../../../../../../backend/src/sro/application/chat/about_an_offer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L1): Docstring

> Turn an offer that cannot simply run into a question in the conversation.
>
> The card used to grow boxes. One text input per name it still wanted, drawn
> under the sentence, and the press disabled until they were full -- and
> `asking.py` already says what is wrong with that, at length, because the run
> path learned it first:
>
>     It asks everybody for what it usually finds by itself, and on `Create a
>     Customer Type` it asked four times for two values, because that job
>     declares each field twice -- the label a person reads and the body key a
>     form posts.
>
> Then the limit work added a second box for a different reason: a value that
> will not fit, pre-filled, with the number beside it. Better than silence and
> still the same shape -- a form, in a card, in a panel that is already a
> conversation.
>
> So the card asks the way everything else here asks. A press that cannot start
> the job writes the question into the operator's own thread, and
> `converse._answer_the_question` takes it from there: one question, one answer,
> the next question, and when the last one lands a `job` decision with `resume`
> on it that the browser starts. That loop is built, it is tested, and until now
> the only way into it was to type a yes in the chat -- the card, which is where
> people actually press, went around it.
>
> **Nothing is decided here.** This writes a question and returns. What the
> person says next is read by the same door that reads everything else they say,
> against the same pending state, so there is one set of rules about what an
> answer means rather than two.

## module, [line 19](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L19): Note on the line above

Code: `DraftsForTheAsker = Callable[[RequestContext, Pending, str], Awaitable[bool]]`

> Write a mail to whoever sent the request, for a job stopping short of a
> value. A callable rather than the use case, so the drafter can be bound to this
> request's own tenant and operator.

## `AskAboutTheOffer`, [line 22](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L22): Docstring

> Ask, in the operator's own conversation, for what an offer still needs.

## `SayTheRunStarted`, [line 117](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L117): Docstring

> Put a run into the conversation that authorised it.
>
> The thread is the spine of a piece of work: the request arrives, the
> question is asked, the answer lands, and until now the story stopped
> there. The run started in the worker, its card was drawn on Home, and
> nothing in the conversation said which run came of the sentence somebody
> had just typed -- so the one place that holds the whole decision held
> everything except its result.
>
> A `run` message with the id on it is all the panel needs: the ledger has
> drawn a live card under one since the skills path existed, and the rig
> path never wrote one.
>
> Said by the browser rather than by the door that decided it, which is
> backwards-looking but true: the run is started in the worker, because the
> credential lives there, so the worker is the only thing that knows the id.

## `AskAboutTheOffer._also_settable`, [line 35](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L35): Docstring

> Fields this job can fill that the page does not ask for, and what
> each was last time. Empty where the job is unknown or declares none.

## `AskAboutTheOffer._what_the_boxes_hold`, [line 48](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L48): Docstring

> Every limit known for the names this question is about.
>
> The smaller of the two where both say something: a limit is a ceiling,
> and two ceilings mean the lower one is the truth. The browser's is kept
> rather than overwritten because it can know something this cannot --
> `too_long` is computed against what a run actually found.
>
> Silent about every failure. A job that cannot be read, a deployment
> with nothing documented, a name nothing declares -- all of them mean
> the question is asked exactly as it was asked before, which is what
> happened for every one of these until now.

## `AskAboutTheOffer.execute`, [line 65](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L65): Docstring

> The question that was asked, or `""` where there was nothing to ask.
>
> Empty rather than an error for an offer that needs nothing: a caller
> that got here about a job which turned out to be ready should start it,
> and a refusal would make that an error path instead of the ordinary
> one.

## `AskAboutTheOffer.__init__`, [line 33](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L33): Comment

Code: `self._drafts: DraftsForTheAsker | None = drafts`

> Optional throughout: a deployment with no mailbox asks the operator
> and nobody else, exactly as it did.

## `AskAboutTheOffer._also_settable`, [line 40](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L40): Comment

Code: `try:`

> Silent about every failure, exactly as the limits beside it are: a
> job this door cannot read is one whose question is asked as it was
> asked before. An offer is worth making and never worth a 404.

## `AskAboutTheOffer.execute`, [line 73](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L73): Comment

Code: `pending = replace(pending, limits=await self._what_the_boxes_hold(ctx, pending))`

> What is outstanding is what nobody supplied AND what was supplied in
> a form the box will not take.
>
> The second half is the case this door was built for and the case it
> first got wrong: an offer read out of a mail carrying a ten-character
> code for a four-character field has nothing MISSING, so it read as
> ready and asked nothing at all. Measured on the deployment
> 2026-09-18: `asked about mail_1a0b3da3e11ad236 in the conversation:
> nothing to ask`, on the one press this exists to answer.
>
> Order kept and duplicates dropped: a name can be both unsupplied and
> capped, and asking for it twice is the form this replaces.
> The limits this job's boxes are documented to hold, read here rather
> than taken from the browser.
>
> What arrives on the request is the offer's `too_long` map, which
> holds a name only where a value ALREADY overflows. So the question
> asked for a value nobody had yet carried no limit at all -- and
> `answered` refuses a too-long answer by consulting exactly that map.
> Measured on the deployment 2026-09-18: the question for `Customer
> Type` stored `"limits": {}`, a seventeen-character answer was taken
> for a four-character field, and the run typed it into the form and
> was refused by the WMS.
>
> The moment a limit is worth knowing is BEFORE somebody answers. So
> the job's own declared limits are read for every name it is about,
> and the question says the number the first time it asks.

## `AskAboutTheOffer.execute`, [line 79](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L79): Comment

Code: `offered=await self._also_settable(ctx, pending),`

> And what the job could ALSO fill, which nothing has to answer.
>
> The fourth door to make this offer and the last: the run's own
> question, the mail card, the chat door's job offer and this one
> all describe the same job to the same person, and an operator who
> presses a card is told what the one who typed a sentence is told.
> Measured on the deployment 2026-09-22 at 14:44 -- pressed "Yes,
> do it", was asked for Customer Type, and never learnt the job
> could set Department or Manufacturer at all.

## `AskAboutTheOffer.execute`, [line 83](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L83): Comment

Code: `asked = opening(pending, about)`

> The whole of what the card said, carried into a conversation that was
> not standing beside it. Every answer after this one gets the short
> question -- the context is said once, where it is needed.

## `AskAboutTheOffer.execute`, [line 86](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L86): Comment

Code: `for_operator=PrincipalId(ctx.principal_id.value),`

> The person who pressed. An offer is answered by whoever it was
> put in front of, and a question in somebody else's conversation
> is one they never see.

## `AskAboutTheOffer.execute`, [line 88](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L88): Comment

Code: `speaker=Speaker.ASSISTANT,`

> A question, not an announcement -- see `SayWhatHappened.execute`.

## `AskAboutTheOffer.execute`, [line 95](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L95): Comment

Code: `"offered": [list(one) for one in pending.offered],`

> What the job could ALSO fill, so a second browser reading
> the thread offers the same fields and an answer arriving
> minutes later is still an answer to this.

## `AskAboutTheOffer.execute`, [line 97](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L97): Comment

Code: `"limits": dict(pending.limits),`

> What the boxes hold, so the next question can say why it is
> being asked -- and so an answer that still will not fit is
> refused rather than carried into the form.

## `AskAboutTheOffer.execute`, [line 98](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L98): Comment

Code: `"mail_thread": pending.mail_thread,`

> The mail this was asked for in, so the run the ANSWER starts
> is findable by a reply to it -- the same as one the card
> starts directly.

## `AskAboutTheOffer.execute`, [line 103](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L103): Comment

Code: `if self._drafts is not None and mail_thread.strip():`

> And whoever sent the request, where the offer names a mail.
>
> Both places a job stops short of a value ask the same person, and
> wiring the draft only to the run made it unreachable for the case it
> was built for: a mail with no code in it is answered here, before any
> run starts, so a run never comes up short and never asks anybody.
>
> Nothing here can stop the question that has already been asked.

## `SayTheRunStarted.execute`, [line 130](../../../../../../../backend/src/sro/application/chat/about_an_offer.py#L130): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM and not ASSISTANT, which is the distinction `announce`
> draws: this is a thing that HAPPENED, not a thing anybody said.
> It also must not be mistaken for a question -- `pending_job`
> reads back the last thing the assistant decided, and a run
> announcement standing where a question should be would answer
> the next sentence into nothing.
