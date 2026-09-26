# Notes for `backend/src/sro/application/execution/mail_job.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/mail_job.py`](../../../../../../../backend/src/sro/application/execution/mail_job.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/mail_job.py#L1): Docstring

> A mail job, drafted through the mailbox's API and sent on a press.
>
> See `domain/execution/mail_job.py` for why a job that is nothing but mail is not
> replayed through Gmail's page. This is the half that does it: read the
> conversation the job answers, have a model write the mail, and put it in front
> of the operator as the draft card they already know -- `SendTheDraft` sends it,
> once, when they press, and finishes the run on Gmail's answer.
>
> Nothing here sends. The tool caller is used to READ the conversation, and the
> only write is into the operator's own thread.

## module, [line 28](../../../../../../../backend/src/sro/application/execution/mail_job.py#L28): Note on the line above

Code: `K_MESSAGES = 5`

> How much of a conversation the model reads: the latest few messages. A
> reply answers what was said last; a thread three weeks deep is not context,
> it is noise the model will quote from.

## module, [line 30](../../../../../../../backend/src/sro/application/execution/mail_job.py#L30): Note on the line above

Code: `K_BODY = 2000`

> How much of one message it reads. Enough for a request and its quoted
> history to be recognisable; a newsletter is not what is being answered.

## `Written`, [line 36](../../../../../../../backend/src/sro/application/execution/mail_job.py#L36): Docstring

> One mail, as the model wrote it and as it will be sent.

## `write_the_mail`, [line 44](../../../../../../../backend/src/sro/application/execution/mail_job.py#L44): Docstring

> The mail this job sends, or why it could not be written.
>
> Never an address nobody gave. A mail to the wrong person is the one step of
> a mail that cannot be taken back, so the draft is checked by `check_draft`
> before anything can send it: it goes only to the conversation's participants
> (a sender, or a recipient in `to` or `cc`) and to the addresses the job's own
> evidence typed into a recipient field (`sent_to`), and every value in its body
> is cited to a message that says it or is one of the run's values. The run's
> values no longer name a recipient: they are mail text as often as the
> operator's, and mail text is untrusted (decided 2026-09-25).
>
> A failed check is returned as the reason, a `str`, which every caller turns
> into a stopped step and a question -- nothing is sent. A job started with no
> thread and no demonstrated recipient therefore always asks.

## `send_the_mail`, [line 115](../../../../../../../backend/src/sro/application/execution/mail_job.py#L115): Docstring

> Send it, and say what Gmail answered: its id, or why it did not go.
>
> The id is remembered as a mail this system sent, exactly as `SendTheDraft`
> does, so the next look in the mailbox does not read it as a request.

## `MailHand`, [line 154](../../../../../../../backend/src/sro/application/execution/mail_job.py#L154): Docstring

> A run's way to write and send a mail through the mailbox's API, for a
> step that sends one in a job that does other things too.

## `draft_the_mail_job`, [line 161](../../../../../../../backend/src/sro/application/execution/mail_job.py#L161): Docstring

> Write the mail this job sends and park the run on the operator's press.
>
> Ends `stopped` with one step `awaiting`, which is what a run waiting on a
> person already looks like -- and which, unlike `running`, does not hold
> this browser: the operator's other jobs are not blocked by a mail they
> have not read yet.

## `_conversation`, [line 214](../../../../../../../backend/src/sro/application/execution/mail_job.py#L214): Docstring

> The messages of the conversation this job answers, oldest first.

## `draft_the_mail_job`, [line 185](../../../../../../../backend/src/sro/application/execution/mail_job.py#L185): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM for the reason `DraftForTheAsker` gives: a draft standing where
> the assistant's question should be would eat the operator's next
> sentence.

## `draft_the_mail_job`, [line 194](../../../../../../../backend/src/sro/application/execution/mail_job.py#L194): Comment

Code: `"job": workflow.id,`

> What makes this the job's own mail rather than a question to
> whoever asked: `SendTheDraft` finishes the run on it.
