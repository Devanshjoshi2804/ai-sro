# Notes for `backend/scripts/open_joins.py`

Comments and docstrings moved out of [`backend/scripts/open_joins.py`](../../../../backend/scripts/open_joins.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/open_joins.py#L1): Docstring

> The joins nobody has answered, as questions a person can answer.
>
> **With what the browser was doing either side of them, across every tab.** A
> join is a question about identity, and a candidate on its own cannot answer it:
> segmentation runs each host on its own stream, so the mail half of a two-system
> job looks exactly like a mail client talking to itself. On tenant `new`,
> 2026-09-10, the browser went mail -> warehouse -> mail -> warehouse sixteen
> times in an hour, thirty-five seconds and then two seconds apart. Read per host
> that is `Create u on mail.google.com`; read in time order it is somebody doing
> what a mail asked them to do.
>
> So each episode is printed with the other hosts worked in around it. Whoever
> answers can see the minute, not the host.
>
> The last unmet item on phase 7's precondition
> (`docs/new-agent-doc-arc/two-miners-one-day.md`) and the only one no script can
> close: a model may notice that two candidates look like one piece of work and
> say why, and **a person decides whether they are**. The answer names who said
> so, because "these two are the same task" is a claim about somebody's work.
>
>     uv run python scripts/open_joins.py            # every tenant
>     uv run python scripts/open_joins.py acme
>
> Reads only. It prints each question once -- a join is stored on both
> candidates, so the store holds two rows per question -- with the evidence
> either side and the exact call that answers it.

## module, [line 14](../../../../backend/scripts/open_joins.py#L14): Note on the line above

Code: `BESIDE = timedelta(minutes=3)`

> How far either side of an episode counts as the same sitting.
>
> Three minutes because the real interleaving is far tighter than that -- the
> gaps measured on `new` are seconds -- and because a window wide enough to be
> wrong in the other direction would sweep in the next task and call every
> episode two-system.

## `_beside`, [line 22](../../../../backend/scripts/open_joins.py#L22): Docstring

> The other hosts somebody worked in around this episode.
>
> Gestures, not calls: a page talking in the background is not somebody
> working, which is the distinction `Episode.touched_from` was added for.

## `_elsewhere`, [line 35](../../../../backend/scripts/open_joins.py#L35): Docstring

> One line: what else the browser was being worked in, and when.

## `_split`, [line 87](../../../../backend/scripts/open_joins.py#L87): Docstring

> Work this tenant holds that can never be paired, and why.
>
> `_variants` and `_workflows` both require one principal on both sides, and
> they are right to: a candidate is `(principal, signature)`, and pairing two
> people's days into one job would be a claim about somebody's work that
> nobody made. So this does not widen the rule -- it says out loud that the
> rule is biting, which nothing did.
>
> It bites hardest on the deployment this was written on. A token names its
> own principal, so a browser re-registered with a second one becomes a
> second device on purpose (`GrantHost`: "a browser is not a person"), and a
> month of one person's evidence arrives as two workers who never met. On
> `new` that is 131 batches as `devansh` against 882 as `operator`, and every
> cross-system pair between them is passed over in silence.
>
> An instrument reads; it does not steer. What to do about it -- one token
> per person from here on, or a way to say two principals are one operator --
> is a decision, and this only makes sure it is a decision somebody knows
> they are taking.

## `_ask`, [line 62](../../../../backend/scripts/open_joins.py#L62): Comment

Code: `continue`

> The same question from the other side. One decision, not two.
