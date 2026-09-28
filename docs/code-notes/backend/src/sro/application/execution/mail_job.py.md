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

## module, [line 49](../../../../../../../backend/src/sro/application/execution/mail_job.py#L49): Note on the line above

Code: `K_MESSAGES = 5`

> How much of a conversation the model reads: the latest few messages. A
> reply answers what was said last; a thread three weeks deep is not context,
> it is noise the model will quote from.

## module, [line 51](../../../../../../../backend/src/sro/application/execution/mail_job.py#L51): Note on the line above

Code: `K_BODY = 2000`

> How much of one message it reads. Enough for a request and its quoted
> history to be recognisable; a newsletter is not what is being answered.

## `Written`, [line 61](../../../../../../../backend/src/sro/application/execution/mail_job.py#L61): Docstring

> One mail, as the model wrote it and as it will be sent.

## `write_the_mail`, [line 78](../../../../../../../backend/src/sro/application/execution/mail_job.py#L78): Docstring

> The mail this job sends, or why it could not be written.
>
> Never an address nobody gave. A mail to the wrong person is the one step of
> a mail that cannot be taken back, so the draft is checked by `check_draft`
> before anything can send it: it goes only to the conversation's participants,
> to the To, Cc and Bcc of the mail the job's demonstration actually sent
> (`_allowed`), to the addresses its operator named for the job, and to the
> addresses the operator's own `request` names; every value in its body is cited
> to a message or the request that says it, or is one of the run's values. The
> run's values never name a recipient: they are mail text as often as the
> operator's, and mail text is untrusted (decided 2026-09-25).
>
> `request` (S4) is the words the run's starter typed in their own panel thread
> for this run (`the_operator_s_words`) plus their answers to its questions. It
> goes to the model as trusted JSON, never fenced: it is the operator speaking,
> not mail. QA 2026-09-28: a chat-started `Compose and Send Email` with no body
> parameter and no demonstrated recipient came back `to=""`, `body=""` on both
> flash models, because the writer never saw what the operator asked for. An
> address the request names that the draft goes to is kept on the job as
> confirmed by the starter (`keep_the_named`), as the recipient answer is.
>
> `Written.to` and `Written.bcc` are built from the addresses the check read,
> never the model's string, so the header sent is exactly what was checked.
>
> A failed check is returned as the reason. A refusal of who the mail goes to is
> `Unaddressed`, which the tool lane turns into the run's `recipient` question;
> a refused value is `Unwritten`, carrying the refused draft so the operator can
> be shown it; an empty or failed answer is a plain `str`. The draft path asks
> the operator (`mail_body`) on every one; the tool lane fails the step on the
> last two. Nothing is sent either way. The log line carries counts only.

## `Unwritten`, [line 74](../../../../../../../backend/src/sro/application/execution/mail_job.py#L74): Docstring

> A draft refused for a value in its body nobody gave: the reason, carrying the
> refused `draft`. The draft path shows it in its `mail_body` question, so a yes
> makes those words the operator's own request and the redraft may cite them.

## `Unaddressed`, [line 70](../../../../../../../backend/src/sro/application/execution/mail_job.py#L70): Docstring

> A draft refused for who it goes to: the reason, marked so the run asks the
> operator who the mail goes to rather than failing the step -- the tool lane on
> Steel, `draft_the_mail_job` on the draft path. A `str`, so the extension's
> legacy `_through_the_mailbox`, which QA no longer runs, still just stops on it.

## `_allowed`, [line 176](../../../../../../../backend/src/sro/application/execution/mail_job.py#L176): Docstring

> Who this job may write to besides the conversation: for each Send its
> evidence pressed, the To, Cc and Bcc of the one SENT message in the threads
> its send call named whose Gmail time falls within `K_SEND_WINDOW_S` of the
> press -- read through the connector's `get_thread` -- and the recipients its
> operator confirmed. None or more than one such message grants nobody.
> A SENT mail this system sent is left out first: one that carries the
> `X-SRO-Marker` header, or whose id or marker holds a `sent_key`. The look's
> `mail_key` read-claim alone never leaves it out -- the look reads the
> operator's own Send too -- except a row written with the tool `K_OURS`: that
> is a send from before `sent_key` (`mail_key(id)`, or main's
> `mail:{operator}:{id}`), never recipient-checked, so it stays ours.
>
> One log line per call says why the demonstration granted what it did, in
> counts only: Send clicks, clicks whose calls named no thread (none, or more
> than `K_SENT_THREADS`), threads and messages read, SENT mails in the window,
> and clicks that found none, more than one, or exactly one. QA's `Compose and
> Send Email` came back with nobody (S4); this line is how the next run says
> which way. A new compose is the suspect: its Send may name its new thread only
> by the account-side `thread-a:r…` id the API does not know, which reads as
> "named no thread" or as "found no sent mail" among the other threads the sync
> answered with.

## `send_the_mail`, [line 230](../../../../../../../backend/src/sro/application/execution/mail_job.py#L230): Docstring

> Send it, and say what Gmail answered: its id, or why it did not go.
>
> The id is remembered as a mail this system sent, exactly as `SendTheDraft`
> does, so the next look in the mailbox does not read it as a request.

## `MailHand`, [line 261](../../../../../../../backend/src/sro/application/execution/mail_job.py#L261): Docstring

> A run's way to write and send a mail through the mailbox's API, for a
> step that sends one in a job that does other things too. `write` takes the
> operator's own request (`LaneContext.request` on Steel; the legacy extension
> runtime passes none).

## `draft_the_mail_job`, [line 269](../../../../../../../backend/src/sro/application/execution/mail_job.py#L269): Docstring

> Write the mail this job sends and park the run on the operator's press.
>
> Ends `stopped` with one step `awaiting`, which is what a run waiting on a
> person already looks like -- and which, unlike `running`, does not hold
> this browser: the operator's other jobs are not blocked by a mail they
> have not read yet.
>
> A mail that cannot be written never stops silently (S4): who it goes to asks
> `recipient`; an empty body, a model error or a refused value asks `mail_body`
> ("What should the mail say?"), the refused draft shown. `answers` are the
> starter's answers to that question, trusted as the request is.

## `_conversation`, [line 349](../../../../../../../backend/src/sro/application/execution/mail_job.py#L349): Docstring

> The messages of the conversation this job answers, oldest first.

## `draft_the_mail_job`, [line 319](../../../../../../../backend/src/sro/application/execution/mail_job.py#L319): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM for the reason `DraftForTheAsker` gives: a draft standing where
> the assistant's question should be would eat the operator's next
> sentence.

## `draft_the_mail_job`, [line 329](../../../../../../../backend/src/sro/application/execution/mail_job.py#L329): Comment

Code: `"job": workflow.id,`

> What makes this the job's own mail rather than a question to
> whoever asked: `SendTheDraft` finishes the run on it.

## `redraft_the_mail_job`, [line 367](../../../../../../../backend/src/sro/application/execution/mail_job.py#L367): Docstring

> The operator answered who a drafted run's mail goes to, or what it says: keep
> any address on the job, take the question by a compare-and-set on the run's
> progress, then draft again with the answer as part of the operator's request
> (a yes to a refused draft adds that draft's words). Only an answered
> `recipient` or `mail_body` question is taken, and only once: a second
> resume of the same answer (two presses, a retry) finds it gone and drafts
> nothing. A crash after the question is taken and before the draft leaves the
> run stopped with the address already kept, so running the job again goes
> through without asking.

## `keep_the_named`, [line 419](../../../../../../../backend/src/sro/application/execution/mail_job.py#L419): Docstring

> The one writer of a job recipient, for both runtimes: each address the
> operator's answer named, with who named it and when. An upsert, so carrying an
> answer out twice keeps one row.

## `the_operator_s_words`, [line 409](../../../../../../../backend/src/sro/application/execution/mail_job.py#L409): Docstring

> What the run's starter typed for it in their own panel (`the_request`): read
> from the starter's own current thread -- `opened_by` is theirs, and only a
> thread's opener can say anything in it (S1) -- so a colleague's words are
> never among them. A run the mail door started carries a mail key as its
> offer, which is never a thread message, so it has none: a request relayed
> from mail never becomes trusted.
>
> Ceiling: only the starter's current thread is read. A run whose starter
> opened a new thread before it drafted has no request, and asks instead.

## `_ask`, [line 435](../../../../../../../backend/src/sro/application/execution/mail_job.py#L435): Docstring

> The draft path's questions, `recipient` and `mail_body`: the run stops (holding no browser, as a
> draft waiting on its press does), with the question on its progress and a
> `run_asks` in the operator's thread. `AnswerRun` takes an answer on a stopped
> drafted run for this one kind, and resumes it through `redraft_the_mail_job`
> rather than a Temporal signal.
