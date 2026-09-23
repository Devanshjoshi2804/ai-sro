# Notes for `backend/src/sro/application/observation/mine.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/mine.py`](../../../../../../../backend/src/sro/application/observation/mine.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/mine.py#L1): Docstring

> Noticing that somebody keeps doing the same thing.
>
> No model decides what a candidate is. Clustering is a function of the evidence,
> so the same week of observation produces the same candidates every time it is
> mined, and a candidate can be argued with by reading its episodes. What a model
> may do later is write the sentence on the front of it.
>
> Re-runnable by construction: an episode already recorded is not counted twice,
> so mining the same window again changes nothing and a better segmenter can be
> run over evidence that is already stored.

## `MineObservations`, [line 32](../../../../../../../backend/src/sro/application/observation/mine.py#L32): Docstring

> One tenant's observation, over a window, turned into candidates.

## `title_for`, [line 100](../../../../../../../backend/src/sro/application/observation/mine.py#L100): Docstring

> A sentence somebody can recognise, derived rather than written.
>
> Deliberately not a model's: naming is the one thing here a model would be
> good at, and it is also the one thing that would make a candidate's identity
> depend on what was answered that afternoon. A person renames it when they
> teach it.

## `MineEverything`, [line 111](../../../../../../../backend/src/sro/application/observation/mine.py#L111): Docstring

> Every tenant that has been observed lately.
>
> Deliberately tenant-blind, and the only caller is the scheduled sweep: there
> is no request behind this and nobody to take a tenant from. It asks which
> tenants have evidence and then mines each one inside its own context.

## `MineObservations._observed`, [line 74](../../../../../../../backend/src/sro/application/observation/mine.py#L74): Docstring

> Every batch's events, read back and grouped by whose browser they
> came from. A task is one person's; two operators doing the same work is
> two candidates, and the sentence an extension shows says "you".

## `MineObservations._observed`, [line 82](../../../../../../../backend/src/sro/application/observation/mine.py#L82): Comment

Code: `continue`

> Evidence that has aged out of its retention window. The
> candidates it fed are already counted; a missing blob is not a
> reason to fail a mining run.

## `MineEverything.execute`, [line 131](../../../../../../../backend/src/sro/application/observation/mine.py#L131): Comment

Code: `try:`

> After the counting, never instead of it. What the miner
> decided stands whatever a model says next, and a model that
> is unreachable costs this sweep its sentences and nothing
> else -- so its failure is logged here rather than raised
> into a sweep that has already done its real work.
