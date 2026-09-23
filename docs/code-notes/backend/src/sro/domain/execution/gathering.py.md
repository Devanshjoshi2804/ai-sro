# Notes for `backend/src/sro/domain/execution/gathering.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/gathering.py`](../../../../../../../backend/src/sro/domain/execution/gathering.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/gathering.py#L1): Docstring

> What a search for a job's values may decide, and when it has to stop.
>
> The pure half of the context gather. A run of a mined job needs a value for
> every parameter the job declares, and until now there was exactly one source:
> somebody typed them into the press. The live failure that named this was step 1
> of `Create a Customer Type` -- "Open an email requesting a new customer type"
> -- refusing with *"The open email is for customer type GPDP rather than the
> requested ZQ41"*. The run had values and the mailbox had a different request,
> and nothing could go and look.
>
> **A value is found or it is missing, and a missing one is said.** The rule the
> rest of this system keeps: `write_plan_for` refuses rather than guessing, and
> so does this. A gather that returned its best effort would put a model's
> reading of somebody's mail into a warehouse write, which is the one place this
> codebase spends its care avoiding.
>
> **Every value carries where it came from.** `Found.from_message` and
> `Found.quoting` are not decoration: "evidence decides identity, a model writes
> the sentence" is the governing rule, and a value read out of a mail is only as
> good as the mail it was read from. A person asked to approve a write can go and
> look at the message; an audit a month later can too.
>
> Pure, so the loop's stopping rules can be tested without a model or a mailbox:
> what counts as done, what counts as progress, and what a round may ask for next.

## module, [line 7](../../../../../../../backend/src/sro/domain/execution/gathering.py#L7): Note on the line above

Code: `K_ROUNDS = 6`

> How many times a gather may look before it gives up.
>
> Bounded because an unbounded gather is a bill and a stall, not a better answer.
> Six is enough for the shape these mailboxes actually have -- search, read the
> likeliest, read one more, and a couple of narrower searches when the first
> query was wrong -- and small enough that a loop going nowhere costs a handful
> of calls rather than an afternoon.

## module, [line 9](../../../../../../../backend/src/sro/domain/execution/gathering.py#L9): Note on the line above

Code: `K_PATIENCE_S = 45.0`

> How long a gather may take in total, however many rounds that buys.
>
> `K_ROUNDS` bounds the number of looks and not the time they take, and those are
> different bounds: measured on the deployment 2026-09-16, a run sat at "Step 0"
> for three and a half minutes because Google answered one round with a 5xx and
> the asker did what it should -- three attempts, two-second backoff, a
> two-minute ceiling each. Six rounds of that is half an hour of a card saying
> nothing while a person watches it.
>
> So the loop has a clock as well as a counter. What it has found when the clock
> runs out is what it comes back with, which is the same answer it gives for a
> mailbox that holds nothing: the run then asks a person, and asking is what this
> was always going to do about a value it could not find.
>
> Forty-five seconds because a person watching a card is the measure here, not
> the model: past about a minute they go and do the job themselves, and a gather
> that finishes after they have is a gather that wasted its own answer.

## module, [line 11](../../../../../../../backend/src/sro/domain/execution/gathering.py#L11): Note on the line above

Code: `K_NOTE = 240`

> How much of what a search or a read answered is kept as history.
>
> The whole mail is not kept, and that is deliberate. The failure modes of a
> gather loop are context poisoning, distraction and confusion -- a model leaning
> on accumulated history instead of re-reading the question -- and the mitigation
> every account of them agrees on is structured note-taking rather than raw
> accumulation. What the next round needs is "this search found three messages
> and here are their subjects", not four screens of somebody's mail.

## module, [line 14](../../../../../../../backend/src/sro/domain/execution/gathering.py#L14): Note on the line above

Code: `K_HIT = 160`

> How much of ONE row of a search result is kept.
>
> A search answers with a list, and a list trimmed by length is one row. Measured
> on the deployment 2026-09-16: `search_threads` came back with five threads and
> `K_NOTE` cut the whole answer after the first, mid-snippet -- so four message
> ids the next round could have read were never shown to it, and it answered
> `done` with nothing. "The mailbox does not hold this" said about a prompt
> again, which is the exact failure the deterministic opening search was added to
> end.
>
> Per row, so every hit's id survives and no hit's body arrives whole.

## module, [line 16](../../../../../../../backend/src/sro/domain/execution/gathering.py#L16): Note on the line above

Code: `K_BODY = 1200`

> How much of a message a read is allowed to show the next round.
>
> `K_NOTE` is the cap for an answer nothing is being read out of. A read is the
> opposite: it is the one call whose whole point is the text a value is quoted
> from, and 240 characters of it cannot hold a request that opens with a greeting
> and a line of context. Still bounded -- six rounds of this is the ceiling --
> but bounded at the size of a mail rather than of a snippet.

## `Found`, [line 20](../../../../../../../backend/src/sro/domain/execution/gathering.py#L20): Docstring

> One value, and the message it was read out of.

## `Found`, [line 23](../../../../../../../backend/src/sro/domain/execution/gathering.py#L23): Note on the line above

Code: `quoting: str = ""`

> The span the value was read from, short. What a person checks the
> reading against without opening the mail.

## `Gathered`, [line 27](../../../../../../../backend/src/sro/domain/execution/gathering.py#L27): Docstring

> What one gather came back with.

## `Gathered`, [line 29](../../../../../../../backend/src/sro/domain/execution/gathering.py#L29): Note on the line above

Code: `missing: tuple[str, ...] = ()`

> Parameters nothing could be found for. Said rather than guessed, and
> said rather than left out: a caller has to be able to tell "there is no
> value" from "nobody looked".

## `Gathered`, [line 31](../../../../../../../backend/src/sro/domain/execution/gathering.py#L31): Note on the line above

Code: `looked: tuple[str, ...] = ()`

> What was searched and read, in order. The audit trail for a value that
> came from somebody's mailbox rather than from a person typing it.

## `Gathered`, [line 35](../../../../../../../backend/src/sro/domain/execution/gathering.py#L35): Note on the line above

Code: `unasked: tuple[str, ...] = ()`

> Names the reading offered that this job declares no parameter for.
>
> Carried rather than dropped in silence. See `dropped`: a mail asking for a
> field the job cannot take is a request half-done, and the half that went
> missing has to be nameable by whoever reads the run.

## `still_wanted`, [line 42](../../../../../../../backend/src/sro/domain/execution/gathering.py#L42): Docstring

> The parameters with no value yet, in the order the job declares them.
>
> Order matters for the sentence a person reads: a job that declares a code
> and a description should say them in that order every time, rather than in
> whatever order a dict happened to iterate.

## `keep`, [line 46](../../../../../../../backend/src/sro/domain/execution/gathering.py#L46): Docstring

> The values that answer a parameter this job actually declares.
>
> A model asked for two values and offering a third is not a bonus, it is a
> reading of the mail nobody asked for -- and a run that carried it would
> send a field the job never had. Dropped silently rather than refused: the
> two it was asked for may be perfectly good, and the third costs nothing to
> ignore.
>
> Empty and blank values are dropped for the same reason `typed_values` drops
> them: a parameter answered with "" is a parameter nobody answered.

## `dropped`, [line 55](../../../../../../../backend/src/sro/domain/execution/gathering.py#L55): Docstring

> The names a reading offered that this job has no parameter for.
>
> `keep` discards them, which is right -- a run that carried a field the job
> never had would send a slot nothing demonstrated. Discarding them SILENTLY
> is not right, and is the shape of every fault this system has had worth
> having: a request that asked for three things, a record that holds two, and
> nothing anywhere saying which one went missing.
>
> A job's parameters are what two doings proved VARY. The form has far more
> fields than that, and a mail naming one of them is a person asking for
> something perfectly reasonable that this job simply cannot take yet. They
> should be told, not ignored.
>
> Names only, never values: this goes into a run record and a log line.

## `note`, [line 60](../../../../../../../backend/src/sro/domain/execution/gathering.py#L60): Docstring

> One line of history: what was asked, and a trimmed sight of the answer.
>
> Trimmed here rather than at the call site so every round is the same size
> in the prompt, whatever the mailbox handed back -- and trimmed by the SHAPE
> of what came back, because the three shapes a mailbox answers in do not
> survive the same cut. A list of hits is trimmed row by row so every id
> reaches the round that could read it; a message is given room for its body,
> which is the text the value gets quoted from; anything else is a snippet.

## `_messages`, [line 67](../../../../../../../backend/src/sro/domain/execution/gathering.py#L67): Docstring

> The hits in a search answer, or `None` if this was not one.

## `_is_a_message`, [line 77](../../../../../../../backend/src/sro/domain/execution/gathering.py#L77): Docstring

> One message, read whole. The answer a value is quoted out of.

## `_row`, [line 85](../../../../../../../backend/src/sro/domain/execution/gathering.py#L85): Docstring

> One hit, short enough that five of them are still a note.
>
> The id first and never trimmed away: it is the only part of a hit the next
> round can act on, and a row whose id was cut is a message nobody can ask
> for.

## `_trimmed`, [line 92](../../../../../../../backend/src/sro/domain/execution/gathering.py#L92): Docstring

> One line, at most `cap` characters of it.
