# Notes for `backend/src/sro/domain/chat/asking_the_asker.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/asking_the_asker.py`](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L1): Docstring

> The mail a run writes to whoever asked, when it cannot finish without them.
>
> The panel's question works because somebody is standing in front of it. The
> case this exists for is the one where nobody is: a request arrives naming a
> description and no code, the run goes looking, the mailbox does not say either,
> and the only person who can answer is whoever sent it -- who is not the
> operator, is not watching a panel, and may be in another country.
>
> **It is drafted and never sent.** What leaves this module is words; what sends
> them is a person pressing a button having read them. That is not a formality
> here. A mail is the least reversible thing this system does -- it cannot be
> unsent, it goes to somebody outside the company's own systems, and it goes over
> the operator's name. The approval ladder that guards a warehouse write guards
> this for the same reason and more strictly: a wrong record can be deleted.
>
> **The person is told what is missing and why, never what to do.** "The code
> must be four characters" is a fact about the system; "call it NSRO" is this
> system making up a customer type, which is exactly the guess the whole ladder
> refuses. So the draft asks, and it says enough that one reply can answer it:
> what is being made, what is already known, which field is short, and what the
> box will take.
>
> Pure. What it needs to know it is given -- there is no mailbox here, no model,
> and no clock.

## module, [line 5](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L5): Note on the line above

Code: `K_RE = "Re: "`

> What a reply is called when the request had a name. Gmail threads on its own
> id and every other client threads on the subject, so this matters to the person
> reading it rather than to us.

## module, [line 53](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L53): Note on the line above

Code: `K_SUBJECT = 200`

> How long a reply's subject may be. A forwarded chain stacks `Re:` and `Fwd:`
> prefixes until the line is unreadable; two hundred characters is a subject and
> anything longer is somebody's mail history.

## `draft_for`, [line 8](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L8): Docstring

> The subject and body of the mail that asks for what is missing.
>
> `about` is what the request was called, so the reply reads as a reply.
> Without one the subject names the job instead, which is the honest fallback
> -- a mail with an invented subject is one nobody recognises.
>
> `signed` is the operator this is sent on behalf of. Named rather than
> anonymous: somebody receiving "what should the Customer Type be?" from a
> system they have never heard of deletes it, and rightly.

## `worth_asking`, [line 56](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L56): Docstring

> Whether there is anything here a person could answer.
>
> A run that is not short of anything has nothing to ask, and a mail that
> says so is a mail that should not have been sent -- this system is careful about what it puts
> in somebody's inbox, and its own state is not it.

## `draft_for`, [line 14](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L14): Comment

Code: `f"I am working on {pending.title} from your request"`

> The title as it is, never lowercased. A mined title is a noun phrase
> -- `Create a Customer Type` -- and folding its case makes it read as
> an instruction: "I am setting up create a customer type".

## `draft_for`, [line 27](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L27): Comment

Code: `had = pending.values.get(wanted, "")`

> What is wrong, and why, in that order. A person told only "I need the
> Customer Type" sends back the one they already sent.

## `draft_for`, [line 43](../../../../../../../backend/src/sro/domain/chat/asking_the_asker.py#L43): Comment

Code: `rest = list(pending.missing[1:])`

> The rest, named but not asked about: one question per mail is the same
> rule the panel keeps, and a list of four is a mail somebody answers one
> line of.
