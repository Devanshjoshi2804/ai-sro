# Notes for `backend/scripts/one_whole_run.py`

Comments and docstrings moved out of [`backend/scripts/one_whole_run.py`](../../../../backend/scripts/one_whole_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/one_whole_run.py#L1): Docstring

> A job, watched in a real browser and then done by the system, end to end.
>
> Nothing in this repository has ever finished a workflow run. Four runs exist
> across both real tenants and all four are `stopped`; the furthest any reached
> was step 3 of 6. Every one died the same way, and not because the runner is
> broken: `scripts/stub_device.py` refuses screenshots on purpose, so `verify`'s
> third rung -- the one that looks at a picture -- has never executed once, and
> a step that rung would have held reads `unclear` instead, which stops the run.
>
> What this proves, and what it does not. It proves the chain: a real Chromium
> with the real extension watching a real page, gestures uploaded to the real
> backend over the real socket, a workflow standing on those gestures, and
> `run_workflow` driving that same browser back through them with a real model
> looking at real screenshots. It does NOT prove anything about a warehouse:
> the page is a local form, and a page nobody has to log into is an easier page
> than Blue Yonder.
>
> The run is dry, and a dry run CAN finish: `run_workflow` ends `held` when every
> step is `held` or `withheld`, so the typing step is verified for real and the
> Save step is shown in full and withheld. A live run needs a person to tap
> Approve in the panel, which is the half this still does not reach.
>
>     make one-whole-run
>
> Needs the API up (`make up && make api`) and a Chromium Playwright can load an
> extension into. Nothing here is part of the product.

## module, [line 21](../../../../backend/scripts/one_whole_run.py#L21): Note on the line above

Code: `REFERENCE = "PO-88213"`

> A second field, so the job is three steps rather than two.
>
> `recognise.match` scans `k` down from `shape.length - 1`: an offer is made with
> something still LEFT to do, so a two-step job can never be offered at all --
> `K_OFFER_AFTER` is 2 and the highest k a two-position shape allows is 1. Three
> steps is the shortest job this browser can be offered, which is what `--offer`
> is here to see happen.

## `_Depot`, [line 89](../../../../backend/scripts/one_whole_run.py#L89): Docstring

> The page the work happens on, and the one call it makes.

## `_Depot`, [line 92](../../../../backend/scripts/one_whole_run.py#L92): Note on the line above

Code: `writes: ClassVar[list[str]] = []`

> Every mutation this depot was actually sent. The operator's own doing is
> the first; anything after it came from the run, which is the only evidence
> that a write really went out rather than being reported as though it had.

## `_watch_this_tab`, [line 151](../../../../backend/scripts/one_whole_run.py#L151): Docstring

> Nothing is captured from a tab nobody pointed at.

## `_approve_in_the_panel`, [line 163](../../../../backend/scripts/one_whole_run.py#L163): Docstring

> Press Approve, in the real panel, as this browser.
>
> The half nothing in this repository had ever exercised. A parked run is a
> live Chrome holding a warehouse write open, and every approval this system
> has recorded was tapped with the tenant's bare credential naming no browser
> -- the supervisor's-console path, which skips `approver_is_the_driver`
> entirely. This is the other one: the panel never holds the rig's bearer, so
> the press goes to the worker, which sends the run id with this device's own
> `?device_id=` and `X-Device-Secret`.
>
> Through the button rather than the message behind it. `run-card.js` draws
> Approve only on a step whose outcome is `awaiting` AND only while the run is
> live, and the panel only draws the card at all once the worker has adopted
> the run -- `commands.js` writes `source: "rig"` for every command arriving
> on the rig's channel, whoever started it. Sending `approve-rig-run` by hand
> would prove the backend door and skip every one of those.

## `_offered_in_the_panel`, [line 180](../../../../backend/scripts/one_whole_run.py#L180): Docstring

> Do the whole job by hand again, and read what the panel says about it.
>
> The half of phase 5 nothing had ever run live. `make offer-replay-backend`
> proves the matcher over the real corpus -- 6 served shapes, 6 offered as
> themselves -- but a replay is not a browser: nothing had ever shown a
> browser being served a shape and offering the job off its own gestures.
>
> The offer lands in the middle of the doing, which is the whole point of it.
> `change` fires on blur, so clicking Save emits the Reference gesture first
> and the click second -- and between those two the tail is exactly the
> shape's first two positions, `K_OFFER_AFTER` is 2, and `recognise.match`
> scans k down from `shape.length - 1` because an offer has to leave
> something to finish. That is also why the job is three steps: a two-step
> job can never be offered at all.
>
> What it matches is a job this tenant already knows, which may be this
> script's own from an earlier invocation rather than the one just built --
> they have the same shape, and which id the panel names is not what is being
> proved. The values on the offer are this doing's.
>
> Retried as a whole doing rather than waited on, because the worker holds
> served shapes for five minutes and only ever caches a non-empty answer: on
> a tenant with no proven job the first doing matches, and on one with older
> jobs the list is already warm.

## `_accepted_in_the_panel`, [line 228](../../../../backend/scripts/one_whole_run.py#L228): Docstring

> Press Yes on the offer, as the operator it was made to.
>
> The last thing in the spec's phase 5 line that nothing had ever done. An
> offer being MADE was proved on 2026-09-14; nobody had ever answered one, so
> no run in this system's history had been started by a person accepting an
> offer rather than by a console press, a trigger or a script.
>
> Through the card's own button, and through its own inputs: `ready()` keeps
> Yes disabled until every value the offer could not read off the page has
> been typed, which is the panel refusing to start a run with a blank in it.
> Filling them here is the operator doing what the card asks.

## `_watch`, [line 271](../../../../backend/scripts/one_whole_run.py#L271): Docstring

> Follow a run to its end, pressing Approve in the panel when it parks.
>
> One loop for every way a run can start -- a press, a trigger, a schedule, an
> offer somebody accepted -- because what happens after the start is the same
> story and reading it two ways would let the two disagree.
>
> Returns 2 where the run ended anywhere but `held`, so the caller's exit code
> says whether the ladder held.

## `_fired_by_the_worker`, [line 310](../../../../backend/scripts/one_whole_run.py#L310): Docstring

> Put the job on a cron and wait for the Temporal worker to fire it.
>
> The one link in the chain nothing had proved, and the one that was broken
> until today. A schedule fires inside the worker; the socket to that Chrome
> is held by whichever process the extension connected to, which is the API.
> Started in-process there, `StartWorkflowRun` looks for the browser in the
> worker's own empty register and skips forever with "not connected" -- so
> the worker asks the API through `RunDispatcher.start_job`, exactly as the
> skill half has always asked through `start`.
>
> Every minute, because that is the shortest cron there is and the first
> firing is the whole proof. Deleted in a `finally` whatever happens: a
> trigger left on this tenant would drive somebody's browser once a minute
> for as long as the worker lives.

## `_build_workflow`, [line 358](../../../../backend/scripts/one_whole_run.py#L358): Docstring

> A two-step job standing on the two gestures just recorded.
>
> Built here rather than mined, deliberately. `mining_pass.mine` is proven on
> both real corpora and costs a 150K-token call; what this script is for is
> the half nothing has ever exercised, which is downstream of it. A
> hand-built workflow citing real gestures reaches `run_workflow` through
> exactly the same door a mined one does.

## `_Depot.do_POST`, [line 115](../../../../backend/scripts/one_whole_run.py#L115): Comment

Code: `made = f"ORD-{len(_Depot.writes):04d}"`

> 201, which is what every real create in both stores came back with,
> carrying the name the depot gave the record. A real create answers
> with one and `made_by` reads it off the 201's own body -- it is the
> only place a browser can learn what the warehouse called the thing
> it just made, and a run that cannot say which records it created
> cannot be checked and cannot be undone by hand.

## `call`, [line 122](../../../../backend/scripts/one_whole_run.py#L122): Comment

Code: `request = urllib.request.Request(  # noqa: S310`

> S310: every url is built from this file's own constants.

## `_approve_in_the_panel`, [line 177](../../../../backend/scripts/one_whole_run.py#L177): Comment

Code: `return`

> Left open: the panel polls the run, and closing it here would take the
> only thing watching the write it just let out.

## `_offered_in_the_panel`, [line 197](../../../../backend/scripts/one_whole_run.py#L197): Inline

Code: `except Exception:`

> the next doing is the retry

## `_offered_in_the_panel`, [line 207](../../../../backend/scripts/one_whole_run.py#L207): Comment

Code: `drawn = panel.locator('li[data-kind="nudge"][data-state="open"]').count() > 0`

> Two different claims, and this script printed the second while proving
> only the first. The worker MATCHING a shape and making an offer is a
> record in storage; the panel DRAWING it is a card in the DOM, and the two
> came apart for real: `show()` skipped its redraw whenever the thread was
> unchanged, and a rig offer writes nothing to the thread.

## `_offered_in_the_panel`, [line 213](../../../../backend/scripts/one_whole_run.py#L213): Comment

Code: `if accept:`

> The record behind the sentence. An offer that names the job and draws an
> empty box for every value is half an offer -- `valuesFrom` reads the live
> tail at the positions the served shape indexes, so an empty one means the
> two sides of the wire disagree about where a value is or about what a
> gesture put.

## `_offered_in_the_panel`, [line 218](../../../../backend/scripts/one_whole_run.py#L218): Comment

Code: `walk = worker.evaluate(`

> A value the operator has already typed, asked for again, is the
> defect this print exists to catch -- so the walk it matched is shown
> beside it rather than left to be guessed at.

## `_accepted_in_the_panel`, [line 229](../../../../backend/scripts/one_whole_run.py#L229): Comment

Code: `card = panel.locator('li[data-kind="nudge"][data-state="open"]').first`

> Off the CARD rather than off the stored record. The two can differ: the
> panel draws one nudge per tab and redraws on every poll, and a value the
> offer could not read is an input the card made, not a field the record
> promised. Asking the card what it is showing is also what an operator
> does.

## `_accepted_in_the_panel`, [line 233](../../../../backend/scripts/one_whole_run.py#L233): Comment

Code: `where = panel.evaluate(`

> The panel draws an OPEN nudge only for the tab it is sitting beside:
> `beside()` takes the active http tab of its own window, falling back
> to the most recently used one when the active tab is the panel
> itself. Which tab that lands on decides whether this card exists, so
> both ids are printed rather than guessed at from an empty ledger.

## `_watch`, [line 286](../../../../backend/scripts/one_whole_run.py#L286): Comment

Code: `if live and not tapped and any(s["verdict"] == "awaiting" for s in run["steps"]):`

> A live run parks on the write and waits for a person. This is the
> person -- until the job has EARNED the right to write unasked, at
> which point nothing parks and this never fires. That is the whole
> ladder, and the only way to see it is to run the same job until it
> climbs.

## `_watch`, [line 289](../../../../backend/scripts/one_whole_run.py#L289): Comment

Code: `page.wait_for_timeout(500)`

> Playwright's own loop has to keep turning or the page the run is
> driving never repaints.

## `_watch`, [line 293](../../../../backend/scripts/one_whole_run.py#L293): Comment

Code: `print(`

> `step`, not `order`: `_withheld` names the step under the key a person
> reading the panel sees.

## `_fired_by_the_worker`, [line 336](../../../../backend/scripts/one_whole_run.py#L336): Comment

Code: `page.wait_for_timeout(1000)`

> The page has to keep repainting or the run it is about to drive
> has nothing to drive.

## `_build_workflow`, [line 365](../../../../backend/scripts/one_whole_run.py#L365): Comment

Code: `typed = saved = None`

> The upload is a flush plus a round trip, so the evidence is not there the
> instant the click returns. Waited for rather than slept on: a fixed sleep
> is either a slow script or a flaky one, and there is no version of it
> that is neither.

## `_build_workflow`, [line 370](../../../../backend/scripts/one_whole_run.py#L370): Comment

Code: `gestures = [`

> This depot and this doing. A previous run of this script left its own
> gestures in the store on its own port, and taking the first match
> built a job whose origin no tab was open on -- which is exactly the
> refusal `run_workflow` gave: "no tab is open on 127.0.0.1:57647".
> Newest first, and only from the page this run is driving.

## `main`, [line 488](../../../../backend/scripts/one_whole_run.py#L488): Comment

Code: `args.live = True`

> Not a flag the mode respects -- a job a trigger starts is started
> live, always. Said here rather than silently overridden.

## `main`, [line 490](../../../../backend/scripts/one_whole_run.py#L490): Comment

Code: `args.runs = 1`

> A minute per run, and the point is the first one.

## `main`, [line 498](../../../../backend/scripts/one_whole_run.py#L498): Comment

Code: `server = ThreadingHTTPServer(("127.0.0.1", args.port), _Depot)`

> A fixed port, so every run of this script leaves evidence on one origin
> rather than scattering a job's worth across a new one each time.

## `main`, [line 536](../../../../backend/scripts/one_whole_run.py#L536): Comment

Code: `page.fill("#client", CLIENT_CODE)`

> The work, done by hand in a real browser.

## `main`, [line 543](../../../../backend/scripts/one_whole_run.py#L543): Comment

Code: `with ThreadPoolExecutor(max_workers=1) as pool:`

> In a thread of its own: Playwright's sync API runs inside its own
> event loop, and `asyncio.run` refuses to start a second one
> there. The thread gets a clean loop and the container's
> connections are opened and closed inside it.

## `main`, [line 554](../../../../backend/scripts/one_whole_run.py#L554): Comment

Code: `worst = _watch(`

> Everything the depot has been sent so far is the
> operator's own doing; anything after this line came from
> the run the offer started.

## `main`, [line 569](../../../../backend/scripts/one_whole_run.py#L569): Comment

Code: `by_hand = len(_Depot.writes)`

> The operator's own doing is the first write this depot saw.
> Anything after it came from a run.

## `main`, [line 575](../../../../backend/scripts/one_whole_run.py#L575): Comment

Code: `trigger = call(`

> The whole point of this mode: nothing here says
> "workflow-runs". A trigger names the job, the device and
> the values, and firing it is all this script does. What
> starts the run is `FireTrigger` -> `start_job_for` ->
> the dispatcher -> the API's own door, which is the path
> a schedule at 3am takes with nobody in the room.

## `main`, [line 583](../../../../backend/scripts/one_whole_run.py#L583): Comment

Code: `"authorized_by": True,`

> A job is a write by the honest reading, so it
> needs a name behind it; `auto_approve` is about
> the CARD, not about the run's own approval tap,
> which is still pressed in the panel below.
