# Notes for `backend/src/sro/domain/observation/identity.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/identity.py`](../../../../../../../backend/src/sro/domain/observation/identity.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/identity.py#L1): Docstring

> A5 — the shape key: what makes two doings the same job.
>
> Cited gesture ids are per-occurrence, so two independent doings of one job cite
> disjoint sets and overlap on them is always zero. That question -- "is this a
> re-read of evidence I have already processed" -- is answered by ids. This is the
> other question: "is this the same job as one I saw on different evidence", and
> it needs a key derived from the evidence rather than the evidence itself.
>
> Never cssPath or xpath: both encode document position, both change when the page
> is restyled, and a key built on them is the brittleness this replaces.

## module, [line 11](../../../../../../../backend/src/sro/domain/observation/identity.py#L11): Note on the line above

Code: `K_TEXT_IDENTITY_MAX = 40`

> The longest free text that can stand as a control's identity.
>
> A button says "Save"; a paragraph of page copy says nothing about which control
> was touched, changes with the page, and would be served to every browser as a
> shape.

## module, [line 56](../../../../../../../backend/src/sro/domain/observation/identity.py#L56): Note on the line above

Code: `K_SAME_NAME = 0.5`

> How alike two jobs' names must be before a shape may call them one job.
>
> **A veto, never a join.** The shape decides what is the same; this can only
> keep two things apart. The model's own `same_as` decides nothing here and
> still does not -- nothing is asked to re-judge anything. What is compared is
> the names it already gave two pieces of work, and only to stop a merge.
>
> Why it has to exist. Measured on the deployment 2026-09-21, one pass:
>
>     Send Email:    recognised as a job already stored -- wfl_207e… at 1.00
>     Forward Email: recognised as a job already stored -- wfl_207e… at 1.00
>
> `wfl_207e…` is `Reply to Email`. Three different tasks, one stored job, full
> confidence -- and no threshold could have saved it, because the shapes really
> were indistinguishable:
>
>     Reply to Email    [textbox|Describe your message, click]
>                       [button|Send ⌘Enter,            click]
>     Forward Email     [anon|click,                    click]
>                       [button|Send ⌘Enter,            click]
>
> They happen on one screen, so the screen rule cannot separate them. `anon`
> aliases onto any named click of the same kind, which it must -- whether a
> recording could name a control is a property of that recording and not of the
> job, and without the alias one job recorded twice splits in two (2026-09-19,
> the same mailbox). So the anon click matches the textbox, `Send` matches
> `Send`, and a two-entry shape is 2/2 contained by another. There is nothing
> left in the evidence that says `Forward` rather than `Reply`.
>
> Except the name. `reply to email` against `forward email` shares one word in
> four; `create a customer type` against `create customer type` shares three in
> four, which is the same job named twice by a model that does not phrase things
> identically. Half is between them, and comfortably.

## module, [line 58](../../../../../../../backend/src/sro/domain/observation/identity.py#L58): Note on the line above

Code: `NOT_A_NAME = frozenset({"a", "an", "the", "to", "for", "of", "in", "on", "and"})`

> Words that say nothing about which job this is.

## module, [line 108](../../../../../../../backend/src/sro/domain/observation/identity.py#L108): Note on the line above

Code: `ANON = "anon|"`

> What `target_identity` returns when it cannot name the control at all.
>
> It is the ABSENCE of a name, not a different name, and two shapes that differ
> only there are not two jobs. See `_shared`.

## `target_identity`, [line 18](../../../../../../../backend/src/sro/domain/observation/identity.py#L18): Docstring

> What to call the control this gesture touched, stably across occurrences.

## `screen_of`, [line 40](../../../../../../../backend/src/sro/domain/observation/identity.py#L40): Docstring

> Which SCREEN this happened on, not merely which system.
>
> `system` is an origin, and an origin is not a screen in a single-page
> application: every configuration screen in this deployment's WMS is
> `bf56-kms-wms-web-np2.jdadelivers.com`, and which one you are looking at
> lives in the fragment. Measured 2026-09-21, on an operator's own
> demonstration:
>
>     demonstrated  …/portal?siteId=SG#wm.config/wm.config.equipment.
>                   equipment.transportequipmenttype////
>     folded into   …/portal?siteId=SG#wm.config/wm.config.equipment.
>                   equipment.warehouseequipmenttype////   at 0.50
>
> Two different screens, one origin, and the same widget choreography every
> config screen in the product has -- click a tab, click Add, type, type,
> click Save. With only the origin in the key there was nothing left to tell
> them apart, so three clean demonstrations of a new job were recognised as
> an old one, and a parameter learnt from one screen was written onto the
> other. This store holds 13 screens across 2 origins; the key could see the
> 2.
>
> **The query is dropped and the fragment's value tail with it.** `siteId`
> is which warehouse somebody is signed in to and the trailing `////` are
> empty positional segments -- both change between two doings of one job,
> and a screen that changed per doing would make every doing a new job,
> which is the same bug pointing the other way. What is kept is the dotted
> route, which is what the application calls the screen.
>
> `page_url` and not `url`: the tab's address, because a gesture inside an
> iframe reports the frame's src, and the frame is not the screen.

## `shape_key`, [line 50](../../../../../../../backend/src/sro/domain/observation/identity.py#L50): Docstring

> The job's shape: which control, on which screen, touched how -- in order.

## `named_alike`, [line 71](../../../../../../../backend/src/sro/domain/observation/identity.py#L71): Docstring

> Whether these two names could be the same job's.
>
> Generous on purpose, because it is a veto: a name this cannot read -- an
> empty one, a job proposed with no title -- is not evidence of difference,
> so it does not block anything.

## `containment`, [line 78](../../../../../../../backend/src/sro/domain/observation/identity.py#L78): Docstring

> |a ∩ b| / min(|a|, |b|).
>
> Containment rather than Jaccard, because a three-step "create supplier" sits
> INSIDE a twelve-step "create supplier, add item, set status in SAP". Jaccard
> drowns the small set in the union and calls them different jobs; containment
> says the smaller is part of the larger, which is true and is the variant
> relation worth surfacing.

## `jaccard`, [line 84](../../../../../../../backend/src/sro/domain/observation/identity.py#L84): Docstring

> |a ∩ b| / |a ∪ b|. For the occurrence question, where the two sets are
> the same size by construction.

## `_shared`, [line 111](../../../../../../../backend/src/sro/domain/observation/identity.py#L111): Docstring (debt)

> How many steps these two shapes have in common.
>
> Equal entries, and then an unnamed step against a named one on the same
> system doing the same thing. `target_identity` falls back to `anon|click`
> whenever a recording gives it nothing to work with -- no component, no
> role, no accessible name, no test id, no short text -- and whether it has
> anything to work with is a property of THAT recording, not of the job.
>
> Measured on the deployment 2026-09-19, tenant `greyorange`:
>
>     Reply to Email  [mail.google.com, "link|Reply",  click]
>                     [mail.google.com, "button|Send", click]
>     Reply to Email  [mail.google.com, "anon|click",  click]
>                     [mail.google.com, "button|Send", click]
>
> Two rows, one job, mined three hours apart. The overlap was the Send button
> and nothing else, which is one step, which is under the bar -- so the second
> reading was kept as a NEW job rather than folded into the first. The same
> day held three `Log in to Keycloak` and two `Navigate to Warehouse Sub-menu`
> for the same reason, and each of them offers itself on the page it belongs
> to: the operator signs in, the job is satisfied, and a duplicate still
> thinks the page is its own and asks again.
>
> Only across a matching system and kind: an unnamed click on the mailbox is
> not the warehouse's Save button, and it is not a keystroke either.
>
> ponytail: `anon` is the only aliasing here. Two recordings that both name a
> control and disagree -- `viewport toolbar` against `toolbar button`, the
> third duplicate of that day -- stay apart, because a rule that called those
> the same would call every click on a system the same. The upgrade is
> `skill.learned.same_control`'s alias set, which needs the names carried on
> the shape and is a migration, not an edit.

## `resolve`, [line 124](../../../../../../../backend/src/sro/domain/observation/identity.py#L124): Docstring

> Which of the known workflows, if any, this proposal already is.
>
> No guard for an empty shape or an uncited proposal: containment and jaccard
> both return 0.0 for an empty set, no threshold here is at or below zero, and
> a proposal that matches nothing falls out of the bottom as "new" anyway.

## `target_identity`, [line 21](../../../../../../../backend/src/sro/domain/observation/identity.py#L21): Comment

Code: `return f"anon|{gesture.action.kind}"`

> A scroll has no target -- you scroll a page, not an element.

## `target_identity`, [line 29](../../../../../../../backend/src/sro/domain/observation/identity.py#L29): Comment

Code: `if target.role and target.name and _names_a_control(target.name):`

> The same rule on the name as on the text below it, and for the same
> reason. An accessible name is free text off the page, not an identifier a
> developer assigned -- `item_id`, `query` and `test_id` are those -- and it
> is at least as likely to be a paragraph as `innerText` is. It was the one
> branch the rule was not applied to.
>
> Measured on this deployment, 2026-09-15: an operator clicked the body of
> the mail telling them what to create, and Chrome's accessible name for
> that div was the whole instruction -- so `Create a Customer Type` was
> shaped on
>
>     name|a customer type :- GGD\ndescription :- leaning new SRO type 01
>
> A shape keyed on the words of ONE mail cannot match the next one, so the
> job could never be recognised again; and `shape.py` promises in its first
> paragraph that nothing here carries a typed value, while this served an
> operator's own mail to every browser in the tenant asking for shapes.

## `target_identity`, [line 37](../../../../../../../backend/src/sro/domain/observation/identity.py#L37): Comment

Code: `return f"anon|{gesture.action.kind}"`

> Honest rather than precise. "A click on mail.google.com we cannot name"
> is what actually happened, and the rest of the shape is what tells this
> job from another.

## module, [line 90](../../../../../../../backend/src/sro/domain/observation/identity.py#L90): Comment

Code: `K_SAME_EVIDENCE = 0.5`

> A11 — identity, and it is arithmetic.
>
> Two questions that look like one. Cited gesture ids are per-occurrence, so two
> independent doings of the same job cite disjoint sets and their overlap is
> always zero -- ids can only tell you whether this is a re-read of a window
> already processed. Whether it is the SAME JOB seen on different evidence needs a
> key derived from the evidence, compared by containment.
>
> The model's own `same_as` is recorded and decides neither. A model asked to
> re-judge its earlier verdict disagrees with itself at roughly 90%, and `same_as`
> asks precisely that.

## module, [line 92](../../../../../../../backend/src/sro/domain/observation/identity.py#L92): Comment

Code: `K_MIN_SHARED_STEPS = 2`

> Containment divides by the SMALLER shape, so a two-step workflow is half
> contained by anything sharing a single step -- a lookup both jobs happen to
> begin with would fold two unrelated jobs into one. A ratio alone cannot tell
> "half of two" from "half of twenty", so the overlap must also be real in
> absolute terms.
>
> But it cannot ask for more shared steps than the smaller shape HAS, and it
> did. A shape is a SET, so a job whose two steps touch the same control the
> same way is one entry wide -- measured on the deployment 2026-09-19:
>
>     Log in to Keycloak  [keycloak, "name|Username or email", type]
>                         [keycloak, "name|Username or email", type]
>
> Containment against the stored job of the same name was 1.0, a perfect
> match, and `1 >= 2` refused it. So it was kept as a new job, and so was the
> next reading of it, and the tenant ended the day with three `Log in to
> Keycloak` -- each one offering itself on the sign-in page, so signing in
> never made the card stop. A bar nothing can clear is not a bar.

## `Resolution`, [line 97](../../../../../../../backend/src/sro/domain/observation/identity.py#L97): Inline

Code: `kind: str`

> "new" | "same_occurrence" | "same_job"

## `Resolution`, [line 101](../../../../../../../backend/src/sro/domain/observation/identity.py#L101): Comment

Code: `contains: bool = False`

> True when MINE is the larger shape -- mine contains theirs. Three states
> exist and this collapses two of them: "theirs contains mine" and "neither
> contains the other" are both False here, and they are not the same fact.
>
> A bool on purpose, for now. Nothing acts on it: Task 6 flagged the
> collapse, Task 7 confirmed there was no first consumer, and Task 8
> confirmed the mining loop does not branch on `same_job` at all -- so the
> third state would be a distinction drawn for no reader, and a guess at
> what that reader will want.
>
> The caller that needs it is specific and namable: the one that must decide
> whether to REPLACE a known workflow with this proposal rather than link to
> it. "Mine contains theirs" is the case for replacing; "theirs contains
> mine" is the case for discarding mine; "neither" is the case for keeping
> both. Whoever writes that caller should widen this to those three states
> rather than reading False as "theirs contains mine".

## `_shared`, [line 117](../../../../../../../backend/src/sro/domain/observation/identity.py#L117): Comment

Code: `named = sorted(one for one in right if not one[1].startswith(ANON))`

> Sorted so a shape matching several candidates matches the same one every
> time. No bookkeeping to stop two unnamed steps claiming one named step:
> an entry carries its kind twice -- `anon|click` beside `click` -- so two
> unnamed entries of one system and kind are one entry by the time a set
> has been made of them.

## `resolve`, [line 125](../../../../../../../backend/src/sro/domain/observation/identity.py#L125): Comment

Code: `peers = [other for other in known if other.tenant == proposal.tenant]`

> tenant is the one other field of Workflow that can make two rows
> unmergeable however alike they look. known_workflows() scopes its query by
> tenant; resolve() takes whatever list it is handed, and welding one
> tenant's job onto another's is not a mistake anyone can undo afterwards.

## `resolve`, [line 135](../../../../../../../backend/src/sro/domain/observation/identity.py#L135): Comment

Code: `return Resolution("same_occurrence", seen.id, seen_score)`

> The overlap as measured, not a flat 1.0: three citations of four is
> the same occurrence and is not identity, and a constant is a number
> no caller can ever threshold on a second time.

## `resolve`, [line 143](../../../../../../../backend/src/sro/domain/observation/identity.py#L143): Comment

Code: `matched = _shared(shape, theirs)`

> Containment over the SAME notion of a shared step the bar below uses.
> Two gates that disagree about what counts as shared is one gate: with
> `containment`'s raw set intersection here, a proposal whose unnamed
> step aliases a named one scored as though it had not, and `Reply to
> Email` cleared K_SAME_JOB at exactly 0.5 by arithmetic coincidence.

## `resolve`, [line 145](../../../../../../../backend/src/sro/domain/observation/identity.py#L145): Comment

Code: `whole = matched >= K_MIN_SHARED_STEPS or matched == len(shape)`

> Both bars first, then the best of whatever clears them -- not the best
> overall and then the bars. A one-step stub is 1.0-contained by
> anything beginning where it does; ranking before filtering lets it win
> the comparison, fail the step count, and hide the real match behind it.
> Two shared steps, OR every step this proposal has. See
> K_MIN_SHARED_STEPS: the bar cannot ask a one-entry shape for two, and
> `min(K_MIN_SHARED_STEPS, len(shape), len(theirs))` is the wrong way to
> say so -- measured on the deployment 2026-09-19, it folded a two-step
> `Navigate to Warehouse Sub-menu` into `Navigate to Receiving`, whose
> own shape is one generic `tabItem` click repeated three times, on the
> strength of that one click. Wholly-contained is the honest reading:
> every distinct step this proposal has already exists in that job, so
> it is a fragment of it rather than a new job.

## `resolve`, [line 146](../../../../../../../backend/src/sro/domain/observation/identity.py#L146): Comment

Code: `if (`

> And the name, which can only keep them apart. Two jobs on one screen
> whose shapes are equally generic -- a mailbox's `Reply`, `Forward`
> and `Send` -- have nothing else left to be told apart by. See
> `K_SAME_NAME`.
