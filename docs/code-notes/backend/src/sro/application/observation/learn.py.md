# Notes for `backend/src/sro/application/observation/learn.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/learn.py`](../../../../../../../backend/src/sro/application/observation/learn.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/learn.py#L1): Docstring

> Learning a task nobody demonstrated.
>
> The evidence for a task somebody keeps doing is already stored, verbatim, and
> teaching a candidate reads it back rather than asking for the task again. So
> the only thing standing between "you have done this three times" and a skill is
> somebody pressing a button -- and the operator this system is for is doing
> their job, not watching a panel.
>
> So it presses it. What that produces is a skill at the bottom of the ladder:
> `recorded`, never run, never promoted by this. Every gate that decides whether
> something may act is downstream of here and untouched -- a rehearsal, ten clean
> runs, a named person for anything that writes. What is automatic is the
> noticing, which was always evidence rather than judgement.
>
> Nothing here decides identity: which doings are the same task is the miner's
> exact clustering, and what varies between two of them is the two-run diff.

## `Learned`, [line 19](../../../../../../../backend/src/sro/application/observation/learn.py#L19): Note on the line above

Code: `still_waiting: list[str] = field(default_factory=list)`

> Candidates that have been done often enough but whose evidence will not
> induce yet, and the reason for each. They stay `new`, which is what puts
> them in front of an operator as "teach me this once".

## `LearnWhatRepeats`, [line 22](../../../../../../../backend/src/sro/application/observation/learn.py#L22): Docstring

> Every candidate done often enough to be worth offering, taught.

## `LearnWhatRepeats._tried`, [line 56](../../../../../../../backend/src/sro/application/observation/learn.py#L56): Docstring

> Written down before the attempt, not after it.
>
> An attempt that dies halfway -- a model timing out, a process killed --
> must still count, or a candidate that breaks induction becomes a sweep
> that does the same expensive thing forever.
>
> Stamped with the rules that made it, so the next change to induction is
> what brings this candidate back rather than a doing that may never come.

## `LearnWhatRepeats.execute`, [line 38](../../../../../../../backend/src/sro/application/observation/learn.py#L38): Comment

Code: `continue`

> Nothing new to try it on, and nothing new to try it with. The
> sweep comes round every quarter of an hour; an attempt on
> evidence that already refused under these same rules would
> refuse again and leave two more sealed recordings behind it.

## `LearnWhatRepeats.execute`, [line 43](../../../../../../../backend/src/sro/application/observation/learn.py#L43): Comment

Code: `logger.info("%s was not taught: %s", candidate.title, nothing)`

> Somebody dismissed or taught it between the listing and here.

## `LearnWhatRepeats.execute`, [line 46](../../../../../../../backend/src/sro/application/observation/learn.py#L46): Comment

Code: `logger.exception("%s could not be learned", candidate.title)`

> One candidate whose evidence breaks induction must not stop
> the others: this runs unattended, on a sweep, and a sweep
> that dies on the first bad candidate silently stops learning
> anything at all.
