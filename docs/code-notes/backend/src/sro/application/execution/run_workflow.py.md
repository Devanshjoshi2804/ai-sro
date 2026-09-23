# Notes for `backend/src/sro/application/execution/run_workflow.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/run_workflow.py`](../../../../../../../backend/src/sro/application/execution/run_workflow.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1): Docstring

> The loop. Look, plan, refuse-or-perform, verify, escalate once, stop.
>
> Ported from `run_workflow` in `new_agent_arch/src/rig/runner.py`. Between steps
> the stop button and the budget are checked; after every step the run is saved,
> so the page can watch it and so a crash mid-run leaves a record rather than a
> mystery.
>
> Nothing here drives a browser or calls a vendor: `Channel` sends the command the
> demonstration recorded, `Asker` plans it, and the repositories behind
> `UnitOfWork` are where the run is written down.
>
> The plan model plans; the rescue model rescues. A clean step never touches the
> expensive one, and only the steps that surprise us cost what surprises cost.
> Below both rungs, and only for a control neither of them could find, one rung
> that looks at the picture.
>
> The first execution of any workflow is dry. Reads and navigations go out; a
> step whose evidence carries a mutation is shown in full and withheld. That
> reading is `writes()`, the narrow one, and the gap is deliberate: a Save click
> the recorder heard no traffic from carries no mutation the evidence knows
> about, so a dry run SENDS it, against a real warehouse, unwithheld and
> unapproved. It is the only live write that escapes this gate, and it escapes
> because withholding every click nothing was heard from would leave a dry run
> performing almost none of the job. `may_write` below is the wider reading, and
> it guards the two places where being wrong costs more than that: the tap, and
> the rescue.
>
> A person presses through to live -- and until the job has earned it by verified
> effect, every live write that goes out stops and waits for a tap first.
>
> The stop button is `Stops`, shared with the backend's own runs -- there is one
> register of "somebody pressed stop" and no second one to build. It is checked
> between steps and never mid-command: a gesture already sent cannot be recalled
> from a warehouse. It is checked once more on the way out of an approval wait,
> because a release says only that the wait ended and a stop releases it too.

## module, [line 82](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L82): Note on the line above

Code: `KnownFields = Callable[[tuple[str, ...], str], Awaitable[Mapping[str, Mapping[str, object]`

> What the knowledge base says about these body keys, by key.
>
> A callable rather than `Retrieve` itself, for `SecretFor`'s reason: this module
> drives a run and does not learn what a vector store is. A deployment with an
> empty knowledge base passes nothing and every step says nothing, which is what
> happened before the claims were ever ingested -- 2,076 of them, and the store
> on QA held none until 2026-09-16.

## module, [line 84](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L84): Note on the line above

Code: `K_SAME_WRITE_WINDOW = timedelta(minutes=30)`

> How long one job's write stays claimed against a second run making it again.
>
> Not forever, which is right for a connector call keyed by run and step and
> wrong here: this key is the JOB, the step and the values, so a claim that never
> expired would mean a tenant could create one supplier with a given code, ever.
> Long enough to cover the case this exists for -- a rule that fires twice, two
> browsers taking one job, a card answered while another run of it is still
> going -- and short enough that "do that again" after lunch just works.

## module, [line 92](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L92): Note on the line above

Code: `K_CAP_EVERY = 10`

> How many legs a run may perform between two readings of the day's bill.
>
> The cap was read once, at the press, and never again -- `over_cap` appears
> nowhere in this module's history. One press on a 25-item list is about a
> hundred legs, and at this deployment's measured $0.0118 a step that is $1.20
> against a $5 day, spent after a check that saw $0. Ten is small enough that
> the overspend is a rounding error and large enough that a four-step job pays
> for no extra query at all: the day's bill is a sum over four tables.
>
> A new thing on the list is always a reading, whatever this says. That is where
> a run can still be stopped having done whole records rather than half of one.

## module, [line 94](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L94): Note on the line above

Code: `K_STEP_SLACK = 3`

> Attempts a run may make beyond its step count before it stops. A model
> looping on a form is money spent and a warehouse confused.

## module, [line 96](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L96): Note on the line above

Code: `K_STILL_COMING_S = 2.0`

> How long a step waits for a page that had not finished arriving.
>
> Long enough for a panel to draw, short enough that it costs less than the rung
> it replaces -- a model call about a half-drawn screen is seconds and money,
> and this is neither. One wait per step: a screen still coming after this is
> stuck, and waiting again turns a fault into a hang.

## module, [line 98](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L98): Note on the line above

Code: `GatherValues = Callable[[Sequence[str]], Awaitable[Gathered]]`

> Go and find the values this run was not given, or say which are missing.
>
> A callable rather than `GatherContext` itself, for `SecretFor`'s reason: this
> module drives a run and does not learn what a mailbox is. A deployment with no
> connector passes nothing, and a run with missing values refuses exactly as it
> always did.

## module, [line 100](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L100): Note on the line above

Code: `K_OPENINGS = 3`

> How many things one rung may open before it must answer the step.
>
> A screen is answered with as many clicks as it takes -- open the menu, see the
> item, click it -- and a rung that allowed exactly one was a rung that could not
> reach a control under a menu nobody demonstrated. Measured on the deployment
> across 2026-09-16 and 17: `Create a Customer Type` never once reached its form
> on the screen, and that was why.
>
> Three, because it is the depth a warehouse menu actually has and because a
> planner that only ever opens things has to run out rather than loop. Each
> costs a command and a picture; the step budget above bounds the rest.

## module, [line 102](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L102): Note on the line above

Code: `K_LOOKS = 4`

> Moves a step that changes nothing may make on its own, looking each time.
>
> The verifier has always known what went wrong. Measured on the deployment
> 2026-09-22, in its own words: "the search filter was applied to 'Create
> Shipment By' instead of 'Customer Type'", then "the Delete button is disabled
> because no customer type row has been selected". Both right, and neither
> acted on: the only rung that plans from a picture ran for a control the
> browser could not FIND, and each of these was a control found and clicked
> without the effect. So the run clicked the same wrong thing again, stopped,
> and a person rewrote a locator.
>
> A `look` rung is that picture, asked again with the verifier's own sentence,
> and allowed to act on the answer -- `pursue_goal`'s rules, applied to one
> step of a demonstrated job:
>
> - **A budget.** This many moves, then the step fails as it would have.
> - **Only where the step changes nothing.** A filter, a row, a tab. A step
>   whose evidence shows a write never gets one: Save, Delete and OK are done
>   the demonstrated way or not at all.
> - **What it did is read, not assumed.** A click at a point is on whatever is
>   there now, so after every move the browser is asked what the tab sent. A
>   mutating call stops the run where it is, as a write whose state is unknown.
> - **The model never decides it worked.** The verifier does, after each move.
>
> Not charged to the run's step budget, which is sized for one attempt per
> step and a few retries; this bounds itself.

## module, [line 104](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L104): Note on the line above

Code: `K_NOT_HERE = frozenset({"no_tab_for_system", "no_tab_for_origin"})`

> The two refusals that mean the browser is not where the step needs it.
>
> Not a broken job and not a wrong plan: the tab was closed, or the system signed
> the operator out and took the page with it. The same run would work a second
> later with a person signed in, so the run asks for one rather than failing --
> see `_let_in`.
>
> Both are sent by the extension after looking: `no_tab_for_system` is nothing
> open on the system at all, `no_tab_for_origin` is a tab that has been taken
> somewhere else, which is what an identity provider does on the way to its login
> page.

## module, [line 106](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L106): Note on the line above

Code: `K_MIGHT_BE_BEHIND = K_NOT_HERE | frozenset({"control_not_found"})`

> The refusals that can mean "the operator has already been through here".
>
> The two tab-level ones, and the control-level one: on the deployment
> 2026-09-23 every failed `Log in using Azure B2C SSO` run said
> `control_not_found` about a dialog and an SSO link somebody had already
> clicked. It stays a question rather than an answer -- a control can also be
> missing because the page moved under the job -- which is why `_ahead_of_here`
> decides it by reading where the browser actually is, and refuses to step over
> a write.

## module, [line 108](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L108): Note on the line above

Code: `K_NEVER_SENT = K_NOT_HERE | frozenset({"focus_not_permitted", "aborted"})`

> Refusals that mean the extension never reached the wire, so a write claimed
> for this step can be given back.
>
> `drivers._NO_BROWSER` is the same list with `timeout` in it, and the difference
> is the whole of this constant. A timeout is the one case where the send may
> well have landed -- it is the case `ToolCallRepository.remember` is written
> around -- so it keeps its claim. These four are the extension refusing BEFORE
> it acted: no tab on the system, no tab on the origin, focus it was not given,
> a run already aborted. None of them touched the warehouse.
>
> Found on the live deployment 2026-09-16: a run failed `no_tab_for_system`
> because the operator's Blue Yonder session had expired, and every later run of
> the same job with the same values was refused for half an hour on the grounds
> that the first one might have landed. It could not have.

## module, [line 110](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L110): Note on the line above

Code: `K_LEAVES = ("http.send", "navigate")`

> The two kinds whose target the model chooses, and so the only two ways a
> plan can leave the system the evidence was recorded on. For everything else the
> origin comes off the evidence.

## module, [line 273](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L273): Note on the line above

Code: `logger = logging.getLogger(__name__)`

> What the ladder did, said out loud.
>
> The mining side has logged its reasoning since it was written -- "1 step(s)
> repointed at the control the operator pressed" -- and the execution side had
> 2,251 lines and not one logger. What a run left behind was a truncated
> sentence on a step row, read back through the console, and that sentence is
> everything anybody has had to debug a run with.
>
> Measured over 2026-09-15 to 17: four separate faults in one job (a frame
> lookup that could not work, an unbounded viewport walk, an occluded window
> with no frame to photograph, a step recorded as refused that the page had
> taken) each arrived as the same few words. Every one of them took a
> deploy-and-rerun cycle to tell apart, and three were diagnosed wrongly first.
>
> So the ladder narrates: every rung it built, every rung it tried, what that
> rung planned, what the browser answered, and what it concluded. One line each,
> greppable by run and by step, and about the LADDER rather than about any job
> -- a rule that reads "Customer Type" anywhere is a rule that helps one
> workflow and lies about the rest.
>
> Nothing here carries a value, a body or a header. `_said` keeps a command to
> its kind and its shape, for the same reason `_result` keeps a reply to three
> facts: a log outlives the run and a warehouse's payload has no business in it.

## module, [line 275](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L275): Note on the line above

Code: `K_ACTS = {`

> What identifies a command by WHAT IT DOES, per kind.
>
> Not the whole payload. Two attempts at one step differ in fields that change
> nothing about the page -- `starts_on` is carried by the first command a run
> sends and by none after it -- so comparing payloads whole says two identical
> clicks are different commands.

## module, [line 292](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L292): Note on the line above

Code: `K_SAID = 120`

> How much of a plan's shape one line carries. A url and a method, not a body.

## `write_key`, [line 87](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L87): Docstring

> What makes two writes the same write.
>
> The job, the step within it, and the values the run was given -- not the
> run id, because two runs are exactly what this is about. The values are
> hashed rather than spelled: they are a customer's data and this key is
> stored, and a row in `tool_calls` is not a place to keep a supplier's name.

## `_Leg`, [line 114](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L114): Docstring

> One step of a run, and which thing on the list it is being done for.

## `_Leg`, [line 119](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L119): Note on the line above

Code: `rescue: bool = False`

> Whether this step belongs to ANOTHER job, spliced in to get through an
> interruption -- signing back in, today.
>
> Every per-step decision this run made up front is keyed on `step.order`,
> and another job's steps start at 0 like everyone else's. Measured on the
> deployment 2026-09-19, run `run_d6e7a78`: the sign-in job's first click was
> recorded `not_needed -- this step only opened the request, which was read
> before the run began`, because the job being run has a mail-opening step 0
> and the orders collided. The run then tried the SECOND click on a page the
> first had never touched.
>
> So a rescue leg is exempt from all of them: what was already read, what was
> collapsed into a call, what the operator did before the offer. None of
> those were decided about this job.
>
> It is NOT exempt from the write rules. Those are decided about the step in
> front of the run, and a spliced step is judged by its own evidence like any
> other -- see `sign_in_step` in `run_workflow`.

## `_itinerary`, [line 122](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L122): Docstring

> The steps this run will actually perform, in the order it will do them.
>
> A job that does one thing once answers with its own steps and nothing else
> -- and so does a repeating job handed no items, or one item, which is what
> keeps every other rule in this loop from having to learn about repeats.
>
> Where there is a list, the body is laid out once per thing on it, with that
> thing's values over the run's own. The item's values win: a run carrying a
> `facility` for the whole job and an item carrying its own is a run where
> the item is the more specific answer.
>
> Nothing is interleaved. The body is done for the first thing and then for
> the second, because that is the order an operator does them in and the
> order a half-finished run has to be readable in: three records made and two
> not, rather than five records each missing their last field.

## `_worth_asking`, [line 145](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L145): Docstring

> Whether the day's bill is worth a query before this leg.
>
> Never at the first: the press just asked, and a run refused on its own
> opening leg would be a 429 wearing a run's clothes.
>
> Otherwise at the start of each new thing on the list -- the one boundary
> where stopping leaves whole records rather than half of one -- and every
> `K_CAP_EVERY` legs for a job that is long without being a list.

## `_save`, [line 176](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L176): Docstring

> The run as it stands, totalled and committed.
>
> Totalling and saving are one call because they were never two: a run saved
> without its steps summed is a row whose bill disagrees with the steps
> underneath it, and the panel reads the row.

## `_the_way_back_in`, [line 192](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L192): Docstring

> The job that signs this run back in and its steps, where the tenant has
> shown them.
>
> A session expiring mid-flow is not an exception, it is a Tuesday: an
> operator works in a system all day and the system logs them out. Until this
> the run stopped and the request went nowhere until somebody noticed, which
> on a job started from a mailbox can be hours.
>
> **The way back in is mined evidence like anything else.** On the deployment
> the operator has clicked through `blueyonderalphaus.b2clogin.com` many
> times with the recorder on, and that is `Log in using Azure B2C SSO` --
> two clicks, both on that host. `signing_in.signs_in_at` is the lookup, by
> the host the browser actually sits on and never by a title.
>
> The steps come back as ordinary legs, spliced into the itinerary ahead of
> the step that met the page. Nothing here performs anything: they go through
> the same ladder, the same write gate and the same belts as any other step,
> and a password still comes out of the vault under `needs_secret` -- which
> means a tenant that has stored none gets the refusal that asks for one,
> rather than a run that guesses.
>
> **Not "this looks like a login" -- "the operator has been through this
> page".** `A_LOGIN` is `input[type=password]`, and the deployment's chooser
> has no password box at all: two SSO buttons, `Local WMS users` and
> `Kenco Management Services`. Measured 2026-09-19, run `run_db684040`, which
> landed there and read `signed_out: false`. A page recognised by its
> controls will always miss the next platform's idea of a login.
>
> What is not a guess is that the browser is somewhere this step's system is
> not, and that the tenant has a job found to sign in whose every gesture is
> on that page.
>
> So: the step failed, the browser is off its own system -- or the page did
> say it was asking -- and exactly one job of this tenant's that signs in is
> entirely there. A step that failed on the right screen goes nowhere near
> this.
>
> **Only jobs found to sign in.** "Entirely on that page" alone was the
> earlier rule, and it is also every ordinary job done on one host: a run
> that bounced to a page the tenant had done real work on would splice that
> work in and do it again. `Workflow.signs_in` is decided by the mining pass
> from what the operator did (`checks.signs_in`), so the lookup reads a fact
> rather than a shape.

## `_target_origin`, [line 227](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L227): Docstring

> The origin a planned command would actually reach. For `http.send` and
> `navigate` that is the url's own host, not the step's: those two are the
> only ways a plan can leave the system the evidence was recorded on.

## `_refused_origin`, [line 234](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L234): Docstring

> Whether a planned command's target is one this job's evidence forbids.
>
> Two sets, because a plan can reach somewhere two different ways. `standing`
> is where the operator actually was, and it is what may take the BROWSER
> somewhere. `replayable` adds the origins their pages' own requests named,
> which `http.send` needs: a step's demonstrated call can be to an API origin
> the page itself never was, and refusing those refuses the step its own
> write.
>
> The difference is not hypothetical. A page calls whoever it likes -- a
> Gmail page calls Google's own infrastructure -- so one set for both
> questions made `https://play.google.com` somewhere a planner could have
> navigated an operator's browser to, on the evidence of a telemetry beacon,
> for a job about warehouse customer types.
>
> Named no origin at all -- `about:blank`, `file:`, a bare path -- is a
> refusal for the two kinds that choose their own target, and not for the
> rest: there `None` means the recorder saw no url, which the extension
> resolves itself.
>
> Lifted out of the run loop because that is the only way anything can ask
> it. Inside, it was three lines nothing could reach without driving a whole
> run, and the sets it compares had just been merged into one.

## `_let_in`, [line 242](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L242): Docstring

> Ask for a browser that is signed in, and wait for somebody to say there
> is one. True when the step may go again.
>
> The one refusal this system can do something about by asking. A job whose
> plan is wrong needs a demonstration and a value nobody typed needs a
> mailbox, but a session that has aged out needs a person who is already
> sitting in front of the panel -- and until now the run told them their job
> had failed on a sentence about a tab.
>
> The write gate's own machinery, because it is the same question asked in
> the same place: the record says `awaiting`, the panel draws the button off
> that, and the tap releases the wait. Nothing new to learn, on either side.
>
> Not a remedy that signs anybody in. `Remedy.REFRESH_SESSION` exists for the
> browsers this system owns; this is the operator's own Chrome, where the
> only thing that may type a password is the person sitting at it.

## `_command_key`, [line 283](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L283): Docstring

> One command, as a string equal for two commands that do the same thing.
>
> For comparison and never for a log: `value` is what an operator typed, and
> on a sign-in step it is a password out of the vault. `_said` is the half
> that is safe to print.

## `_said`, [line 295](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L295): Docstring

> One command, in the few facts that identify it and none that reveal it.
>
> A url's path and nothing after it: the query holds session tokens and the
> fragment holds the screen, and neither belongs in a log that is kept.

## `_sign_in_here`, [line 322](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L322): Docstring

> Fill this system's login page with what the vault holds. True if it went.
>
> The credential is read here and put in one command. It is not returned, not
> logged, and not written to the record -- `record.sent` keeps what the
> extension was asked to DO and never what it was given, which is the same
> rule `without_secrets` keeps for every other step that types one.
>
> False for every reason there is: no vault, nothing stored, a browser that
> refused, a page that took neither box. Each of them leaves the step exactly
> as it was -- failed, and about to ask for a password -- because a sign-in
> that did not happen must not read as one that did.

## `_ask_for_the_password`, [line 366](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L366): Docstring

> The refusal, carrying the vault key this system's password belongs under.
>
> Only where there is nothing stored yet: a run that stopped at a login page
> with a credential already in the vault has a different problem -- the
> password is wrong, or the system wants a second factor -- and asking for it
> again would be this system's answer to everything.
>
> Left exactly as it was on every other path, including when the vault cannot
> be reached. A refusal that grew a password box because a vault timed out
> would have somebody typing their credential to fix an outage.

## `_what_earlier_steps_made`, [line 390](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L390): Docstring

> What the named steps created, keyed `step<order>.<field>`.
>
> Read off the run rather than held in a local, for `run.values`' reason: a
> resume re-reads the row and hands it back down, and anything kept only in
> this frame is a thing the second half of a run does not know.
>
> The LAST attempt of a step that ran more than once, which a repeating job
> does per item: the record this item is about is the one that step just
> made, not the one it made for the item before.
>
> Empty for a step that made nothing, which is most of them, and for one that
> has not run yet -- which the workflow checks refuse, and this must not
> depend on them having.

## `_a_write_went_out`, [line 400](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L400): Docstring

> The mutating call the last command made on this system, or "".
>
> Asked after a `look` move, which is a click at a point a model chose on a
> page that may have moved: what it landed on is known only by what the tab
> sent. A browser that cannot say is answered as if it had written -- the
> move stops the run rather than being trusted.

## `_refused_by_the_system`, [line 425](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L425): Docstring

> What the system itself refused during this step, if it refused anything.
>
> The last of the five, and the only one no amount of looking at a screen can
> answer: an operator who can reach a screen and not the action on it sees a
> page that looks exactly right and a control that does nothing. What says so
> is the status, and the calls the driven tab made are already asked for --
> `by_what_the_page_called` reads them to settle a step, but only for the
> step's own demonstrated endpoint and only where the evidence recorded a
> write. A 403 on anything else went unread.
>
> `401` and `403` told apart, because they are two different problems with
> two different fixes: nobody is signed in, and this account may not do this.
>
> Empty for everything else, including a browser that would not answer. A
> step that failed for an ordinary reason must not be told it was refused.

## `_said_what_is_there`, [line 456](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L456): Docstring

> The same verdict, saying what was on the screen instead.
>
> `control_not_found: no control matched` is true and says nothing about
> why, and the two things that most often put it there are both visible: a
> login page, and a dialog over the form. Neither renames the verdict -- a
> run that decided WHY a step failed would be a run guessing, and what this
> knows is only what is on the screen. The original reason is kept beside
> it, because the selector may be broken as well.
>
> Only for a failure. A step that held in front of a dialog is a step that
> held: plenty of screens confirm a save in one.

## `_ahead_of_here`, [line 491](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L491): Docstring

> The later step the browser is already standing on, or `None`.
>
> A step that cannot find what it wanted is asking one of two questions, and
> they have different answers: "nobody is signed in" is a thing to ask a
> person about, and "you did this part yourself" is a thing to step over.
> This answers the second by reading where the browser is and matching it
> against the screen each later step's own demonstrations agree on.
>
> `None` where nothing later matches, where the page cannot be read, or
> where getting there would step over a write -- a write stepped over is a
> record never made, in a run that reports it held.

## `_through_the_mailbox`, [line 544](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L544): Docstring

> Write the mail this step sends, put it in front of a person, and send it
> on their word -- every time, earned or not.
>
> A mail cannot be unsent and its words are a model's, so the `earned` rung
> that lets a job's warehouse writes go unasked does not reach it. A dry run
> writes it and stops there: `withheld`, with the words on the record.

## `_host_path`, [line 599](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L599): Docstring

> A url as host and path, the screen of a page whose route is not in its
> fragment -- a sign-in form, a chooser.

## `_where`, [line 604](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L604): Docstring

> Where the browser is, and no picture.
>
> For the step a status already settled. The record still says where the
> step left the browser -- that is what `after_url` is -- and asking for it
> costs a message rather than a screenshot, an upload and a vision call.

## `_look`, [line 627](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L627): Docstring

> Where the browser is and what is on the screen. A refused screenshot --
> `focus_not_permitted` -- is no picture, not a failure: the planner works
> from the url and the digest.

## `_too_long_for`, [line 676](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L676): Docstring

> Which of this step's parameters the box will not hold.
>
> The step says which parameters it fills and the run says what they are, so
> the name to ask about is arithmetic rather than a guess. Named rather than
> described, for the reason `run.needs` exists at all: a name parsed back out
> of an English sentence is a name that breaks the first time the sentence is
> reworded.

## `_result`, [line 684](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L684): Docstring

> What the extension answered -- not what it answered WITH.
>
> An `http.send` reply carries the response body and headers, and `verify`
> deliberately keeps those out of a prompt. A run record has no more business
> holding customer payload than a prompt does, and it holds it for longer, so
> only the three facts anything downstream reads are kept. `error_kind` stays
> its own field rather than `Reply.detail`, which concatenates kind and detail
> into prose nothing can branch on.

## `_saw_nothing`, [line 722](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L722): Docstring

> Whether the capture recorded this step's gesture and no traffic at all
> beside it. A call that never completed is not traffic the recorder saw --
> the same completion guard `origin_of` and `expected_statuses` already wear.
>
> Any completed call counts, including one `recorded_call` now discards as
> the page's own timer (`K_CAUSED_S`). That looks like an oversight and is
> not: the question here is not "did this gesture write", it is "was the
> recorder listening when this gesture happened" -- and a keep-alive captured
> beside a click is evidence about the recorder, not about the click. Where
> the capture was working and heard nothing from a Save, nothing silently
> wrote.
>
> It is the weaker half of that evidence, and worth naming: six steps across
> both real stores have completed traffic of which none is theirs -- acme's
> `Create a Work Operation` step 3 and its `Create a Carrier Cross Reference`
> step 2, and four in `new`. Widening `may_write` to cover them would park
> step 1 of every cross-system job on a person's approval, since "Read the
> details in an email" is a Gmail click beside Gmail's own chatter, and that
> is the friction the `earned` ladder exists to retire rather than to feed.

## `_not_given`, [line 733](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L733): Docstring

> The parameters this job declares that this run has no value for.
>
> Read off the JOB rather than off the steps: `Step.parameters` is what one
> step types, and a value typed by one step can be wanted by the body another
> sends. The job's own declaration is the whole set, in its own order.
>
> A blank counts as missing, for `typed_values`' reason: a parameter answered
> with an empty string is a parameter nobody answered.
>
> **Only the ones the PAGE says must be filled**, plus the older rule about
> routes.
>
> `required` is the star the form puts on its own label, carried in `names`
> since the day the job was demonstrated and read since 2026-09-22. It is a
> fact about the warehouse. `in_all` -- every doing compared reached this
> control -- is a fact about what the operator happened to do, and it made
> Manufacturer mandatory on this deployment because two demonstrations both
> filled it. Measured at 01:24 that night: an operator with no Manufacturer
> to give could not run the job at all, and dropped it.
>
> So a parameter is demanded only where the page asked for it. Everything
> else is offered and skipped -- see `_skippable`, which is what stops a run
> typing an empty value into a field nobody answered for.
>
> The failure modes are why unknown reads as optional. A required field
> treated as optional reaches Save and the form refuses, which the screen
> belt reports honestly and which teaches the job something. An optional
> field treated as required cannot run at all.
>
> `in_all` still speaks, for the case it was written for: a control a third
> doing never reached belongs to a route this run may not be taking, and is
> never demanded whatever its label says. Absent reads as `True`, as it
> always has -- those were stored before it existed.

## `_optional_of`, [line 745](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L745): Docstring

> This step's parameters that the page does not ask for.
>
> Matched on every name the control answers to, because the two ends write
> it differently. A step names the body key the form posts --
> `departmentNumber` -- and the job's parameter is named for the label a
> person reads, `Department`, with the page's own itemId
> `customertype-departmentNumber` beside it in `names`.
>
> Measured on the deployment 2026-09-22 at 09:32. The run was given the two
> values the form demands and reached "Focus and enter the Department code"
> anyway, because this lookup asked for `departmentNumber` among names that
> held `Department` and `customertype-departmentNumber` and found nothing.
> The step ran, typed nothing, and the screen belt failed it for an empty
> field -- correctly, about a field nobody had to fill.
>
> The itemId's last segment is an alias too, and only where it is unique:
> `customertype-departmentNumber` is what the page calls the control and
> `departmentNumber` is what the step calls it, and two parameters ending
> the same way are two this cannot tell apart.

## `_by_alias`, [line 753](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L753): Docstring

> Every name each of this job's parameters answers to, to the parameter.
>
> One control is written four ways across this system -- the label a person
> reads, the body key the form posts, the page's own itemId, and that
> itemId's last segment -- and every place that has to recognise one from
> another needs the same map. It was inline in `_optional_of`; it is named
> because `_under_every_name` is the second reader and a map built twice is
> a map that drifts.

## `_under_every_name`, [line 779](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L779): Docstring

> This run's values, filed again under every name their controls answer to.
>
> `value_for` asks a gesture what its control is called and looks the answer
> up among the run's values. The gesture says `filterComboBox`, which is the
> page's itemId; the run says `Customer Type`, which is what the job named
> the parameter and therefore what the person was asked for. Neither end is
> wrong and they never meet, so the lookup misses and the plan falls through
> to the value the DEMONSTRATION typed.
>
> Measured on the deployment 2026-09-22 at 11:07. `Delete a Customer Type`
> ran with `{"Customer Type": "NEX"}`, planned a type at the filter box, and
> the screen belt failed it: "The filter input field remains completely
> empty and the customer types grid has not been filtered." Sixteen runs of
> that job, and not one of them had ever put the operator's value in the box.
>
> The bridge already existed -- the job's parameter carries `names`, every
> name the control answered to when it was demonstrated -- and nothing on
> the planning path had ever been shown it. So it is applied once, to the
> run's values, before any step is planned: every reader downstream then
> finds the value under whichever name it happens to hold.
>
> The run's own row keeps the names the person was asked for. This is what
> the planner is handed, not what the run IS.

## `_skippable`, [line 790](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L790): Docstring

> Whether this step has nothing to do and nothing it must do.
>
> Every parameter it names is one the page does not ask for, and this run has
> a value for none of them. A step that names no parameter at all is never
> skippable: it clicks, navigates or saves, and skipping it would take the
> job apart.
>
> Deliberately ALL and not ANY. A step that types two fields, one answered
> and one not, still has work to do -- and skipping it would lose the answer
> somebody gave.

## `_fell_over`, [line 805](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L805): Docstring

> The run died. Whatever it was doing when it died is the step that
> failed, so the record says which one and why rather than stopping at
> `running` and leaving a reader to guess.

## `_withheld`, [line 816](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L816): Docstring

> The write a dry run did not send, in full: what a person reads before
> pressing through to live.

## `fail_orphans`, [line 834](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L834): Docstring

> Every run still `running` marked failed, and how many there were.
>
> Called once at startup, across tenants -- nobody is making the request. One
> worker owns every run, so a row that says `running` when the process starts
> is a run nobody is driving: the process that was driving it died mid-step.
> Left alone it would 409 its browser forever and keep the extension asking
> after it on every heartbeat.
>
> The sweep itself is the repository's, which is where the "on the last step,
> or on a new step when the run never reached one" rule lives. What is here
> is the commit: a startup that sweeps and does not commit has done nothing.

## `run_workflow._next_after`, [line 1023](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1023): Docstring

> The step the job does next, by its own order.

## `run_workflow._screen_of`, [line 1027](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1027): Docstring

> The screen this step's own demonstrations agree on.

## module, [line 28](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L28): Comment

Code: `already_done as effect_already_holds,`

> `already_done` is taken in this module: the steps an operator did
> themselves before the run picked it up. Two true meanings of one name,
> and mypy caught the collision the moment the import landed.

## `_the_way_back_in`, [line 203](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L203): Comment

Code: `known = [job for job in await uow.workflows.known(tenant_id) if job.signs_in]`

> Only the jobs that sign in are candidates, so only their evidence is read.

## `_the_way_back_in`, [line 204](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L204): Comment

Code: `cited = sorted({one for job in known for step in job.steps for one in step.cites})`

> Every candidate's evidence, in one read. The lookup is about WHERE the
> gestures happened, so it cannot be made without them -- and this run has
> loaded only its own job's cites. One query, and only ever on the failure
> that met a sign-in page.

## `_the_way_back_in`, [line 216](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L216): Comment

Code: `by_id.update({one: seen[one] for step in job.steps for one in step.cites if one in seen})`

> And into the run's own map, because everything downstream -- planning,
> the locator ladder, the belts -- reads a step's evidence from there.

## `_let_in`, [line 253](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L253): Comment

Code: `approvals.register(run.id)`

> Registered before the save, for the write gate's reason: the save is what
> puts this in front of a person, and a tap that lands before the wait
> starts must find an event to set rather than a 409.

## `_let_in`, [line 267](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L267): Comment

Code: `record.verdict, record.verdict_by = "skipped", "none"`

> Back to what an in-flight step already says, for the reason the write
> gate gives: a row left `awaiting` through the send is a row that lies for
> as long as the step takes, and an operator who tapped Approve watches the
> same paused card redraw with the same button.

## `_sign_in_here`, [line 351](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L351): Comment

Code: `steps = (answered.result or {}).get("did")`

> What it DID, which is the half worth keeping. A run record read by a
> person, by the panel and by the model asked to rescue the next step, and
> none of those has any business holding a credential.

## `_said_what_is_there`, [line 472](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L472): Comment

Code: `if refused:`

> What the system itself said, before anything read off the screen: a 403
> is the whole answer, and the screen above it looks entirely normal.

## `_said_what_is_there`, [line 465](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L465): Comment

Code: `return replace(`

> What it SAID, first and in full. A person reading this is looking for
> the sentence the warehouse put on the screen, and every word this
> wraps around it is a word between them and it.

## `_said_what_is_there`, [line 479](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L479): Comment

Code: `where = look.url or look.elsewhere`

> And the plainest of the three: the browser is somewhere else.
>
> Not a login, no dialog, and a control nothing matched -- because the
> screen this step was demonstrated on is not the screen in front of it.
> A redirect, a half-finished navigation, an operator who clicked away.
> Seen on the deployment 2026-09-18: a run reported a missing tab item
> while the browser sat on the Warehouse configuration screen, after the
> operator had signed back in and landed somewhere else.
>
> `same_screen` and not string equality, which is the comparison this
> already makes everywhere else: a query string and a fragment's
> particulars are not a different screen.
> `elsewhere` when the browser is not on this system at all, which is what
> every interruption looks like: the login host, a consent screen, an error
> page a proxy served. Reading only `url` left the run saying nothing about
> any of them.

## `_said_what_is_there`, [line 467](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L467): Comment

Code: `reason=(`

> The urls themselves. `screen_of` answers what a set of VISITS
> agree on, which is not this question -- and a person reading a
> step record wants the address they can go and look at.

## `_ahead_of_here`, [line 505](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L505): Comment

Code: `logger.info(`

> Said whichever way it goes. Nothing else records what the browser
> answered here -- a `ui.url` that succeeds leaves no trace -- and "why did
> it not step over" was unanswerable from the record on 2026-09-23.

## `_ahead_of_here`, [line 519](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L519): Comment

Code: `same = bool(screen) and (`

> `same_screen` and not `page_of`: a warehouse portal keeps its route
> in the fragment, so `page_of` calls the Warehouse screen and the
> Customer Types screen the same page -- and this would step over the
> navigation between them.
>
> Except across systems. A sign-in page reached by a redirect carries
> the fragment of the page the operator LEFT: `wfl_5873ec01`'s SSO
> chooser was recorded as `…/oauth2/v2.0/authorize?…#wm.config/
> wm.config.partners.customers.types////`, the portal screen whose
> session expired. That fragment is not the chooser's route, and
> comparing it made the chooser the operator was standing on a
> different screen from the chooser that was recorded -- `run_18c9f4ef`,
> 2026-09-23, two more tabs and nothing done. Within one system the
> full route still decides.

## `_ahead_of_here`, [line 534](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L534): Comment

Code: `if any(`

> Nor over a step that puts a value in. A page that looks right is not
> a field that holds it: Keycloak serves its one login form at two
> addresses, `…/openid-connect/auth` and, once posted, `…/login-actions/
> authenticate`, and `wfl_5873ec01` recorded its Sign In on the second.
> `run_6f30e995`, 2026-09-23, stood on that address after an earlier
> failed run, matched Sign In, stepped over the username and the
> password, and pressed Sign In on an empty form. Only while the browser
> is still on that value's host: one that has left it -- the portal,
> after a sign-in somebody did themselves -- is past it.

## `_look`, [line 658](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L658): Comment

Code: `refused = shot.detail if not shot.ok else ""`

> Why there is no picture, kept rather than dropped. A browser that refused
> the screen says so in its own words, and a picture that arrived with no
> viewport beside it is a different fault again -- both used to reach the
> step record as the same four words.

## `_look`, [line 668](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L668): Comment

Code: `elsewhere=str(where.result.get("elsewhere") or "") if where.ok else "",`

> Read off the same answer the url came in. Both readers carry it or
> only route steps would ever notice a login page, and a route step is
> the one kind that already knows where it is.

## `_result`, [line 692](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L692): Comment

Code: `short = reply.result.get("short")`

> What the box would not take, where the browser said so.
>
> Lengths and a flag, never the value: this is a run record and a log. The
> browser truncates silently and BEFORE the request, so a field that stops
> at 28 characters puts 28 into the body, the read-back returns 28, and
> the photograph shows 28 -- every belt agreeing, because every one of them
> compares the record to itself. This is the only fact that disagrees.

## `_result`, [line 700](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L700): Comment

Code: `shown["wrote"] = True`

> The one fact the register of verified writes needs and cannot
> recompute: SQL cannot ask `writes()`, and the evidence a later reader
> would have to ask it about may have been re-mined by then.

## `_result`, [line 703](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L703): Comment

Code: `tried = reply.result.get("tried")`

> What was tried, and where it looked.
>
> `error_kind` alone says a control was not found and nothing about
> which locators were attempted or which frames answered the probe --
> and those are the whole diagnosis. The same step refused twice on the
> deployment (KKYT 2026-09-20, SMK1 2026-09-21) and reading the second
> one took five rounds of pasting into a console with the dialog held
> open by hand, because the browser knew all of this at the time and
> nothing kept it.
>
> This system's own selectors and frame ids. Not `error_detail`, which
> carries near-miss control NAMES read off the page -- a run record has
> no more business holding those than a prompt does, which is the rule
> this function opens by stating.

## `_by_alias`, [line 773](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L773): Comment

Code: `for tail, count in seen_tail.items():`

> A tail two parameters share names neither of them.

## `_skippable`, [line 794](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L794): Comment

Code: `declared = [`

> Never where the run has nothing at all to go on.
>
> The rule this skipping rests on is "the page does not ask for this
> field", and the page is talking about its own form. A filter box is not
> a form field: nothing marks it required, and on `Delete a Customer Type`
> it is the only parameter the job has and the only thing that says WHICH
> record is deleted. Skipping it leaves the run to delete whatever row
> happens to be selected.
>
> Written down 2026-09-22, before it could happen: a card pressed with no
> value would have skipped the step that picks the record and gone on to
> Delete and OK.
>
> So: a run holding a value for NONE of the job's parameters is not
> performing a parameterised job, it is replaying a recording against
> whatever is in front of it, and nothing may be skipped on the strength
> of a form's own markings. A run holding some -- the create, with its two
> required fields given and its two optional ones not -- skips exactly as
> it did.

## `_withheld`, [line 822](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L822): Comment

Code: `shown.update({key: planned.payload.get(key) for key in ("method", "url", "body")})`

> The plan IS the write here, and it is not always the write the
> demonstration made. `write_plan_for` re-aims the recorded body at
> this run's values, so reading the recorded bytes would show a person
> the code the operator typed on the day and have them press through
> into a run that sends a different one. A dry run whose card cannot
> be trusted to name what will go out is worse than no dry run.

## `_withheld`, [line 824](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L824): Comment

Code: `call = recorded_call(step, by_id)`

> A click, withheld because the evidence behind it writes. There is no
> planned call to show, so the demonstration's is the only answer.

## `run_workflow`, [line 868](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L868): Comment

Code: `saved = await uow.workflow_runs.get(tenant_id, run_id) if run_id else None`

> A run the caller already claimed. `POST /v1/runs` writes the `running` row
> itself, before it answers, so a second press for the same browser is
> refused rather than landing in the window between `create_task` and this
> task's first slice. That row is then the authority for what was asked
> for -- read back here rather than rebuilt from the arguments, so there is
> one answer to "what is this run doing" and not two that can drift.

## `run_workflow`, [line 869](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L869): Comment

Code: `if saved is not None and (`

> The two ways in have to agree. Reading the row's `device_id` back when it
> disagrees with the argument would put a hand on a browser nobody asked
> about, and its `workflow_id` would perform a different job under this
> run's id -- both silent, and neither a thing to guess between. Refused
> before anything is sent and before the row is touched: a run whose
> arguments do not match it is not this caller's run to mark failed.
>
> And `outcome`, which the rig does not check and we do -- a deliberate
> divergence, not a port regression. If the row is the authority for what
> this run is doing, `outcome` is the one field that says whether there is
> anything left to do: a row already `held`, `failed` or `aborted` picked
> up here plans step zero, pays for the model call, has the send blocked
> further down, saves the step `skipped` and then breaks out carrying the
> stale outcome plus a step that never happened. The rig gets away with it
> because nothing re-presses a finished run; phase 4's route will, and the
> cheapest place to say no is the same refusal that already reads the row.
>
> And `from_step`, the fourth thing the press asked for: how many steps the
> operator did themselves before the offer. A re-press that moves it
> finishes a different job under this run's id -- steps the operator never
> performed recorded `done_by_operator` and skipped, or steps they did
> perform redone against a live warehouse. Silent, because the other three
> checks all pass; and the only one of the four the row could not answer
> until it had a column.

## `run_workflow`, [line 880](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L880): Comment

Code: `attribute(`

> Every line the rest of this run writes says which run it was, on whose
> tenant, in whose browser. `attribute` rather than a block because the
> work to attribute is the whole of what follows; see its own docstring for
> why that is sound inside a task.

## `run_workflow`, [line 897](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L897): Comment

Code: `from_step=from_step,`

> On the row, not just in this frame: it is what the check above
> compares a re-press against, and a row that does not carry it would
> refuse every resume as a disagreement with zero.

## `run_workflow`, [line 901](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L901): Comment

Code: `watched = run.watched`

> And which of the two ways this run does the job, off the ROW like the
> rest: a re-press that disagreed with the row about whether somebody is
> watching would be a run that fills the form for one caller and posts for
> the next.

## `run_workflow`, [line 904](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L904): Comment

Code: `if gather_values is not None and (short := _not_given(workflow, values)):`

> The values nobody typed, found before anything is planned.
>
> A press carries what the person filled in. A job fired by a rule, or one
> whose request arrived as a mail, has a parameter and no value -- and
> until now that was the end of it. The live failure that named this was
> step 1 of `Create a Customer Type` refusing with "the open email is for
> customer type GPDP rather than the requested ZQ41": the mailbox held a
> request and the run had no way to read it.
>
> Before the loop and once, not per step: a value is a fact about the run,
> and a gather per step would read the same mailbox repeatedly and could
> answer differently each time.
>
> What it finds is merged UNDER what the run was given. A person who typed
> a value has said what they want and a mailbox does not overrule them --
> the gather is only asked about what is missing, and this ordering says
> the same thing a second time so the two cannot disagree.

## `run_workflow`, [line 905](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L905): Comment

Code: `run.doing = "looking in your mail for " + ", ".join(short)`

> Said on the row before it starts, because this is the one thing a run
> does with no step to show for it -- and a card reading "Step 0" for
> three and a half minutes while the mailbox is read is a run somebody
> reasonably believes has hung.

## `run_workflow`, [line 910](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L910): Comment

Code: `run.values = dict(values)`

> On the ROW and not only in this frame. `perform` re-reads the row and
> hands its values back down, so a gather kept in a local is a gather
> every resume does again -- against a mailbox that may answer
> differently the second time -- and a console showing a run that typed
> GPP into a form would show it running with no values at all.

## `run_workflow`, [line 915](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L915): Comment

Code: `if got.unasked:`

> What the mail asked for that this job cannot take.
>
> A job's parameters are what two doings proved VARY; the form has far
> more fields than that. So a mail saying "code GV3, description X,
> Department Inbound" is a perfectly reasonable request, and the run
> makes a record with no Department in it -- silently, because `keep`
> drops a name the job has no parameter for and said nothing about it.
>
> The dropping is right. The silence is the shape of every fault worth
> having here: a request that asked for three things, a record that
> holds two, and nothing anywhere naming the one that went missing.

## `run_workflow`, [line 924](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L924): Comment

Code: `if still := _not_given(workflow, values):`

> A value nobody typed and nobody could find is not a value.
>
> The door lets a run start with a parameter unanswered ONLY because
> something can go and look for it, and until this a look that came
> back with nothing was read as permission to carry on. Measured on the
> deployment 2026-09-16: the gather lost a round to a 5xx, came back
> empty, and the run went on to press Save on a form somebody else had
> half filled an hour earlier.
>
> Here rather than at the door, because the door cannot know what the
> looking will find; and here rather than at the step, because the
> answer is the same for every step and a person reading the row should
> find one sentence rather than a verdict per step. Only on this path:
> a deployment with no gather was refused at the door, as it always
> was.

## `run_workflow`, [line 926](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L926): Comment

Code: `run.needs = list(still)`

> And WHICH ones, machine-readably, beside the sentence. The
> sentence is for the person reading the row; these are what the
> question in their conversation is built from, one at a time, and
> a name parsed back out of an English sentence is a name that
> breaks the first time the sentence is reworded.

## `run_workflow`, [line 946](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L946): Comment

Code: `verified_writes = (*verified_writes, *demonstrated_writes(workflow, by_id))`

> And what this job's own demonstrations proved, for this run alone. See
> `demonstrated_writes`: a job that cannot yet finish by the interface can
> never have a run of ours watch its write succeed, however many times the
> operator's own recording shows the server answering it.

## `run_workflow`, [line 947](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L947): Comment

Code: `learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}`

> What earlier runs found out about this job's steps, by step order. Read
> once: it is a handful of rows and every step of the loop would otherwise
> ask for the same table.

## `run_workflow`, [line 948](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L948): Comment

Code: `taught = await learn_from_the_rescue(uow, tenant_id, workflow, by_id)`

> And what the operator taught it by hand since the last run failed, which
> is a lesson nothing else in this system can learn: the ladder heals a
> control that moved, and a step that fails the same way every time on a
> control that never moved is repaired by the person who does it
> themselves. See `sro.domain.execution.rescued`.

## `run_workflow`, [line 951](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L951): Comment

Code: `observed = seen_values(workflow)`

> Two sets, because they answer two questions. `standing` is where the
> operator actually was and is where a plan may SEND the browser;
> `replayable` adds the origins their page's own requests named, which is
> what `http.send` replays a demonstrated call to.

## `run_workflow`, [line 952](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L952): Comment

Code: `placeable = await declared_keys(`

> Which body key each value this run holds is posted as, where the job
> itself declares no parameter for it.
>
> A job's parameters are what two doings proved VARY, and the form posts
> far more than that -- so a request naming one more had nowhere to put it.
> `write_plan_for` fills the slot where the dictionary names it and the
> record can be made to prove it landed; this is where that join is read,
> once per run rather than once per step.
>
> Only the names the job does NOT declare. A parameter it does declare is
> bound from the evidence, which is stronger than a declaration and is
> `_assigned`'s own rule.

## `run_workflow`, [line 961](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L961): Comment

Code: `if len(run.items) > K_MOST_ITEMS:`

> A list longer than one press can mean.
>
> Refused before anything is sent and before the first record is made: an
> operator pressing yes on "add these" has read a mail with a handful of
> rows in it, and two hundred is either a mistake or a decision they have
> not made. Whoever wants the two hundred can say so twice.

## `run_workflow`, [line 980](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L980): Comment

Code: `collapsed: set[int] = set()`

> The steps that exist only to put a form on the screen, where the write
> that form was for is going out as a call instead.
>
> Measured on the deployment's own row: of the six steps of `Create a
> Customer Type`, only step 6 changes warehouse state. Steps 4 and 5 make
> no network call at all -- they are keystrokes into a form that step 6
> posts -- and step 2's thirty-four GETs are the screen loading. Replay the
> write and there is nothing left for the other five to do, so doing them
> is five plans, five commands and four screenshots spent to arrive where
> the call was going to be sent from anyway.
>
> Decided here and once, because a scaffolding step comes BEFORE the write
> it scaffolds: by the time the run reaches step 6 it has already performed
> the five it did not need. Only the replay the EVIDENCE decides can be
> known this early -- a model's `http.send` is chosen at the step, long
> after step 2 has been done -- which is the second thing the deterministic
> rung buys.
>
> Safe against a job whose values move per item: `write_plan_for` refuses
> on the shape of the values, never on the values themselves (a slot is
> claimed by comparing the DEMONSTRATED body against `seen_values`), so
> every leg of a repeat answers this the same way.
> Nothing is collapsed for a run somebody is watching.
>
> The two ways to do a job are not interchangeable and the choice is the
> RUN's, not the step's: replaying the call is fast, deterministic and
> invisible, and performing it is the one a person can see happen. A run
> that skipped the typing because it was going to post, and then pressed
> Save as if it had typed, is what deciding per step looks like.
>
> So a watched run performs every step: the fields fill, the button is
> pressed, and somebody standing at the screen watches their job being
> done. It costs a reading per step and the determinism of the replay, and
> that is the trade being made on purpose rather than by accident.

## `run_workflow`, [line 981](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L981): Comment

Code: `in_reserve: set[int] = set()`

> What an unwatched run would have collapsed, held in reserve for a watched
> one. See `_the_screen_gave_up` at the foot of the step loop: a run
> somebody is watching performs the form-filling steps, and when the page
> will not take one of them the job is not over -- the write those steps
> were filling in is still a call this run knows how to make.

## `run_workflow`, [line 997](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L997): Comment

Code: `already_read: set[int] = {`

> The step that opens the mail, once the mail has been read.
>
> A job that starts in somebody's mailbox cites the gestures of them
> finding that afternoon's message, so the plan clicks a link whose text is
> that message: "a customer type :- GGD, description :- leaning new SRO
> type 01". A job is asked for by a NEW mail every time. That link is not
> on the screen and will not be again, and on 2026-09-16 a watched run
> stopped at step 0 holding it -- `not_actionable: the page did not answer`
> -- for a job whose values this same run had already read out of the right
> mail, server-side, a second earlier.
>
> So it is not performed, in EITHER mode. This is not the collapse above:
> that one is about a form whose write is going out as a call, and it is
> off for a watched run on purpose. This is a step whose whole content was
> done before the run began, and performing it is impossible rather than
> merely unnecessary. A person watching wants to see the form fill; nobody
> wants to watch their own mailbox be clicked.
>
> Whatever read it, and this was got wrong once.
>
> The first version of this rule asked whether the GATHER had read the mail
> -- `run.gathered` -- and on 2026-09-16 at 21:11 a press failed anyway:
> the panel's own look had already pulled the code out of the message and
> the press carried it, so the run held every value it needed and had
> gathered nothing. `gathered` says which of the two things read the mail,
> and this step does not care. By the time a run exists the request has
> been read -- by the gather, by a look, or by the person who typed the
> values into the card -- because a run cannot start without its values.
>
> There is no state of this system in which opening that mail achieves
> anything: the link the plan clicks names the message from the recording,
> and that message will not be on the screen again.

## `run_workflow`, [line 1000](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1000): Comment

Code: `mail_sends: set[int] = (`

> A step that sends a mail is sent through the mailbox's API, never clicked:
> the composer is a page a click cannot carry a recipient, a subject and a
> body into, and nothing on it can say the mail went. Only where the
> connector can write -- `MAILBOXES` -- and only with a hand to do it.

## `run_workflow`, [line 1014](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1014): Comment

Code: `claimed_here: set[str] = set()`

> The steps the operator already did cost nothing and are not attempted, so
> they buy no slack either: the budget is what is left to perform.
> Which writes this run has claimed the right to make, so a rescue of a
> refused write is not stopped by its own first attempt.
>
> Write keys, not step numbers. A repeating job performs one step.order
> once per thing on its list, so a set of step numbers claimed the first
> item and let every other one past `tool_calls.remember` entirely -- two
> runs whose lists overlap then created the overlap twice, which is the
> accident the ledger exists to stop. The key already carries the values,
> so a retry of the same leg still finds its own claim and is still let
> through.

## `run_workflow`, [line 1015](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1015): Comment

Code: `approved_for_the_list: set[int] = set()`

> Which steps a person has already approved for this list. One tap answers
> for every thing on it: they read the rows and pressed once.

## `run_workflow`, [line 1016](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1016): Comment

Code: `proved_the_first = False`

> Whether the person has seen the first thing done and said to do the rest.

## `run_workflow`, [line 1021](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1021): Comment

Code: `sent_nothing_yet = True`

> Whether any command has gone out yet, which is what makes the next one
> the run's first: `starts_on` belongs to that one alone.

## `run_workflow._next_after`, [line 1023](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1023): Comment

Code: `def _next_after(steps: list[Step], step: Step) -> Step | None:`

> The page this run begins on, which is the page of the step it begins at
> -- not the job's first page. The extension opens a tab at `starts_on`
> when the operator's own tab is elsewhere, and aiming a run that starts at
> step k there would abandon the progress the offer was made on.
>
> Not `page_of` the way `Shape.starts_on` is narrowed: that one is compared
> and this one is NAVIGATED to, and no component of a url is particular or
> general on its face. A warehouse addresses its screens BY fragment --
> `…/portal?siteId=SG#wm.config/wm.config.partners.customers.types////` --
> while Gmail puts a message id in the same place, so dropping either
> component by rule lands a run on the portal root and plans every step
> against the wrong page.
>
> So it is asked of the demonstrations instead. Every gesture this step
> cites is a doing of it, and `screen_of` keeps what they agree on: what
> varies between two doings of one step is the visit, and what does not is
> the screen. No rule about queries or fragments is needed, and none is
> right -- the evidence says which parts moved.
>
> With one doing it returns that url whole, which is the honest answer:
> nothing has said which half of it was the job. It sharpens as the same
> work is demonstrated again, with no re-mine and no new field.
>
> `primary_gesture` stays the anchor, so the origin and the choice of which
> gesture speaks first are exactly what they were. What changes is that the
> others are now allowed to disagree with it.
>
> Found the bug it fixes on this deployment's own row: step 2 of `Create a
> Customer Type` is "Navigate to the Customer Types screen", and its two
> cited gestures sit on `…inbound.receiving.optimaldoorassignment` and
> `…warehouse.warehouse` -- the screens the operator happened to be on when
> they reached for the menu, neither of them this step's. A run resuming
> there opened whichever one `primary_gesture` picked. They agree on
> `/portal?siteId=SG`, which is where that step actually starts.
>
> The first step the run will PERFORM, not the first one it has. A job
> whose write goes out as a call collapses the steps that only opened the
> form for it, and those are the ones at the front -- `Create a Customer
> Type` collapses "Open an email" and "Navigate to the Customer Types
> screen", so taking `starts_on` off the first step names the operator's
> mail for a run whose only command is a warehouse call. `opensFor` in
> `commands.js` drops a `starts_on` whose origin is not the command's, so
> the browser is never driven into the wrong system -- but the tab is then
> never opened either, and a run whose operator has no warehouse tab open
> fails instead of opening one.

## `run_workflow`, [line 1042](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1042): Comment

Code: `step_here = next(`

> And `already_read` beside `collapsed`, for the same reason: the page this
> run opens at is taken from the first step it will actually perform. A run
> whose mail step is skipped would otherwise open the browser at the
> mailbox and then send its first command to the warehouse.

## `run_workflow`, [line 1052](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1052): Comment

Code: `in_flight: RunStep | None = None`

> The step being worked on, so a browser that goes away mid-step fails THAT
> step -- with the tokens its plan already cost, and its own order -- rather
> than a fabricated one whose order can collide on (run_id, ord).

## `run_workflow`, [line 1053](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1053): Comment

Code: `itinerary = list(itinerary)`

> A LIST walked by index rather than an iterator, because a run that meets
> a sign-in page splices the way back in ahead of the step that met it --
> see `_the_way_back_in`. Everything else about the walk is unchanged.

## `run_workflow`, [line 1055](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1055): Comment

Code: `joined_at: int | None = None`

> The step this run joined the job at, where a step found its page gone
> because the operator had already been through it. See `_ahead_of_here`.

## `run_workflow`, [line 983](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L983): Comment

Code: `if (`

> Behind the page the browser is on. Recorded and never sent: the
> job is being joined where it stands rather than replayed into a
> browser that has left those pages.

## `run_workflow`, [line 1084](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1084): Comment

Code: `if step.uses:`

> What the steps this one NAMES have made, under their own names.
>
> `Step.uses` is CrewAI's `Task.context` and its argument: a step
> that names the prior steps it depends on can be read, where an
> implicit shared map means reading the whole job and guessing. The
> binding is the other half of saying it.
>
> `step<order>.<field>`, never merged flat: a create answering
> `{"id": ...}` and a job with a parameter called `id` would
> otherwise silently be the same value.
>
> Under the run's own values, not over them: something a person
> supplied or a mail said is what they asked for, and a job whose
> wiring quietly replaced it would be doing something nobody could
> see in the request.

## `run_workflow`, [line 927](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L927): Comment

Code: `run.steps.append(`

> The operator did this one before the offer was made. Recorded
> so the run reads whole, cited so a reviewer can see what it
> was, and never sent: the job is being finished, not redone.
>
> `leg.item in (None, 0)`, because what they did, they did
> once. A repeating job performs this same step.order again for
> every other thing on the list, and skipping those was the
> run filling the form for the first item and then pressing
> Save for the second and the third against whatever was left
> on the screen -- reported `held`, with the fill steps marked
> "performed by the operator" for items nobody had touched.

## `run_workflow`, [line 1107](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1107): Comment

Code: `if _worth_asking(position, leg, itinerary) and (`

> The day's bill, again. Read at the press and then never, a run
> that passed the check at $0 could spend the rest of the tenant's
> day inside one press -- and the longer the list, the more it
> spends before anything asks. Asked at the start of each new thing
> on the list, and otherwise every `K_CAP_EVERY` legs.

## `run_workflow`, [line 1124](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1124): Comment

Code: `if not leg.rescue and _skippable(step, workflow, leg.values):`

> A step that exists only to fill a field nobody has to fill, with
> nothing to put in it.
>
> `_not_given` stopped demanding these on 2026-09-22, which is what
> lets the run start -- and starting is not enough on its own. The
> step is still in the job, and performing it types an empty string
> into the control, or worse the literal word somebody offered
> instead of a value. Measured that night: an operator with no
> Department answered "nothing", and the form came back holding
> NOTHING.
>
> Recorded rather than dropped, for the reason the skip below
> already gives: a job that silently performed six of its nine
> steps reads as a job that lost three.

## `run_workflow`, [line 963](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L963): Comment

Code: `run.steps.append(`

> Recorded rather than dropped: the per-step audit trail is
> what a reviewer reads, and a job that silently performed four
> of its six steps would read as a job that lost two.

## `run_workflow`, [line 1196](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1196): Comment

Code: `sign_in_step = (leg.rescue or workflow.signs_in) and not does_business(step, by_id)`

> A step of a job that signs in, whose own evidence wrote nothing
> back to its system, is not a write -- for `mutates` and for
> `may_write` both, and for every leg alike.
>
> There used to be a leg exemption here instead: `may_write` was
> false for any spliced leg, on the reasoning that a sign-in click
> cannot create a warehouse record. True of a sign-in, but the leg
> said nothing about whether it WAS one -- the way back in was any
> job entirely on the page the browser sat on, and a spliced leg
> that saved a record went out unapproved and was retried as if
> nothing could have landed.
>
> So the classification moved to the step. `rescue` stands for
> "found to sign in" because `signs_in_at` only ever returns such
> a job. The credential post a sign-in makes is recorded as a
> mutation (`writes` reads the method), and `does_business` is what
> tells it from work: a sign-in posts and is sent somewhere else, a
> write comes back 2xx on the page it came from. A step that did
> that is a write whatever job it is in.
>
> Measured on the deployment 2026-09-19, run `run_d6e7a78`: the SSO
> button click, judged as a write, ended the run with "state
> unknown after a write; not retried", and the result card then
> offered no "Try it again" either.

## `run_workflow`, [line 1198](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1198): Comment

Code: `writes_ahead = any(`

> Whether this job's own write is still ahead of this step.
>
> A click the recorder heard nothing from is a possible write --
> a Save whose call was missed would otherwise be retried into a
> second record. That is right for the step a job WRITES at, and
> wrong for every step before it: opening a dropdown, pressing Add,
> filling a field. The demonstration says which is which, because
> it recorded the call on a later step.
>
> Measured on the deployment 2026-09-19, run `run_74a9a812`: the
> operator pressed Undo, the delete started, and its first step --
> "Opens the filter dropdown" -- failed `state unknown after a
> write; not retried`. One dropdown click ended the run, took its
> ladder away and suppressed the retry button, on a job whose
> DELETE was four steps further on.

## `run_workflow`, [line 1202](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1202): Comment

Code: `if live and leg.item == 1 and not proved_the_first:`

> The first thing is the proof.
>
> A tap on "add these twenty" is one decision made before anything
> happened. It is a good decision about a job that does what the
> person thinks it does -- and the way to find out is to do one and
> show them. A job read out of a sentence can be the wrong job: an
> operator asking for a warehouse equipment type was once answered
> with a customer type, and the same guess against a list is a list
> of wrong records.
>
> So the run stops once, before the second thing, with the first
> one's result in front of them. Two taps for a list of any length,
> and the second one is informed by something real.
>
> Asked even of a job that has earned the right to write unasked,
> which is the one place this system does not let earning through.
> Earning says the job's writes have been watched to hold over
> runs; it says nothing about whether this is the right job for
> what somebody just asked for, and that is the question a list
> makes expensive. A job cannot earn its way out of being the wrong
> job twenty times.

## `run_workflow`, [line 1233](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1233): Comment

Code: `record.verdict, record.verdict_by = "skipped", "none"`

> Said yes to the rest, so the write gate is not asked again
> for them either: they answered about this list twice already.

## `run_workflow`, [line 1240](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1240): Comment

Code: `record.reason = "no cited gesture can be acted on"`

> A step with nothing actionable cited gets no model call at
> all: it is recorded skipped and the run stops below rather
> than doing its later steps on an assumption nobody checked.

## `run_workflow`, [line 1242](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1242): Comment

Code: `replay = (`

> A replay the evidence decides on its own, where there is one,
> then the plan model, then the rescue model once, then -- only
> when both missed the control by every recorded identity -- the
> rescue model once more, by sight. A step with nothing actionable
> cited gets none of them: it is recorded skipped and the run stops
> below.
>
> First rather than instead. `replay_without_asking` covers exactly
> the step the evidence fully determines -- a call in the ledger
> whose body this run's values fit -- and a replay that comes back
> refused is precisely when clicking Save is the right next move,
> which is what the rungs behind it are.

## `run_workflow`, [line 1250](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1250): Comment

Code: `starts_on=_screen_of(step),`

> THIS step's own screen, not the run's, and not only for
> the run's first command.
>
> Measured on the deployment's own row, 2026-09-16. `Create
> a Customer Type` step 1 is "Open an email" and carries 15
> writes -- Gmail's own -- so it is not scaffolding and is
> performed; steps 2 to 5 collapse; and the replay is the
> SECOND command, by which time `sent_nothing_yet` is false
> and the run-level `starts_on` has been spent on Gmail.
> The call then wants a Blue Yonder tab to read
> `CSRF-ENCRYPT-TOKEN` off, the browser is in the mail, and
> the step fails `no_tab_for_origin`.
>
> Safe where the run-level one was not, and the 2026-09-15
> failure says exactly why: what dragged a cross-system job
> back to its first system was sending every step the page
> the RUN began on. A step's own screen names its own
> system by construction, and `opensFor` refuses a
> `starts_on` whose origin is not the command's, so this
> can only ever open the page the call is going to.

## `run_workflow`, [line 1260](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1260): Comment

Code: `route = route_for(step, _next_after(ordered, step), by_id)`

> A step that is only arriving somewhere goes there, first and
> without asking anybody.
>
> The application wrote down how to reach its screens in its own
> urls, and the operator's visits recorded it: both demonstrations
> of `Navigate to the Customer Types screen` carry the same route.
> Measured across 2026-09-16 and 17, the alternative -- a model
> shown a picture, working out that the screen is under a menu --
> cost thirteen cents a run and landed about half the time.
>
> First, not instead: a route that no longer exists leaves the
> rungs behind it to find the screen the hard way, which is what
> they are for.
> The step after this one in the job, which is where the evidence
> says this one arrives: a gesture records the page it happened on,
> never the page it led to.

## `run_workflow`, [line 1263](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1263): Comment

Code: `signed_in_here = False`

> The form this write would have been typed into was never filled.
>
> A run whose write goes out as a CALL collapses the steps that
> only put the form on the screen -- that is the whole point of
> replaying it. The ladder's next rung after a failed replay is a
> model planning from the evidence, and what the evidence says is
> "click Save": right when the five steps before it were performed,
> nonsense when this run skipped them on purpose.
>
> Measured on the deployment 2026-09-16: steps 0-4 `not_needed`
> "this run sends as a call", then step 5 sent `ui.perform` click
> on `toolbar button#saveButton`, against a form an operator had
> half filled an hour earlier. The warehouse refused it for an
> empty required field, which is the only reason it is not a wrong
> record instead of a failed one.
>
> So a collapsed write has one rung. If the call will not go, the
> step stops and says why -- and the job is still there to be run
> again with the form filled, which is a decision for a person
> rather than a fallback for a ladder.
> Whether this step has already been signed in for. Per STEP, so a
> run whose session dies twice can recover twice -- and once within
> a step, so a wrong password cannot be spent over and over against
> an account with a lockout policy.

## `run_workflow`, [line 1264](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1264): Comment

Code: `waited_here = False`

> And whether it has already been given a moment to finish drawing.

## `run_workflow`, [line 1273](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1273): Comment

Code: `rungs = (("replay", ""),)`

> This run has already given up on the screen -- that is what
> put this step's scaffolding in `collapsed` -- so the form in
> front of the operator was never filled. Walking the screen
> again to press its button would be pressing Save on a form
> with nothing in it, and would spend the budget finding that
> out. One rung: the call.

## `run_workflow`, [line 1275](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1275): Comment

Code: `rungs = (*rungs, ("replay", ""))`

> Watched, and the screen would not take it.
>
> A watched run performs the job where somebody can see it, and
> that is the whole of what `watched` buys. It must not also
> mean "and if the page cannot be driven, do not do the job":
> measured on the deployment 2026-09-16, every UI step ever
> attempted on the warehouse host failed while the same write
> went through as a call on the first try. The operator pressed
> yes; a system that answers "I could not click it" while
> holding a call it knows works is refusing for the wrong
> reason.
>
> LAST, and that ordering is the decision. The screen is tried
> first and fully -- plan from the evidence, plan again, then
> look at a picture -- so a run somebody is watching is still a
> run they watch whenever watching is possible. The call is
> what happens instead of stopping.
>
> It cannot write twice. The step claims its write in
> `tool_calls` before it goes out, keyed on the job, the step
> and the values, so a click that actually landed leaves a
> claim the replay then finds taken -- and a click that failed
> left none. The safety here is the ledger's, not this
> ordering's, which is why the fallback can be unconditional.

## `run_workflow`, [line 1287](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1287): Comment

Code: `refused_already: set[str] = set()`

> Commands this step has already sent and had refused.
>
> The rescue rung is handed `previous_attempt_failed` and exists to
> plan something ELSE. Measured on the deployment, 2026-09-17 at
> 17:32: `run_e1ff6362` step 3 planned `ui.perform click by
> component,css_path`, was told `control_not_found` naming both
> locators, and the rescue planned the same two locators again --
> $0.0125 then $0.0453 to be refused twice in the same words,
> before the ladder reached the rung that could have helped.
>
> A rule in the runner rather than a sentence in a prompt, because
> a prompt is a request and this is arithmetic: a command this page
> has just refused will be refused again, whatever model proposed
> it and whatever job it belongs to.

## `run_workflow`, [line 1288](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1288): Comment

Code: `asked_for_a_browser = False`

> Once per step. A session that ages out again three steps later is
> a second question worth asking; the same step asking twice in a
> row is a panel arguing with the person who just answered it.

## `run_workflow`, [line 1289](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1289): Comment

Code: `stepped_over = False`

> Set when a step turns out to be behind the browser rather than
> broken: the run joins the job further on, and none of the
> failure handling below applies to a step nobody needed.

## `run_workflow`, [line 1291](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1291): Comment

Code: `if stepped_over:`

> A step found to be behind the browser is over, whichever rung
> found it. The hooks that decide it sit inside the planning
> loop below, where a `break` only leaves that loop -- and the
> next rung then planned the step again and navigated back to
> a page the operator had left, in a new tab each time.

## `run_workflow`, [line 1293](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1293): Comment

Code: `if how == "look" and (`

> Only after the SCREEN failed a move, because that is the one
> verdict that says what is wrong in a sentence a picture can
> act on. A navigate that would not go, a point off the screen,
> a control nobody could find -- each has its own answer
> already, and a look is not it.

## `run_workflow`, [line 1062](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1062): Comment

Code: `if (`

> The sight rung is for a page that moved, not for a plan that
> was wrong: a control the browser could not find is the one
> failure a picture can answer. Anything else stops here.

## `run_workflow`, [line 1083](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1083): Comment

Code: `continue`

> `continue`, not `break`. Skipping the picture is right --
> it answers a control the browser could not find and
> nothing else -- but it must not skip what is behind it:
> on a watched run the rung after sight is the call, and a
> page that refuses to be driven at all is exactly when
> that call is the answer. With `break` the run stopped
> holding a write it knew how to make.

## `run_workflow`, [line 1302](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1302): Comment

Code: `planned: Planned | None = None`

> One rung of the ladder: plan, and plan again once if getting
> to the right page was all the model asked for. Getting there
> is not doing the step, so a navigate must not spend the one
> rescue -- it does spend budget, so a planner that only ever
> navigates still runs out.

## `run_workflow`, [line 1305](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1305): Comment

Code: `openings = 0`

> A dropdown is answered with two clicks: one to open the list
> and one to choose the row. The first is not the step, the
> same way a navigate is not the step.
>
> A screen is answered with as many as it takes, and that is
> the difference between this and a rung that gives up. The
> control for "click Customer Types" lives under a menu nobody
> demonstrated: one click opens the menu, a fresh picture shows
> it, the next click is the step. Measured on the deployment
> across two days -- that job never once reached its form on
> the screen, and the reason was a ladder that allowed exactly
> one thing to happen before the answer.
>
> Bounded, because a planner that only ever opens things must
> run out rather than loop: `K_OPENINGS` of them per rung, and
> the step budget above still bounds the whole step.

## `run_workflow`, [line 1306](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1306): Comment

Code: `previously = (record.planned_by, record.sent, record.result)`

> What the record says was planned and sent, before this rung
> touches it. A rung that ends without producing a command has
> to give it back: the verdict on the record is still the
> previous rung's, and a `planned_by` that disagrees with the
> verdict beside it is a lie about who failed.

## `run_workflow`, [line 1316](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1316): Comment

Code: `before = await _where(channel, tenant_id, device_id, run.id, origin)`

> No model, no picture: the evidence says where this
> step ends up and the browser is told to be there.

## `run_workflow`, [line 1329](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1329): Comment

Code: `before = await _where(channel, tenant_id, device_id, run.id, origin)`

> No picture: nobody is being shown one. The url is
> still wanted -- `before_url` is on the record -- and
> that is a message rather than a camera.

## `run_workflow`, [line 1344](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1344): Comment

Code: `opened=openings > 0,`

> The same guard the dropdown's two clicks use: one
> opening is allowed per rung, so a planner that
> only ever opens menus spends its budget instead
> of looping.

## `run_workflow`, [line 1352](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1352): Comment

Code: `learned=learned.get(step.order),`

> What a previous run found when this step's own
> recorded identity did not match. Tried first, and
> the recorded ladder still underneath it.

## `run_workflow`, [line 1357](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1357): Comment

Code: `starts_on=starts_on if sent_nothing_yet else None,`

> Only for the first step this run performs.
>
> `starts_on` is where a tab is OPENED when the
> operator's own is elsewhere, and it is a fact
> about beginning the run -- which is what the
> comment where it is computed has always said.
> Attached to every step instead, it dragged a
> cross-system job back to the first system on
> every leg: measured 2026-09-15, step 2 of `Create
> a Customer Type` went out with `origin` naming the
> warehouse and `starts_on` naming the operator's
> mail, so the extension found their warehouse tab,
> threw it away because it was not on that page, and
> clicked a warehouse control in Gmail. The step
> failed `not_actionable: the page did not answer`.
>
> After the first, the run has a tab pinned to it
> and `commands.js` keeps it while it is on the
> step's own origin, which is the whole of what the
> later steps need.

## `run_workflow`, [line 989](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L989): Comment

Code: `seen=observed,`

> What each declared parameter has been seen taking,
> which is how a value this run supplies finds its
> slot in a recorded body. Read off the stored job
> once, before the loop.

## `run_workflow`, [line 1370](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1370): Comment

Code: `record.planned_by = proposal.by or model`

> Who actually planned it. A replay asks nobody, and
> writing a model's name beside a step it never saw is a
> lie in the one field a reviewer reads to know who to
> blame.

## `run_workflow`, [line 1379](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1379): Comment

Code: `if live:`

> A planner that finds nothing to do here may be
> looking at a page the operator has already left
> behind: a session-expired dialog that is not up, a
> link somebody already clicked. The same question the
> browser's refusals get asked below -- where is it
> standing? -- asked before anything is sent, because
> a decline sends nothing. Measured 2026-09-23,
> `run_43ab2c7c`: "the browser is currently not loaded
> on the required page for this step" on step 0 of a
> sign-in, and the run stopped there.

## `run_workflow`, [line 1404](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1404): Comment

Code: `if _refused_origin(`

> For the two kinds whose target the model chooses, a url
> that names no origin at all -- about:blank, file:, a bare
> path -- is a refusal, not permission. `ui.perform` keeps
> its origin from the evidence and None there means the
> recorder saw no url, which the extension resolves itself.

## `run_workflow`, [line 1416](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1416): Comment

Code: `shown = await channel.send(`

> Sent from here, ahead of the gate that withholds a
> write and parks one on a person -- and only for a
> step that changes nothing, which is what makes this
> the same safe position `navigate` sends from.
>
> `not mutates` is said here as well as in the
> planners. A step whose evidence shows a write may
> need a menu opened to reach its button, and reaching
> it is not the writing -- but an opening click is a
> click the model chose, and the gate that parks those
> on a person is BELOW this line. Until that ordering
> is worth rearranging, a write step climbs the ladder
> as it always did.

## `run_workflow`, [line 1317](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1317): Comment

Code: `proposal = Planned(`

> Already sent, already refused. `break`, not a fall
> through: this is inside the loop that lets a rung
> open a menu and ask again, and leaving `planned`
> unset there re-asks THIS rung rather than moving to
> the next one -- which buys the same answer
> `K_OPENINGS` times instead of twice. The rung is
> spent; the ladder has another.

## `run_workflow`, [line 1438](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1438): Comment

Code: `planned = proposal`

> A navigate is normally the way to the step and not
> the step -- except on this rung, where arriving IS
> what the step says it does.

## `run_workflow`, [line 1447](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1447): Comment

Code: `if live:`

> Going BACK to this step's page, when the operator is
> already further on, is the wrong way. The browser has
> no tab on this step's system -- that is why the
> planner wants to navigate -- so the navigate opened
> one, and each rung that asked opened another.
> Measured 2026-09-23, `run_f1a970de`: step 0 of `Log in
> using Azure B2C SSO` is a session-expired dialog on the
> portal, the browser was on the SSO chooser that step 1
> clicks, and the run kept opening the portal in new
> tabs until it gave up.

## `run_workflow`, [line 917](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L917): Comment

Code: `logger.info(`

> A rung that answered and was not taken. This is the half
> nothing recorded: the step's reason keeps the LAST rung's
> words, so a rung that proposed something the runner would
> not use left no trace at all.

## `run_workflow`, [line 1502](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1502): Comment

Code: `refusal = record.sent if (record.sent or {}).get("payload") else None`

> A refusal that carries STRUCTURE is kept, because it is
> not "no command" -- it is the one thing a person can act
> on. `needs_secret` names the system and field a step
> wanted a password for, and the panel draws a box from it;
> rolling it back to the previous rung's command left the
> operator with a step marked ✗ and nothing to do about it,
> which is the whole defect this payload exists to fix.

## `run_workflow`, [line 1506](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1506): Comment

Code: `if how == "sight" and verdict is not None:`

> The sight rung's answer, when it had none: the record
> keeps the last command that went out, and says beside it
> what the picture said -- "not on this screen" is the fact
> a person acts on, and it was about to be lost.

## `run_workflow`, [line 1514](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1514): Comment

Code: `if not live and mutates:`

> Still `writes()`, deliberately: withholding every click the
> recorder heard nothing from would leave a dry run performing
> almost none of the job, while not RESCUING one costs a
> rescue. The asymmetry is the cheap side of each.

## `run_workflow`, [line 1521](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1521): Comment

Code: `pressing = planned.payload.get("action") in ("click", "press")`

> `writes()` is not the whole of a write. It is False when the
> cited evidence records no mutating call AT ALL, which is what
> a click on Save looks like when the recorder never saw the
> traffic -- a beacon, a worker, a frame nothing was attached
> to. A click or a press on evidence that came back silent is
> the same unknown state as an accepted write; a click that
> fired a completed read -- a menu, a tab -- is not.
>
> One predicate, both gates below: a step nobody may retry
> afterwards is a step nobody may send unasked either.
> A click at a point the model chose is a click on whatever is
> there now, on a page that has already moved under the job:
> what the demonstrated control's traffic showed says nothing
> about it. Every sight click is a possible write.
> A step that signs in is not a step that writes -- see
> `sign_in_step`, which decides that from the step's evidence
> for every leg alike.

## `run_workflow`, [line 1522](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1522): Comment

Code: `signing_in = is_sign_in_page(primary.url if primary is not None else None)`

> A silent click on an identity provider's page signs somebody
> in and cannot write anything -- see `is_sign_in_page`. A
> recorded write there is still a write here; what takes a
> recorded write out of `mutates` is `sign_in_step`, which reads
> the job and the step's evidence rather than the page's path.

## `run_workflow`, [line 1525](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1525): Comment

Code: `or (`

> A click at a point the MODEL chose is a click on whatever
> is there now, on a page that has already moved under the
> job: what the demonstrated control's traffic showed says
> nothing about it. Every sight click is a possible write,
> whatever the job does later.
> Except a `look` move, which is judged by what it sent
> rather than by what it might have: see `K_LOOKS`.

## `run_workflow`, [line 1531](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1531): Comment

Code: `or (`

> A click the recorder heard nothing from is a possible
> write too -- unless this job's own write is still ahead
> of it. Then the demonstration says what this step is:
> scaffolding, opening a dropdown or a form, on the way to
> a call it recorded somewhere later.

## `run_workflow`, [line 1540](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1540): Comment

Code: `if live and may_write:`

> Already true, so there is nothing to do.
>
> Before the approval gate on purpose: a person asked to
> approve a write that has already happened is a person being
> asked to make a duplicate. The run that made this worth
> writing signed an operator in who was already signed in, and
> the class behind it is wider -- a rule that fires twice, two
> browsers on one job, a card answered a day late -- and every
> one of those ends in a second record a warehouse wanted one
> of.
>
> Only where the step's own evidence shows the page reading its
> effect back and this run carries the value to look for. None
> of the run's other steps are touched: a step that opens a
> form or picks a row has no read and is done the way it always
> was.

## `run_workflow`, [line 1553](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1553): Comment

Code: `record.result = {"skipped": True, "already": True}`

> Not a write this run made. `record_effect` is what
> earns a job the right to write unasked, and a step
> that sent nothing has not demonstrated anything about
> this job's ability to write correctly.

## `run_workflow`, [line 1557](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1557): Comment

Code: `key = write_key(workflow.id, step, values) if live and mutates else ""`

> And the same write, claimed before it is sent.
>
> `already_done` above asks the warehouse whether the record is
> there; this asks our own store whether we are already making
> it. They catch different halves: a read cannot see a write
> that is in flight in another run right now, and a claim
> cannot see a record somebody made by hand.
>
> Claimed and kept, never released on failure -- the reason
> `tool_calls` gives for connector calls holds here word for
> word: a timeout is the one case where the send may well have
> landed, and releasing the key would retry it into a second
> write.
> `mutates` and not `may_write`, which is the wider of the
> two on purpose. `may_write` includes a click whose evidence
> recorded no traffic at all -- a Sign In that submits a form
> the recorder cannot see is one -- and there the evidence says
> nothing was created, so refusing a second attempt would stop
> an operator retrying a login that failed. A step whose
> evidence carries a real mutating call is the one that can
> leave a second record behind.

## `run_workflow`, [line 1560](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1560): Comment

Code: `claimed = await uow.tool_calls.remember(`

> Not `first`: that name is a gesture in this function.

## `run_workflow`, [line 1568](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1568): Comment

Code: `claimed_here.add(key)`

> Once per step per run, not once per attempt. A write the
> server itself refused is the one write this loop is
> allowed to plan again, and a claim made by the first
> attempt must not refuse the second -- that is this run
> colliding with itself.

## `run_workflow`, [line 1579](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1579): Comment

Code: `if known_fields is not None and planned.filled:`

> What is already known about the fields this write fills,
> asked once, for every write that is about to go out.
>
> Not inside the approval branch below, and the difference is
> the point: a job that has EARNED the right to write unasked
> is exactly the one nobody is watching, and the note belongs
> in its audit too. The dictionary is the vendor's own
> documentation and the question it answers is "will this value
> fit" -- the sharpest instance of the one failure the ladder
> cannot see, because a column that keeps four characters of
> six still answers 201 and the read-back shows the record the
> system actually made.
>
> A note and never a refusal: see `field_notes`. The two
> sources disagree by construction -- the dictionary says
> `customerType` holds 60, the ledger's own gotcha says
> `csttyp truncates at 4 chars` -- and refusing on the
> documented one would stop correct runs against a system that
> behaves differently from its manual.

## `run_workflow`, [line 1585](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1585): Comment

Code: `record.notes = list(`

> The screen as well as the keys. A body key does not name
> a form -- `customerType` is posted by both Customer Types
> and Existing Customers on this deployment -- so a lookup
> by key alone would lend one screen's required fields to
> another screen's write.

## `run_workflow`, [line 1594](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1594): Comment

Code: `approved_here = leg.item is not None and step.order in approved_for_the_list`

> A live write, on a job that has not yet earned the right to
> write unasked: shown in the panel with what would go out, and
> held until somebody taps. `live` is checked here rather than
> inherited from the block above, whose narrower `mutates` lets
> a dry run walk past it: a dry run withholds, never waits.
> Once for the list, not once per thing.
>
> A person answering "add these three" read three rows and
> pressed one button. Asking them again for the second and the
> third is asking them to authorise what they have already
> authorised -- and a card per thing on a list of ten is a
> panel nobody reads by the fourth. So the tap on one step
> covers that step for the rest of the list, and only for the
> rest of THIS list: a second run asks again, because a second
> press is a second decision.
>
> Not the same as earning the right to write unasked. That is
> a job proving itself over runs, and this is one person
> answering about one list they have in front of them.

## `run_workflow`, [line 1595](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1595): Comment

Code: `opening_the_form = not leg.rescue and step.order in in_reserve`

> A step this same job would SKIP is not a write to ask about.
>
> `may_write` is deliberately wide: a click whose demonstration
> showed no traffic might be a write, so it asks. But a step in
> the reserve is one an unwatched run of this very job does not
> perform at all -- it is scaffolding for a write that is in
> the ledger, and the ledger's write is the Save at the end of
> it. Asking a person to approve doing what the same job would
> otherwise not do is incoherent, and it cost three approval
> windows on 2026-09-17: every watched run parked on "Click the
> Add button", which opens a form.
>
> The write itself still asks. `in_reserve` never holds the
> step that carries the call -- `scaffolding_for` returns what
> comes BEFORE it -- so this narrows the question to the one
> step that changes the warehouse.

## `run_workflow`, [line 1373](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1373): Comment

Code: `record.sent = {`

> `without_secrets`: this row is read by the panel, by an
> operator reviewing what happened, and by the model asked
> to rescue a failed step. A password typed from the vault
> would otherwise reach all three and outlive the run.

## `run_workflow`, [line 1210](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1210): Comment

Code: `approvals.register(run.id)`

> Registered before the save, not by the wait below: the
> save is what puts this step in front of a person, and a
> tap that lands before the wait starts must find an event
> to set rather than a 409.

## `run_workflow`, [line 1101](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1101): Comment

Code: `if stops.asked(run.id):`

> A released wait is not a yes. The stop button releases it
> as well as setting the flag, so a person who pressed Stop
> rather than Approve gets an aborted run and not a write.

## `run_workflow`, [line 1224](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1224): Comment

Code: `with suppress(DeviceUnreachable):`

> The browser is told here too, and not only between
> steps. This is the path where somebody is WATCHING:
> they pressed Stop on a panel showing a write, and
> until the extension hears the abort its band goes on
> claiming the run for up to `RUN_QUIET_MS`. The route
> sends nothing itself -- `AbortWorkflowRun` releases
> the wait and the loop is what talks to the browser.
>
> Suppressed where the between-steps send at the top of
> this loop is bare, which is a deliberate difference
> and the rig's own shape (`api.py:1250`). There, a
> send that raises is a browser that went away and the
> run honestly failed. Here the person's intention is
> already recorded and the row already says `aborted`,
> and letting this raise would hand it to `_fell_over`
> -- which rewrites the outcome to `failed` and the
> reason to the socket error, reporting "the browser
> went away" for a run a person deliberately stopped.
> A browser that has gone is also the commonest reason
> to press Stop.

## `run_workflow`, [line 1637](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1637): Comment

Code: `if leg.item is not None:`

> Answered yes, and the answer stands for the rest of the
> list. Recorded after both refusals above, so a wait that
> timed out or a Stop cannot be mistaken for a tap.

## `run_workflow`, [line 1640](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1640): Comment

Code: `if record.verdict == "awaiting":`

> The row stops saying it is waiting on a person, before the
> command goes out rather than after it comes back.
>
> `awaiting` is what the panel draws the Approve button from.
> Left standing through the send it is a row that lies for as
> long as the step takes -- the call, the read-back, and on the
> ladder's third rung a screenshot and a vision call -- so an
> operator taps Approve, the tap is recorded, the wait really
> is released, and the panel redraws the same paused row with
> the same button. Reported as "I clicked approve and nothing
> happened" on the live deployment, 2026-09-16, against a run
> whose approval had in fact landed every time (`resumed:
> true`, three taps).
>
> Back to `skipped`, which is what an in-flight step already
> says: it is this record's starting value, the panel draws it
> `○`, and the real verdict overwrites it a few lines below.
> Not a new word for "sending" -- the vocabulary is closed and
> a state that exists only between two statements of the same
> function is not a disposition anybody needs to read about.

## `run_workflow`, [line 1644](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1644): Comment

Code: `assert before is not None  # noqa: S101 -- see the comment above`

> `before` and `planned` are set by the same pass of the while
> above: a command to send is a command something was looked at
> before planning.

## `run_workflow`, [line 1645](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1645): Comment

Code: `holds = (learned.get(step.order) or LearnedStep(step.order, "", "", "")).holds`

> The moment the command went out, so the calls the page makes
> because of it can be told from the ones it was already
> making. Taken here and not after the reply: a form submit
> posts before the click's own answer comes back.
> A box already known not to take this does not get filled.
>
> The limit was learnt by a run that found it the hard way: it
> typed, the browser silently kept a prefix, and the run
> stopped. Knowing that and typing anyway would half-fill a
> form in front of somebody to reach the same conclusion --
> which is the difference between a system that learns and one
> that repeats, and the whole point of writing the limit down.
>
> Checked here rather than at the door, because the value for
> a step is not known until it is planned: a run may supply it,
> a mailbox may, and a body may carry it.

## `run_workflow`, [line 1648](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1648): Comment

Code: `run.needs = _too_long_for(step, values, holds)`

> Asked about, not merely refused. The same road a value
> nobody could find takes: the names go on the row, and the
> conversation turns them into a question somebody answers
> -- and the run starts again on the yes they already gave.
> A run that stops dead here is an operator who pressed
> once and got a dead card, which is the thing
> `_ask_for_values` was built to end.

## `run_workflow`, [line 1665](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1665): Comment

Code: `sent_nothing_yet = False`

> Whatever came back, a command has now gone out and a tab is
> pinned to this run: `starts_on` has done its one job and the
> next step is driven by its own origin.

## `run_workflow`, [line 1667](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1667): Comment

Code: `if how == "look" and reply.ok:`

> What a move made to work the step out actually sent, read
> before any belt looks -- a read-back is itself a command, and
> the browser answers `calls.since` from the last one.

## `run_workflow`, [line 1685](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1685): Comment

Code: `cut = record.result.get("short")`

> A field that would not take what it was given stops the run,
> here, before the Save.
>
> The browser truncates silently and BEFORE the request. On
> this deployment `Warehouse.Description` stops at about 28
> characters with no error and no warning -- so 28 characters
> go into the body, 28 come back from the read, and 28 are in
> the photograph. Every belt this run has agrees, because every
> one of them compares the record to ITSELF, and the record it
> makes is not the record the request asked for.
>
> Stopped rather than noted, and this is the one place in the
> ladder that judges a step the page performed perfectly well.
> The rule is the same one the blank-value gate is built on: a
> write with the wrong thing in it is a wrong record, and a
> warehouse record cannot be un-created. Somebody shortening
> the description themselves is a minute; a wrong record in a
> warehouse is not.
>
> Only a truncation. A field that trimmed a space or fixed a
> case changed what was asked for and did not LOSE any of it,
> and stopping for that would stop correct runs on a hundred
> ordinary forms.

## `run_workflow`, [line 1687](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1687): Comment

Code: `kept = cut.get("kept")`

> Learnt, not merely reported. A limit found once and
> forgotten is this job discovering the same fact every
> run -- which is what `learned_step.py` calls repeating
> rather than learning, and it says what that cost when
> the fact was a locator.

## `run_workflow`, [line 1716](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1716): Comment

Code: `if not reply.ok and reply.error_kind in K_NOT_HERE and workflow.signs_in:`

> The browser is not where this step needs it, and that is a
> question for a person rather than a verdict about the job.
>
> Measured on the live deployment 2026-09-16: a run failed
> `no_tab_for_system` because the operator's Blue Yonder
> session had expired. The job was right, the plan was right,
> the values were right, and the run died on a sentence naming
> a tab. The system signs people out on its own schedule and
> takes the tab to an identity provider when it does, which is
> `no_tab_for_origin` -- the same thing with the page still
> open.
>
> So the panel asks, in the one place the operator is already
> watching, and the same command goes again when they say they
> are back. Live only: an unattended dry run has nobody to ask,
> and parking one for half an hour is a hang rather than a
> question.
>
> The claim is not given back before the second send. The
> release below reads the FINAL reply, which is what decides
> whether anything left the browser.
> There WAS a rule here that read this as "already signed in",
> and it was wrong. It said: a job that does nothing but sign
> in, a step that cannot find its tab, and an earlier step that
> held -- so the page went away because the sign-in completed.
>
> On a job that IS the sign-in, an earlier step holding means
> the LOGIN FORM was being filled. It is the strongest evidence
> in the run that nobody is signed in yet, and it was read as
> the opposite. Measured on the deployment 2026-09-20, run
> `run_28f14216`: step 0 typed `RKUCHIYAGM` into the Keycloak
> username box and held, step 1 was skipped as "already signed
> in", the run ended `held` -- and the operator was sitting in
> front of that same form with the password box empty and
> nothing on screen asking them for anything.
>
> What it was built for -- `run_83efedf5` -- has the same shape
> and a different cause: the browser lost the tab it had pinned
> when this worker was evicted between two commands, which
> `commands.js` now carries through storage. A failure read as
> a success is how a fault gets a coat of paint instead of a
> fix, and this one painted over the password card: a skipped
> step asks for nothing.
>
> So the question is not what held. It is WHERE THE BROWSER
> IS, which is a thing this can go and ask.
>
> A sign-in page that is gone because the sign-in worked leaves
> the browser somewhere else and not asking anybody to sign in.
> A sign-in page that is gone because this run lost its tab
> leaves the browser on that page still, with the form in front
> of the operator. Those are two different answers to `ui.url`
> and they were one answer to this.
>
> Measured on the deployment 2026-09-20, both halves:
>
>   run_28f14216  step 0 typed the username and held; the
>                 operator was looking at the Keycloak form
>                 with the password box empty. `signed_out`.
>                 -> ask, which is what this now does.
>   run_1dd7e8..  step 0 typed the username, the sign-in went
>                 through, and the browser was in the WMS
>                 portal saying "Hello Rudy". Step 1 failed
>                 `no_tab_for_system` on a page that no longer
>                 exists because the job had SUCCEEDED, and the
>                 card said "The run stopped".
>                 -> nothing left to do, which is this.
>
> `elsewhere_is_ours`, so the page read is the tab this run
> pinned and not whatever window happened to be in front. And
> only for a job that does nothing BUT sign in: a bigger job
> whose sign-in completed has the rest of itself to do, and
> ending its run here would be this same mistake wearing the
> other coat.
>
> "Does nothing but sign in" is `Workflow.signs_in`, stored by
> the mining pass. It used to be guessed here from every cited
> gesture sitting on one origin, which is also every ordinary
> job done on one warehouse host: a `Create a Customer Type`
> run that lost its page while the browser sat elsewhere on the
> system ended `held` -- reported as succeeded -- with its Save
> never pressed. An ordinary job here goes on to the failure
> path below, which asks for the browser.

## `run_workflow`, [line 1727](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1727): Comment

Code: `if live and not reply.ok and reply.error_kind in K_MIGHT_BE_BEHIND:`

> Or this run is simply behind the browser.
>
> A run starts at step 0 whatever is on screen, so a job joined
> halfway replays its first pages into a browser that has left
> them. Measured on the deployment 2026-09-23: four runs of
> `Log in using Azure B2C SSO` failed on a dialog and an SSO
> link the operator had already clicked -- `control_not_found`,
> "the browser is currently not on the step page".
>
> Asked only when a step has actually failed to find what it
> wanted, so a run that is where it should be sends nothing
> extra and its first command is still its own.

## `run_workflow`, [line 1297](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1297): Comment

Code: `if (`

> Otherwise a sign-in that cannot find its page asks. The
> operator can see the screen and this cannot.

## `run_workflow`, [line 1780](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1780): Comment

Code: `if key and not reply.ok and reply.error_kind in K_NEVER_SENT:`

> A write whose command never left the browser gives its claim
> back. Kept for everything else, including a timeout: see
> `K_NEVER_SENT`.

## `run_workflow`, [line 1785](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1785): Comment

Code: `if reply.ok and planned.kind == "ui.perform_at":`

> A point has no locator: the record says the control was found
> by sight, in both places a reader looks.

## `run_workflow`, [line 1789](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1789): Comment

Code: `settled = (`

> The cheap rung first, and the picture only if it cannot
> answer. A step whose demonstrated endpoint has just answered
> 201 is done, and photographing the screen to ask a model
> whether it looks done costs a screenshot, a vision call and
> most of the step's wall clock to reach a worse answer -- the
> verifier's own docstring puts the status first and the screen
> "last and least", and until the browser could be asked what
> it called, a UI step could never reach the first rung.
> Never for a replay, and for two separate reasons.
>
> It cannot work: the extension sends an `http.send` through the
> page's own `fetch` in the ISOLATED world specifically so the
> replay does NOT re-enter the evidence plane as the operator's
> own action, so `calls.since` can never see it. The round trip
> is spent to be told nothing.
>
> And it must not work. This rung settles a step by STATUS, and
> `settled or await verify(...)` means a verdict here is a
> verdict instead of the ladder -- so a call the page happened
> to make to the same endpoint shape would hold the step on its
> status and skip the read-back that `rewrote` exists to reach.
> The one belt that can tell a truncated record from the record
> this run asked for would be bypassed by a coincidence.

## `run_workflow`, [line 1798](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1798): Comment

Code: `aimed_url=(`

> Where this run's values put the write -- a delete's
> record is in its path, and the demonstration's url
> names a record this run was not asked about.

## `run_workflow`, [line 1813](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1813): Comment

Code: `after = (`

> Where the status settled it, the url is still wanted -- the
> record says where the step left the browser -- and that is a
> question the browser answers without a camera.
>
> And for a replay, where there was never a picture to take. An
> `http.send` is a `fetch`: no click, no navigation, no repaint,
> so the "after" screen IS the before screen and the screen rung
> would ask a model whether an unchanged page proves a record
> was created. That is not a weak answer, it is a meaningless
> one -- and it can come back `held`. Without a picture the
> rung refuses instead: a step that writes cannot reach the
> "changes nothing" hold, so an odd status ends `unclear` and
> stops the run, which is the honest end for a write nothing
> could confirm.

## `run_workflow`, [line 1819](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1819): Comment

Code: `after_failed = after`

> Kept for the rescue: if this attempt does not hold, the next
> rung is shown the page it left behind beside the page as it
> is when it plans.

## `run_workflow`, [line 1820](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1820): Comment

Code: `arrived = (`

> A step that was only arriving is judged by where the
> browser is, which is a fact this side can read: no status to
> weigh, no picture to interpret, and nothing for a model to be
> confident about. `page_of` drops the query and the fragment's
> particulars, so the same screen reached twice compares equal.

## `run_workflow`, [line 1827](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1827): Comment

Code: `else f"the browser is on {after.url}, not {route}"`

> `elsewhere` where the browser is not on this
> system at all: without it this said "the browser
> is on None", which is the sentence a person read
> on the deployment while looking at a sign-in
> page.

## `run_workflow`, [line 1853](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1853): Comment

Code: `next_says=(`

> What this screen has to be good enough for. A step
> that changes nothing is judged on whether the job can
> go on, and the next leg is what going on means.

## `run_workflow`, [line 1860](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1860): Comment

Code: `refused = (`

> A step that failed in front of a login page failed for one
> reason, and it is not the one it was about to report.
>
> `control_not_found: no control matched` is true and says
> nothing: somebody reading it goes looking for a broken
> selector. Measured on the deployment 2026-09-18 -- a session
> expired, the operator spent minutes signing back in, and
> every run in between blamed a missing tab item. The page in
> front of it was a login form the whole time.
>
> The verdict stands; what changes is what it SAYS. A run that
> renamed the failure would be a run deciding it knows why the
> step failed, and what this knows is only what is on screen.
> Asked only of a step that failed, and only once: a round
> trip per failure is cheap, and one per step is not.

## `run_workflow`, [line 1872](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1872): Comment

Code: `if verdict.state == "failed" and after.loading and not waited_here:`

> And where nothing is stored to sign in WITH, the refusal
> carries the key, so the panel can ask for it.
>
> The box already exists: a step that types a password and
> finds the vault empty refuses with `needs_secret`, and the
> run card draws "this job needs your password for <system>"
> and a field. What never reached it is this case -- a job
> mined from an already-signed-in session has no login step at
> all, so nothing ever asked, and the operator was left with a
> run that stopped and a sentence about a session.
>
> Same key either way. `secret_key_of` and `secret_key_for`
> normalise the field identically for exactly this reason: the
> side asking and the side storing have to spell it the same or
> the value is invisible to the one thing that needs it.
> A page that had not finished arriving gets a moment, and the
> same rung again.
>
> This is the one of the screen's answers a run can DO
> something about rather than only report. A step that failed
> against a half-drawn screen otherwise spends the rest of its
> ladder on it -- a model call about a page that was not there
> yet, then a sight rung photographing a spinner -- and reports
> a missing control that appeared a second after it gave up.
>
> Once per step, like the sign-in. A screen that is still
> coming after one wait is a screen that is stuck, and a run
> that waited again would turn a fault into a hang.

## `run_workflow`, [line 1883](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1883): Comment

Code: `here = after.url or (after.elsewhere if after.elsewhere_is_ours else "")`

> Sign in and try the step again, where there IS something
> to sign in with.
>
> `KeepSessionsOpen` has done this for years against a
> hosted browser, and the runs that matter drive the
> operator's own Chrome, which nothing could sign in. So a
> session that died mid-shift left a stopped run and a
> person whose only way on was to do the whole job by hand.
>
> Once per step and no more. A login that did not take is a
> wrong password or a second factor, and a run that tried
> again would spend an account's lockout budget on a
> credential that is not going to start working.
> The page the browser is ACTUALLY in front of, and only
> then the one the recording named.
>
> A credential belongs to the system whose box it is typed
> into. `after.url` is empty whenever the step's own origin
> is not where the tab got to -- which is every sign-in
> that bounced -- so this used to fall back to the
> RECORDING's origin and ask for that system's password
> while the operator looked at another system's form.
>
> Measured on the deployment 2026-09-20, run
> `run_b949148d`: `Log in using Azure B2C SSO` is mined
> entirely on `blueyonderalphaus.b2clogin.com`, the live
> sign-in bounced to Keycloak, and the b2clogin password
> went into the Keycloak form. The page said *Invalid
> username or password*. A credential in the wrong
> system's box is worse than a step that fails: it spends
> an account's lockout budget, and it is the operator's
> account.
>
> `elsewhere_is_ours` and not `elsewhere`: the browser
> answers with the tab in front when this run pinned none,
> and "your password for <whatever window was open>" is a
> credential prompt for a system nobody named.

## `run_workflow`, [line 1596](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1596): Comment

Code: `if (`

> And a credential goes out only where this run can say
> which page it is for. `sign_in` fills the run's own tab
> WHEREVER it has got to -- it has to, a sign-in page is on
> another host by design -- so the origin in the command is
> not a guard on where the typing lands. This is: with no
> reading of where the browser is, the honest answer is to
> ask rather than to send somebody's password somewhere
> nothing looked at.

## `run_workflow`, [line 1916](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1916): Comment

Code: `record.made = dict(verdict.made)`

> What the warehouse called the record this step made. On
> the row because it is the only place it exists: the panel
> says which records a run created, and an undo -- the day
> the evidence for one exists -- addresses them by it.

## `run_workflow`, [line 1918](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1918): Comment

Code: `record.result = {**(record.result or {}), "called": dict(verdict.called)}`

> On the RESULT, where `_remember_the_write` looks, and on
> its OWN condition: `made` is the fields that name the
> record and a create whose answer carries none leaves it
> empty, which has nothing to do with whether a call was
> watched. Nested under `made`, this stored nothing for
> exactly the writes it exists to learn from.

## `run_workflow`, [line 1920](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1920): Comment

Code: `record.result = {**(record.result or {}), "refuted": True}`

> A read went and looked, and the write is not there. On the
> result because `can_try_again` reads the step, and the
> step is what a later reader has -- the verdict object is
> gone by then.

## `run_workflow`, [line 1922](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1922): Comment

Code: `if planned.kind == "ui.perform_at" or (`

> Found by sight, or by the last locator: the page moved
> under the job, and the job is flagged before it breaks.

## `run_workflow`, [line 1932](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1932): Comment

Code: `found = learned_from(`

> And WHAT it found, which is the half that was
> missing. Marking the step stale says it is about to
> break; this says what worked instead, so the next
> run tries that first rather than climbing the same
> ladder and paying for the same model call to reach
> the same control.
> The REPLY, not the record: `_result` keeps the three
> facts a row needs and the control the browser named
> is not one of them -- it is for the job, not for the
> audit of this run.

## `run_workflow`, [line 1940](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1940): Comment

Code: `await uow.workflows.clear_stale(workflow.id, step.order)`

> The step was found the strong way again: a warning
> that never clears is a warning nobody reads.

## `run_workflow`, [line 1941](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1941): Comment

Code: `await record_effect(uow.workflows, run, record, at=_now())`

> A write this run made that the verifier saw hold by
> state. The three gates -- live, held, wrote -- are
> `record_effect`'s own, read off the record rather than
> off these locals so a second caller cannot forget one.

## `run_workflow`, [line 1754](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1754): Comment

Code: `if (`

> A write that went out and was accepted, and then could not be
> shown to have held, is not a step to try again: the second
> attempt would create the order twice. Only a write the server
> itself refused -- or one the browser never sent -- is safe to
> rescue. A read is always safe. `may_write` above is the same
> reading of "this may have changed something" the tap uses.

## `run_workflow`, [line 1951](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1951): Comment

Code: `if stepped_over:`

> Said once the rungs are spent, because it explains what was NOT
> tried: the interface. A person reading "the call would not go"
> would otherwise reasonably ask why it did not just press the
> button, and the answer is that this run never filled the form.

## `run_workflow`, [line 1962](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1962): Comment

Code: `if record.verdict == "skipped" and verdict is not None:`

> A rung that never reached a command -- an unplannable step, a
> navigate that would not go -- left its reason on the local verdict
> and nothing on the record, which then read `skipped` and let the
> run walk past it.

## `run_workflow`, [line 1970](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1970): Comment

Code: `took_it = bool(isinstance(record.result, dict) and record.result.get("ok"))`

> Held, or deliberately withheld by a dry run. Anything else --
> failed, unclear, refused, or a step with nothing actionable to
> cite -- is a step nobody watched succeed, and the rest of the job
> assumes it did. Nothing runs unattended past one.
> **A step the page TOOK is not a step the page refused.**
>
> The collapse below exists for one premise -- "the page would not
> take this step" -- and when the browser answered `ok` that
> premise is false. run_7ebafa8f, the deployment, 2026-09-17 at
> 22:17: step 3 typed `GS7` into Customer Type and the browser said
> `ok: true, matched_by: component`. It came back `unclear` only
> because there was no screen to confirm it against, the reserve
> collapsed it as a refusal, and the card told the operator "the
> form was never filled for this run" over a form holding GS7.
>
> That is the worst of both: a half-filled form left in front of
> somebody who might press Save on it, and the same write going out
> as a call beside it. So a step the page took stops the run
> instead, with the form as it is and a reason that matches it --
> which is a decision for a person, and the reserve is for the case
> where the page did nothing.

## `run_workflow`, [line 1278](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1278): Comment

Code: `logger.info(`

> Only a step the BROWSER would not do reaches here, and that
> is by construction rather than by a check: a step in the
> reserve is never parked on a person (see the approval gate),
> and a wait nobody answers ends the run before this. A
> timeout read as "the page refused" would collapse the job
> and walk past the thing somebody was being asked about,
> which is what happened on 2026-09-17 while both were true.
> The screen would not take it, and the job is not over.
>
> A watched run performs the steps that put the form on the
> screen, and this is one of them. Measured on the deployment,
> 2026-09-17 at 10:40: the run stopped on "Navigate to the
> Customer Types screen" -- a step with no call of its own --
> while the write it was on its way to was a call this run knew
> how to make, three steps later and never reached. The
> fallback built for the write step could not help, because a
> run stops at its first failed step.
>
> So the run gives up on the SCREEN rather than on the job: the
> steps that were only ever scaffolding for the write are
> collapsed, exactly as an unwatched run would have had them
> from the start, and the write goes out as a call. Once --
> `in_reserve` is emptied -- so a job that fails again fails.

## `run_workflow`, [line 1994](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1994): Comment

Code: `_signing_in, back = (`

> A session that went is not a job that failed.
>
> The browser is at a sign-in page, the tenant has shown how to
> get through it, and the steps for that go in ahead of the one
> that met it -- so the run signs itself back in and tries
> again, through the same ladder as everything else.
>
> Once per run, and never twice: a second sign-in page after
> signing in is a system this run cannot get into, and a loop
> that kept trying would spend a budget it cannot see the end
> of on somebody's credentials.
> Nor while this step is itself on a sign-in page: the job is
> signing in, and its own next steps are the way through.
> `run_3610aa05`, 2026-09-23: `Log in using Azure B2C SSO`'s
> password step could not be photographed, read the Keycloak
> form as a session that had gone, and spliced `Log in to
> Keycloak` into the middle of itself -- two sign-ins, and a
> run left asking for a third after the second worked.

## `run_workflow`, [line 1207](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L1207): Comment

Code: `record.reason = (`

> Signed in once and the system is still asking. That is
> not a session that went, it is one this run cannot get
> into -- wrong credential, a second factor, an account
> locked -- and trying again would spend somebody's
> attempts on it.

## `run_workflow`, [line 2009](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2009): Comment

Code: `standing = standing | stood_on(_signing_in, by_id)`

> Where those steps may act: the sign-in job's OWN
> evidence, and nothing wider. The run's allowlist is built
> from the job being run, so without this the spliced steps
> are refused for reaching a host this job never stood on
> -- which is the right rule for the job and the wrong one
> for the page it has been bounced to.

## `run_workflow`, [line 2012](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2012): Comment

Code: `budget += len(back) + 1`

> The rescue's own steps, and the retry. Without this the
> budget below ends the run part way through signing in.

## `run_workflow`, [line 2023](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2023): Comment

Code: `if run.steps and all(one.verdict == "not_needed" for one in run.steps):`

> Every step skipped is not a job done.
>
> A run whose steps were all `not_needed` performed nothing, sent
> nothing and made nothing, and until this it reported `held` --
> measured on the deployment 2026-09-17 at 03:59, where a job made
> entirely of steps in a mailbox had all five skipped and said it
> had worked. A run that claims the job is done and did not do it
> is worse than one that fails, because nobody goes looking.
>
> `not_needed` and not the rest: `withheld` is a dry run, which
> deliberately does nothing and says so in its own word, and a run
> with no steps at all never reaches here.

## `run_workflow`, [line 2034](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2034): Comment

Code: `_fell_over(run, in_flight, f"{type(broke).__name__}: {broke}")`

> Not handled, and not silently a run that says `running` forever
> either. The record is finished and saved by the `finally` below, then
> this goes on up.

## `run_workflow`, [line 2037](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2037): Comment

Code: `if run.outcome == "running":`

> In the finally, so an exception this function does not handle still
> leaves a saved record rather than a row that says `running` forever.
>
> Still `running` here means neither `except` above ran, and the only
> way out of the loop that skips both is a BaseException -- in practice
> the CancelledError a shutdown delivers to this task. That is a run
> nobody watched finish, so it says so rather than being read later as
> one still in flight on a process that no longer exists.

## `run_workflow`, [line 2039](../../../../../../../backend/src/sro/application/execution/run_workflow.py#L2039): Comment

Code: `await forget_effects(uow.workflows, run)`

> A write that went out and did not hold un-earns the whole job: the
> next runs ask for a tap again. Here rather than in the step body,
> because the step body is not reached when a browser goes away
> mid-write -- and that run wrote, was never shown to have held, and
> would have kept its autonomy.
