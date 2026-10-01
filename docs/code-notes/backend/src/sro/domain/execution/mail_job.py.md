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

## module, [line 16](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L16): Note on the line above

Code: `MAILBOXES = frozenset({"mail.google.com"})`

> The mailbox the connector reads and writes, as a host -- which is what
> `origin_of` answers, scheme and all left off. One, because the connector is
> Gmail's; a second provider is a second connector before it is a line here.

## module, [line 47](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L47): Note on the line above

Code: `MAILBOX_HOSTS = frozenset({"mail.google.com", "outlook.office.com", "outlook.live.com"})`

> Every mailbox a person reads requests in. Wider than `MAILBOXES`, which is
> only the one the connector can also write through.

## `is_mail_only`, [line 19](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L19): Docstring

> Whether every step of this job happened in the mailbox.
>
> Read off the evidence each step cites, and the step's own system where it
> cites nothing this store still holds. A job with one step anywhere else --
> a sign-in, a warehouse screen -- is not a mail job: its mail half is read
> by the gather rung, and the rest is a page that has to be driven.

## `sends_mail`, [line 35](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L35): Docstring

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

## `on_the_mailbox`, [line 43](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L43): Docstring

> Whether this happened on a mailbox's own page -- by where it happened,
> not by the system it was filed under. `Log in to Google Account` is filed
> under the mailbox and types its password on `accounts.google.com`.

## `_VALUE_LIKE`, [line 64](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L64): Note on the line above

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

## `K_SENT_THREADS`, [line 72](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L72): Note on the line above

Code: `K_SENT_THREADS = 10`

> A send call naming more threads than this is a sync of the mailbox, not the
> send of one mail, so it grants nobody.

## `REQUEST`, [line 76](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L76): Note on the line above

Code: `REQUEST = "request"`

> The citation source for the operator's own request: a draft cites a value it
> took from the request as `{value, message: "request"}`. No Gmail id reads
> "request", and the request overrides one in `check_draft` anyway: it is the
> operator's text, trusted.

## `MAIL_BODY`, [line 78](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L78): Note on the line above

Code: `MAIL_BODY: Final = "mail_body"`

> The question a mail that could not be written asks its starter: what it should
> say. A literal, so `NeedsAPerson.kind` takes it; here in the domain so
> `asks_a_person` and the store's `waiting_on` find a stopped run asking it.

## `DRAFTED`, [line 80](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L80): Note on the line above

Code: `DRAFTED = "mail_draft"`

> The decision kind of a mail written and not sent: the asker's door writes
> it, and the panel draws the words with a press under them. A mail job no
> longer does (Q1): it sends at once and says `SENT`.

## `SENT`, [line 82](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L82): Note on the line above

Code: `SENT: Final = "mail_sent"`

> The decision kind of a mail that went, or may have (`sent` on the decision
> says which). The mail job says it once its mail is sent; `SendTheDraft` says
> it for the asker's draft. The panel reads it to stop drawing a press under
> words that have already left -- a send that cannot be shown to have failed is
> never retried either.

## `K_SEND_WINDOW_S`, [line 74](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L74): Note on the line above

Code: `K_SEND_WINDOW_S = 120.0`

> How far from the Send click the sent copy's Gmail time may be and still be the
> mail that click sent. Gmail stamps it as it takes the mail, seconds after the
> press; two minutes allows a slow network and no more, since a second SENT mail
> in that window makes the click ambiguous and grants nobody.

## `JobRecipient`, [line 129](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L129): Docstring

> An address the job's operator said its mail goes to, answering the run's
> `recipient` question -- with who said it and when, as an alias is kept. Only
> that answer writes one (`RunSteps.answered`); a model never does.

## `Allowed`, [line 136](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L136): Docstring

> Who a draft may go to besides the conversation's participants: `to` holds the
> To and Cc of the mail the job's demonstration sent, and the addresses its
> operator confirmed; `bcc` holds the Bcc of that mail, which stays Bcc.

## `Checked`, [line 142](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L142): Docstring

> A draft's verdict. `why` is empty when it may go, and says what was refused
> otherwise -- the address, or the value -- for the operator's question. `logged`
> says the same in counts only: an address or a body token never reaches a log
> line. `recipient` marks a refusal of who it goes to -- including a draft whose
> only recipient is a Bcc, which never goes out with an empty To -- which the operator can
> answer; `to` and `bcc` are the addresses checked, and the only ones a header
> is built from.

## `mailboxes`, [line 150](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L150): Docstring

> The addresses a header or an answer names, casefolded, or `None` when any
> entry does not read as a plain ASCII address. Parsed by
> `email.utils.getaddresses` (strict), the way a mail client reads a header, so
> what is checked is exactly what is sent: `eve@[10.0.0.1]`, `evé@evil.com`,
> `eve!ana@acme.example`, a `;` list or a trailing comma are refused whole
> rather than half-read by a pattern. An internationalised address is refused
> too; the operator is asked instead.

## `participants`, [line 195](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L195): Docstring

> Who the conversation lets a draft go to: the sender of every message, and the
> To and Cc of every message the operator's own mailbox sent (`sent`, Gmail's
> SENT label -- not the `From` header, which any sender can write).
>
> A Cc on an incoming mail is the sender's say-so and names nobody (M4, against
> invariant 7): a reply-all to somebody only a sender cc'd asks first. Headers,
> never bodies.

## `sent_from`, [line 205](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L205): Docstring

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

## `check_draft`, [line 243](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L243): Docstring

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
>
> `request` (S4) is the run's starter's own words, typed in their own panel. An
> address it names (`named_in`) is operator-named, as an answer to the
> recipient question is, and a value it says may be cited to message `REQUEST`.
> Only the application's `the_operator_s_words` and the starter's answers ever
> fill it; mail never does.
>
> `vouched` (S4 round 1, C1) is text the operator said yes to -- a refused
> draft's own body -- whose values count as given. It proves values only: who
> the mail goes to is checked exactly as before, and it never names a
> recipient.

## `named_in`, [line 187](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L187): Docstring

> Every address the operator's own words name: `addresses_in`, the one rule
> for a person's words.

## `addresses_in`, [line 165](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L165): Docstring

> The addresses a person's words name, casefolded, in order, once each (Q1).
> An operator answers who a mail goes to the way they would tell a colleague --
> "to devansh.j@greyorange.com" -- and QA 2026-09-28 refused exactly that,
> because `mailboxes` reads a whole text as a header. Here the words around the
> addresses are words; none found names nobody. An address is never cut out of
> a longer word (`evé.x@evil.com`, `a@x.exampleé` name nobody): `_ADDRESS`
> needs a boundary at both ends.
>
> Headers, a model's `to` and stored answers stay on `mailboxes`: a display
> name can hold an address (`"bob@evil.com" <alice@x.example>`), and only a
> parse says which one the mail goes to.

## `one_address_in`, [line 169](../../../../../../../backend/src/sro/domain/execution/mail_job.py#L169): Docstring

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

## `WHICH_MAIL`, [line 84](../../../../../../backend/src/sro/domain/execution/mail_job.py#L84): Note on the line above

Code: `WHICH_MAIL: Final = "which_mail"`

> The question a reply or a forward asks its starter when it was started on no
> mail (M4): which mail it acts on. Their answer is words that find it through
> the Gmail tool's search; exactly one mail found is the run's conversation, and
> none or several ask again. Never guessed. The words find a mail and are never
> the request the writer is given.

## `DRAFT_QUESTIONS`, [line 86](../../../../../../backend/src/sro/domain/execution/mail_job.py#L86): Note on the line above

Code: `DRAFT_QUESTIONS: Final = ("recipient", MAIL_BODY, WHICH_MAIL)`

> The questions a drafted mail job asks with its run stopped rather than
> running: `AnswerRun` takes them on a stopped run and resumes the draft,
> `Converse` routes the starter's words to them, and `asks_a_person` counts
> them. The mail door's by-thread lookup still names only `recipient` and
> `mail_body`: a run asking `which_mail` waits on no thread, so no reply can
> reach it.

## `SEND_A_MAIL`, [line 88](../../../../../../backend/src/sro/domain/execution/mail_job.py#L88): Note on the line above

Code: `SEND_A_MAIL: Final = "mail_send"`

> The built-in mail actions (M4, decided with the user 2026-09-28): send, reply
> and forward are code, never mined jobs. Their ids are fixed and hold no row;
> the workflow store's `get` hands one to every tenant, and `job_recipients`
> keeps who their operators named under the same id.

## `ON_A_MAIL`, [line 94](../../../../../../backend/src/sro/domain/execution/mail_job.py#L94): Note on the line above

Code: `ON_A_MAIL: Final = frozenset({REPLY_TO_A_MAIL, FORWARD_A_MAIL})`

> The built-ins that act on a mail: they need the conversation the run was
> started on, or one the starter names (`WHICH_MAIL`). A send writes a new mail
> and ignores any conversation it was started on.

## `built_in`, [line 108](../../../../../../backend/src/sro/domain/execution/mail_job.py#L108): Docstring

> A built-in mail action as a one-step job whose only system is the mailbox, so
> `is_mail_only` holds and every door that starts a mail job starts it the same
> way: `write_the_mail` with the starter's words, the draft card, the Send
> press. Its evidence is the tenant's mined mail-only jobs (`_allowed`).
> ponytail: a forward is written as a new mail in the forwarded conversation,
> quoting what it may; the tool has no forward, so attachments do not travel.
