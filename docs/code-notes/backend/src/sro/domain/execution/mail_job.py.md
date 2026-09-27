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

## module, [line 15](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L15): Note on the line above

Code: `MAILBOXES = frozenset({"mail.google.com"})`

> The mailbox the connector reads and writes, as a host -- which is what
> `origin_of` answers, scheme and all left off. One, because the connector is
> Gmail's; a second provider is a second connector before it is a line here.

## module, [line 46](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L46): Note on the line above

Code: `MAILBOX_HOSTS = frozenset({"mail.google.com", "outlook.office.com", "outlook.live.com"})`

> Every mailbox a person reads requests in. Wider than `MAILBOXES`, which is
> only the one the connector can also write through.

## `is_mail_only`, [line 18](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L18): Docstring

> Whether every step of this job happened in the mailbox.
>
> Read off the evidence each step cites, and the step's own system where it
> cites nothing this store still holds. A job with one step anywhere else --
> a sign-in, a warehouse screen -- is not a mail job: its mail half is read
> by the gather rung, and the rest is a page that has to be driven.

## `sends_mail`, [line 34](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L34): Docstring

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

## `on_the_mailbox`, [line 42](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L42): Docstring

> Whether this happened on a mailbox's own page -- by where it happened,
> not by the system it was filed under. `Log in to Google Account` is filed
> under the mailbox and types its password on `accounts.google.com`.

## `_VALUE_LIKE`, [line 61](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L61): Note on the line above

Code: `_VALUE_LIKE = re.compile(`

> What counts as a value in a mail body: an address, or a token with a digit in
> it, where digits joined by `, . / :` stay one token -- `1,200`, `12/10/2026`,
> `3,450.00`, `10:30`. Split at the punctuation, `200` was "proven" by a cited
> `1,200` and a date with its day and month swapped by the date itself. The body,
> the cited values and the run's values are all read by this one pattern.
>
> Ceiling (M3): a value with no digit and no `@` is not seen as one -- a number
> in words ("twelve hundred"), a weekday or a month name, an address spelled
> out. Those pass unchecked. The upgrade is a model check of the body against
> the thread, which the eval would have to measure first.

## `K_SENT_THREADS`, [line 69](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L69): Note on the line above

Code: `K_SENT_THREADS = 10`

> A send call naming more threads than this is a sync of the mailbox, not the
> send of one mail, so it grants nobody.

## `K_SEND_WINDOW_S`, [line 71](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L71): Note on the line above

Code: `K_SEND_WINDOW_S = 120.0`

> How far from the Send click the sent copy's Gmail time may be and still be the
> mail that click sent. Gmail stamps it as it takes the mail, seconds after the
> press; two minutes allows a slow network and no more, since a second SENT mail
> in that window makes the click ambiguous and grants nobody.

## `JobRecipient`, [line 75](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L75): Docstring

> An address the job's operator said its mail goes to, answering the run's
> `recipient` question -- with who said it and when, as an alias is kept. Only
> that answer writes one (`RunSteps.answered`); a model never does.

## `Allowed`, [line 82](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L82): Docstring

> Who a draft may go to besides the conversation's participants: `to` holds the
> To and Cc of the mail the job's demonstration sent, and the addresses its
> operator confirmed; `bcc` holds the Bcc of that mail, which stays Bcc.

## `Checked`, [line 88](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L88): Docstring

> A draft's verdict. `why` is empty when it may go, and says what was refused
> otherwise -- the address, or the value -- for the operator's question. `logged`
> says the same in counts only: an address or a body token never reaches a log
> line. `recipient` marks a refusal of who it goes to -- including a draft whose
> only recipient is a Bcc, which never goes out with an empty To -- which the operator can
> answer; `to` and `bcc` are the addresses checked, and the only ones a header
> is built from.

## `mailboxes`, [line 96](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L96): Docstring

> The addresses a header or an answer names, casefolded, or `None` when any
> entry does not read as a plain ASCII address. Parsed by
> `email.utils.getaddresses` (strict), the way a mail client reads a header, so
> what is checked is exactly what is sent: `eve@[10.0.0.1]`, `evé@evil.com`,
> `eve!ana@acme.example`, a `;` list or a trailing comma are refused whole
> rather than half-read by a pattern. An internationalised address is refused
> too; the operator is asked instead.

## `participants`, [line 125](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L125): Docstring

> Who the conversation lets a draft go to: the sender of every message, and the
> To and Cc of every message the operator's own mailbox sent (`sent`, Gmail's
> SENT label -- not the `From` header, which any sender can write).
>
> A Cc on an incoming mail is the sender's say-so and names nobody (M4, against
> invariant 7): a reply-all to somebody only a sender cc'd asks first. Headers,
> never bodies.

## `sent_from`, [line 135](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L135): Docstring

> For each Send the job's evidence pressed, when it was pressed and the Gmail
> threads its own send call (`POST mail.google.com/sync/u/N/i/s`, answered 2xx)
> names -- `thread-f:<decimal>`, whose hex is the API's thread id. The sent mail
> is then the one SENT message of those threads dated within `K_SEND_WINDOW_S`
> of the press, and its own To, Cc and Bcc are the demonstrated recipients: what
> was sent, never what was typed.
>
> Not `msg-f`: measured on the QA box (309 send calls, 11 Send clicks), those
> are the thread's earlier messages -- three Sends carried none, two carried
> more than ten -- while the new mail is named only by an account-side
> `msg-a:r…` id the API does not know. `thread-f` sits on the same calls. A
> click with no thread, or no single SENT mail in the window, grants nobody.

## `check_draft`, [line 169](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L169): Docstring

> Whether a draft may go, and to whom (`Checked`).
>
> - `to` parses (`mailboxes`) and every address in it is a participant, or
>   allowed (`Allowed`); otherwise the refusal is a `recipient` one.
> - Each citation is kept only if its message -- subject or body -- says its
>   value; a bad one is dropped, never the whole draft (invariant 14), and the
>   token check decides.
> - Every value-like token of the body is a whole token of a kept citation or
>   of one of the run's values (which include its read results).
>
> A demonstrated Bcc that is nobody's To stays Bcc (M1).
>
> Accepted (M5): an address the mail's text names can be put in the body when
> cited to that mail ("please reply to eve@..."). It is never a recipient.

## `one_address_in`, [line 103](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L103): Docstring

> The one address an operator's mail names in its own text, or `""`. The quote
> is found by structure, never by an English "On …": the first `>` line starts
> it, and the paragraph right above it is the client's attribution in whatever
> language ("Le jeu. …, Eve <eve@…> a écrit :", "Am Do. … schrieb Eve …"), so
> both go. A reply (In-Reply-To or References) with no `>` quote at all cannot
> be told apart from its quote, and names nobody -- it fails closed.
>
> Each word with an `@`, stripped of the punctuation around it, must read as one
> address (`mailboxes`, i.e. getaddresses); exactly one distinct address
> answers, so "please send to x@y." counts, and two addresses, an unreadable
> one, or none leave the question open.
>
> Ceiling: a client that quotes without `>` (Outlook's "From: … Sent: …" block)
> is never answered by mail; the panel still is.

