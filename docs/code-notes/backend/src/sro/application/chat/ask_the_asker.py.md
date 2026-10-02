# Notes for `backend/src/sro/application/chat/ask_the_asker.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/ask_the_asker.py`](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L1): Docstring

> Draft a mail to whoever asked, and -- separately -- send the one approved.
>
> Two use cases in one module because they are two halves of one rule, and the
> rule is the reason this exists at all: **what drafts never sends, and what
> sends never drafts.** A mail cannot be unsent, it leaves the company over the
> operator's name, and the only thing standing between a model's reading of a
> situation and somebody's inbox is a person who read the words first. Splitting
> them is what makes that structural rather than a promise -- there is no path
> through `DraftForTheAsker` that reaches the mailbox.
>
> The case: a request arrives naming a description and no code. The run goes
> looking, the thread does not say either, and the run ends short. The panel
> asks the operator, which is right and often enough -- but the operator did not
> write the request and may not know. The person who does is whoever sent it,
> and until now nothing could reach them.
>
> **One draft per run.** A run that stopped twice does not write twice, and a
> person does not get two mails about one request. The check is the run's own
> row rather than a counter here, because a worker restart must not buy anybody
> a second mail.

## `DraftForTheAsker`, [line 25](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L25): Docstring

> Write the mail, put it in front of the operator, and stop.
>
> Nothing here can send. The tool caller it holds is used to READ the
> conversation -- who asked, and what the message id is to reply to -- and
> the only write it makes is into the operator's own thread.

## `_address`, [line 151](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L151): Docstring

> The address out of `Tanisha Pradhan <tanisha@example.com>`.
>
> A display name is not something to send to, and a header with none is
> already an address. Nothing is invented where neither is there: an empty
> answer means nobody to ask, which is a thing this door says rather than
> guesses past.

## `SendTheDraft`, [line 158](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L158): Docstring

> Send the mail the operator read, and nothing else.
>
> **The words are taken from the thread, never from the caller.** The panel
> sends an id; this re-reads the draft that was actually put in front of
> somebody and sends that. A door that sent a body handed to it would be a
> door where the words that go out and the words that were read are two
> different things, and every guarantee this system makes about a person
> having seen what they authorised would rest on a browser being honest.
>
> The press is the authorisation and it is the only one. Nothing here
> decides that a mail should go -- it decides that this mail, which somebody
> has read, may.

## `_the_draft`, [line 353](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L353): Docstring

> The drafted mail with that id, if it is still the last word on it.
>
> By id and not "the newest draft": two runs can both be waiting, and a press
> on the older card must not send the newer mail.

## `DraftForTheAsker.execute`, [line 40](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L40): Docstring

> Whether a draft was put in front of somebody.
>
> Called from both places a job stops short of a value, because there are
> two and only one of them has a run behind it. A card that cannot be
> answered from what the mail said asks in the conversation before
> anything starts; a run that goes looking and comes back empty asks
> after. The person who can answer is the same person either way, and
> wiring this only to the second made it unreachable for the case it was
> built for -- a mail with no code in it never reaches a run.
>
> `thread` is the conversation to write into, and it wins over the run's
> own: an offer has one before any run exists.
>
> False for every ordinary reason -- no mailbox behind it, nothing
> missing, somebody already asked. None of those is a failure.

## `DraftForTheAsker._already_drafted`, [line 107](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L107): Docstring

> Whether somebody already has a draft in front of them for this mail.
>
> Read off the operator's own thread, which is where the draft was put:
> there is no run to hang a flag on before one starts, and the thread is
> already the record of what has been said. A draft that was SENT is not
> a reason to refuse another either -- the run column covers that, and
> this covers the window before it exists.

## `DraftForTheAsker._who_asked`, [line 124](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L124): Docstring

> Who to answer, which message to answer, and what it was called.
>
> The FIRST message of the conversation, not the last: a thread the
> operator has replied to would otherwise have this system writing to the
> operator about the operator's own request. The first message is the
> request, and whoever sent it is who to ask.

## `SendTheDraft.execute`, [line 173](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L173): Docstring

> The address it went to, or `""` where nothing was sent.
>
> Raises nothing for an ordinary refusal. A draft already sent, a draft
> nobody can find, a run that has since been asked about another way --
> all are reasons not to send, and none of them is an error worth a 500.


## `SendTheDraft._claim`, [line 294](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L294): Docstring

> Take this draft, or say somebody already has it.
>
> Never given back. A send that timed out may well have landed, and a
> claim released on failure would retry it into a second mail -- the same
> rule the connector ledger keeps everywhere else, and for the strongest
> reason it has: a duplicate mail cannot be deleted afterwards.
>
> **Keyed by the draft alone, not by the draft and whoever pressed.** A
> draft belongs to one thread and a thread to one operator, so the
> principal added nothing to the identity -- what it added was a second
> claim for the same words. `threads.get` is scoped to the tenant and
> not to the person, so a colleague holding the id could press it again
> and the guard would let them, which is the one thing this claim
> exists to stop. The draft id is unique in the tenant on its own.

## `SendTheDraft._say`, [line 311](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L311): Docstring

> What happened, in the conversation the draft was read in.
>
> `sent` is whether it actually went. Both answers end the press -- the
> claim is taken either way, and a send that may have gone out is not one
> to try again -- but the row must not say a mail was sent when nobody
> knows whether it was. One kind, one honest flag, rather than a line
> reading `mail_sent` under the words "I could not reach the mailbox".

## `DraftForTheAsker.execute`, [line 63](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L63): Comment

Code: `if run is not None and run.asked_the_asker:`

> One per run, read off the row rather than counted here: a worker that
> restarted between two stops must not buy anybody a second mail.

## `DraftForTheAsker.execute`, [line 68](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L68): Comment

Code: `if await self._already_drafted(owner, conversation):`

> And one per REQUEST, for the half that has no run yet. Two presses on
> one card would otherwise put two drafts in front of somebody, and the
> second is a mail they can send after the first has gone.

## `DraftForTheAsker.execute`, [line 86](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L86): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM, not ASSISTANT: `pending_job` reads back the last thing the
> ASSISTANT decided, and a draft standing where the question should
> be would eat the operator's next sentence.

## `DraftForTheAsker._who_asked`, [line 146](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L146): Comment

Code: `str(first.get("rfc822_message_id") or ""),`

> The mail's OWN id and nothing else. Gmail's internal id used to
> stand in for it, and a wrong `In-Reply-To` is worse than none:
> the header names a message the receiving client has never heard
> of, so it draws an orphan AND has thrown away the subject it
> would otherwise have threaded on.
>
> Measured on the deployment 2026-09-18: the mail this system sent
> arrived in the recipient's mailbox as a new conversation rather
> than under the request it was answering.

## `SendTheDraft.execute`, [line 190](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L190): Comment

Code: `if not await self._claim(uow, ctx, message_id):`

> The press itself, claimed before anything else.
>
> The run column below is one mail per RUN, and it is the only claim
> there was -- so the half with no run behind it had none at all. A
> card asks before any run exists (`run_id` is ""), `run` is None, the
> check is skipped, and every press sends another mail. Measured on the
> live deployment 2026-09-18: two identical mails to one person about
> one request, 15:05:34 and 15:09:06, both logged `asked ... about `
> with nothing after the `about`.
>
> Keyed by the DRAFT, which exists on both paths and is unique to the
> words somebody actually read.

## `SendTheDraft.execute`, [line 200](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L200): Comment

Code: `if run is not None:`

> Claimed before the send, not after. Between a check and a mailbox
> sits a network call, and a second press landing in that gap is a
> second mail about one request -- which is the one thing the
> column exists to stop.

## `SendTheDraft.execute`, [line 218](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L218): Comment

Code: `"thread_id": str(draft.get("thread") or ""),`

> Inside the conversation it answers. A reply that starts
> its own thread cannot be matched back to the run waiting
> on it, so the person answers into a void.

## `SendTheDraft.execute`, [line 243](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L243): Comment

Code: `logger.warning(`

> The claim stands. A send that may have gone out and cannot be
> shown to have is not one to try again -- the same rule the write
> ladder keeps, and for a stronger reason: a duplicate mail cannot
> be deleted afterwards.

## `SendTheDraft._say`, [line 331](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L331): Comment

Code: `decision={`

> The run AND the draft, so the panel can stop offering a
> press under words that have already left. The run is
> empty on the half that asks before any run exists, and a
> panel keyed only on that went on showing `Send it` under
> a mail already in somebody's inbox.

## `SendTheDraft._say`, [line 335](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L335): Comment

Code: `"to": to,`

> Who is being waited ON. The sentence says it and the
> panel had to read the sentence to know it, which is
> a panel parsing prose to find a fact the decision
> was already carrying everything else about.

## `_the_draft`, [line 358](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L358): Comment

Code: `if str(getattr(message, "id", "")) == str(message_id):`

> Both sides through `str`: a message id is an `Identifier`, and a
> caller holding one compares unequal to the same id read back off a
> row as text. The two were never going to match by accident, which is
> the worst kind of mismatch -- every draft would quietly refuse.

## `SendTheDraft.execute`, [line 175](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L175): Comment

Code: `thread = await uow.threads.get_for_answer(ctx.tenant_id, thread_id)`

> Locked, as an answer locks it, and the claim is taken under the same
> lock: the press and the answer are ordered. A press after the answer finds the
> question closed.

## `SendTheDraft.execute`, [line 183](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L183): Comment

Code: `if not question or not still_asking(thread.messages, question):`

> A draft asks about the question standing when it was written. Once that
> is answered -- typed in the chat, or by the sender's reply -- the server
> refuses to send it, whatever the panel still shows. QA 2026-09-29: the
> PHARM26 draft was sent at 10:14:21, after its question was answered at
> 10:13:50, asking the sender for a value already given.

## `SendTheDraft.execute`, [line 278](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L278): Comment

Code: `if still_asking(thread.messages, question)`

> The answer can land while the mail is in flight: the press claimed it with
> the question standing. Then "I will carry on when they reply" would be about a
> run that no longer waits on them, so the line says what happened instead.
> Nothing is sent to the sender to take it back -- that is a separate decision.

## `SendTheDraft.execute`, [line 227](../../../../../../../backend/src/sro/application/chat/ask_the_asker.py#L227): Comment

Code: `await self._unclaim(ctx, message_id, run_id)`

> `NotConnected` and `NotSent` are definite: the mailbox was never asked to send. The claim
> `draft:{id}` and the run's `asked_the_asker` are given back, and the message is a `mail_not_sent`,
> a kind of its own because an already-installed extension marks a draft done only on
> `mail_sent`; the card keeps its Send it and the operator reconnects and presses again rather than writing
> the mail by hand. A failure that may have gone out keeps both: a second press would send it
> twice, and the text says to look in Sent and, if it is not there, to send it from the
> mailbox.
