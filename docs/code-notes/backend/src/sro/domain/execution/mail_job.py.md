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
> Pure: what counts as a mail job, what the model is asked, and who may be
> written to. The reading, the drafting and the sending are the application's.

## module, [line 11](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L11): Note on the line above

Code: `MAILBOXES = frozenset({"mail.google.com"})`

> The mailbox the connector reads and writes, as a host -- which is what
> `origin_of` answers, scheme and all left off. One, because the connector is
> Gmail's; a second provider is a second connector before it is a line here.

## module, [line 42](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L42): Note on the line above

Code: `MAILBOX_HOSTS = frozenset({"mail.google.com", "outlook.office.com", "outlook.live.com"})`

> Every mailbox a person reads requests in. Wider than `MAILBOXES`, which is
> only the one the connector can also write through.

## `is_mail_only`, [line 14](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L14): Docstring

> Whether every step of this job happened in the mailbox.
>
> Read off the evidence each step cites, and the step's own system where it
> cites nothing this store still holds. A job with one step anywhere else --
> a sign-in, a warehouse screen -- is not a mail job: its mail half is read
> by the gather rung, and the rest is a page that has to be driven.

## `sends_mail`, [line 30](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L30): Docstring

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

## `on_the_mailbox`, [line 38](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L38): Docstring

> Whether this happened on a mailbox's own page -- by where it happened,
> not by the system it was filed under. `Log in to Google Account` is filed
> under the mailbox and types its password on `accounts.google.com`.

## `addresses_in`, [line 85](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L85): Docstring

> Every email address named anywhere in these, lowercased.

## `recipient_allowed`, [line 89](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L89): Docstring

> Whether every address the model put in `to` was already on the page.
>
> A mail sent to an address nobody gave is the one mistake this job cannot
> take back, so the rule is the evidence's: an address in the run's values
> or in the conversation being answered, and nothing else. `to` may list
> several; every one of them has to pass.
