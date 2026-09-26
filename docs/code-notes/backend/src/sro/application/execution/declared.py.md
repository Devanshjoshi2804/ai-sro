# Notes for `backend/src/sro/application/execution/declared.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/declared.py`](../../../../../../../backend/src/sro/application/execution/declared.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/declared.py#L1): Docstring

> What a job's own fields are declared to hold, before any run finds out.
>
> `workflow_learned.holds` is what a run MEASURED: it typed, the browser silently
> kept a prefix, and the run wrote the number down so the next run of that job
> would not have to spend a person's press rediscovering it. That works, and it
> works one field at a time, one job at a time, and only after somebody has
> already been sent a record that does not say what they asked for.
>
> Somebody wrote the numbers down years ago. `index/field-dictionary.json` holds
> 404 payload keys with their screen labels and their `maxLength`, and
> `index/form-models-all.json` holds 88 real create forms captured from the
> application itself. Both are already ingested -- `infrastructure/knowledge/
> catalogue.py` has read them into `field` and `form` claims since long before
> the rig could type -- and nothing asked them what a JOB's parameters hold.
>
> So this is a join and not a new source: the job names its parameters the way
> the screen names them, the claims are filed under the key the body posts, and
> the labels are the bridge. See `field_notes.limits_named` for the rule, which
> is the interesting half: the lowest ceiling binds, and a label two keys answer
> to decides nothing.
>
> **Declared, and a declaration is not a measurement.** The dictionary says
> `customerType` holds 60 and the real form says 4. So this is a ceiling handed
> to `limits_for` beside what runs have learnt, never instead of it.

## module, [line 13](../../../../../../../backend/src/sro/application/execution/declared.py#L13): Note on the line above

Code: `K_EVERY_FIELD = 800`

> How many field claims one lookup asks for.
>
> Every one, rather than a search. `search` matches terms against a claim's title
> and key, and what this needs to match is a LABEL inside the body -- so a lookup
> for `Customer Type Description` scores on the title it happens to appear in and
> misses the four keys it does not. Measured on QA 2026-09-16: 404 field claims.
> Eight hundred is room for a base twice that size before a job stops seeing
> fields it has.

## module, [line 15](../../../../../../../backend/src/sro/application/execution/declared.py#L15): Note on the line above

Code: `K_EVERY_FORM = 400`

> How many create forms one lookup asks for. `workflow_runs.K_EVERY_FORM` says
> why every one rather than a search; 88 on this deployment.

## `kb_rows`, [line 20](../../../../../../../backend/src/sro/application/execution/declared.py#L20): Docstring

> Every field and form claim the tenant holds, read once (round 1, I2). This
> used to run inside `declared_limits`/`declared_keys` on every call, which
> was fine for the single job each of those was ever asked about (an offer,
> a pending question, a start) but wasteful for `job_facts`, which asks about
> every job in the tenant on every chat sentence and every console read: the
> same 404 field claims and 88 forms do not change per job, so `job_facts`
> reads them once for the whole call and calls `limits_from_rows` per
> workflow, never `declared_limits` itself.

## `limits_from_rows`, [line 31](../../../../../../../backend/src/sro/application/execution/declared.py#L31): Docstring

> `declared_limits`'s join, pulled out so it can run against rows already in
> hand (`job_facts`, once per tenant) as easily as rows fetched for one job
> (`declared_limits` itself, below). `_screen_label` resolves the job's own
> screen to the label the field dictionary's `screens` list speaks in before
> `_on_its_screen` filters by it -- see `_on_its_screen`'s own note for why.

## `keys_from_rows`, [line 41](../../../../../../../backend/src/sro/application/execution/declared.py#L41): Docstring

> `limits_from_rows`'s sibling for `keys_named`'s half of the join. Nothing
> in this plan calls it against pre-fetched rows yet; kept beside
> `limits_from_rows` so `declared_keys` and any future batched caller share
> one join, not two.

## `declared_limits`, [line 51](../../../../../../../backend/src/sro/application/execution/declared.py#L51): Docstring

> What this job's parameters are documented to hold, by parameter name.
>
> The screen's own form first and the dictionary second, which is the order
> `limits_named` reads them in and the order the evidence deserves: a form
> model was captured from the form an operator actually uses, and the
> dictionary is what the vendor's manual says about a key across every screen
> that posts it.
>
> Empty for a job whose names nothing documents, which is the honest answer
> and the one that changes nothing -- a limit nobody declared is a limit the
> first run still finds out the hard way, exactly as it did before.
>
> A single-job caller's own fetch-then-join: `kb_rows` then `limits_from_rows`.
> Kept as one call for `about_an_offer`, `from_the_mail`, `workflow_runs` and
> `run_workflow`, none of which ask about more than one job at a time.

## `declared_keys`, [line 60](../../../../../../../backend/src/sro/application/execution/declared.py#L60): Docstring

> Which body key each of these screen names is posted as.
>
> `declared_limits`' sibling and the same two sources in the same order, for
> `keys_named`'s half of the join: that one asks how big the box is, this
> asks which slot it is.
>
> What it is FOR is a field no demonstration varied. A job's parameters are
> what two doings proved vary and a form has far more fields than that, so a
> request naming one more had nowhere to put it -- and the value was dropped
> and, until `54926cba`, dropped silently.
>
> Empty for a name nothing documents and for a label two keys answer to,
> which is `keys_named`'s own refusal: a guess between ten keys called
> `Description` is a value written into a slot nobody chose.

## `_slots`, [line 69](../../../../../../../backend/src/sro/application/execution/declared.py#L69): Docstring

> The fields of whichever captured form this job's screen is.
>
> Joined on the route the form claim is keyed by, the same containment
> `workflow_runs._forms` uses -- and for its reason: a body key does not name
> a form, because `customerType` is posted by two of them on this deployment,
> so a lookup by key alone would lend one screen's numbers to another
> screen's write.

## `_screen_label`, [line 89](../../../../../../../backend/src/sro/application/execution/declared.py#L89): Docstring

> The screen label the field dictionary's `screens` lists speak in --
> `"Customer Types"`, never the route hash -- read off whichever form claim's
> route is contained in this job's screen, the same containment `_slots`
> matches a form by. `None` when no form claim matches, which is exactly
> "the job's screen is not one this dictionary can name" (round 1, I1): a
> field entry scoped to particular screens gets none of them, on the same
> reasoning `_slots` already applies to a form -- a body key, or here a
> label, does not name a screen on its own.

## `_on_its_screen`, [line 101](../../../../../../../backend/src/sro/application/execution/declared.py#L101): Docstring

> Which field claims speak about this job's screen (round 1, I1: Important
> #1 of the C2 review). `index/field-dictionary.json` files `description`
> under 8+ unrelated keys across screens from 20 to 2000 characters apart, and
> a field claim carries its own `screens` list (`catalogue._fields`,
> `entry.get("screens", [])`) precisely so a uniquely-labelled field scoped to
> one screen never lends its limit to a job on another. A claim whose
> `screens` list is empty or absent is not scoped by anything this dictionary
> knows and stays universal, matching every caller before this round and
> every test built on the pre-round-1 fixtures, which never set `screens` at
> all. A claim WITH a `screens` list attaches only when `label` (the job's
> own screen, resolved by `_screen_label`) is in it -- so an unresolved screen
> (`label is None`) drops every scoped claim rather than guess, the same
> "unknown means none" `_slots` already applies to forms.

## `names_of`, [line 115](../../../../../../../backend/src/sro/application/execution/declared.py#L115): Docstring

> What this job calls its fields, in the order it declares them.
>
> The JOB's parameters and not the steps', which are a different list for a
> good reason: a step's `parameters` say which step fills which name, and
> only a step that some demonstration actually varied has any. A job knows
> what it is about before it knows which step types it -- and this question
> is asked of a job that has not started.

## `_cites_with_params`, [line 123](../../../../../../../backend/src/sro/application/execution/declared.py#L123): Docstring

> The one predicate `screen_for` and `screen_of_loaded` must agree on: which
> cited gestures actually type a value. Pulled out so the DB-backed and the
> already-loaded path can never quietly drift apart on what counts.

## `screen_of_loaded`, [line 127](../../../../../../../backend/src/sro/application/execution/declared.py#L127): Docstring

> `screen_for`'s own answer, computed from gestures a caller already holds
> (round 1, I2: `job_facts` builds `by_id` once per workflow from the one
> tenant-wide `gestures_for` it already made; asking `screen_for` again would
> have queried the same rows a second time, once per job, on the hottest
> path in the system). Same rule, same `screen_of`; only the source of the
> gestures differs.

## `screen_for`, [line 136](../../../../../../../backend/src/sro/application/execution/declared.py#L136): Docstring

> The screen this job's fields are on, as its own demonstrations agree.
>
> A form claim is keyed by the route it was captured on, so a job with no
> screen gets the dictionary alone -- which is the weaker half, and the half
> that says `customerType` holds 60 when the form an operator uses says 4.
> Worth one read of the cited gestures to avoid.
>
> Only the steps that fill a parameter, which is narrower than it first
> looks and had to be. Measured on QA 2026-09-18 against the real `Create a
> Customer Type`: its six steps open a MAIL, navigate to the WMS, press Add,
> type twice and Save -- so the citations of all six are two systems, and
> `screen_of` anchors on the first url it is given and answers with the Gmail
> inbox. The form half then matched nothing, `Customer Type` came back as the
> manual's 60 rather than the real form's 4, and a card would have accepted
> `NEWSROTEST`, sent it, kept `NEWS` and been answered 201.
>
> Narrower is also more true. A limit is a fact about the box a value is
> typed into, so the screen worth asking about is the one the typing happens
> on -- not the one the job opens on, and not a collapse across both.
>
> Empty where no step declares a parameter, and the dictionary answers alone.
> That is the honest reading rather than a fallback to every step: a job with
> no typing step has no form to be measured against, and widening the net to
> find one is how the Gmail url got in here.
