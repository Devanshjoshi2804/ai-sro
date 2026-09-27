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

## module, [line 12](../../../../../../../backend/src/sro/domain/observation/identity.py#L12): Note on the line above

Code: `K_TEXT_IDENTITY_MAX = 40`

> The longest free text that can stand as a control's identity.
>
> A button says "Save"; a paragraph of page copy says nothing about which control
> was touched, changes with the page, and would be served to every browser as a
> shape.

## module, [line 57](../../../../../../../backend/src/sro/domain/observation/identity.py#L57): Note on the line above

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

## module, [line 59](../../../../../../../backend/src/sro/domain/observation/identity.py#L59): Note on the line above

Code: `NOT_A_NAME = frozenset({"a", "an", "the", "to", "for", "of", "in", "on", "and"})`

> Words that say nothing about which job this is.

## module, [line 109](../../../../../../../backend/src/sro/domain/observation/identity.py#L109): Note on the line above

Code: `ANON = "anon|"`

> What `target_identity` returns when it cannot name the control at all.
>
> It is the ABSENCE of a name, not a different name, and two shapes that differ
> only there are not two jobs. See `_shared`.

## `target_identity`, [line 19](../../../../../../../backend/src/sro/domain/observation/identity.py#L19): Docstring

> What to call the control this gesture touched, stably across occurrences.

## `screen_of`, [line 41](../../../../../../../backend/src/sro/domain/observation/identity.py#L41): Docstring

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

## `shape_key`, [line 51](../../../../../../../backend/src/sro/domain/observation/identity.py#L51): Docstring

> The job's shape: which control, on which screen, touched how -- in order.

## `named_alike`, [line 72](../../../../../../../backend/src/sro/domain/observation/identity.py#L72): Docstring

> Whether these two names could be the same job's.
>
> Generous on purpose, because it is a veto: a name this cannot read -- an
> empty one, a job proposed with no title -- is not evidence of difference,
> so it does not block anything.

## `containment`, [line 79](../../../../../../../backend/src/sro/domain/observation/identity.py#L79): Docstring

> |a ∩ b| / min(|a|, |b|).
>
> Containment rather than Jaccard, because a three-step "create supplier" sits
> INSIDE a twelve-step "create supplier, add item, set status in SAP". Jaccard
> drowns the small set in the union and calls them different jobs; containment
> says the smaller is part of the larger, which is true and is the variant
> relation worth surfacing.

## `jaccard`, [line 85](../../../../../../../backend/src/sro/domain/observation/identity.py#L85): Docstring

> |a ∩ b| / |a ∪ b|. For the occurrence question, where the two sets are
> the same size by construction.

## `_shared`, [line 122](../../../../../../../backend/src/sro/domain/observation/identity.py#L122): Docstring (debt)

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
> Either way round (2026-09-23): the stored job may be the unnamed reading and
> the new doing the named one. Only the proposal's unnamed entries used to be
> aliased, so the same pair of recordings folded or split depending on which
> one happened to be mined first.
>
> ponytail: `anon` is the only aliasing here. Two recordings that both name a
> control and disagree -- `viewport toolbar` against `toolbar button`, the
> third duplicate of that day -- stay apart, because a rule that called those
> the same would call every click on a system the same. The upgrade is
> `skill.learned.same_control`'s alias set, which needs the names carried on
> the shape and is a migration, not an edit.

## `resolve`, [line 145](../../../../../../../backend/src/sro/domain/observation/identity.py#L145): Docstring

> Which of the known workflows, if any, this proposal already is.
>
> `signs_in_to` maps a workflow id to the system it signs in to, for the jobs
> (and the proposal) that sign in; see the note at `here`.
>
> No guard for an empty shape or an uncited proposal: containment and jaccard
> both return 0.0 for an empty set, no threshold here is at or below zero, and
> a proposal that matches nothing falls out of the bottom as "new" anyway.

## `target_identity`, [line 22](../../../../../../../backend/src/sro/domain/observation/identity.py#L22): Comment

Code: `return f"anon|{gesture.action.kind}"`

> A scroll has no target -- you scroll a page, not an element.

## `target_identity`, [line 30](../../../../../../../backend/src/sro/domain/observation/identity.py#L30): Comment

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

## `target_identity`, [line 38](../../../../../../../backend/src/sro/domain/observation/identity.py#L38): Comment

Code: `return f"anon|{gesture.action.kind}"`

> Honest rather than precise. "A click on mail.google.com we cannot name"
> is what actually happened, and the rest of the shape is what tells this
> job from another.

## module, [line 91](../../../../../../../backend/src/sro/domain/observation/identity.py#L91): Comment

Code: `K_SAME_EVIDENCE = 0.5`

> A11 — identity, and it is arithmetic.
>
> Two questions that look like one. Cited gesture ids are per-occurrence, so two
> independent doings of the same job cite disjoint sets and their overlap is
> always zero -- ids can only tell you whether this is a re-read of a window
> already processed. Whether it is the SAME JOB seen on different evidence needs a
> key derived from the evidence, compared by containment.
>
> The model's own opinion (`same_as`, removed in M1) decided neither. A model
> asked to re-judge its earlier verdict disagrees with itself at roughly 90%,
> and `same_as` asked precisely that.

## module, [line 93](../../../../../../../backend/src/sro/domain/observation/identity.py#L93): Comment

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
>
> That case is now the sign-in fold's (see `resolve`), and the bar is held
> at two for every shape: letting a one-entry shape clear it on "all of it
> matched" folded unrelated doings at 1.0 (2026-09-23 review).

## `Resolution`, [line 98](../../../../../../../backend/src/sro/domain/observation/identity.py#L98): Inline

Code: `kind: str`

> "new" | "same_occurrence" | "same_job"

## `Resolution`, [line 102](../../../../../../../backend/src/sro/domain/observation/identity.py#L102): Comment

Code: `contains: bool = False`

> True when the stored job's steps appear, in time order, inside this
> proposal's, and the proposal has more -- see `_in_order`. Read by the mining
> pass's `_grow`, which replaces the stored steps with the proposal's only then.
>
> Three states exist and this collapses two: "theirs contains mine" and
> "neither contains the other" are both False, and both mean "do not grow".
> That is the only question the one reader asks.

## `_shared`, [line 127](../../../../../../../backend/src/sro/domain/observation/identity.py#L127): Comment

Code: `for one in left:`

> Sorted on both sides so a shape matching several candidates matches the
> same one every time, and each entry on the other side is consumed once, so
> two unnamed steps cannot claim one named step. Two unnamed entries of one
> system and kind are one entry by the time a set has been made of them.

## `_alike`, [line 112](../../../../../../../backend/src/sro/domain/observation/identity.py#L112): Docstring

> The same step: equal, or one of the two unnamed on the same screen, done the
> same way. See `_shared`.

## `_in_order`, [line 135](../../../../../../../backend/src/sro/domain/observation/identity.py#L135): Docstring

> Whether the doing holds every stored step in the order the job does them,
> with more besides -- which is what `contains` means and what `_grow` may
> act on.
>
> It used to be "the doing's shape is bigger", which is true of a doing that
> did the job's steps in another order, or did a different job sharing most
> of its controls, and `_grow` replaced the stored steps with it either way.
> Greedy, earliest match first, which is exact for a subsequence test.

## `resolve`, [line 151](../../../../../../../backend/src/sro/domain/observation/identity.py#L151): Comment

Code: `peers = [other for other in known if other.tenant == proposal.tenant]`

> tenant is the one other field of Workflow that can make two rows
> unmergeable however alike they look. known_workflows() scopes its query by
> tenant; resolve() takes whatever list it is handed, and welding one
> tenant's job onto another's is not a mistake anyone can undo afterwards.

## `resolve`, [line 162](../../../../../../../backend/src/sro/domain/observation/identity.py#L162): Comment

Code: `return Resolution("same_occurrence", seen.id, seen_score)`

> The overlap as measured, not a flat 1.0: three citations of four is
> the same occurrence and is not identity, and a constant is a number
> no caller can ever threshold on a second time.

## `resolve`, [line 164](../../../../../../../backend/src/sro/domain/observation/identity.py#L164): Comment

Code: `here = lands.get(proposal.id) if proposal.signs_in else None`

> Two jobs that both sign in (`Workflow.signs_in`) to the same application
> through the same identity provider are one job, whatever path each took to
> the password box -- an identity chooser first, a refused attempt, another
> login screen of the same provider. Their shapes share almost nothing and
> their names were made up separately, so neither can say so. The key is
> `checks.signs_in_to`, (credential host, the host the operator went on to),
> computed by the caller because it needs the gestures.
>
> Of several stored copies of one sign-in, the one the doing most resembles
> wins, not the oldest. And two sign-ins whose keys are both known and differ
> are never folded by their shape either: identical password pages in front
> of two applications look the same and are not.

## `resolve`, [line 184](../../../../../../../backend/src/sro/domain/observation/identity.py#L184): Comment

Code: `matched = _shared(shape, theirs)`

> Containment over the SAME notion of a shared step the bar below uses.
> Two gates that disagree about what counts as shared is one gate: with
> `containment`'s raw set intersection here, a proposal whose unnamed
> step aliases a named one scored as though it had not, and `Reply to
> Email` cleared K_SAME_JOB at exactly 0.5 by arithmetic coincidence.

## `resolve`, [line 186](../../../../../../../backend/src/sro/domain/observation/identity.py#L186): Comment

Code: `whole = matched >= K_MIN_SHARED_STEPS`

> Both bars first, then the best of whatever clears them -- not the best
> overall and then the bars. Two shared distinct steps, whichever side is the
> smaller, and nothing less.
>
> Two escape hatches were tried and both removed (2026-09-23 review). "Every
> step the STORED job has" folded -- and grew -- any bigger doing into a
> one-entry job: an unnamed click on the warehouse is present in every doing
> that clicks the warehouse. "Every step the PROPOSAL has" folded a doing
> that pressed one control twice into any bigger job touching that control,
> at 1.0 -- and since a folded doing is now placed, its gestures were filed
> under the wrong job for good. `validate` counts steps, not distinct shape
> entries, so two steps on one control reach here as a one-entry shape.
>
> What those hatches were for -- the 2026-09-19 `Log in to Keycloak` typed
> into one box twice -- is a sign-in, and the sign-in fold above recognises
> it by what it signs in to. A one-entry doing that is not a sign-in resolves
> new; what it cites is one entry wide either way.
>
> Ranked by how many steps are shared, then by containment, so a one-entry
> stub 1.0-contained by the proposal cannot beat the real match behind it.

## `resolve`, [line 187](../../../../../../../backend/src/sro/domain/observation/identity.py#L187): Comment

Code: `if (`

> And the name, which can only keep them apart. Two jobs on one screen
> whose shapes are equally generic -- a mailbox's `Reply`, `Forward`
> and `Send` -- have nothing else left to be told apart by. See
> `K_SAME_NAME`.

## `resolve`, [line 210](../../../../../../../backend/src/sro/domain/observation/identity.py#L210): Comment

Code: `named = _as_words(proposal.title)`

> Extend, never mint (M1 round 1). The shape rules above could only say
> `new` for wfl_88bc: two mail clicks and a Save from a later doing, one step
> shared with wfl_4857, which is under the bar. It carried the job's own
> title. A proposal whose title, with punctuation and stop words gone, is a
> stored job's title is a doing of that job. The model names jobs from the
> "Jobs already proven" list, so an equal title is its recognition, and
> two live jobs under one title are what the operator could never pick
> between ("Did you mean X or X?").
>
> After the shape rules, so a shape match still wins, and after the
> sign-in filter, so two sign-ins that land in different places are not
> joined by a title.

## `resolve`, [line 216](../../../../../../../backend/src/sro/domain/observation/identity.py#L216): Comment

Code: `if not proposal.parameters:`

> A proposal with nothing that varies, sharing even one step with a stored
> job, and resolving to nothing else, is a fragment of that job, never a
> new one. The keep path refuses it by name. A proposal WITH parameters that
> shares one step stays new: the absolute bar above exists for real jobs
> that share a lookup or a Save.
>
> The review also asked that "steps covered by a stored job" resolve to that
> job. That is already the shape rule when two or more steps are shared and
> the names are alike. Below that, two measured cases forbid it:
> `test_a_doing_of_one_distinct_step_does_not_fold_into_a_bigger_job` and
> `test_forwarding_is_not_replying_however_alike_the_clicks_are`. So a
> covered proposal that fails those guards is refused as a fragment if it
> has no parameters, and is otherwise new.

## `resolve`, [line 201](../../../../../../../backend/src/sro/domain/observation/identity.py#L201): Comment

Code: `if sum(1 for entry in shape if not entry[1].startswith(ANON)) >= K_MIN_SHARED_STEPS:`

> Steps a stored job already holds, every one of them exactly (as a set,
> no `anon|` alias), and at least K_MIN_SHARED_STEPS of them: that job,
> whatever the title (M1 round 3). A proposal that is wholly a part of a job
> is that job; the name veto exists to keep apart jobs that merely look
> alike. Exact, because the alias is what made Forward look like Reply. At
> least two distinct entries, because one entry is any doing that touches
> that control (see the bar above). A proposal with a step of its own --
> an Edit that presses Edit on the create form -- is not wholly the create,
> so this rule leaves it to the shape rule above, where its name decides.
>
> Round 4 tightened it twice.
> - Only NAMED entries count toward K_MIN_SHARED_STEPS, though every entry
>   must still be contained: `anon|click` equals `anon|click` and names
>   nothing. Reply and Forward, both read as `[anon|click, Send]`, stay
>   apart.
> - The proposal must be at least half (K_SAME_JOB) of the job's distinct
>   steps, so a short job inside a longer, different one ("Log Out" inside a
>   six-step password change) stays new. Of the jobs that qualify, the one
>   it is most of wins. A tie in share is a tie in size (the proposal is
>   the same set), so "then the most steps" needs no key of its own.
>
> Known limit: under a name alike at K_SAME_NAME ("Edit a Customer Type"
> against "Create a Customer Type", 2 words of 4), the shape rule above
> still joins an Edit sharing two steps and half the form. Telling them
> apart by the verb is an identity decision of its own, not made here.

## `resolve`, [line 210](../../../../../../../backend/src/sro/domain/observation/identity.py#L210): Comment

Code: `named = _as_words(proposal.title)`

> Equal title, and at least one shared step (M1 round 3): the title is the
> model's recognition, the shared step is the evidence that it is the same
> screen. A mailbox "Log out" and the warehouse's "Log Out" share a title
> and not a step, and stay two jobs.
