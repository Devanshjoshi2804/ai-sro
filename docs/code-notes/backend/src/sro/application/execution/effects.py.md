# Notes for `backend/src/sro/application/execution/effects.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/effects.py`](../../../../../../../backend/src/sro/application/execution/effects.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/effects.py#L1): Docstring

> The register of verified writes, and what it buys a job.
>
> Ported from `new_agent_arch/src/rig/effects.py`, over the `WorkflowRepository`
> port -- and with it the two gates the rig's runner kept around those calls,
> which are the half of the rule that decides which of a run's steps reach the
> register and which empty it.
>
> The rule itself is `sro.domain.execution.belts` and is not restated here:
> `state_verified` is the gate the repository keeps, `RunProof` is what it
> assembles out of the runs, and `earned_from` counts them.
>
> D2 of the autonomous-workflows design: autonomy is earned by verified effect,
> not by counting runs. A write counts only when the verifier decided `held` by
> state -- a status the server answered, or a read that showed the record -- and
> never by a picture, because a model reading a screenshot is not evidence
> anything was written. `K_EARNED_RUNS` live runs that held, each with every
> write of theirs in the register, is what a job pays for the right to write
> without asking a person first.
>
> And one failed write empties the register for the WORKFLOW, not for the run
> that made it. A job that has ever written wrongly starts earning again from
> zero, and the next runs ask for a tap.

## module, [line 10](../../../../../../../backend/src/sro/application/execution/effects.py#L10): Note on the line above

Code: `K_UNEARNING = ("failed", "unclear")`

> The verdicts on a write that un-earn the job. `unclear` counts with
> `failed`: a live write nobody could show held is exactly the state the tap
> exists for.

## `wrote`, [line 13](../../../../../../../backend/src/sro/application/execution/effects.py#L13): Docstring

> Whether this step sent something that may have changed the warehouse.
>
> The step's own marker, which the runner set at send time out of the same
> `may_write` the tap and the rescue gate use -- SQL cannot ask `writes()`,
> and the evidence a later reader would have to ask it about may have been
> re-mined by then. So a step marked `wrote` is a step that can earn, and the
> same predicate is what un-earns: a step that could not earn cannot un-earn.
>
> A skipped step has no stored result at all, so it is not a write. It is not
> something a run has to have verified, and it must not stop one that did.

## `record_effect`, [line 17](../../../../../../../backend/src/sro/application/execution/effects.py#L17): Docstring

> Register one write of this run that the verifier saw hold by state.
>
> Three gates, read off the record rather than off the runner's locals so
> that a second caller cannot forget one: the run was live, because a dry run
> sent nothing and proves nothing about writing; the step held; and the step
> wrote. The fourth -- that the verdict came from a state belt and not from a
> picture -- is `state_verified`, which is kept once, by the repository.

## `_remember_the_write`, [line 37](../../../../../../../backend/src/sro/application/execution/effects.py#L37): Docstring

> And that this ENDPOINT can be sent, which is a different fact.
>
> An effect is about one write of one run of one job. This is about the
> `(method, path)` itself, and it is what decides whether the next run of
> any job may send the call instead of clicking Save -- `plan_step` refuses
> unless the endpoint is in a ledger, and the only ledger was
> `knowledge-base/index/write-endpoints.json`, a research project's file
> edited by hand between sessions. So a deployment that had watched its own
> write succeed could not say so: `Delete a Customer Type` ran eight times
> here, each confirmed by a read-back, and the ninth run still clicked.
>
> Measured 2026-09-21 on this deployment: 26 steps planned from evidence
> against 162 planned by a model, and a run whose write replays as a call
> performs 0.7 clicks against 1.5 while skipping 4.1 steps of scaffolding.
> The gate was not the mechanism. It was that nothing could widen it.
>
> The same four gates as the effect above, because this is the same moment
> -- and the bar is the one the file itself claims: somebody watched this
> endpoint succeed and confirmed it on the state, not in a picture.

## `may_have_landed`, [line 64](../../../../../../../backend/src/sro/application/execution/effects.py#L64): Docstring

> Whether a write this step made might actually be in the warehouse.
>
> The question `forget_effects` has always meant to ask and could not: its
> own docstring says *a write that went out and did not hold*, and the marker
> it had says only *this step was going to write*. The two are different for
> most of the ways a step fails, and the difference is the whole of item 7's
> approval fatigue.
>
> Measured on the deployment 2026-09-19. `Create a Customer Type` had
> **twenty live runs whose write held by a state belt** and exactly **one**
> row in its effects register, because seventeen other runs failed a write
> and each one wiped the register whole. Of those seventeen, ten never wrote
> anything at all: five `TypeError: Failed to fetch`, one with no CSRF token
> on the page, one with no tab open on the system, one whose control was
> never found, and two where nobody approved the write inside five minutes.
> The job could therefore never reach `K_EARNED_RUNS`, and every run this
> system has ever done asked a person to tap approve.
>
> Two readings, and each is one the rescue gate two lines away already makes:
>
> **The browser answered `ok: false`** -- it never performed the command:
> unreachable, no tab on the system, no control found, the approval that
> timed out. Nothing left the machine, so nothing can be in the warehouse.
>
> **The server itself refused it** -- a `4xx`. A warehouse that answered 422
> did not write the record, and the deployment's own register was emptied by
> one of those.
>
> A `5xx` is NOT that case and must go on un-earning: a server that broke
> half way may have written and then failed, and "the state is unknown after
> a write" is exactly what the register is for. Everything else is a write
> that went out and could not be shown to have held, which is likewise what
> must cost a job its autonomy.
>
> A step with no result at all never reaches here: `wrote` reads the marker
> off the result, and the step `_fell_over` stamps has neither. That is the
> rule this file has always had, and `test_effects.py` says so by name.

## `can_try_again`, [line 74](../../../../../../../backend/src/sro/application/execution/effects.py#L74): Docstring

> Whether this run can be started again with one press.
>
> A run stops for reasons that have nothing to do with the job -- a session
> that expired, a tab closed, a browser that could not be reached -- and the
> offer that started it is spent, so the request sits there until somebody
> notices. On a job started from a mailbox that can be hours.
>
> **Only where nothing it did may have landed.** Every step that wrote either
> never left the browser or was refused by the warehouse: `may_have_landed`,
> the same reading that decides whether a failed write costs a job its
> autonomy, asked here about the other half of the same danger. A second
> press after a write that might be in the warehouse is how a customer gets
> two of something, and no button is better than that.
>
> Nothing to try again on a run that held, and nothing to press on one still
> going.

## `forget_effects`, [line 80](../../../../../../../backend/src/sro/application/execution/effects.py#L80): Docstring

> A write that went out and did not hold un-earns the whole job.
>
> Everything the WORKFLOW had earned, not this run's own rows: a job that has
> ever written wrongly starts again from zero.
>
> Asked of a finished run rather than from the step that failed, because the
> step body is not reached when a browser goes away mid-write -- and that run
> wrote, was never shown to have held, and would otherwise have kept its
> autonomy.
>
> And only where the write MAY have landed. A step whose command the browser
> never performed changed nothing, and punishing a job for it is how a job
> with twenty verified writes ends up with one row in its register and a
> person tapping approve on every run. See `may_have_landed`.
>
> Returns how many effects were forgotten, and zero when this run un-earned
> nothing.

## `earned`, [line 92](../../../../../../../backend/src/sro/application/execution/effects.py#L92): Docstring

> Whether this job may write without asking a person first.
>
> Task 1's `tallies` is deliberately not asked here, and not because it is
> the more expensive read: it cannot answer this question at all. It counts
> runs and runs that held, and has no notion of a verified effect -- a job
> with a hundred held runs and nothing in its register has earned nothing.
> Only `proofs` carries what the rule compares.

## `_remember_the_write`, [line 45](../../../../../../../backend/src/sro/application/execution/effects.py#L45): Comment

Code: `watched = (step.result or {}).get("called")`

> What the STATUS BELT watched go out, and only then what this step sent.
>
> The belt first because it is the one that covers a click: the send is a
> click and carries no url, so a ledger fed only by `sent` could only ever
> learn endpoints that already replayed as calls -- a bootstrap that never
> starts, and the whole reason `Delete a Customer Type` clicked Save on
> its ninth run.

## `_remember_the_write`, [line 51](../../../../../../../backend/src/sro/application/execution/effects.py#L51): Comment

Code: `return`

> Nothing watched and nothing sent: a step verified some other way.
> A pattern learnt from a call nobody identified is a licence to send
> one nobody watched.

## `may_have_landed`, [line 68](../../../../../../../backend/src/sro/application/execution/effects.py#L68): Comment

Code: `if result.get("refuted") is True:`

> A read that went and looked, and did not find it.
>
> Measured on the deployment 2026-09-22 at 01:37. `Create a Customer Type`
> clicked Save, the read-back answered, and the record was not in it --
> "a read of .../customerTypes does not show the value this run supplied".
> The run stopped, and because the step had written, this said the state
> was unknown and the panel offered nothing at all. The operator was left
> with a half-filled form and a sentence.
>
> It was not unknown. Something looked. `refuted` is set by exactly one
> verdict -- `verify`'s read-back, and only where the read itself answered
> -- so it cannot be confused with the several other ways a write ends up
> `failed` by the read belt with the state genuinely open.
