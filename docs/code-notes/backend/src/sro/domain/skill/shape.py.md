# Notes for `backend/src/sro/domain/skill/shape.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/shape.py`](../../../../../../../backend/src/sro/domain/skill/shape.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/shape.py#L1): Docstring

> What the extension matches a live tail against.
>
> One entry per proven workflow: its shape -- (system, control identity, kind)
> per cited gesture in step order, scrolls left out, the same key `identity.py`
> resolves on -- and where in that shape each declared parameter was typed.
> Computed from the cited gestures rather than read from `workflow.shape_key`, so
> the parameter indices are indices into the very list the extension will walk.
>
> Nothing here carries a typed value. A shape is control identities, hosts and
> parameter *names*; the values that went into those controls stay in the
> gestures, which is the only place they were ever allowed.
>
> The queries that gather the evidence -- the proven workflows, the held tally,
> the cited gestures and this job's own offers -- live in the application layer.
> What is left here is the arithmetic: given the pairs and the counsel, the shape.

## `Shape`, [line 26](../../../../../../../backend/src/sro/domain/skill/shape.py#L26): Note on the line above

Code: `writes: list[dict[str, str]] = field(default_factory=list)`

> What pressing this job would write, in step order. Empty where the
> evidence shows no mutation -- and empty is said as nothing rather than as
> "it writes nothing", because a job whose gestures have aged out and a job
> that only reads look the same from here.

## `Shape`, [line 30](../../../../../../../backend/src/sro/domain/skill/shape.py#L30): Note on the line above

Code: `quiet_until: str | None = None`

> Set when the asking browser refused this job three times running: the
> shape is still served -- the list stays whole and cacheable, and an open
> offer on the job can still tell diverging from finishing -- and
> `recognise.js` declines to offer it until then.

## `_all_in_a_mailbox`, [line 36](../../../../../../../backend/src/sro/domain/skill/shape.py#L36): Docstring

> Whether every gesture of this job happened in a mailbox.
>
> Every one, not any: a job that reads a request and then does it in the
> warehouse is the shape this whole system is for, and it cites gestures on
> both. `K_MAILBOXES` is the same named list `asked_by` reads requests out
> of, for its own reason -- "any host that is not the warehouse" would call a
> second warehouse system a mailbox.

## `in_time_order`, [line 43](../../../../../../../backend/src/sro/domain/skill/shape.py#L43): Docstring

> The cited gestures in the order they happened.
>
> **Not step order, and this is the difference between a shape that matches
> and one that cannot.** A shape key is a SEQUENCE of `(system, control,
> kind)`, and `recognise.js` asks whether the operator's last *k* gestures
> ARE this shape's first *k* -- against a tail the browser appends to as
> gestures arrive, which is time order and nothing else. A shape written in
> step order is written in the order the MODEL narrated the job, and a model
> narrates sensibly: "read the request, then create the record". Tenant
> `new`'s `Create a Warehouse Equipment Type` was really done the other way
> round -- the operator opened the WMS form at 16:18:35 and read the mail at
> 16:18:46 -- so its step order and its time order disagree, and only one of
> them is what a browser will ever send.
>
> Measured on both corpora through the real matcher, with the replay fixed to
> feed gestures in time order as a browser does: a step-ordered shape offers
> **3 of acme's 7 jobs and 0 of `new`'s 2**. The same shapes rebuilt in time
> order offer **6 of 7 and 1 of 2**. The missing measurement was in the
> harness -- `dry_run._gestures_of` replayed each job's gestures in step
> order, the same order the shape was built from, so the matcher was being
> handed its own answer.

## `_when`, [line 47](../../../../../../../backend/src/sro/domain/skill/shape.py#L47): Docstring

> Time, then id. `at` is the browser's clock and two gestures of one burst
> can share it, so `at` alone is not a total order -- and a shape that
> permutes between two builds is a shape that stops matching itself.

## `cited_pairs`, [line 51](../../../../../../../backend/src/sro/domain/skill/shape.py#L51): Docstring

> The cited gestures in the order they happened, each still paired with
> the step that cited it. The pairing is what `typed_at` needs and what a
> flat list of gestures throws away.
>
> Time order and not step order, for the reason `in_time_order` gives: the
> served shape is built from this list, and the tail it is matched against is
> a browser's, which has never heard of a step. `typed_at` reads its index
> out of the same list, so the parameter's position in the shape moves with
> it rather than pointing at whatever now sits where it used to.

## `put_by`, [line 63](../../../../../../../backend/src/sro/domain/skill/shape.py#L63): Docstring

> What this gesture put into the form, as strings a seen value can match.
>
> Typing carries it in `action.value`. A pick from a dropdown does not. The
> WMS's combo is an ExtJS one: the operator clicks the field, a floating list
> appears, and they click a row of it -- two clicks, neither with a value,
> and what they chose is the clicked row's TEXT. So ten of the forty declared
> parameters across both real stores had no shape index, every one of them a
> dropdown, and an offer could not lift `External System Name` off a live
> tail even where the operator had just picked it.
>
> Matching the text against the parameter's own `seen_values` is what keeps
> this honest: every click has a label, and "Save" is not a value anybody
> declared. A credential contributes nothing, the rule `typed_values` and the
> tail already wear.

## `typed_at`, [line 75](../../../../../../../backend/src/sro/domain/skill/shape.py#L75): Docstring

> Where in the shape this parameter was typed, by the step that declares it.
>
> Scanning every cited gesture for the first value match binds the wrong
> control on any search-then-create flow: the code is typed into the search
> box before it is typed into the field the workflow is actually filling, so
> the extension would fill the search box and stop. Only the step whose
> `parameters` names this one is asked.

## `walkable`, [line 88](../../../../../../../backend/src/sro/domain/skill/shape.py#L88): Docstring

> The cited pairs the extension can actually match on.
>
> A scroll is not one: `recognise.js` drops one before it is ever written
> into the tail, so a served shape carrying one could not be matched at any k
> -- a job whose first triple is a scroll could never be offered at all.
> Dropped before both the shape and the parameter indices are computed, so
> `at` indexes the very list the extension walks.

## `resumes_at`, [line 92](../../../../../../../backend/src/sro/domain/skill/shape.py#L92): Docstring

> Which step a browser that matched `matched` shape entries is in.
>
> A shape entry is one GESTURE, not one step: `shape_of` walks the cited
> pairs, and a step of four gestures is four entries. `recognise.match`
> answers with how many entries the operator's tail matched, and the run
> start wants how many STEPS they finished -- two different numbers that were
> the same field. On this deployment's own job they are 19 and 6.
>
> So the answer is the step the LAST matched entry belongs to, and a run
> resumes there rather than after it. That is deliberately the conservative
> end: a step marked done that was only half done is never sent and nothing
> notices, while a step performed again that the operator had finished is
> caught -- `already_done` asks the warehouse whether the record is there
> before any live write goes out. Skipping is what nothing catches.
>
> Zero for a tail that matched nothing, which is a run from the top.

## `shape_of`, [line 102](../../../../../../../backend/src/sro/domain/skill/shape.py#L102): Docstring

> One workflow as the extension needs it, or None when it cannot be
> served: nothing cited, a start its own evidence never names, or too short a
> walk to ever be offered.

## `where_steps_moved`, [line 138](../../../../../../../backend/src/sro/domain/skill/shape.py#L138): Docstring

> Which `ord` each of a job's steps has after the job grew.
>
> A stored job's steps never grew, and that is half of why a field two
> doings varied could not become a parameter: `parameters_across` compares
> the stored job against the proposal, and the stored job is one doing that
> never reached the control. Measured on the deployment 2026-09-21 --
> `Department` and `Manufacturer` typed in two doings, varied in both, and
> the job went on holding two parameters.
>
> So a doing that WHOLLY CONTAINS the stored job replaces its steps. This is
> what `Resolution.contains` was computed for and never read, and its own
> note names this caller: *"Mine contains theirs" is the case for replacing*.
>
> **What is keyed to a step's number has to move with it.** The locator a
> run last found (`workflow_learned`), the mark that a step is about to
> break (`workflow_stale`) and what a job taught itself
> (`workflow_learned_history`) are all keyed `(workflow_id, ord)`, and a
> step that becomes step 5 takes its learning with it or the learning now
> describes somebody else's step. What is NOT moved is a past run's own
> record: `workflow_run_steps` and `workflow_effects` are a log of what
> happened when the job had the shape it had then, and `proofs` compares
> those two with each other and never with the job -- which is why growing a
> job cannot cost it the autonomy it earned.
>
> Matched on what the steps DID, not on what the model called them: the
> prose is written freshly every mining and a step index is its opinion. Two
> steps are the same step when their cited gestures have the same shape, in
> time order, which is the same identity `shape_key` is built from.
>
> A step of the old job that the new one does not have is absent from the
> mapping, and its learning is dropped: the step is gone, and a locator for
> a step nobody performs is a locator nobody can check.

## `_did`, [line 152](../../../../../../../backend/src/sro/domain/skill/shape.py#L152): Docstring

> What one step did, as the shape key says it: which control, on which
> screen, touched how -- in the order it happened.

## `in_time_order`, [line 44](../../../../../../../backend/src/sro/domain/skill/shape.py#L44): Comment

Code: `return sorted((by_id[cited] for cited in ordered_cites(workflow) if cited in by_id), key=_when)`

> `ordered_cites` and not `cited_ids`: the second is a SET, and a gesture
> two steps both stand on is two rungs of the key -- dropping the duplicate
> shortens the shape by one and it stops matching its own job.

## `typed_at`, [line 82](../../../../../../../backend/src/sro/domain/skill/shape.py#L82): Comment

Code: `for index, (gesture, _) in enumerate(cited):`

> A parameter learned across doings (`parameters_across`) is recorded on
> the workflow and on no step: it is named after the control it was typed
> into, so the control with that name, typing one of its values, is where
> it sits. Narrower than a value scan -- the search box is not named
> `workArea` -- and without it every learned parameter had no index and
> no offer could lift its value from a tail.

## `resumes_at`, [line 98](../../../../../../../backend/src/sro/domain/skill/shape.py#L98): Comment

Code: `_, step = walk[min(matched, len(walk)) - 1]`

> Clamped rather than trusted. `match` scans k down from `len(shape) - 1`
> so it cannot overrun, but this is a number off the wire and the cost of
> believing a bad one is an IndexError in the middle of a press.

## `shape_of`, [line 106](../../../../../../../backend/src/sro/domain/skill/shape.py#L106): Comment

Code: `return None`

> A mailbox is where work is ASKED FOR, not work to repeat.
>
> An operator lives in their mail all day, so the miner mines what they
> do there: this deployment holds four `Compose Email`, two `Reply to
> Email` and two `Forward an Email`, none of them ever run but one. The
> matcher then offers one whenever the last two gestures look like its
> first two -- which, in a mailbox, is most of the time. Measured
> 2026-09-19: an operator working through six requests was offered
> `Forward an Email` on nearly every screen, and the one card that
> mattered sat under it.
>
> Worse than noise: the mail reader hesitated between `Create a
> Customer Type` and `Forward an Email` for a mail that plainly asked
> for the first, and said nothing at all rather than choose.
>
> This does not unmine them or hide them from the console -- they are
> still evidence, still readable, and `signing_in` still finds a mail
> sign-in job by the host it stands on. It stops them being OFFERED,
> which is the only place they cost anybody anything.

## `shape_of`, [line 113](../../../../../../../backend/src/sro/domain/skill/shape.py#L113): Comment

Code: `starts_on = page_of(first.page_url or first.url)`

> The screen, not the visit. What was served here was the whole url of the
> first gesture of ONE demonstration, so `Create a Customer Type` carried
> the message id of the mail that operator happened to read, and a WMS job
> would carry a `libraryContext` session token -- to every browser in the
> tenant that asks for shapes.
>
> Nothing loses anything. Every consumer of this field reduces it to host
> and path before comparing: `nudge.page` on the way in, `rigArrivals` on
> what that produced, and `nudge.js` says so in its own docstring -- "the
> same shape the miner records `starts_on` in", which was not true until
> now. What NAVIGATES is a different `starts_on` computed in
> `run_workflow`, and that one still carries the whole url because a
> warehouse addresses its screens by fragment.

## `shape_of`, [line 114](../../../../../../../backend/src/sro/domain/skill/shape.py#L114): Comment

Code: `hosts = sorted(stood_on(workflow, by_id))`

> Where the operator stood, not everywhere their pages called. `hosts`
> says which systems this job is done on, and a Gmail page's telemetry
> beacon is not one of them -- it put `https://play.google.com` on a
> warehouse job's shape, served to every browser in the tenant.

## `shape_of`, [line 115](../../../../../../../backend/src/sro/domain/skill/shape.py#L115): Comment

Code: `if system_of(starts_on) not in hosts:`

> `starts_on` is the tab's origin; `hosts` is what the evidence names,
> which is the frame's. When they disagree the extension would be sent
> to open an origin no cited gesture ever proved -- so it is not sent.

## `shape_of`, [line 117](../../../../../../../backend/src/sro/domain/skill/shape.py#L117): Comment

Code: `walk = walkable(cited)`

> `starts_on` and `hosts` are read off the whole of the evidence above:
> where the job begins is a fact about the recording, not about what can
> be matched.

## `shape_of`, [line 118](../../../../../../../backend/src/sro/domain/skill/shape.py#L118): Comment

Code: `if len(walk) <= K_OFFER_AFTER:`

> `recognise.js` offers on `shape.slice(0, k)`, and it scans k DOWN FROM
> `shape.length - 1`: an offer has to leave something to finish, so the
> whole of a shape is never a prefix anybody is offered. With k at least
> `K_OFFER_AFTER`, that makes a walk of exactly `K_OFFER_AFTER` positions
> unmatchable at any k -- served, cached and walked by every browser on
> every gesture, and unable to fire.
>
> This read `< K_OFFER_AFTER` and was off by one against the matcher, which
> nothing could have caught from this side: the offer replay only ever fed
> it real mined jobs, all longer. Found by watching a browser do a two-step
> job over and over with the panel open and nothing ever appearing, and
> confirmed against `match`'s own loop bound.
>
> acme holds shorter rows still: a one-step `Create a Customer Type`, no
> parameters, whose whole content is "Save the customer type
> configuration". `validate` refuses to mine such a workflow now, for the
> neighbouring reason that `resolve` needs `K_MIN_SHARED_STEPS` to dedupe
> one, but the rows mined before that check are still in the store and
> there is no way to retire one.
>
> `offer_after` below caps at `len(walk) - 1` for the same reason, and that
> cap is what gives this line its exact form: a shape whose floor exceeds
> its own cap is one the matcher can never reach.

## `shape_of`, [line 133](../../../../../../../backend/src/sro/domain/skill/shape.py#L133): Comment

Code: `offer_after=max(K_OFFER_AFTER, min(advice.offer_after, len(walk) - 1)),`

> What this job's own offers say: resting on this browser, or offered
> later. Capped at the last gesture but one, which is as late as
> `recognise.js` can offer: a job that diverges even there keeps
> diverging, on record.

## `where_steps_moved`, [line 148](../../../../../../../backend/src/sro/domain/skill/shape.py#L148): Comment

Code: `moved[step.order] = same.pop(0)`

> First unclaimed, so a job that does one thing twice keeps both
> rather than folding two steps onto one.
