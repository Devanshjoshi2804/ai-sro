# Notes for `backend/src/sro/domain/execution/evidence.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/evidence.py`](../../../../../../../backend/src/sro/domain/execution/evidence.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/evidence.py#L1): Docstring

> A13: what a step knows before any model is asked.
>
> A step cites gestures; those gestures carry recorder.js fingerprints; so the
> locator list the protocol wants is built from the cited evidence with no model
> involved, in the protocol's own priority order. `origin` is per step, from that
> step's own evidence -- in a job spanning two systems the Blue Yonder steps carry
> Blue Yonder's origin and the SAP step carries SAP's. A documented
> cross-application agent failure is losing window focus during a hand-off, so
> data meant for the second application is typed into the first; this is what
> stops it.

## module, [line 14](../../../../../../../backend/src/sro/domain/execution/evidence.py#L14): Note on the line above (debt)

Code: `K_CAUSED_S = 0.5`

> How long after a gesture a call the gesture caused can still start.
>
> A browser dispatches a request from the event handler, so a call the operator
> caused starts in the same instant they acted. A page's background traffic runs
> on its own timer and lands on whatever gesture happened to be open when it
> fired. Measured over every same-origin mutating call in both real stores, the
> two populations do not touch:
>
>     every real create   0.016s to 0.059s after its gesture
>     every chatter call  0.667s to 8.118s after its gesture
>
> -- 18 real calls under 60ms, 12 chatter calls over 660ms, and nothing between.
> The threshold sits an order of magnitude above the slowest real one and still
> below the fastest piece of chatter.
>
> It is deliberately generous, because the two mistakes do not cost the same. A
> chatter call read as a write makes a run withhold and park a step that changes
> nothing -- wasteful. A write read as chatter makes a dry run SEND it. So the
> rule only excludes a call it can show was not caused: a call whose start time
> the recorder never captured is kept, which is the opposite of `confirming_read`
> and for the same reason -- there, "after the write" is the claim being made, so
> an untimed call cannot support it; here, "not caused by the gesture" is the
> claim, so an untimed call cannot support that either.
>
> ponytail: one constant, no per-host calibration. A page that saves on a
> debounce longer than this would look like chatter, and the fix then is the
> debounce's own length, not a cleverer rule.

## module, [line 16](../../../../../../../backend/src/sro/domain/execution/evidence.py#L16): Note on the line above

Code: `CREATED = 201`

> What a create came back with, on every real one in both stores, and what no
> chatter endpoint returned. See `recorded_call`, which prefers such a call over
> a sibling on the same step.

## module, [line 18](../../../../../../../backend/src/sro/domain/execution/evidence.py#L18): Note on the line above

Code: `READ_METHODS = ("GET", "HEAD", "OPTIONS")`

> The methods that change nothing. One copy, because "does this step write?"
> and "is this the read that confirms the write?" have to be the same question --
> `sro.domain.execution.belts` asks it of the same calls this module does.

## module, [line 88](../../../../../../../backend/src/sro/domain/execution/evidence.py#L88): Note on the line above

Code: `PUTS_A_VALUE = frozenset({"type", "select", "upload"})`

> The gesture kinds that put something somewhere. A step the job says carries
> a value was demonstrated by one of these, whatever else was cited beside it.

## `Locator`, [line 22](../../../../../../../backend/src/sro/domain/execution/evidence.py#L22): Docstring

> One rung of the ladder. `within` and `visible_only` are read by the
> extension (`new-chrome-extension/src/page/page-code.js`) to scope and
> filter the match at the wire -- dropping them would let a hidden control
> through.

## `locators_for`, [line 41](../../../../../../../backend/src/sro/domain/execution/evidence.py#L41): Docstring

> The ladder, strongest first: the framework's own handle, then role and
> name, then visible text, then the test id, then the css path the protocol
> calls a last resort. A gesture with no target -- a scroll -- has no ladder.

## `_stable_leaf`, [line 65](../../../../../../../backend/src/sro/domain/execution/evidence.py#L65): Docstring

> The last element of a css path, with what render order assigned struck.
>
> `td#ext-gen5745 > div.x-grid-cell-inner > div.x-grid-row-checker:nth-of-type(2)`
> is `div.x-grid-row-checker`: the tag and the classes the application gave
> it, which are the same on every render. Empty where nothing stable is left
> -- a bare tag names every element of that kind.

## `origin_of`, [line 73](../../../../../../../backend/src/sro/domain/execution/evidence.py#L73): Docstring

> Scheme and host of the page the gesture happened on -- else of the first
> call that completed and names a system, else of any call that names one.
>
> The page first, and this inverts A13's written order on purpose. Every
> consumer of `origin` -- `ui.url`, `screenshot`, the tab `ui.perform` acts
> in -- is about the page the operator was on; `http.send` carries its own
> url and the extension picks a tab from that, so the request host never
> decided the tab. Request-first also had a real failure: a call that never
> completed can be the earliest on a gesture, and a run steered at a dead
> host spends its retries there.

## `primary_gesture`, [line 91](../../../../../../../backend/src/sro/domain/execution/evidence.py#L91): Docstring

> The cited gesture this step is aimed at.
>
> **The one that puts a value, where the step declares it takes one.** A step
> cites everything the operator did while performing it, in the order mining
> listed them, and that order is not a statement about which control the step
> is FOR.
>
> Measured on the deployment 2026-09-22 at 16:09. `Delete a Customer Type`
> step 1 -- "Enter filter criteria to locate the target customer type" --
> cited twenty-four gestures across three demonstrations, and the first was
> a click on `removeCriterionButton`: the small cross that clears a filter
> somebody had left behind. So the locator ladder was built for the cross.
> It exists only when a criterion is already present, so on a clean grid the
> ladder found nothing, the run fell to the vision rung, clicked a
> coordinate near the top of the page and typed into nothing. The step is
> named for typing a filter and was aimed at the button that clears one.
>
> `step.parameters` is the job's own word that this step carries a value, so
> a gesture that put one is what it was demonstrated by. Where the step
> declares none -- a click, a navigation, a Save -- the first citation is
> still the answer, which is what this has always returned.
>
> Order is otherwise untouched: among the value-putting citations the first
> still wins, so a step that types into two boxes is aimed exactly where it
> was.
>
> **And the one putting a value into a control this run holds a value for**,
> whatever the step declares -- `holds` is every name the run's values are
> filed under, which since `_under_every_name` includes the page's own
> itemId. `step.parameters` is a model's answer and mining leaves it empty:
> the re-mined `Delete a Customer Type` of 2026-09-22 at 12:03 came back with
> `parameters: []` on its filter step again, citing thirty-eight gestures
> whose first targeted one was a click on no component at all. The run held
> `filterComboBox` and the step cited eight typings into it.
>
> Measured before it was written, across every job on the deployment: the
> steps this re-aims are twelve, and all twelve are "Enter X" -- not one
> Save, not one Delete. Two of them were aimed at the wrong control until
> now, that filter step and `Create a Customer Type`'s "Enter the Customer
> Type Description" at a grid row.

## `control_names`, [line 108](../../../../../../../backend/src/sro/domain/execution/evidence.py#L108): Docstring

> What this gesture's control is called -- the names `value_for` looks
> a run's value up by, in the same three places.

## `_caused_by`, [line 122](../../../../../../../backend/src/sro/domain/execution/evidence.py#L122): Docstring

> Whether this gesture is what made this call. See `K_CAUSED_S`.

## `recorded_call`, [line 128](../../../../../../../backend/src/sro/domain/execution/evidence.py#L128): Docstring

> The call this step's evidence made: a mutation that came back `CREATED`
> if there is one, else the first mutation, else the first call at all. What
> `http.send` would replay, and what `verify` reads an expected status from.
>
> Only calls on the gesture's OWN origin. A page's third-party traffic is not
> what the operator did, and reading it as the step's write is what stopped
> every run this repository has ever recorded: step 1 of `new`'s `Create a
> Warehouse Equipment Type` is "Read the equipment type details from an
> email", a click on `mail.google.com`, and the only call it recorded was a
> `POST` to `play.google.com/log` -- Google's telemetry beacon. `writes` read
> that as a mutation, so the run parked for a human approval on a beacon, and
> then `verify` demanded a read-back showing the value the run supplied,
> which a beacon can never show. Six runs, six `stopped`.
>
> Measured over both real corpora, 719 gestures: of 360 mutating calls, 144
> are cross-origin and every one of them is third-party -- 75 to
> `play.google.com/log`, 44 to assorted `*-pa.clients6.google.com`, 6 from
> the WMS to its sign-in host. So this costs nothing that any operator did.
>
> **Same origin does not finish the job, and not only on Gmail.** A page's own
> origin makes chatter too, and the warehouse host is no exception -- which an
> earlier draft of this docstring got wrong by counting its mutating calls
> and calling them work. Counted by how many DISTINCT gestures fire each
> same-origin mutating endpoint:
>
>     16  POST mail.google.com/mail/u/*/
>     15  POST mail.google.com/sync/u/*/i/s
>     14  POST <wms>/refs/data/api/v1/rp/admin/sessionKeepAlive
>      9  POST mail.google.com/sync/u/*/i/fd
>      8  POST <wms>/data/WM/wm/webPerformanceEntries/batch
>      4  POST <wms>/data/WM/wm/customerTypes          <- real
>      3  POST <wms>/data/WM/wm/workAreas              <- real
>      1  POST <wms>/data/WM/wm/equipmentTypes         <- real
>
> A session keep-alive and a performance-telemetry batch are POSTs on the
> warehouse's own host, and `recorded_call` returns them. Measured against
> the stored jobs: of 13 steps this classifies as writes, **4 are chatter and
> 3 of those 4 are on the WMS** -- `new`'s `Create a Warehouse Equipment
> Type` has its step 5 read as a write by `sessionKeepAlive` and its step 6
> by `webPerformanceEntries/batch`, and both of those steps only type into a
> field. A dry run withholds them, a live run parks them on a person, and
> `verify` asks for a read-back that a keep-alive can never satisfy.
>
> That table is what `K_CAUSED_S` answers, and frequency is not how. The
> table separates chatter from work everywhere except the 3-to-4 band, where
> `logstreamz` (chatter) sits beside `workAreas` and `workOperations` (real),
> so a threshold on it would be wrong on real jobs. What does separate them
> completely is WHEN the call starts: a write leaves the event handler in the
> same instant the operator acted, and a timer's traffic does not. Of the 13
> steps this used to classify as writes, the 4 chatter ones are now correctly
> not writes, and the 9 that remain are every real create in both stores.
>
> The response status agrees with that reading, and half of it is safe to act
> on as well. Across both stores every real create came back 201 --
> `customerTypes`, `equipmentTypes`, `workAreas`, `workOperations`,
> `carrierCrossReferences`, `activityCodes` -- and no chatter endpoint ever
> did: `sessionKeepAlive`, `webPerformanceEntries/batch`, Gmail's `sync/u/*`
> and `mail/u/*`, `logstreamz`, `waa` and `perftrace` answer 200 or 204.
>
> Only half, because the converse does not hold. A real UPDATE returns 200
> too, so "not 201, therefore chatter" would tell a dry run that an edit is
> safe to send unwithheld -- a write must fail safe, and that reading fails
> the wrong way. `writes` is therefore still method-only.
>
> What IS safe is the preference above: among this step's same-origin
> mutating calls, a 201 is picked over its siblings. It is still a mutation,
> so nothing a dry run withheld stops being withheld, and on the four steps
> that record both -- acme's `Create a Customer Type` steps 1 and 6, its
> `Create an Activity Code` step 7, `new`'s `Create a Customer Type` step 5
> -- it picks the create over the keep-alive by rule rather than by the luck
> of which one the browser happened to fire first.

## `writes`, [line 155](../../../../../../../backend/src/sro/domain/execution/evidence.py#L155): Docstring

> Whether performing this step changes something. A dry run withholds it.

## `route_for`, [line 160](../../../../../../../backend/src/sro/domain/execution/evidence.py#L160): Docstring

> Where this step leaves the browser, when leaving it somewhere is all it
> does -- and there is no other way to know.
>
> A gesture records the page it happened ON, never the page it led to. The
> click that opens the Customer Types screen is recorded on the Warehouse
> screen, so the step's own evidence names where it STARTED. Read as a
> destination it sends the browser back where it began, which is what the
> first version of this did and what the suite said about it within a minute.
>
> The destination is recorded, one step along: the next step was performed
> somewhere, and that somewhere is where this one arrived. Both doings of
> `Navigate to the Customer Types screen` are followed by `Click the Add
> button` on
>
>     .../portal?siteId=SG#wm.config/wm.config.partners.customers.types////
>
> Measured on the deployment across 2026-09-16 and 17, the alternative cost
> thirteen cents a run and landed about half the time: a model was shown a
> picture, worked out that the screen lives under a menu called Partners,
> clicked one and then the other, and the verifier looked afterwards to see
> whether any of it had taken.
>
> Three things make it None, and each is a way of not knowing:
>
> **This step writes.** Then it does something at a screen rather than being
> the arrival at one, and going to a page would skip what it was for.
>
> **Nothing follows it**, so nothing recorded where it arrived.
>
> **The next step is on the same page**, so this step did not move the
> browser and a navigate would be a command that changes nothing.

## `_agreed`, [line 173](../../../../../../../backend/src/sro/domain/execution/evidence.py#L173): Docstring

> The page this step's doings have in common. `screen_of` keeps what every
> visit agrees on and drops what varies, so a session token or one record's
> id cannot become the page a run is sent to.

## `stood_on`, [line 178](../../../../../../../backend/src/sro/domain/execution/evidence.py#L178): Docstring

> Every system the operator was actually ON while doing this job.
>
> The tab's origin and the frame's, and nothing else. This is where a plan
> may SEND the browser, and it is the narrower of the two sets on purpose:
> driving somebody's browser somewhere is a different act from replaying a
> call their own click already made.
>
> `allowlist` is the wider one, and the difference is not hypothetical.
> Measured on this deployment, 2026-09-15: `Create a Customer Type` cites a
> click in Gmail, a Gmail page calls Google's own infrastructure, and so
> `https://play.google.com` was an origin a planner could have navigated an
> operator's browser to -- on the evidence of a telemetry beacon, for a job
> about warehouse customer types. No gesture ever happened there.

## `allowlist`, [line 191](../../../../../../../backend/src/sro/domain/execution/evidence.py#L191): Docstring

> Where a call this job's evidence already made may be replayed to.
>
> `stood_on` plus the origin of every request a cited gesture produced. Those
> origins are here for `recorded_call`: a step's evidence can be a call to an
> API origin the page itself never was -- a form on `wms.example` posting to
> `api.wms.example` -- and `http.send` replays exactly that call. Refusing
> them would refuse the step its own demonstrated write.
>
> So this is the set for `http.send` alone. What may take the browser
> somewhere is `stood_on`, which is the same question asked about a person
> rather than about a request their page made.

## `locators_for`, [line 50](../../../../../../../backend/src/sro/domain/execution/evidence.py#L50): Comment (debt)

Code: `leaf = _stable_leaf(target.css_path)`

> A view is a container of rows, and the row is what was clicked.
>
> Measured on the deployment 2026-09-22 at 13:54. `Delete a Customer
> Type` step 2 was demonstrated as a click on a row's checkbox --
> `div.x-grid-row-checker` -- whose component is the grid's
> `gridview`. The component rung matched the whole view, the click
> landed on it, nothing was selected, and Delete stayed disabled.
> The css path that named the checkbox is keyed on `td#ext-gen5745`,
> an id assigned in render order that never exists twice.
>
> So the recorded leaf, with its id and position struck, scoped to
> the view: the checkbox of the first row the view shows.
>
> ponytail: the FIRST row. Right after a step that filtered on a
> key, which is how every job here reaches a row; a view showing
> several would get its first. Name the row by its cell text when a
> job selects among many.

## `recorded_call`, [line 141](../../../../../../../backend/src/sro/domain/execution/evidence.py#L141): Comment

Code: `if is_background_traffic(request.url):`

> A keep-alive that happened to fire within `K_CAUSED_S` of the
> click is still the page's timer: `wfl_5873ec01`'s session-expired
> dialog was a "write" by `sessionKeepAlive` and `perftrace` alone,
> and a run could not step over it.

## `route_for`, [line 164](../../../../../../../backend/src/sro/domain/execution/evidence.py#L164): Comment

Code: `if not cited or any(one.action.kind != "click" or one.action.value for one in cited):`

> Only clicks, and nothing typed into anything.
>
> "Does not write" is not "only arrives": the step that types a customer
> type into a field writes nothing and is emphatically not a navigation.
> The suite said so the first time this rule was tried -- a run navigated
> instead of filling in the form. A step whose every gesture is a click is
> a step made of moving about.
