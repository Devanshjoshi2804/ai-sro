# Notes for `backend/src/sro/domain/execution/mail_job.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/mail_job.py`](../../../../../../../backend/src/sro/domain/execution/mail_job.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L1): Docstring

> A job that is nothing but mail, done as mail rather than as clicks.
>
> Mined mail jobs used to be replayed through Gmail's page, and a mailbox is the
> worst place to drive a browser: one step carries the recipients, the subject
> and the body, and a click cannot carry any of them. Measured on the deployment
> 2026-09-23 -- three runs of `Reply to Email` refused with "a click cannot
> carry a value", three of `Compose and Send Email` ended "state unknown after a
> write" because nothing on a screen can say a mail went.
>
> The mailbox has an API, and the deployment already talks to it for everything
> else mail does -- reading requests, reading replies, sending the draft to
> whoever asked. So a job whose every step is in the mailbox is not run on the
> page at all: a model writes the mail, the operator reads it, and their press
> sends it through the connector, whose answer is the verdict.
>
> Pure: what counts as a mail job and who may be written to. What the model
> is asked is the `WRITE_MAIL` record, in `sro.domain.prompts.write_mail`. The reading, the drafting and the sending are the application's.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L12): Note on the line above

Code: `MAILBOXES = frozenset({"mail.google.com"})`

> The mailbox the connector reads and writes, as a host -- which is what
> `origin_of` answers, scheme and all left off. One, because the connector is
> Gmail's; a second provider is a second connector before it is a line here.

## module, [line 43](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L43): Note on the line above

Code: `MAILBOX_HOSTS = frozenset({"mail.google.com", "outlook.office.com", "outlook.live.com"})`

> Every mailbox a person reads requests in. Wider than `MAILBOXES`, which is
> only the one the connector can also write through.

## `is_mail_only`, [line 15](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L15): Docstring

> Whether every step of this job happened in the mailbox.
>
> Read off the evidence each step cites, and the step's own system where it
> cites nothing this store still holds. A job with one step anywhere else --
> a sign-in, a warehouse screen -- is not a mail job: its mail half is read
> by the gather rung, and the rest is a page that has to be driven.

## `sends_mail`, [line 31](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L31): Docstring

> Whether this step pressed a mailbox's Send button.
>
> By the control, never by the traffic. Gmail POSTs to fetch a thread, to
> save a draft and to send, so a mailbox step's calls say nothing about
> whether it wrote -- measured across every job on the deployment
> 2026-09-23: `Create a Customer Type`'s "Read the customer type details in
> Gmail" was a write by its `POST mail/u/4/`. What does separate them is
> what was pressed: each of the nine steps that sent a mail, in every job
> that sends one, clicked a button named `Send (⌘Enter)`, and no other
> mailbox step did.

## `on_the_mailbox`, [line 39](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L39): Docstring

> Whether this happened on a mailbox's own page -- by where it happened,
> not by the system it was filed under. `Log in to Google Account` is filed
> under the mailbox and types its password on `accounts.google.com`.

## `addresses_in`, [line 57](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L57): Docstring

> Every email address named anywhere in these, lowercased.

## `participants`, [line 66](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L66): Docstring

> Everyone a conversation's headers name: each message's sender and its `to`
> and `cc`. Headers, never bodies -- an address a message's text names is the
> sender's say-so, and mail text is untrusted.

## `sent_to`, [line 72](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L72): Docstring

> The addresses this job's own evidence sent to when it was demonstrated: what
> the operator typed into a mailbox's To, Cc or Bcc field (Gmail names them
> `To recipients`, Outlook `To`) in a gesture a step of the job cites.
>
> Only the recipient field. A search box, the body, a page off the mailbox and
> a secret field all carry addresses nobody sent to. The send call's own body
> is not read either: Gmail's reply carries the quoted mail it answers, so an
> address the asker wrote would read as one the operator sent to.
>
> Ceiling: a recipient picked from Gmail's suggestions after typing a part of
> it (`de` then a click on the contact) is not seen, because neither gesture
> carries the address -- that job asks. Reading the chosen chip is the upgrade.

## `check_draft`, [line 89](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L89): Docstring

> `""` when the draft may go, else why not.
>
> `to` names at least one address and only participants or addresses the job
> was demonstrated sending to. Each citation names a message whose body says
> its value; one that does not is a model claiming what the thread did not
> say, and refuses the whole draft. Every value-like token in the body -- an
> address, or a token with a digit in it -- is a whole token of a cited value
> or of one of the run's values (which include its read results). A piece of
> one does not count: `44` is not proven by `PO-4411`.
