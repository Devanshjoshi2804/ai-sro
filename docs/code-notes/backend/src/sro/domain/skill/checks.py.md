# Notes for `backend/src/sro/domain/skill/checks.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/checks.py`](../../../../../../../backend/src/sro/domain/skill/checks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/checks.py#L1): Docstring

> A9, A10 — the only code here that overrules a model.
>
> `validate` reads no URL, no body and no call shape. It asks whether a workflow
> has any steps at all, whether every step cites something, whether everything
> cited exists, whether every step says something a person could act on, and
> whether every system named -- by a step or by the workflow -- is one the cited
> evidence actually happened on. Then `coverage` measures where in the window the
> citations fell, because long-context citation bias is real, is model-specific,
> and is invisible without counting.
>
> `work_only` is the one that does read URLs, and it answers a different
> question: not "is this workflow honest about its evidence" but "is this
> evidence a job anybody wanted mined". See its docstring.
>
> Ported from `new_agent_arch/src/rig/checks.py`. Pure -- it reads `Window`,
> `Workflow` and `Gesture` and nothing else, and is told what this deployment is
> rather than reading settings -- so it lives in the domain beside them rather
> than in the application layer with the mining pass that calls it.

## module, [line 17](../../../../../../../backend/src/sro/domain/skill/checks.py#L17): Note on the line above

Code: `_DEFAULT_PORTS = {"http": "80", "https": "443"}`

> `config._origins_of` keeps the same map for the same reason and cannot be
> imported here: the domain reads settings through arguments or not at all.

## module, [line 479](../../../../../../../backend/src/sro/domain/skill/checks.py#L479): Note on the line above

Code: `K_SITTING_GAP_S = 600.0`

> How long a pause has to be before the work after it is a different doing.
>
> **Tied to the recogniser, not chosen here.**
> `new-chrome-extension/src/background/recognise.js` keeps `K_TAIL_TTL_S = 600`:
> a gesture older than ten minutes has fallen out of the browser's tail before
> the next one arrives, so two cited gestures further apart than that can never
> sit in one tail together and no shape spanning the pause can ever be matched.
> Keeping such a pair in one job is keeping a job the operator will never be
> offered.
>
> The bound applies in TIME order, which is the order the tail arrives in and
> the order `shape.in_time_order` now builds the shape from. That correction is
> what makes ten minutes safe: tenant `new`'s `Create a Warehouse Equipment
> Type` looks like it has a 22-minute gap between its step 2 and its step 3, and
> a bound read off STEP order would split it and lose a step. In time order that
> job has no 22-minute gap at all -- it has one stray leading gesture from an
> earlier doing at 15:56 and an unbroken run from 16:18:35. At 600s the stray is
> struck, all seven steps survive, and the opening gap goes from 22 minutes to
> zero.
>
> Measured over both corpora's nine stored jobs, narrowing at 600s: five jobs
> untouched, `new`'s Warehouse Equipment Type 12 cites to 11 with no step lost,
> `Create an Activity Code` 30 to 27 with its opening gap falling from 26
> minutes to 233 seconds -- under the tail's lifetime, and offerable for the
> first time. `Create a Work Operation` loses evidence on 3 of its 11 steps and
> is then refused by `validate` for an uncited step, which is the honest answer:
> those 11 steps were never one doing.

## `validate`, [line 34](../../../../../../../backend/src/sro/domain/skill/checks.py#L34): Docstring

> None when the workflow may be kept, a Rejection when it may not.
>
> `evidence` maps a gesture id in the window to the system it happened on --
> `Gesture.system`, which is scheme and host. A missing or empty value means
> the system could not be established for that gesture.
>
> A mapping rather than a set of ids because the system checks below are the
> reason this module exists. Taking `step.system` as the evidence for
> `step.system` compared the model against itself: it caught an answer that
> contradicted its own step list and could not catch one that was internally
> tidy and wholly invented -- which, in an architecture built to find jobs
> spanning two systems, is the one lie it must not accept.

## `_gini`, [line 89](../../../../../../../backend/src/sro/domain/skill/checks.py#L89): Docstring

> How unequally the citations are spread. Only ever called with a full
> decile list that sums to 1, so it needs no empty case.

## `coverage`, [line 97](../../../../../../../backend/src/sro/domain/skill/checks.py#L97): Docstring

> Which parts of the window were cited at all, and where they clustered.

## `_signed_in_here`, [line 122](../../../../../../../backend/src/sro/domain/skill/checks.py#L122): Docstring

> Whether this gesture put a credential into the page.
>
> The recorder marks the password itself rather than the page around it, so
> this is the one fact about signing in that needs no list of hostnames --
> and a list is exactly what `work_only` below declined to keep, on the
> grounds that every customer runs an SSO nobody here has heard of.

## `_did_business`, [line 127](../../../../../../../backend/src/sro/domain/skill/checks.py#L127): Docstring

> Whether this gesture wrote something to the system it happened on.
>
> A sign-in posts credentials to its identity provider, so "wrote something"
> on its own would call an identity host a working one. Same-origin is what
> separates them: signing in sends you somewhere else, and doing the job
> writes back to the page you are on.

## `undeliverable`, [line 138](../../../../../../../backend/src/sro/domain/skill/checks.py#L138): Docstring

> The declared parameters no step of this job could ever be given.
>
> `planning.value_for` is the one place a run's value reaches a control, and
> it looks the value up by four names in order: the component's `item_id`,
> its `field_label`, the target's `name`, and whatever the step itself listed
> in `parameters`. A workflow parameter whose name is none of those, on any
> step, is a name nothing will ever ask for.
>
> That is not a harmless spare field. `StartWorkflowRun` refuses a press that
> leaves a declared parameter empty, so the operator is made to type a value
> -- and then `value_for` never finds the name, falls through, and performs
> the step with the value the RECORDING happened to contain. The job runs,
> reports success, and did something other than what was asked. A parameter
> that cannot be delivered is worse than no parameter, because no parameter
> at least tells the truth.
>
> Found by reading what the miner actually produced. Three clean mines of one
> real day declared six parameters between them, and **three of the six named
> controls that do not exist in the evidence** -- `Description` where the
> label reads `Customer Type Description`, `Equipment Type` for `Warehouse
> Equipment Type`, `LPN Limit` for `LPN Warehouse Equipment Type Limit`.
> Those three bound anyway, but only because the model had written the same
> invented string into `step.parameters` as well, which `value_for` checks
> last. Nothing anywhere required those two halves of one model answer to
> agree.

## `_during`, [line 165](../../../../../../../backend/src/sro/domain/skill/checks.py#L165): Docstring

> Every gesture of this job's own streams inside its own time span.
>
> A superset of what it cites, and the difference is the point: a citation
> list is a model's summary of a job, not its boundary, and a rule about what
> the operator did has to read the doing rather than the summary.
>
> Bounded by the cited gestures at both ends and by their streams, so this
> never reaches into another tab or into the next job along. A job that cites
> nothing gets nothing, which is `validate`'s problem and not this one.

## `signs_in`, [line 178](../../../../../../../backend/src/sro/domain/skill/checks.py#L178): Docstring

> Whether this job signs in: a credential typed and nothing written back.
>
> Decided once, by the mining pass, and kept on the job as
> `Workflow.signs_in`, because a run cannot decide it: a run has the job's
> cited evidence and nothing else, and it used to guess from every cited
> gesture sitting on one origin -- which is also every ordinary job done on
> one warehouse host. The session broker a server-side browser needs will ask
> the same question, and the answer has to be a fact about the job.
>
> Two of `work_only`'s three halves, and no hostnames: the recorder's secret
> mark (`_signed_in_here`) and `_did_business`. And two more. Every step
> `writes` -- any mutating method at any status -- must be a step
> `is_sign_in_step` proves is part of the sign-in, so the mark agrees with the
> run engine's idea of a write. And the sign-in CHAIN must hold nothing but
> signing in: see `_only_signs_in`. A job with a same-host act in its chain is
> never marked: a PIN approval or an e-signature looks exactly like a sign-in
> until then, and the mark makes a job eligible to end a run `held` and to be
> spliced into another. Step by step the engine still gates such a press; the
> mark is about the whole job.
>
> The chain replaced "every act after the first credential, anywhere in the
> job, left the host", which could not recognise the deployment's own
> `Log in using Azure B2C SSO` (2026-09-23 export, `wfl_5873ec01`): focus
> clicks and an Enter on the password box counted as acts, a refused first
> Sign In sat in the evidence, and the model cited a click in the warehouse
> after landing inside the sign-in step. Each of those is now read for what it
> is, and none of them can make a same-host submit exempt.
>
> `work_only` keeps its own reading of the same halves and does not call this:
> its refusal is "a credential typed, the browser moved, nothing written", and
> tying it to this stricter mark would let a sign-in with a same-host press
> through the miner as a job. The third half -- the browser
> moved the operator -- is what makes a sign-in not a job worth mining, and
> is not what makes it a sign-in.
>
> Asked of what the operator DID during this job, not of what the model
> chose to cite about it -- and that distinction is the whole of whether
> this rule fires at all. Shipped against `cited`, it could not fire on the
> evidence it was written from: a clean re-mine of that same day proposed
> `Log in to Warehouse Management System`, and this let it straight
> through. The password gesture was in the store the whole time
> (`action.secret` true, on the keycloak host) and the model had not cited
> it -- reasonably, because redaction strips a credential gesture of its
> value AND its target name, leaving nothing worth pointing at. So the one
> gesture that proves a job is a sign-in is the one gesture a model
> summarising that job will leave out.
>
> `during` is the cited gestures' own time span on the streams they cite,
> which is the job as the operator lived it. Measured on that day: the
> sign-in job's span holds the credential, and the two real jobs' spans
> hold none -- including a Warehouse Equipment Type job whose span is 52
> gestures wide.

## `is_sign_in_step`, [line 392](../../../../../../../backend/src/sro/domain/skill/checks.py#L392): Docstring

> Whether this step's own evidence proves it is part of signing in, and so
> not a write. Three shapes, and nothing else:
>
> - everything the step cites comes before the job's first cited credential
>   typing, and it records no mutation: nobody is signed in yet, so nothing
>   pressed there writes for anybody -- the identity chooser, a username
>   focus click, an identifier-first Next (final review I-3, 2026-09-24). On
>   the deployed `Log in using Azure B2C SSO` (`wfl_5873ec01`) the chooser
>   and the username step record no traffic and never leave their host, and
>   were spared the write rules only by a list of identity-provider paths
>   that spared any press on such a path on any job. The list is gone; this
>   is the fact it stood in for. Cited, not the job's span: at run time the
>   loop holds the chain's own cites and nothing else. Tags are unchanged on
>   the QA export: `signs_in` asks this only of steps that record a write;
>   and none of it is on the host the sign-in lands on (`_lands_on`, the
>   `worked` half of `signs_in_to`), so a silent "Release wave" pressed in
>   the WMS just before a lapsed session was signed back into is never
>   spared (final re-review N-1). The landing is read off the doing after
>   the leave, not off the leaving submit's own page events: on the
>   deployment those end on the chooser's host (Keycloak redirects back
>   through Azure B2C), which would call the chooser the landing;
> - the step carries the credential (the recorder's secret mark), records no
>   mutation, and every gesture it cites that acts -- a click, a press, a
>   select that submits on change, an upload -- sent the browser to another
>   host: typing the password, alone or with the submit. "Records no
>   mutation" is absence of evidence: a top-level form post is never captured
>   (no Keycloak POST exists anywhere in the stored data), and the miner puts
>   a credential and a press in one step. A PIN typed and Approve pressed on
>   the same host is one such step, and it is a possible write;
> - the step carries the credential, or presses right after the step that
>   typed it on the same host, and the browser was sent to another host --
>   the submit.
>
> Either way nothing it did came back 2xx on its own host (`_did_business`),
> and every act in it left the host. A focus click on the password box is not
> an act. An Enter pressed in it is part of the submit only when this step
> also holds the gesture that left -- the deployment records the leave on the
> Sign In the Enter triggered, at the same instant; pressed on a PIN box that
> answers on the same system it is a submit like any other. A same-host press
> beside the leaving one -- a refused first attempt -- keeps the step a
> possible write: forgiving it here would forgive every same-host submit that
> happens to share a step with a redirect.
>
> And nothing it cites comes after the job's chain left the host
> (`_leaves_at`): a step that mixes the submit with work on the landed page is
> judged as that work. Measured: the Azure chain's last step cites the Sign In
> and a click in the warehouse twenty seconds later.
>
> A post that stayed on its page -- a supervisor PIN, an e-signature, answered
> 302 back to the same system or with no status recorded -- proves nothing,
> and a write must fail safe: it is judged as a write.

## `signs_in_to`, [line 272](../../../../../../../backend/src/sro/domain/skill/checks.py#L272): Docstring

> Which sign-in this is: the one host the credential was typed into, and the
> host the operator next worked on after the browser left it -- or None when
> either cannot be read.
>
> What "the same sign-in" means to `identity.resolve`. Not the chain's first
> host, an identity chooser one doing passes through and another skips. And
> not the identity provider alone: one provider in front of two applications
> is two sign-ins, and folding them left the second application with no way
> back in (review, 2026-09-23).
>
> Read off the doing, not the citations: the model summarises a sign-in as
> the typing (the deployment's `Log in to Keycloak` is two typed values), so
> the submit and what followed it are uncited. They are on the same tab,
> within one sitting of the job's last cited gesture. The landing is the
> first host the operator did anything on afterwards, because the submit's
> own page marks stop part-way down a redirect chain -- measured on the
> deployment's Azure chain, the Sign In's last mark is the identity chooser,
> and the warehouse only shows up on the click after it. The submit's last
> foreign mark stands in when nothing was done afterwards.

## `credentials_typed`, [line 310](../../../../../../../backend/src/sro/domain/skill/checks.py#L310): Docstring

> How many steps of this job type each credential field, keyed by the field's
> screen and identity. The mining pass's `_grow` refuses a doing that types a
> credential the job does not -- a password added to a job that had none, or
> a second, different one (a second factor) added to a job that had one.

## `_in_time`, [line 322](../../../../../../../backend/src/sro/domain/skill/checks.py#L322): Docstring

> What this job cites, once each, in the order the operator did it. The
> model's step order is not time order: the Azure chain cites its first
> password again in a later step.

## `_split`, [line 332](../../../../../../../backend/src/sro/domain/skill/checks.py#L332): Docstring

> The chain (see `_chain`), whether it left the host, and what the job cites
> after the leave.

## `_chain`, [line 327](../../../../../../../backend/src/sro/domain/skill/checks.py#L327): Docstring

> The sign-in chain: from the first credential gesture this job cites to the
> first gesture after it that sent the browser to another host, and whether
> it got there. What comes after that gesture happened on the landed page
> and is outside the chain.

## `_only_signs_in`, [line 345](../../../../../../../backend/src/sro/domain/skill/checks.py#L345): Docstring

> Whether the chain holds nothing but signing in.
>
> Typing is never an act and neither is a focus click on the password box.
> Everything else before the leaving gesture must be one of two things, and
> only when the chain did leave the host: an Enter pressed in the password
> box -- the submit, whose leave the recorder put on the button it
> triggered -- or a same-host press the credential was typed AGAIN after,
> which is a refused attempt. Without a leave there is no successful sign-in
> for either to belong to, and a same-host press is the PIN shape.

## `_lands_on`, [line 367](../../../../../../../backend/src/sro/domain/skill/checks.py#L367): Note

> The host a sign-in lands on: `signs_in_to`'s `worked` half, read off
> what the operator did after the credential left its host, falling back
> to the leaving submit's own page events. None when it never left.
> `_only_signs_in` refuses the tag to a job that pressed anything on that
> host before the credential (final re-review N-1, 2026-09-24): work done
> on the system before a lapsed session was signed back into is work.

## `_leaves_at`, [line 372](../../../../../../../backend/src/sro/domain/skill/checks.py#L372): Docstring

> When the chain left the host, or None when it never did.

## `_on_the_credential`, [line 377](../../../../../../../backend/src/sro/domain/skill/checks.py#L377): Docstring

> A click or a key press on the secret-marked input itself: the recorder's
> mark is on the box, not on a typed value.

## `_typed_the_credential`, [line 382](../../../../../../../backend/src/sro/domain/skill/checks.py#L382): Docstring

> A secret typed -- the only thing that can follow a refused attempt.

## `_acts`, [line 386](../../../../../../../backend/src/sro/domain/skill/checks.py#L386): Docstring

> Anything but typing a value. Typing changes a field; everything else --
> clicking, pressing, choosing, uploading -- can submit. Except a click on the
> password box, which focuses it: the deployment's operators click into the
> box before typing, and each of those clicks counted as a possible submit.

## `_carries_the_credential`, [line 422](../../../../../../../backend/src/sro/domain/skill/checks.py#L422): Docstring

> Whether any gesture this step cites bears the recorder's secret mark.

## `_after_the_credential`, [line 426](../../../../../../../backend/src/sro/domain/skill/checks.py#L426): Docstring

> Whether the step just before this one, in the job's order, typed the
> credential on the same host this step is on.

## `work_only`, [line 439](../../../../../../../backend/src/sro/domain/skill/checks.py#L439): Docstring

> Strike the systems that were never the work, and refuse a job with none
> left. None when it may be kept, as `validate` answers.
>
> ``ours`` is this deployment itself as ``Settings.our_own_origins`` names
> it, host and port, no path -- a workflow's system is a scheme and a host
> and has no path to route on.
>
> Three things are struck. The first two were mined off the real acme
> store; the third off `new`, by the first pass that ever ran over real
> readings:
>
> **This product's own console.** `Review Video Recordings for Teach Task`
> is the miner watching somebody use SRO while capture was on. `admit`
> already refuses the apparatus at the door, which stops the NEXT one and
> does nothing about the day already in the store -- and the operator has
> deliberately emptied the tenant's exclusions, so capture is meant to stay
> whole and the judgment belongs here, where a job is proposed rather than
> where a gesture is kept.
>
> **A hop the browser bounced the operator through.** `Search for Work
> Areas` opened on `blueyonderalphaus.b2clogin.com` and
> `keycloak-...byp.ai`, which is a sign-in redirect chain read as the
> beginning of a job. A system is transit when the job carried on somewhere
> else afterwards AND some gesture on it ended on another system. Both
> halves are needed and each saves a real job the other would have lost: the
> WMS host bounced elsewhere on 4 of its 495 gestures, and is never struck
> because the work ends there; `mail.google.com` is read first and left for
> the WMS in two stored jobs, and is never struck because Gmail bounces
> nobody anywhere.
>
> **A job that is only signing in.** `Sign In to WMS` is three steps on an
> identity host and nothing else. The transit rule cannot reach it, and the
> credential the recorder already marks is what names it without keeping a
> list of hostnames. Refused rather than struck, because the claim is about
> the job and not about one of its systems -- see the comment below.
>
> What it wrongly strikes, said plainly: a job whose last act on one system
> is a hand-off link into another it never returns from -- raise it in the
> ticketing system, follow the link into the WMS, finish there. Real work on
> the first system, and this reads it as a doorway. Naming identity-provider
> domains instead would have been narrower and would also have been a list
> somebody has to keep, wrong for every customer running an SSO nobody here
> has heard of.

## `_sittings`, [line 482](../../../../../../../backend/src/sro/domain/skill/checks.py#L482): Docstring

> Consecutive runs of `times`, split wherever the pause is long enough.

## `one_occurrence`, [line 492](../../../../../../../backend/src/sro/domain/skill/checks.py#L492): Docstring

> Strike every citation but one doing's, in place.
>
> A model asked to read a day and told that an operator often repeats a job
> does not always answer with one job per doing. It answers with ONE job
> whose every step cites every doing's gesture: step 1 of acme's `Create a
> Work Area` cites a gesture from 08-26 10:39 and another from 08-27 13:16,
> and calls that one step.
>
> That is not a harmless surplus of evidence. Three things read these
> citations and all three are wrong about a workflow built this way:
>
> * **The shape.** `shape_key` is built from the cited gestures in order, so
>   a job done three times is served as a shape three doings long with the
>   doings interleaved. The extension's matcher asks whether the operator's
>   last *k* gestures ARE this shape's first *k*, and no single doing ever
>   is. Measured on acme's seven jobs: the three with more than one doing in
>   them are exactly the three the replay never offers.
> * **`learn_parameters`.** It needs a SECOND proposal to diff against the
>   stored one. A pass that folds every doing into a single proposal never
>   produces one, so a job the operator did four times can still be stored
>   with no parameters at all.
> * **`_by_control`.** It keeps the last value per control in time order, so
>   the other doings' values are silently dropped rather than becoming the
>   `seen_values` range that makes a parameter useful.
>
> The doing kept is the one supplying citations to the most steps, and the
> latest of those if two tie -- latest because a re-mine should drift towards
> what the operator does now, not towards the first thing they ever did.
>
> A step left citing nothing is left that way rather than dropped here:
> `validate` refuses an uncited step, and a job whose steps do not all belong
> to one doing should be refused under that name rather than quietly
> reshaped into a shorter job nobody demonstrated.
>
> Nothing recovers the struck doings. They stay in the window and the pool,
> so the next pass reads them again -- which is the path that already exists
> for a second doing, and the path `learn_parameters` was written for.

## `validate`, [line 35](../../../../../../../backend/src/sro/domain/skill/checks.py#L35): Comment

Code: `if not workflow.steps:`

> umbrella.workflow_from drops junk steps one at a time, so a workflow whose
> steps were ALL junk arrives here with steps=[] and no citations at all --
> nothing uncited for the loop below to catch. This is that rejection.

## `validate`, [line 44](../../../../../../../backend/src/sro/domain/skill/checks.py#L44): Comment

Code: `if not step.says.strip():`

> cites' sibling. workflow_from falls back to says="" for a step the
> model left unworded, and a step that says nothing is not a step
> however well it is cited -- it reaches an operator as a blank line.

## `validate`, [line 46](../../../../../../../backend/src/sro/domain/skill/checks.py#L46): Comment

Code: `for used in step.uses:`

> A step may only use steps that come BEFORE it.
>
> Forwards is a job that cannot run: the value is not made until later,
> and a run reaching step two for step five's record would bind
> nothing and type an empty box. Itself is the same fault written
> smaller. And a step that does not exist is a model inventing an
> edge -- the one thing citation exists to refuse everywhere else here.

## `validate`, [line 59](../../../../../../../backend/src/sro/domain/skill/checks.py#L59): Comment

Code: `if step.system:`

> A step naming no system is not checked for one: the umbrella
> substitutes None for a junk value, so an absent system is a silence
> rather than a claim.

## `validate`, [line 60](../../../../../../../backend/src/sro/domain/skill/checks.py#L60): Comment

Code: `touched = {evidence[cite] for cite in step.cites if evidence[cite]}`

> An unknown system confirms nothing -- the rule shared_values and
> correlate._owner already apply. So a step whose every citation is
> unattributed is refused rather than waved through, and it is
> refused under its own reason: "you named a system none of your
> evidence touched" and "your evidence has no known system" are
> different faults and diagnose differently.

## `validate`, [line 75](../../../../../../../backend/src/sro/domain/skill/checks.py#L75): Comment

Code: `evidenced = {evidence[cite] for cite in cited_ids(workflow)}`

> Every cite is in `evidence` by now, so this is the whole of what the
> workflow actually stood on. `systems` is its own model output rather than
> a summary of the steps, so it can name a system no step ever did.
>
> No `if evidence[cite]` filter, unlike the step check above, which needs
> one to tell "no known system" from "the wrong system". Here `claimed` is
> already truthy-only, so an unknown system arriving as "" can never match
> anything it is subtracted from. Filtering both sides is one guard
> pretending to be two -- deleting it changed no test.

## `validate`, [line 80](../../../../../../../backend/src/sro/domain/skill/checks.py#L80): Comment

Code: `if len(workflow.steps) < K_MIN_SHARED_STEPS:`

> Last, because it is the only rejection here that is not about honesty.
> Everything above catches a workflow that misdescribes its own evidence,
> and those diagnose better than "too short" does -- a one-step proposal
> that also cites a gesture nobody recorded should be refused for the
> citation. This one is about what the rest of the system can do with an
> honest answer.
>
> Fewer steps than `identity.resolve` needs to ever recognise this job
> again. The bound is imported from the rule that causes it rather than
> chosen here: `resolve` requires K_MIN_SHARED_STEPS shared shape entries
> before it will call two proposals the same job, so a workflow with fewer
> steps can only ever come back "new". Every pass over the same evidence
> mints another copy and nothing ever merges them.
>
> Mined off the real acme store: a clean six-pass re-mine produced a second
> `Create a Customer Type` of one step -- "Save the customer type
> configuration" -- beside the real six-step job it was a fragment of. One
> step is also not a job an operator would want offered: there is nothing
> to parameterise and nothing in it to save them.

## `coverage`, [line 108](../../../../../../../backend/src/sro/domain/skill/checks.py#L108): Comment

Code: `total = sum(deciles)`

> An empty window skips the loop and lands here, so this is also the
> no-items case: one return for "no citation fell anywhere in it".

## `coverage`, [line 113](../../../../../../../backend/src/sro/domain/skill/checks.py#L113): Comment

Code: `coverage=sum(1 for d in deciles if d > 0) / min(10, n),`

> Over min(10, n) rather than a flat ten: a window of four gestures has
> four parts and can only ever land in four deciles, so dividing by ten
> reported a FULLY cited short window at 0.4 -- under K_MIN_COVERAGE.

## `work_only`, [line 444](../../../../../../../backend/src/sro/domain/skill/checks.py#L444): Comment

Code: `last = {system: index for index, system in enumerate(order)}`

> Last occurrence per system: what matters is whether the job carried on
> after this system the LAST time it was on it, not the first.

## `work_only`, [line 452](../../../../../../../backend/src/sro/domain/skill/checks.py#L452): Comment

Code: `during = _during(workflow, gestures)`

> A job that is only signing in. The transit rule above cannot reach this
> one: it strikes a system the job carried on FROM, and a job that is only
> a sign-in never carries on anywhere -- its last gesture is on the
> identity host, so `index < len(order) - 1` is false and the hop stands as
> if it were the work.
>
> `Sign In to WMS` is what that let through, mined off the real `new` store
> by the first pass that ever ran over real readings: three steps on
> `b2clogin.com` and a keycloak host, no parameters, and it would have been
> offered to an operator as a job worth automating.
>
> Asked of the whole job rather than of one system, because that is the
> claim -- not "this host is a doorway" but "nothing here was work". All
> three halves are needed and each saves a job the others would lose:
>
> - a credential alone condemns the WMS itself on the day somebody mines
>   setting a password for a new user, which is real warehouse work;
> - no writes alone condemns every read-only job, and looking things up is
>   most of what an operator does;
> - a redirect alone condemns an honest hand-off, which `work_only` already
>   says plainly it does not want to strike.
>
> Together they say: a password was typed, the browser moved the operator,
> and nothing was ever written back. That is signing in, and it needs no
> list of identity hostnames -- which this function declined to keep, on
> the grounds that every customer runs an SSO nobody here has heard of.

## `work_only`, [line 469](../../../../../../../backend/src/sro/domain/skill/checks.py#L469): Comment

Code: `if workflow.systems and not kept:`

> `workflow.systems` empty to begin with is a model that named none, which
> `validate` allows and this must not start refusing: nothing was struck.

## `bindable`, [line 147](../../../../../../../backend/src/sro/domain/skill/checks.py#L147): Docstring

> Every name some step of the job can be given: its parameters and the names
> of the controls its gestures cite. `undeliverable` drops a declared
> parameter outside it; `compose` composes a run's value outside it.

## module, [line 192](../../../../../../../backend/src/sro/domain/skill/checks.py#L192): Note

Code: `_SIGN_OUT = re.compile(r"(?<![a-z0-9])(?:log[\s_-]?(?:out|off)|sign[\s_-]?out)(?![a-z0-9])", re.I)`

> The words a sign-out control is labelled with, and (`_SIGNED_OUT_PAGE`) the
> words in a sign-in or signed-out page's path. Matched on whole words, by
> name, as credential fields are: never by reading a value. "Log Out",
> "Logout", "Log off" match; "Logoutput report" does not. "Sign off" is not a
> sign-out: in a warehouse it is an approval ("Sign-Off Queue"), F3 round 1.
> The page's words are read from the URL's path only -- a query string
> carries redirect targets that name anything. `auth` and `authorize` are
> the sign-in paths of Keycloak (`/protocol/openid-connect/auth`) and OAuth
> (`/oauth2/v2.0/authorize`).
>
> ponytail: an English vocabulary. A control labelled in another language, or
> with an icon and no accessible name, is not seen as a sign-out; upgrade by
> reading what the session did (a call that clears the session cookie) once
> the recorder keeps response cookies' names.

## `signs_out`, [line 201](../../../../../../../backend/src/sro/domain/skill/checks.py#L201): Note on the function

> Whether this job signs out (F3): its steps end the session, and ending it is
> all they do (product ruling M4, round 1). Four conditions:
>
> 1. The last cited control labelled as a sign-out (`_ends_the_session`).
> 2. Every cited gesture before it only reaches it (`_only_reaches`): opens a
>    menu or moves between pages. A job that does anything else first --
>    exports a report, fills a field -- and then logs out is work.
> 3. No step up to and including the control writes, by the codebase's own
>    write check (`evidence.writes`: any method that is not a read, at any
>    status) -- not `_did_business`'s 2xx POST/PUT/PATCH, which let a DELETE
>    204, a form POST 302 or a POST with no status through. The control's own
>    call is left out of its step (M5): a log out that is itself a POST 200 is
>    the control, not a write. `_only_reaches` refuses any mutating call on
>    any host, which covers the API's own subdomain that `writes` (same
>    origin only) does not see.
> 4. Then a sign-in or signed-out page: the control's own navigation lands on
>    a path naming signing in or out, or the very next gesture in the same
>    stream and tab is on such a path or is a credential. Another origin alone
>    is never proof (round 1, I3): an operator who clicks on and then works in
>    Outlook has ended nothing. Nothing the job does afterwards may be back in
>    the signed-in system.
>
> Only the next gesture after the control is read, not the whole sitting: an
> operator who signs back in and goes on working ten minutes later has not
> shown that this job ended anything.
>
> Real QA, 2026-09-27: 7 of 23 jobs were sign-in or sign-out chores and drew
> 44% of the offers; `Log Out` was never flagged because no rule asked.
> `Workflow.chore` reads both verdicts; R1 excludes chores from candidates.

## `_only_reaches`, [line 241](../../../../../../../backend/src/sro/domain/skill/checks.py#L241): Note on the function

> A gesture that only gets the operator to the sign-out control: a hover or
> scroll, or a click or press that types nothing, touches no credential, makes
> no mutating call on any host, and either opens something (a menu, menu item,
> tab, tree item or navigation role, on the target or its landmarks; or an
> `aria-haspopup` / `aria-expanded` control) or moves the page. A button that
> reads and moves nowhere -- Export -- is substance.
>
> ponytail: roles are what the page declares. A menu built of bare divs with
> no role and no navigation is read as substance, so its Log Out stays a
> candidate -- the safe side; upgrade by reading the outline's menu structure.
