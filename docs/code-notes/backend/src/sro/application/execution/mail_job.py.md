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

## module, [line 37](../../../../../../../backend/src/sro/application/execution/mail_job.py#L37): Note on the line above

Code: `K_MESSAGES = 5`

> How much of a conversation the model reads: the latest few messages. A
> reply answers what was said last; a thread three weeks deep is not context,
> it is noise the model will quote from.

## module, [line 39](../../../../../../../backend/src/sro/application/execution/mail_job.py#L39): Note on the line above

Code: `K_BODY = 2000`

> How much of one message it reads. Enough for a request and its quoted
> history to be recognisable; a newsletter is not what is being answered.

## `Written`, [line 45](../../../../../../../backend/src/sro/application/execution/mail_job.py#L45): Docstring

> One mail, as the model wrote it and as it will be sent.

## `write_the_mail`, [line 58](../../../../../../../backend/src/sro/application/execution/mail_job.py#L58): Docstring

> The mail this job sends, or why it could not be written.
>
> Never an address nobody gave. A mail to the wrong person is the one step of
> a mail that cannot be taken back, so the draft is checked by `check_draft`
> before anything can send it: it goes only to the conversation's participants,
> to the To, Cc and Bcc of the mail the job's demonstration actually sent
> (`_allowed`), and to the addresses its operator named for the job; every value
> in its body is cited to a message that says it or is one of the run's values.
> The run's values never name a recipient: they are mail text as often as the
> operator's, and mail text is untrusted (decided 2026-09-25).
>
> `Written.to` and `Written.bcc` are built from the addresses the check read,
> never the model's string, so the header sent is exactly what was checked.
>
> A failed check is returned as the reason. A refusal of who the mail goes to is
> `Unaddressed`, which the tool lane turns into the run's `recipient` question;
> any other is a plain `str`, a failed step. Nothing is sent either way. The
> log line carries counts only.

## `Unaddressed`, [line 54](../../../../../../../backend/src/sro/application/execution/mail_job.py#L54): Docstring

> A draft refused for who it goes to: the reason, marked so the run asks the
> operator who the mail goes to rather than failing the step -- the tool lane on
> Steel, `draft_the_mail_job` on the draft path. A `str`, so the extension's
> legacy `_through_the_mailbox`, which QA no longer runs, still just stops on it.

## `_allowed`, [line 137](../../../../../../../backend/src/sro/application/execution/mail_job.py#L137): Docstring

> Who this job may write to besides the conversation: for each Send its
> evidence pressed, the To, Cc and Bcc of the one message the send call named
> that Gmail keeps as SENT -- read through the connector's `get_message` -- and
> the recipients its operator confirmed. A send that names no such message, or
> more than one, grants nobody.

## `send_the_mail`, [line 173](../../../../../../../backend/src/sro/application/execution/mail_job.py#L173): Docstring

> Send it, and say what Gmail answered: its id, or why it did not go.
>
> The id is remembered as a mail this system sent, exactly as `SendTheDraft`
> does, so the next look in the mailbox does not read it as a request.

## `MailHand`, [line 213](../../../../../../../backend/src/sro/application/execution/mail_job.py#L213): Docstring

> A run's way to write and send a mail through the mailbox's API, for a
> step that sends one in a job that does other things too.

## `draft_the_mail_job`, [line 220](../../../../../../../backend/src/sro/application/execution/mail_job.py#L220): Docstring

> Write the mail this job sends and park the run on the operator's press.
>
> Ends `stopped` with one step `awaiting`, which is what a run waiting on a
> person already looks like -- and which, unlike `running`, does not hold
> this browser: the operator's other jobs are not blocked by a mail they
> have not read yet.

## `_conversation`, [line 276](../../../../../../../backend/src/sro/application/execution/mail_job.py#L276): Docstring

> The messages of the conversation this job answers, oldest first.

## `draft_the_mail_job`, [line 246](../../../../../../../backend/src/sro/application/execution/mail_job.py#L246): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM for the reason `DraftForTheAsker` gives: a draft standing where
> the assistant's question should be would eat the operator's next
> sentence.

## `draft_the_mail_job`, [line 256](../../../../../../../backend/src/sro/application/execution/mail_job.py#L256): Comment

Code: `"job": workflow.id,`

> What makes this the job's own mail rather than a question to
> whoever asked: `SendTheDraft` finishes the run on it.

## `redraft_the_mail_job`, [line 294](../../../../../../../backend/src/sro/application/execution/mail_job.py#L294): Docstring

> The operator answered who a drafted run's mail goes to: keep the address on the
> job, take the question by a compare-and-set on the run's progress, then draft
> again. Only an answered `recipient` question is taken, and only once: a second
> resume of the same answer (two presses, a retry) finds it gone and drafts
> nothing. A crash after the question is taken and before the draft leaves the
> run stopped with the address already kept, so running the job again goes
> through without asking.

## `keep_the_named`, [line 324](../../../../../../../backend/src/sro/application/execution/mail_job.py#L324): Docstring

> The one writer of a job recipient, for both runtimes: each address the
> operator's answer named, with who named it and when. An upsert, so carrying an
> answer out twice keeps one row.

## `_ask_who`, [line 340](../../../../../../../backend/src/sro/application/execution/mail_job.py#L340): Docstring

> The draft path's `recipient` question: the run stops (holding no browser, as a
> draft waiting on its press does), with the question on its progress and a
> `run_asks` in the operator's thread. `AnswerRun` takes an answer on a stopped
> drafted run for this one kind, and resumes it through `redraft_the_mail_job`
> rather than a Temporal signal.
