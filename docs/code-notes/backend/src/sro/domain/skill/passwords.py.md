# Notes for `backend/src/sro/domain/skill/passwords.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/passwords.py`](../../../../../../../backend/src/sro/domain/skill/passwords.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/passwords.py#L1): Docstring

> The step a model will never write: typing the password.
>
> An operator asked, more than once, why their browser fills their username,
> presses Sign In, and leaves the password blank. The mined job really does have
> two steps and no third one, and the reason is upstream of the model:
>
>     redaction strips a credential gesture of its value AND its target name,
>     leaving nothing worth pointing at
>
> -- `checks.py` says exactly that, and draws the right conclusion for what it
> was doing: the one gesture that proves a job is a sign-in is the one gesture a
> model summarising that job will leave out. It is invisible for the same reason
> it is safe.
>
> So the step is not asked for. It is ADDED, here, from the evidence the model
> was summarising, under rules narrow enough that a job which is not a sign-in
> cannot grow one by accident:
>
> **Only a gesture the recorder marked secret.** Not "a field called password" --
> the recorder's own mark, the same one `is_secret` reads, set at the boundary
> where a real browser saw a real input of type password.
>
> **Only inside the doing the workflow kept.** `one_occurrence` has already
> struck every citation but one doing's by the time this runs, so the span is
> that doing: a credential typed in another hour, or in another job, is not this
> job's password.
>
> **Only where no step already covers it.** A model that did cite the credential
> gesture -- rare, but it happens when the field carries a label the redaction
> leaves alone -- keeps its own step and gets no second one.
>
> **Never a value.** The step cites the gesture and nothing else. What gets typed
> comes from the vault at run time (`domain/execution/secrets`), by a key built
> from the system and the field. The evidence still holds no password, and this
> module never sees one.

## `with_passwords`, [line 11](../../../../../../../backend/src/sro/domain/skill/passwords.py#L11): Docstring

> Give this job the credential steps it does and the model did not say.
>
> In place, returning how many steps it CHANGED -- added, or removed as a
> second attempt at the same field. A job with no credential in its span is
> untouched and answers 0, which is most jobs, because most work is not
> signing in.

## `_in_the_order_it_happened`, [line 69](../../../../../../../backend/src/sro/domain/skill/passwords.py#L69): Docstring

> Renumber every step by when its evidence happened.
>
> A password step appended to the end would be typed after Sign In was
> pressed, which is not a login, it is a page that has already refused. The
> order the operator did it in is the only order that runs, and the evidence
> carries it -- so this sorts by the earliest gesture each step cites rather
> than trusting the model's numbering, which was correct for the steps it
> knew about and knows nothing about this one.

## `with_passwords`, [line 22](../../../../../../../backend/src/sro/domain/skill/passwords.py#L22): Comment

Code: `once: dict[tuple[str, str], Gesture] = {}`

> ONE step per field, and the first typing of it.
>
> The first real login this ran against had four. The operator had typed
> their password four times inside that doing -- a mistyped attempt, a page
> that came back, a second go -- and every one of them became a step, two
> of them AFTER the Sign In click, which is not a login: it is a job that
> signs in, fails, and types a password into whatever came next.
>
> A person typing a password twice is one step done twice, so the earliest
> is the one that belongs before the submit, and the rest are attempts.
> Keyed by system and field rather than by gesture, because that is what
> makes two typings the same step -- and it is the same key the vault is
> read by, so a job cannot end up with two steps asking for one secret.

## `with_passwords`, [line 24](../../../../../../../backend/src/sro/domain/skill/passwords.py#L24): Comment

Code: `if not is_secret(gesture) or gesture.action.kind not in PUTS_A_VALUE:`

> A credential step TYPES one. A click on a password box is a person
> putting the cursor in it, and on this deployment it happened first --
> so the earliest-wins rule below chose the click, built the whole
> reading around it, and the job ended up with a step that pressed
> Sign In having typed nothing (`wfl_7fa53354`, 2026-09-22).

## `with_passwords`, [line 26](../../../../../../../backend/src/sro/domain/skill/passwords.py#L26): Comment

Code: `if not first <= gesture.at <= last:`

> The doing this workflow kept, and the systems it was done on. A
> credential typed an hour later, or on a host this job never touched,
> belongs to somebody else's job.

## `with_passwords`, [line 33](../../../../../../../backend/src/sro/domain/skill/passwords.py#L33): Comment

Code: `kept = {gesture.id for gesture in once.values()}`

> Steps that cite a typing this rule did not choose: a second attempt,
> written by an earlier version of this rule or by a model that cited one.
> Dropped rather than left, so a job heals rather than accumulating the
> shape of whichever day it was mined on.

## `with_passwords`, [line 44](../../../../../../../backend/src/sro/domain/skill/passwords.py#L44): Comment

Code: `aimed = set()`

> A credential is covered when a step is AIMED at it, not when anything
> happens to mention it.
>
> A step cites what the operator did while performing it, and on a login
> that is both boxes: `Enter username or email` on this deployment cited
> the username's type and the password's. The credential was therefore
> "cited", this rule skipped it, and the step the model had named `Type
> the password.` was left citing a CLICK on the box -- so every run of
> that job planned a click at a password field, typed nothing, and pressed
> Sign In. Measured 2026-09-22, `wfl_7fa53354`: nine runs, no password
> ever typed by the two that reached it.
>
> `primary_gesture` is the same reading the planner makes of a step, which
> is what makes this the right question: if the planner would not aim at
> the credential, no step types it, whoever cites it.

## `with_passwords`, [line 55](../../../../../../../backend/src/sro/domain/skill/passwords.py#L55): Inline

Code: `order=0,`

> renumbered below, once, in time order

## `with_passwords`, [line 57](../../../../../../../backend/src/sro/domain/skill/passwords.py#L57): Comment

Code: `system=gesture.system,`

> The gesture's SYSTEM and not its url. `validate` checks a
> step's system against the systems its cited evidence was
> attributed to, so a step naming the page it happened on is a
> step refused for claiming a system none of its evidence
> touched -- which is the whole job refused, over the one step
> the model could not see.

## `with_passwords`, [line 64](../../../../../../../backend/src/sro/domain/skill/passwords.py#L64): Comment

Code: `if added or spare:`

> Renumbered when anything moved, which includes a spare step removed and
> nothing added: a job left with a hole in its numbering is a job whose
> steps no longer say what order they run in.

## `_in_the_order_it_happened.when`, [line 73](../../../../../../../backend/src/sro/domain/skill/passwords.py#L73): Comment

Code: `return min(times) if times else float(step.order)`

> A step citing nothing this pass can see keeps its place rather than
> being thrown to the front: `validate` refuses an uncited step, so
> this is a step whose evidence is simply not in this window.
