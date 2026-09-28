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

## module, [line 50](../../../../../../../backend/src/sro/application/execution/mail_job.py#L50): Note on the line above

Code: `K_MESSAGES = 5`

> How much of a conversation the model reads: the latest few messages. A
> reply answers what was said last; a thread three weeks deep is not context,
> it is noise the model will quote from.

## module, [line 52](../../../../../../../backend/src/sro/application/execution/mail_job.py#L52): Note on the line above

Code: `K_BODY = 2000`

> How much of one message it reads. Enough for a request and its quoted
> history to be recognisable; a newsletter is not what is being answered.

## `Written`, [line 60](../../../../../../../backend/src/sro/application/execution/mail_job.py#L60): Docstring

> One mail, as the model wrote it and as it will be sent.

## `write_the_mail`, [line 79](../../../../../../../backend/src/sro/application/execution/mail_job.py#L79): Docstring

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
> address the request names that the draft goes to is carried on `Written.named`
> and kept on the job only once the mail has gone (`send_the_mail`, or
> `SendTheDraft` on the press), never while it is being written (S4 round 1,
> I3): a typo in a draft nobody sent is nobody's recipient.
>
> `shown` is a refused draft the operator said yes to (S4 round 1, C1): no model
> is asked; the draft is checked again with its own body `vouched` for, so only
> its values are the operator's -- who it goes to is checked exactly as a
> model's draft is -- and nothing of it enters `request`.
>
> `Written.to` and `Written.bcc` are built from the addresses the check read,
> never the model's string, so the header sent is exactly what was checked.
>
> A failed check is returned as the reason. A refusal of who the mail goes to is
> `Unaddressed`, which the tool lane turns into the run's `recipient` question;
> a refused value is `Unwritten`, carrying the refused draft so the operator can
> be shown it; an empty or failed answer is a plain `str`. Both runtimes ask the
> starter `mail_body` on the last two: the draft path, and the tool lane on
> Steel. Nothing is sent either way. The log line carries counts only.

## `Unwritten`, [line 75](../../../../../../../backend/src/sro/application/execution/mail_job.py#L75): Docstring

> A draft refused for a value in its body nobody gave: the reason, carrying the
> refused `draft` (to, subject, body). The draft path shows it in its
> `mail_body` question, and a yes uses exactly that draft (`shown`); its text
> never becomes the request, which would hand mail-borne words to the trusted
> block (S4 round 1, C1).

## `Unaddressed`, [line 71](../../../../../../../backend/src/sro/application/execution/mail_job.py#L71): Docstring

> A draft refused for who it goes to: the reason, marked so the run asks the
> operator who the mail goes to rather than failing the step -- the tool lane on
> Steel, `draft_the_mail_job` on the draft path. A `str`, so the extension's
> legacy `_through_the_mailbox`, which QA no longer runs, still just stops on it.

## `_allowed`, [line 190](../../../../../../../backend/src/sro/application/execution/mail_job.py#L190): Docstring

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
> A Send click whose calls name no `thread-f:` thread -- a new compose names its
> new mail only by the account-side `thread-a:` id the API does not know (QA,
> 2026-09-28: 3 `/i/s` POSTs, 4 `thread-a:` ids each, no `thread-f:`) -- is
> looked up in the operator's Sent mail instead (`_sent_around`): one
> `search_threads` for `in:sent` within `K_SEND_WINDOW_S` either side of the
> click, then `get_message` for each hit's thread. Those threads then go
> through exactly the filters a `thread-f:` thread does, so one sent mail
> grants its To, Cc and Bcc, and none or several grant nobody.
>
> One log line per call says why the demonstration granted what it did, in
> counts only: Send clicks, clicks whose calls named no thread (none, or more
> than `K_SENT_THREADS`), clicks looked up in Sent, threads and messages read,
> SENT mails in the window, and clicks that found none, more than one, or
> exactly one. Addresses never reach it.

## `send_the_mail`, [line 263](../../../../../../../backend/src/sro/application/execution/mail_job.py#L263): Docstring

> Send it, and say what Gmail answered: its id, or why it did not go.
>
> The id is remembered as a mail this system sent, exactly as `SendTheDraft`
> does, so the next look in the mailbox does not read it as a request.
>
> Once Gmail says it went, the addresses the starter's own words named
> (`Written.named`) are kept on the job, confirmed by the run's principal --
> the starter on Steel. Never before: a mail that did not go names nobody.

## `MailHand`, [line 297](../../../../../../../backend/src/sro/application/execution/mail_job.py#L297): Docstring

> A run's way to write and send a mail through the mailbox's API, for a
> step that sends one in a job that does other things too. `write` takes the
> operator's own request (`LaneContext.request` on Steel; the legacy extension
> runtime passes none).

## `draft_the_mail_job`, [line 305](../../../../../../../backend/src/sro/application/execution/mail_job.py#L305): Docstring

> Write the mail this job sends and park the run on the operator's press.
>
> Ends `stopped` with one step `awaiting`, which is what a run waiting on a
> person already looks like -- and which, unlike `running`, does not hold
> this browser: the operator's other jobs are not blocked by a mail they
> have not read yet.
>
> A mail that cannot be written never stops silently (S4): who it goes to asks
> `recipient`; an empty body, a model error or a refused value asks `mail_body`
> ("What should the mail say?"), the refused draft shown. The starter's answers
> to it are `Progress.told`, trusted as the request is; `shown` is the refused
> draft they said yes to. The card carries `named`, the addresses kept once the
> press sends it.

## `_conversation`, [line 389](../../../../../../../backend/src/sro/application/execution/mail_job.py#L389): Docstring

> The messages of the conversation this job answers, oldest first.

## `_answer`, [line 396](../../../../../../../backend/src/sro/application/execution/mail_job.py#L396): Docstring

> One call to the mailbox, read as a JSON object. A mailbox that cannot be
> reached, or an answer that is not JSON, reads as empty -- the callers grant
> nobody or read no conversation from it -- and only the tool's name is logged.

## `draft_the_mail_job`, [line 358](../../../../../../../backend/src/sro/application/execution/mail_job.py#L358): Comment

Code: `speaker=Speaker.SYSTEM,`

> SYSTEM for the reason `DraftForTheAsker` gives: a draft standing where
> the assistant's question should be would eat the operator's next
> sentence.

## `draft_the_mail_job`, [line 368](../../../../../../../backend/src/sro/application/execution/mail_job.py#L368): Comment

Code: `"job": workflow.id,`

> What makes this the job's own mail rather than a question to
> whoever asked: `SendTheDraft` finishes the run on it.

## `redraft_the_mail_job`, [line 411](../../../../../../../backend/src/sro/application/execution/mail_job.py#L411): Docstring

> The operator answered who a drafted run's mail goes to, or what it says: keep
> any address on the job, take the question by a compare-and-set on the run's
> progress, then draft again with the answer as part of the operator's request
> (`Progress.told`, written in the same compare-and-set) -- or, for a yes to a
> refused draft, with exactly that draft (`shown`). Only an answered
> `recipient` or `mail_body` question is taken, and only once: a second
> resume of the same answer (two presses, a retry) finds it gone and drafts
> nothing. A crash after the question is taken and before the draft leaves the
> run stopped with the address already kept, so running the job again goes
> through without asking.

## `keep_the_named`, [line 467](../../../../../../../backend/src/sro/application/execution/mail_job.py#L467): Docstring

> The one writer of a job recipient, for both runtimes: each address the
> operator's answer named, with who named it and when. An upsert, so carrying an
> answer out twice keeps one row.

## `the_operator_s_words`, [line 455](../../../../../../../backend/src/sro/application/execution/mail_job.py#L455): Docstring

> What the run's starter typed for it in their own panel (`the_request`): read
> from the thread that holds the run's offer, and only one the starter opened
> (`holding`) -- only a thread's opener can say anything in it (S1) -- so a
> colleague's words are never among them, and a new chat opened since does not
> lose it (S4 round 1, M1). A run the mail door started carries a mail key as
> its offer, which is never a thread message, so it has none: a request relayed
> from mail never becomes trusted.

## `_ask`, [line 483](../../../../../../../backend/src/sro/application/execution/mail_job.py#L483): Docstring

> The draft path's questions, `recipient` and `mail_body`: the run stops (holding no browser, as a
> draft waiting on its press does), with the question on its progress and a
> `run_asks` in the operator's thread. `why` is the step's reason, short; `text`
> is the question, which may show a refused draft -- up to `K_BODY` of model
> text written from mail, never a run step's reason (S4 round 1, M6). `AnswerRun` takes an answer on a stopped
> drafted run for this one kind, and resumes it through `redraft_the_mail_job`
> rather than a Temporal signal.
