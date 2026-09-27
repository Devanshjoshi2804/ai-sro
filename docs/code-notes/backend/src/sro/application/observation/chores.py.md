# Notes for `backend/src/sro/application/observation/chores.py`

Whether a job is a chore -- it signs in (`checks.signs_in`) or signs out
(`checks.signs_out`) -- decided from its evidence and written by one writer.
Its own module (F3 round 1, M3) so `Teach.learn_field` imports the decider
and not the whole mining pass.

## `evidenced`, [line 21](../../../../../../../backend/src/sro/application/observation/chores.py#L21): Note on the function

> Whether every gesture a job cites is stored -- the one precondition for
> judging it from its evidence.

## `_sitting`, [line 26](../../../../../../../backend/src/sro/application/observation/chores.py#L26): Note on the function

> The gestures a verdict is judged against: the job's cites and everything
> from its first cite to `K_SITTING_GAP_S` after its last, inclusive at both
> ends. Every path -- grow and heal, which hold the tenant's whole store, and
> the sweep and a learn, which load `evidence_of` -- judges this same set, so
> a verdict cannot flip between passes because one path saw a gesture the
> other did not (F3 round 1, M1: a password typed in the same burst as the
> first cite, at the same instant, was read by the heal and missed by the
> sweep's `at > first`).

## `judged`, [line 37](../../../../../../../backend/src/sro/application/observation/chores.py#L37): Note on the function

> The one decider of `signs_in` and `signs_out`, used by `fill_in_passwords`,
> `_grow`, `decide_sign_ins` and (through it) `Teach.learn_field` alike, and
> always after the password steps and presses are healed in (on a copy, so
> judging writes nothing): the stored steps of a job mined before the healing
> existed lack them, and `signs_in` asks whether every writing step is a
> sign-in step.
>
> A job without its evidence -- no cites, or a cite not stored -- has no
> verdict: `None`, and nothing is written (F3 round 1, I1). A stored `true`
> the evidence once gave is never overwritten by a judgement made without
> it, and a job nobody has judged stays undecided. The cost is that such a
> job is read again on each sweep; bounded by the jobs whose evidence is
> incomplete.

## `decide`, [line 51](../../../../../../../backend/src/sro/application/observation/chores.py#L51): Note on the function

> Judges the job as it was read and writes both verdicts with
> `WorkflowRepository.decide`, a compare-and-set over that read: its steps
> and both verdicts. A grow, heal or learn that changed the steps between the
> read and the write -- or another decider that got there first -- wins, and
> this decision is dropped rather than written over theirs; that writer
> decided from its own steps. Nothing is written when the verdict already
> holds or cannot be judged, so an ordinary pass writes nothing.

## `evidence_of`, [line 68](../../../../../../../backend/src/sro/application/observation/chores.py#L68): Note on the function

> The cited gestures of some jobs, widened to the sitting around each
> (`K_SITTING_GAP_S`): everything `signs_in`, `signs_out`, `with_passwords`
> (between the first and last cite), `with_the_press` (`SOON_S` after a
> click), `signs_in_to` and `recorded_login` read. Bounded by the jobs asked
> about, never the tenant's whole history. Shared with
> `scripts/migrate_vault_keys.py`.
>
> The store's `after` is exclusive, so it is asked from the float just below
> the first cite: a gesture at that very instant is part of the sitting
> (`_sitting`), and asking from the cite itself missed it.

## `decide_sign_ins`, [line 90](../../../../../../../backend/src/sro/application/observation/chores.py#L90): Note on the function

> Decides some jobs of one tenant, new gestures or not: the sweep's undecided
> ones (live, `signs_in` or `signs_out` NULL -- 0087 leaves every stored job's
> `signs_out` NULL, so each is decided both ways once), and a job
> `Teach.learn_field` has just grown. 0069 stored `false` on every existing
> job and only new gestures ever re-judged one, so a quiet system never
> decided anything. Only those jobs' evidence is read (`evidence_of`).
>
> Written through `decide`: column-only, never a whole-job save. New gestures
> re-judge a decided job through `fill_in_passwords`, as before.
