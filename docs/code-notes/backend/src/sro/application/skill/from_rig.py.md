# Notes for `backend/src/sro/application/skill/from_rig.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/from_rig.py`](../../../../../../../backend/src/sro/application/skill/from_rig.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/from_rig.py#L1): Docstring

> A workflow the rig mined, as steps this system can run.
>
> The rig watches a day and proposes workflows; every step of one cites the
> gestures it was read from. That citation requirement exists to stop the model
> inventing steps -- free generation hallucinated up to 21% of them, citation
> forced it under 7.5% -- and it turns out to carry everything a runner needs as
> well, because a cited gesture is a real gesture and a real gesture has a real
> target.
>
> So the prose a step carries is its description, and its citations are its
> mechanism. Measured over the eight workflows mined from 170 hours of real
> capture -- 8 workflows, 66 steps, 165 actions:
>
> - all 66 steps produce at least one action
> - 62 of 66 resolve to at least one locator; the four that do not cite only
>   scrolls, which have no target by design
> - 57 of those reach a component query -- the framework's own handle, the
>   strongest rung on the ladder
> - per action, the strongest rung available is a component query for 118, text
>   for 7, css path for 6, role-and-name for 1, and nothing at all for 33 --
>   which are the scrolls
>
> The 33 matter to how that last figure is read. An earlier version of this note
> said "118 of 132", taking as its denominator only the actions that had ANY
> locator, which quietly excluded every action that had none; against all 165 it
> is 118, not 89%.
>
> Nothing here reaches for the rig. It consumes the shape stored in the rig's
> `gestures.gesture_json` column -- the extension's own wire protocol -- and
> `GET /v1/workflows/{id}/evidence` now serves exactly that, along with the
> captured requests and the capture streams a `Provenance` needs. Not
> `/v1/gestures`, which reduces a target to its NAME for a person reading a
> listing: a caller wired to that one gets a plan with no locators and no error.
>
> So the two systems share a shape rather than a dependency, and there are two
> ways to hold that shape -- the column, for something with the rig's database,
> and the route, for anything else.

## `_text`, [line 24](../../../../../../../backend/src/sro/application/skill/from_rig.py#L24): Docstring

> A JSON value as a string, or None when it is not usable as one.
>
> Everything arriving here came off `json.loads`, so every field is `object`
> until something looks. A non-string where a name belongs is not a name.

## `_literal`, [line 32](../../../../../../../backend/src/sro/application/skill/from_rig.py#L32): Docstring

> A recorded string as a template that means only itself.
>
> `Template` is `string.Template`, so `$` starts a placeholder: a value of
> `A$B` reports `{"B"}` as a parameter it needs, and `render` then either
> raises KeyError or quietly substitutes something the operator never typed.
> Nothing here is a parameter unless a binding says so, and a `$` in a
> recorded value or a css path is a `$` the operator saw. Measured over the
> real corpus: 0 values and 0 css paths contain one, which is the reason this
> is a guard rather than a bug report.

## `locators_for`, [line 36](../../../../../../../backend/src/sro/application/skill/from_rig.py#L36): Docstring

> The ladder for one element, strongest strategy first.
>
> The order is LocatorStrategy's own: a component query is what the
> application's code uses to find the control, and a css path is the last
> resort its docstring calls it. A target with nothing usable yields an empty
> ladder rather than a guessed one -- `UiPlan.replayable` reads that as "the
> demonstration produced nothing worth replaying by", which is a fact about
> the step and not a reason to invent.

## `fingerprint_for`, [line 58](../../../../../../../backend/src/sro/application/skill/from_rig.py#L58): Docstring

> The element as the recorder saw it, or None when it saw nothing usable.
>
> ElementFingerprint refuses one with no identifying signal, and a scroll
> carries no target at all -- so this returns None rather than letting the
> invariant raise on evidence that is simply not about an element.

## `_component`, [line 76](../../../../../../../backend/src/sro/application/skill/from_rig.py#L76): Docstring

> The framework's own handle, when there is a whole one.
>
> ComponentIdentity refuses a framework or query that is empty, and rightly:
> a component identity with no query identifies nothing. A recorder that
> reached the framework enough to report an itemId but not a query still
> yields a usable one, because `#itemId` is a query in ExtJS's own language --
> which is also the locator this builds from it.

## `_order`, [line 96](../../../../../../../backend/src/sro/application/skill/from_rig.py#L96): Docstring

> A step's position, from JSON that is not obliged to be sensible.
>
> Every other field here goes through `_text` or `_mapping`; `order` went
> through neither, and a mix of `1` and `"2"` made `sorted` raise
> TypeError -- while an all-string set sorted lexicographically, putting
> step 10 before step 2 without raising at all, which is worse. Anything
> unusable sorts last rather than at zero: a step whose order nobody can
> read is not a step that ran first.

## `parameter_name`, [line 113](../../../../../../../backend/src/sro/application/skill/from_rig.py#L113): Docstring

> A control's name as something that can actually be a parameter.
>
> The rig names a parameter after the control it was typed into, by the
> ladder in `rig.parameters._by_control`: an ExtJS itemId, else the field's
> own LABEL, else the accessible name. The last two are free-form UI text
> written for a person, and two separate rules downstream refuse it:
> `Parameter.__post_init__` requires `str.isidentifier()`, and
> `string.Template.idpattern` is `(?a:[_a-z][_a-z0-9]*)` -- ASCII only, so a
> name that IS a Python identifier can still be read short. `café` passes
> `isidentifier()`, `$café` parses as `caf`, and the version is then refused
> for referencing a parameter it never declared.
>
> Neither of those is hypothetical. `Username or email` is a control name in
> the real corpus today, in the login flow -- the most repeated job in any
> capture and the first thing a second demonstration will diff. It only has
> not crashed yet because no workflow has reached two occurrences.
>
> So: every character outside `[A-Za-z0-9_]` becomes an underscore, the edges
> are trimmed, and a leading digit is prefixed. Deterministic, because both
> sides of the binding have to agree on it -- this is the one rule, and
> `_control` below reads names through it too.

## `_control`, [line 120](../../../../../../../backend/src/sro/application/skill/from_rig.py#L120): Docstring

> The control a gesture acted on, under the name the rig parameterises by.
>
> `rig.parameters._by_control` keys a doing by exactly this ladder -- ExtJS
> itemId, then the field's own label, then the accessible name -- so a
> parameter's `name` is one of these strings, read through `parameter_name`
> because a UI label is not a valid one. Reproduced here to COMPARE against,
> never to mint a name from: a mismatch leaves the value literal, which is
> the safe direction.

## `declared_parameters`, [line 132](../../../../../../../backend/src/sro/application/skill/from_rig.py#L132): Docstring

> Every parameter the workflow declares: safe name to (label, values).
>
> One reader, because two agreeing loops is how this codebase came to have
> three word-splitters that disagreed about `SAMLResponse`. `bindings_for`
> decides what a gesture's value becomes and `parameters_from_rig` decides
> what the version declares; if those two disagree about a name by one
> character, the version references a parameter it does not declare and the
> domain refuses the whole build.
>
> A safe name two controls both land on is dropped, not merged. Keeping one
> of a colliding pair binds the other control's values to a name that is not
> its own -- the bind-by-coincidence defect this module was already rewritten
> once to close.

## `bindings_for`, [line 155](../../../../../../../backend/src/sro/application/skill/from_rig.py#L155): Docstring

> Each parameter, against the values that job has been seen to take.
>
> Keyed by the parameter -- which is to say by the CONTROL, because the rig
> names a parameter after the control it was typed into. An earlier version
> keyed this by the value instead, to avoid re-deriving that name on this
> side, and the saving was not worth what it cost: two parameters each given
> `Active` on some doing collapsed to one entry, and every gesture carrying
> that value got whichever name sorted first. A value is evidence both sides
> hold, but a value is not an identity -- the control is.

## `plan_for_gesture`, [line 163](../../../../../../../backend/src/sro/application/skill/from_rig.py#L163): Docstring

> One recorded gesture as one step a driver could perform.
>
> None where the gesture is not a thing to replay: an unknown kind, or an
> action that needs a target and has no locator to find one by. The caller is
> expected to keep the step and record that it cannot be run, because a step
> silently missing from a plan is a job that will not do what it says.

## `plans_for_step`, [line 189](../../../../../../../backend/src/sro/application/skill/from_rig.py#L189): Docstring

> Every runnable action a step's citations name, in the order cited.
>
> A step is prose plus citations. The prose says what it was for; these are
> what it did. A citation naming a gesture nobody has is skipped rather than
> guessed at -- the rig's own `validate` refuses a workflow citing evidence
> that does not exist, so reaching this with one means the store moved.

## `plans_for_workflow`, [line 206](../../../../../../../backend/src/sro/application/skill/from_rig.py#L206): Docstring

> Each step beside what it would run, steps that run nothing included.
>
> The empty tuple is the point: a step citing only scrolls produces no plan,
> and a caller that dropped it would offer a job missing a step it was
> described as having.

## module, [line 12](../../../../../../../backend/src/sro/application/skill/from_rig.py#L12): Comment

Code: `_ACTIONS = {kind.value: kind for kind in ActionKind}`

> A gesture kind is already an ActionKind by name -- the rig re-declares the
> extension's protocol and this vocabulary comes from the same place. Mapped
> explicitly anyway, so a kind neither side has heard of is a miss rather than
> a crash.

## module, [line 14](../../../../../../../backend/src/sro/application/skill/from_rig.py#L14): Comment

Code: `_NEEDS_TARGET = {`

> Which of those a driver cannot perform without knowing where. UiPlan enforces
> the same rule; this is here to answer "why is there no plan for that step"
> without constructing one that will be refused.

## `plan_for_gesture`, [line 175](../../../../../../../backend/src/sro/application/skill/from_rig.py#L175): Comment

Code: `value = _text(gesture.get("value"))`

> A credential never reaches here: wire.Gesture drops the value at the
> parse boundary and trim/redaction re-check it. A value that survived to
> this point is the operator's own data, and it becomes a template because
> a run may be asked to type a different one.

## `plan_for_gesture`, [line 176](../../../../../../../backend/src/sro/application/skill/from_rig.py#L176): Comment

Code: `template = _literal(value) if value else None`

> A value the job is known to vary becomes the name it varies under, so a
> run can be asked for a different one. A value nobody has seen vary stays
> literal -- it is part of the job until evidence says otherwise, and
> guessing which literals are really inputs is the thing two doings exist
> to avoid.
>
> Bound only when the value was typed into the control the parameter is
> NAMED after. Matching on the value alone binds by coincidence: two
> parameters that were each given "Active" on some doing collide, and the
> alphabetically-first name wins for both -- and worse, a constant of the
> job that happens to equal some parameter's value turns into a `$name`
> the runner will substitute. This is one equality test against a field
> already in the gesture, not a second implementation of the naming rule.
