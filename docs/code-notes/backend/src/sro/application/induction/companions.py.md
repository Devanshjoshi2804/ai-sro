# Notes for `backend/src/sro/application/induction/companions.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/companions.py`](../../../../../../../backend/src/sro/application/induction/companions.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/companions.py#L1): Docstring

> Skills a demonstration proved without being about them.
>
> Teaching "create a transport mode" opens the screen, and opening the screen
> lists the ones that already exist. That list is a real GET with a real 200 and a
> real body -- so "how many transport modes are there" is answerable from evidence
> already in hand, and asking the operator to demonstrate it separately is asking
> them for something we have.
>
> These are built beside the taught skill, never instead of it, and only ever
> from reads. They start where any read starts and climb on their own record like
> everything else.

## `ambiguity_in`, [line 21](../../../../../../../backend/src/sro/application/induction/companions.py#L21): Docstring

> Two readings of one entity, where picking either would be a guess.
>
> Blue Yonder creates in `transportModes` and refreshes `warehouseTransportModes`:
> sixteen rows at this site, twenty-three across all of them. Both answer "how
> many transport modes are there", and which one somebody means is a fact
> about how they talk, not about the system -- so it is asked, once, rather
> than decided by whichever the screen happened to fetch first.

## `read_skills`, [line 45](../../../../../../../backend/src/sro/application/induction/companions.py#L45): Docstring

> The read that answers questions about this entity, if the demonstration
> made one.
>
> One, not several. A screen reads its subject, and then reads three things
> named after its subject -- unit conversions, defaults, permissions -- and a
> library with four "List transport mode" skills in it is worse than one with
> none, because now somebody has to pick.

## `_chosen`, [line 71](../../../../../../../backend/src/sro/application/induction/companions.py#L71): Docstring

> The read to build from, once somebody has said which collection they mean.
>
> The screen creates in one collection and refreshes another, and only a
> person can say which one their words are about. When they have said, and it
> is not the one the demonstration happened to fetch, the read is built from
> the collection they named -- addressed by the URL the task already writes
> to, which is proven to exist because a 201 came back from it.
>
> That is the operator's instruction, not an inference: the address is
> evidence, and which collection they mean is theirs to declare.

## `objective_for`, [line 96](../../../../../../../backend/src/sro/application/induction/companions.py#L96): Docstring

> A read of the same entity, at the same site, named for what it does.

## `_chosen`, [line 81](../../../../../../../backend/src/sro/application/induction/companions.py#L81): Comment

Code: `return (ReadCapability(replace(write, method="GET", url=write.url.split("?")[0]), prefer, `

> No query at all: the site parameters belong to the site's own view, and
> this collection answers 500 when given them.

## `_skill`, [line 118](../../../../../../../backend/src/sro/application/induction/companions.py#L118): Comment

Code: `listing = capability.rows != 1`

> -1 means the collection was named rather than observed: nobody fetched it
> during the demonstration, so how many it holds is not something to claim.

## `_skill`, [line 121](../../../../../../../backend/src/sro/application/induction/companions.py#L121): Comment

Code: `narrower = bool(written) and capability.entity.lower() != (written or "").lower()`

> The screen creates in one collection and refreshes another: the site's own
> view of it. Both are real and they answer different questions, so a skill
> reading the narrower one says which, rather than calling itself the list.
> Compared raw, not normalised: normalising exists to see through the
> `warehouse` prefix, and the prefix is exactly the difference here.

## `_skill`, [line 145](../../../../../../../backend/src/sro/application/induction/companions.py#L145): Comment

Code: `expected_status=200`

> 200 when the collection was named rather than observed:
> the request it was synthesised from was a create, and a
> read that expects 201 fails on every success.

## `_skill`, [line 149](../../../../../../../backend/src/sro/application/induction/companions.py#L149): Comment

Code: `assertions=(`

> The only assertion a read needs, and the one that makes it
> verifiable: it answered the way it answered for the human.

## `_skill`, [line 162](../../../../../../../backend/src/sro/application/induction/companions.py#L162): Comment

Code: `aligned_recording_ids=(recording_id,),`

> The one step this version has -- a read -- is built from what
> this exact recording observed, not left to the default that
> means "nobody said". One recording, and it plainly shaped it.

## `_skill`, [line 190](../../../../../../../backend/src/sro/application/induction/companions.py#L190): Comment

Code: `version.earn(Verdict.WITHHELD, at)`

> A read is the safest thing in the system and nothing about it is withheld
> at the next rung, so it starts where every other version starts and takes
> the same first step immediately.
