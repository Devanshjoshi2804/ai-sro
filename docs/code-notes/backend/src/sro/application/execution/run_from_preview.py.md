# Notes for `backend/src/sro/application/execution/run_from_preview.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/run_from_preview.py`](../../../../../../../backend/src/sro/application/execution/run_from_preview.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L1): Docstring

> Run a skill an operator has just read the preview of.
>
> `_check_runnable` refuses a RECORDED version because "a recorded skill has not
> been reviewed by anybody". After the preview it has been: by the operator, on
> the exact steps and the exact values, at the screen it will act on, with a stop
> button in front of them. ADR 014 makes that argument in full.
>
> Promote and run in one call. Two calls race, and a version promoted by a press
> that then failed to start is a version sitting at assisted because somebody
> clicked once and walked away.

## `RunFromPreview.begin`, [line 23](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L23): Docstring

> Promote what needs it and write the run row. Nothing has stepped yet.
>
> This is always a device run -- the panel's whole premise is the
> operator's own tab -- and `run_skill`'s device path answers before the
> run finishes so the id exists for `/runs/{id}/stream` and
> `/runs/{id}/stop` while it is still running. A caller that returned
> only once the run was over would have promised a stop button the
> operator could never reach in time to use it.
>
> `previewed` is the version number the panel actually rendered, sent
> back by the client rather than re-derived here. That is the whole of
> ADR 014: what is on the screen when the operator presses `Do it` is,
> line for line, what the run is about to do. This call used to take
> `skill.latest`, which is a different version from the one the panel
> previewed whenever a newer RECORDED one exists -- re-teaching,
> `repair_drift`, `map_step_to_tool` and `add_assertion` all produce one
> -- so the operator read v1's steps and values and v2 wrote, with v1's
> parameters, and an unreviewed version was promoted to ASSISTED on a
> press that never showed it.

## `RunFromPreview.begin`, [line 35](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L35): Comment

Code: `current = skill.runnable or skill.latest`

> What the panel would preview if it asked again, right now. The
> same expression `ResolveIntent` picks a candidate's version with
> (`skill.runnable or skill.latest`), so "has it moved" is asked in
> exactly the terms the preview was built in.
>
> Refused rather than run either way round. Falling *forward* to a
> newer version runs steps and values nobody read. Falling *back*
> to the previewed one, after a newer one exists, runs a version
> somebody has since decided is not the current one -- and
> silently, at the moment a person is least able to notice. So the
> only safe answer is to say so and send them back to look, which
> is one more read of a preview rather than one more warehouse
> write on a stale one.

## `RunFromPreview.begin`, [line 45](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L45): Comment

Code: `while version.stage.rung < PromotionStage.ASSISTED.rung:`

> Only a version that cannot run yet, and only as far as it needs
> to go. A press on the fifth run is not a fifth promotion, and the
> rungs above assisted are earned by runs, not by presses --
> `promote` itself refuses `from_where="preview"` past assisted, so
> this loop never asks it to.
>
> One rung per call: `check_promotion` refuses a jump of more than
> one, so a version sitting at RECORDED climbs through SHADOW on
> its way to ASSISTED rather than in a single bound the ladder
> would reject.

## `RunFromPreview.begin`, [line 50](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L50): Comment

Code: `acknowledging_fixed_values=True,`

> DECISION (task 5, amended after review; see ADR 014's
> "Consequences", which this comment now matches): pass
> True here rather than let a single-demonstration write
> refuse this promotion and dead-end the press.
>
> `acknowledging_fixed_values` exists because a version
> induced from one demonstration was never diffed against
> a second one -- nothing tells the values it sends apart
> from the values that one run happened to carry, so
> promoting it past shadow without anybody having looked
> would mean repeating that one run's exact write forever.
> The flag is the record that somebody looked.
>
> This is NOT the same claim the press already makes to
> reach ASSISTED at all, and the first version of this
> comment was wrong to say so: the preview shows
> `SkillStep.intent`, the resolved value of each
> *parameter*, and the starting tab -- a closed list. A
> value this flag guards is, by definition, not a
> parameter: one demonstration means nothing was diffed, so
> nothing told a value that varies apart from one that is
> simply constant, and it is exactly those constants --
> never surfaced as a parameter, never a line on the
> preview -- that the flag is about. The two sets of values
> do not overlap; reading one is not reading the other.
>
> Setting it is therefore an accepted residual risk, not a
> closed one, taken on the same terms ADR 014 already
> accepts one for: it documents its own gap ("What the
> operator did not read") and closes it the same way every
> other run's unread surprises are closed -- not by the
> preview, but by `run.wrong_because`, read before anything
> else `judge` reads, and `DEMOTE_AFTER_FAILURES` pulling
> the version back down after three. A write sent on a
> fixed value nobody actually read is exactly the surprise
> that backstop exists for. The alternative -- refuse and
> dead-end the commonest shape a freshly induced skill has,
> one demonstration and one write, on its very first press
> -- is the failure this task exists to close, so the risk
> is accepted rather than the feature.

## `RunFromPreview.begin`, [line 58](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L58): Comment

Code: `version=version.version,`

> Pinned to the version the operator previewed, which this
> call has just checked is still the current one and, where
> needed, promoted. Left to resolve on its own, `ExecuteSkill`
> would ask for "the latest version" again when it starts --
> and a second induction landing between this commit and that
> lookup would promote one version and run another, silently.

## `RunFromPreview.begin`, [line 62](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L62): Comment

Code: `medium=Medium.UI,`

> UI, not the NETWORK default: this run acts in the tab the
> preview named (`starts_on`), which is the entire load-bearing
> claim ADR 014 makes -- the operator read what would happen on
> the screen in front of them. A NETWORK replay would send the
> same calls invisibly, which is a different, undisclosed thing
> from what the preview described and the operator agreed to.

## `RunFromPreview.begin`, [line 63](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L63): Comment

Code: `may_take_focus=True,`

> True, deliberately: `run_skill`'s own field doc says a
> console run "somebody just asked for" may bring the tab
> forward, and a scheduled one may not, because the caller is
> the only one who knows whether a person is watching. Here the
> caller knows for certain -- this run exists only because an
> operator is looking at the panel right now, mid-task, with
> ADR 014's stop button already promised to them. Leaving this
> False would drive their own tab in front of them without
> bringing it up to show them, which defeats the one thing this
> feature is for.

## `RunFromPreview.begin`, [line 66](../../../../../../../backend/src/sro/application/execution/run_from_preview.py#L66): Comment

Code: `await ensure_runnable(uow, ctx, skill, version, request, now)`

> Ask before persisting anything, not after. `_check_runnable`
> covers more than the stage this loop just moved past -- a loop
> this deployment cannot yet replay through the browser, a
> parameter nobody supplied, a circuit breaker already open on
> this system -- and every one of those is a reason `ExecuteSkill`
> would refuse to start regardless of the promotion. Checking
> after the commit above (as an earlier version of this file did)
> meant that exact refusal landed with the version already sitting
> at ASSISTED and no run to show for it -- the "clicked once and
> walked away" state this module exists to prevent, just reached
> by a different door than the race the docstring names. Reusing
> `ensure_runnable` rather than re-deriving these rules means
> every reason `StartRun` can refuse today, or gains reason to
> refuse later, is covered here for free.
