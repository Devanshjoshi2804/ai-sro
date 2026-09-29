# Notes for `backend/src/sro/application/execution/verify.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/verify.py`](../../../../../../../backend/src/sro/application/execution/verify.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/verify.py#L1): Docstring

> Check what the system answered against what the demonstration established.
>
> Every failure is a sentence, because a run's value is what it tells the person
> reading it afterwards. "assertion 2 failed" tells them nothing.
>
> Two verifiers live here, for two kinds of step. `check` and its siblings are the
> authored skill's post-conditions: assertions somebody wrote down, checked
> against one response. `verify` is A14's, for a mined workflow, where nobody
> wrote anything down and the only post-condition is "did the thing happen" --
> ported from `new_agent_arch/src/rig/verify.py`. The pure half of that one, the
> belts that need no wire and no model, is `sro.domain.execution.belts`; this is
> the half that sends a probe and asks a model to look at a picture.
>
> The belt order is the product. Measured over the 643 tasks of the WebVoyager
> benchmark, a validator reading the run's own text -- what the calls returned --
> scored 84.24% against 70.04% for one reading screenshots, with over 84%
> agreement with human annotators; a screenshot read beside the agent's final
> answer still only reached 83.00%. So: the response the command itself returned
> first, a confirming read the cited evidence shows the page performs second, and
> the screenshot last and least.
>
> A green toast is the weakest of the three and the
> easiest to be wrong about, and `state_verified` -- which is what a job's earned
> autonomy counts -- never counts it.
>
> Corrected twice, which is the point of writing it down. What stood here first
> -- "86.9% against 78.8%, human agreement at 94%, artifact verification 192 of
> 321 tasks" -- appears in no version of that paper and nowhere else that could
> be found. The correction on 2026-09-14 then said "measured on 322 WebVoyager
> tasks", which is also wrong: 322 is the even-`task_id` subset used for the
> SELF-VALIDATION experiment in Tables 3 and 4, while Tables 1 and 2 -- the
> 84.24/70.04/83.00 figures above -- are over the benchmark's 643 tasks. A
> replaced number is not a checked number, and the note claiming it had been
> checked made the second error harder to see than the first.
>
> Source: *Multimodal Auto Validation for Self-Refinement in Web Agents*,
> arXiv:2410.00689, Tables 1 and 2, read from the paper.

## module, [line 43](../../../../../../../backend/src/sro/application/execution/verify.py#L43): Note on the line above

Code: `_PUTS_A_VALUE = frozenset({"type", "select", "upload"})`

> The gesture kinds that put something somewhere. A step citing one of these
> is a step that can be wrong in a way nothing else on this page would show --
> the right control, the wrong text -- so it is never held on the strength of
> "the browser did something".

## module, [line 154](../../../../../../../backend/src/sro/application/execution/verify.py#L154): Note on the line above

Code: `K_SCREEN_SAID = 600`

> How much of the screen's own text a failed step keeps.
>
> Enough for a dialog and the controls around it; short enough that a run record
> cannot become a copy of the page. The digest is names and positions, which is
> what `sroPage.viewport` collects -- no values, because a form's contents are the
> operator's and a record outlives the run.

## `_was_watched`, [line 37](../../../../../../../backend/src/sro/application/execution/verify.py#L37): Docstring

> Whether the recorder saw this gesture's traffic complete.
>
> A call with no status never returned, so it is not evidence of what the
> gesture did -- the same completion guard `origin_of` and `expected_statuses`
> already wear.

## `check`, [line 46](../../../../../../../backend/src/sro/application/execution/verify.py#L46): Docstring

> Failures, in order. Empty means the step satisfied its post-conditions.

## `check_text`, [line 82](../../../../../../../backend/src/sro/application/execution/verify.py#L82): Docstring

> The same post-conditions against a body with no status code behind it.
>
> What a connector answers is a document, not an HTTP exchange, so the two
> assertions that read a document are checked and the two that read something
> else are reported as unmet rather than skipped. A `http_status` assertion
> on a tool step is a mistake in the mapping, and a mistake nothing mentions
> is a step that verified less than whoever wrote it believed.

## `check_on_screen`, [line 112](../../../../../../../backend/src/sro/application/execution/verify.py#L112): Docstring

> The same post-conditions, against a screen instead of a response.
>
> A gesture landing is not a task being done. The driver answers "performed"
> when it found a control and clicked it, and for a run in the interface that
> was the whole of the verification: a click on the wrong Save, or the right
> Save on a form the application refused, was recorded as a step that
> succeeded and counted towards the version's promotion. Verification is
> supposed to be the control that stands between a model and a warehouse.
>
> Returns failures and, separately, what could not be checked at this rung --
> a response body is not visible from here, and the honest thing is to say so
> rather than to count it as satisfied or to fail a run over it. The
> demonstration's own evidence is what is checked: the text that appeared on
> screen in both runs after this gesture.

## `extract`, [line 130](../../../../../../../backend/src/sro/application/execution/verify.py#L130): Docstring

> A derived parameter's value from this response, or ``None`` if absent.

## `already_done`, [line 157](../../../../../../../backend/src/sro/application/execution/verify.py#L157): Docstring

> Whether this write's effect is already true, said in a sentence.
>
> The verifier's second rung, asked BEFORE the write instead of after. It is
> the same question in both places -- does the system already show the value
> this run would supply -- and the answer means something different on each
> side of the send: after, the write worked; before, there is nothing to do.
>
> The run that made this worth writing signed an operator in who was already
> signed in, and there is a whole class behind it: a rule fires twice, two
> browsers fire the same job, somebody presses Yes on a card they pressed
> yesterday. Every one of those is a second record in a warehouse that wanted
> one, and no amount of care in the runner can take a duplicate back.
>
> Narrow in the same three ways the after-the-fact rung is narrow: only a
> step whose evidence shows the page performing a read after its write, only
> when this run actually carries values for the read to show, and only when
> the read comes back 2xx -- a 404 or a 503 says nothing about the state and
> must never be read as "already there", which would skip a write that never
> happened.
>
> Returns the sentence to record, or None to go ahead and do the step. None
> is the safe answer and the common one: a step with no probe, a read that
> could not be made, a body that does not carry the value.

## `_read_back`, [line 185](../../../../../../../backend/src/sro/application/execution/verify.py#L185): Docstring

> The confirming read, made, or None where it answers nothing.
>
> One function for the two callers -- the rung that judges a write and the
> precondition that decides whether to make one -- because a read that counts
> as evidence in one of them and not in the other is two rules for one fact.

## `by_what_the_page_called`, [line 210](../../../../../../../backend/src/sro/application/execution/verify.py#L210): Docstring

> The status the warehouse answered this step with, or None to look.
>
> Rung 1 of the ladder, for a step performed in a browser rather than
> replayed over http. The verifier's own docstring puts the response the
> command returned first and the screenshot last and least -- and until this
> existed, a UI step could never reach the first rung, because a click's
> reply says "I found the control and clicked it" and nothing about what the
> server said. So every step of every run this deployment has performed was
> judged by photographing the screen and asking a model: `verdict_by =
> screen`, 67 times out of 67, the slowest and weakest rung there is.
>
> The browser keeps the calls its own driven tab made for the length of the
> run -- out of the evidence plane, which still drops them, and in a bounded
> map it can be asked about. This asks, and decides only when the step's own
> demonstrated endpoint is among them:
>
> **Only a step whose evidence recorded a write.** A step that changes
> nothing has no status to be held by, and 2xx on a page's keep-alive is not
> a step being done.
>
> **Only that endpoint.** Matched by method and path shape, so an id in the
> path is not a mismatch and a telemetry beacon on the same host is not a
> match. This is `expected_statuses`' rule, which the same beacons taught it.
>
> **None means look.** No call, no status, or an endpoint nobody recognises
> is not evidence the step failed -- it is the absence of evidence, and the
> ladder goes on to the read and the screen.
>
> **The run's own url, where the run aimed one.** `path_shape` stars only a
> segment that looks like an id by its digits, so a record named by a code
> keeps its name: the demonstration's `DELETE .../customerTypes/MRN5` and
> this run's `.../customerTypes/MRN1` are two shapes, and no delete of any
> other record could ever be held by its status. Measured on the deployment
> 2026-09-22 at 15:28: the first `Delete a Customer Type` to complete was
> held by the screen, so it recorded no effect and taught the ledger
> nothing. `aimed_url` is `write_plan_for`'s url, and matching it is
> stronger than a wildcard would be -- it proves the call went to THIS run's
> record.

## `_named`, [line 259](../../../../../../../backend/src/sro/application/execution/verify.py#L259): Docstring

> The slots this run filled, as the warehouse now holds them.
>
> Same discipline as `made_by`: short values only. This is stored on the run
> for as long as the tenant keeps it, and a description field can be a
> paragraph -- what is kept is what NAMES the row.

## `verify`, [line 270](../../../../../../../backend/src/sro/application/execution/verify.py#L270): Docstring

> Did this step actually happen: state first, and a picture only last.

## `check`, [line 77](../../../../../../../backend/src/sro/application/execution/verify.py#L77): Comment

Code: `failures.append(f"cannot check UI text {expected!r} from a network replay")`

> Nothing at this rung is looking at a screen. Recorded as
> unchecked rather than passed: a UI assertion silently counted
> as satisfied is how a network replay convinces itself it
> produced a result nobody saw.

## `already_done`, [line 171](../../../../../../../backend/src/sro/application/execution/verify.py#L171): Comment

Code: `distinctive = {`

> Only values that say WHICH record. A run carries its context as well as
> its content -- a facility, a site, a warehouse -- and those appear in the
> probe's own url because they are what the page is scoped to. They also
> appear in every row it returns, so a list read would match on them and
> skip a write for a record nobody has created yet. Asked after the write
> this does not matter; asked before it, it is the difference between
> "already there" and "this is the right screen".

## `already_done`, [line 177](../../../../../../../backend/src/sro/application/execution/verify.py#L177): Comment

Code: `if got is None or not carries_every(got, distinctive):`

> EVERY distinctive value, not any of them. A job carries values that
> change from run to run beside values that do not, and `mentions` -- the
> right rule after the write, where one value coming back is the record
> coming back -- reads a record whose unchanged half matches as the record
> this run was about to create. Four live runs of a three-step job proved
> it on 2026-09-15: a new client code each time, the same reference, and
> all four skipped the write on the PREVIOUS record's reference and
> reported `held` with nothing sent.

## `_read_back`, [line 204](../../../../../../../backend/src/sro/application/execution/verify.py#L204): Comment

Code: `status = status_of(got.result) if got.ok else None`

> The read has to have come back 2xx before its body means anything. A 404
> or a 503 answers ok=True with a body that matches nothing.

## `by_what_the_page_called`, [line 226](../../../../../../../backend/src/sro/application/execution/verify.py#L226): Comment

Code: `got = await channel.send(`

> `since` is sent and the browser does not compare against it. It cannot:
> this is the server's clock and the calls are the browser's, and while
> that comparison stood -- an ISO string against a float -- it was false
> for every call ever made and this rung never once fired. The extension
> marks its own counter when a command goes out and answers with what came
> after it (`commands.js`'s `marks`), which has one clock and no skew. The
> value stays on the wire because it is what an older extension reads.

## `by_what_the_page_called`, [line 253](../../../../../../../backend/src/sro/application/execution/verify.py#L253): Comment

Code: `called={"method": method, "url": str(call.get("url", ""))},`

> What went out, for the ledger of endpoints that may be sent
> without a click. The raw url and not `shape`: which segment
> is the identifier is decided from this run's own values, and
> `shape` has already starred by a digits heuristic that never
> fires on a code like `GZ5`.

## `by_what_the_page_called`, [line 255](../../../../../../../backend/src/sro/application/execution/verify.py#L255): Comment

Code: `return None`

> The endpoint answered something the demonstration never saw. Not a
> failure and not a hold: exactly the case the rest of the ladder is
> for.

## `verify`, [line 283](../../../../../../../backend/src/sro/application/execution/verify.py#L283): Comment

Code: `origin: str | None,`

> Unused, and kept: the extension picks the probe's tab from the url itself
> (tabOnOrigin), so an origin in the payload would be ignored. The parameter
> is here because the runner calls every step's verifier the same way --
> `test_the_probe_names_no_origin_because_the_url_already_does` fails if a
> probe ever starts carrying one.

## `verify`, [line 293](../../../../../../../backend/src/sro/application/execution/verify.py#L293): Comment

Code: `if sent_kind == "http.send":`

> 1. Artifact: what the command itself returned.

## `verify`, [line 296](../../../../../../../backend/src/sro/application/execution/verify.py#L296): Comment

Code: `if status >= 400:`

> Refusal first: a demonstration that recorded a 409 would otherwise
> teach the verifier that a 409 is what success looks like. What the
> operator got is evidence, not a licence.

## `verify`, [line 299](../../../../../../../backend/src/sro/application/execution/verify.py#L299): Comment

Code: `if not rewrote and (status in wanted or (not wanted and 200 <= status < 300)):`

> Belt ORDER, not belt availability -- but only for bytes sent as
> they were recorded. `test_a_status_that_already_decided_is_not_
> second_guessed_by_a_read` is the rule, and it holds because the
> endpoint answered the demonstration the same way, so its answer
> means the demonstrated effect.
>
> A body this run RE-AIMED breaks that. The status then says
> something was created; it does not say the thing carries the
> values this run was given. The ledger's own note is the instance
> -- `csttyp truncates at 4 chars`, so a create asking for five
> characters is answered 201 and the record is four, with nobody
> told. So a re-aimed write falls through to the read-back below,
> which is the belt that can tell.

## `verify`, [line 307](../../../../../../../backend/src/sro/application/execution/verify.py#L307): Comment

Code: `probe = confirming_read(step, by_id)`

> 2. Hidden state: a read the cited evidence shows this page performs.

## `verify`, [line 308](../../../../../../../backend/src/sro/application/execution/verify.py#L308): Comment

Code: `askable = bool(confirm) if rewrote else bool(values)`

> No values means no proposition the read could confirm: a body matches
> nothing, and "nothing was found" is not evidence the step failed.
> A probe whose url carries a struck-out credential would ask with the
> marker's text in the query string; that answers nothing about the state.
> A re-aimed write is asked about the SLOTS it filled, and a plan that can
> name none of them has no proposition for a read to settle -- so it does
> not make one. Falling through to the status below is not a weaker answer
> there, it is the only true one: every field this run wrote is a field the
> demonstration shows the server rewriting, so the record will never hold
> what was posted into it however right the record is.

## `verify`, [line 312](../../../../../../../backend/src/sro/application/execution/verify.py#L312): Comment

Code: `found = record_carrying(body, confirm) if rewrote else None`

> `carries_in_slot` for a body this run re-aimed, `mentions` for the
> rest, and the difference is the whole point of reaching here at
> all. `mentions` is `any`, so a record whose UNCHANGED half matches
> reads as the record this run meant to create -- which is exactly
> what a truncated code looks like: the description still matches
> and the code does not. Measured live on 2026-09-15, four runs of
> a job that types a new code and the same reference each time all
> skipped their write and reported held on `any`.
>
> And `carries_every` is not the answer either, which is the fix
> this replaced. It searches the whole record, so it holds on a
> value sitting in a key the plan never wrote -- and it FAILS a
> correct record whenever the server stores something else in a
> slot this run filled. Measured over the 94 recorded creates whose
> request and response are both JSON objects: 16 send a value that
> appears nowhere in the answer, every one of them a `…Description`
> key holding the label its code resolved to. A failed write stops
> the run and empties the job's register of verified effects, so
> that is roughly one create in six un-earning a job for being
> right.

## `verify`, [line 315](../../../../../../../backend/src/sro/application/execution/verify.py#L315): Comment

Code: `missing_back = unreturned(body, values)`

> Held on ANY value coming back, and specific about the ones
> that did not. See `unreturned`: a warehouse that silently
> shortens a field answers exactly like one that stored it, and
> every belt in this chain compares the record to itself.

## `verify`, [line 325](../../../../../../../backend/src/sro/application/execution/verify.py#L325): Comment

Code: `made=_named(found, confirm),`

> What the warehouse called the record this step made, off
> the read-back rather than off the create's own answer.
>
> `made_by` cannot name this one and the plan said so before
> it was built: its suffix rule wants a key ending in
> `id`/`code`/`name`/`number`/`key` and the identifier here
> is `customerType`. Measured on the live create,
> 2026-09-16: 201, record created, `made` empty -- so the
> run could say it had made something and not which.
>
> The plan knows which keys this job varies, and the record
> those keys found is the record this run created. Both
> halves are read: the key the operator was shown filling,
> with whatever the warehouse kept in it, which is not
> always what was sent.

## `verify`, [line 331](../../../../../../../backend/src/sro/application/execution/verify.py#L331): Comment

Code: `refuted=True,`

> The read answered, and the record is not there. `can_try_again`
> reads this: everything else about a write that did not hold
> leaves the state unknown, and this is the one case that does
> not.

## `verify`, [line 334](../../../../../../../backend/src/sro/application/execution/verify.py#L334): Comment

Code: `status = status_of(answer.result)`

> Belt AVAILABILITY, and this is where it is decided rather than
> assumed. A re-aimed write whose evidence carries no confirming read --
> or a run with no values for one to confirm -- has nothing but its
> status, and the status is real. Falling to the screen for it would
> photograph a page to ask a model about a record the warehouse already
> answered for.

## `verify`, [line 343](../../../../../../../backend/src/sro/application/execution/verify.py#L343): Comment

Code: `changes_nothing = not writes(step, by_id) and not any(`

> 3. Visible state: last, and least.
>
> A step that changes nothing by itself -- no write in its own evidence, no
> value put anywhere. What a picture can settle about such a step is not
> what it was FOR; see `CHECK_WAY_THROUGH`.

## `verify`, [line 347](../../../../../../../backend/src/sro/application/execution/verify.py#L347): Comment

Code: `if changes_nothing and any(_was_watched(gesture) for gesture in cited):`

> Nothing to see, and for some steps nothing to have seen. A step whose
> own evidence carries no write and no typing changed nothing: it
> opened a mail, moved to a tab, followed a link. There is no state for
> rungs 1 and 2 to confirm and no proposition a picture could settle,
> so "I cannot tell" is the wrong answer -- the browser reporting that
> it performed the command and found the control is the whole of the
> evidence such a step can ever have.
>
> This matters because `run_workflow` stops on anything but `held`, and
> rightly: a step nobody watched succeed is one the rest of the job
> assumes. But every cross-system job this rig mines BEGINS with a step
> like this -- `new`'s `Create a Warehouse Equipment Type` opens the
> request in Gmail before it touches the WMS -- so an `unclear` here
> stopped the job on its first rung, every time, whatever came after.
>
> Last, and only with no screenshot, on purpose. Where a browser
> supplies one the model still looks, and a click that missed is caught
> there. This does not spend that check to save a model call; it
> answers the case where the check cannot run at all.
>
> "Changes nothing" and "we have no evidence either way" are not the
> same claim, and only the first earns a `held`. A step whose cited
> gestures recorded no completed traffic at all -- the capture missed
> it, or a re-mine took the evidence with it -- is the second, and it
> stays `unclear`. What this rung asserts is that the traffic WAS
> watched and none of it on the page's own origin mutated anything.

## `verify`, [line 348](../../../../../../../backend/src/sro/application/execution/verify.py#L348): Comment

Code: `return StepVerdict(`

> With the browser's own words for why there was no screen, where it
> gave any. A step that types a value has no status and nothing to read
> back -- the screen is its only belt -- so "no screen to look at" is
> the whole difference between a step that worked and a step recorded
> as `unclear`. Measured on the deployment, 2026-09-17 at 17:05: the
> value WAS typed (`ok: true, matched_by: component`) and the run
> collapsed the form anyway, saying four words about it.

## `verify`, [line 363](../../../../../../../backend/src/sro/application/execution/verify.py#L363): Comment

Code: `"browser_answered": {"ok": answer.ok, "status": status_of(answer.result)},`

> Not `answer.result` whole: for an http.send that is the response
> body and headers, and nothing here trims them. The model is
> judging a picture; it does not need the payload to do it.

## `verify`, [line 367](../../../../../../../backend/src/sro/application/execution/verify.py#L367): Comment

Code: `**({"next_step": next_says} if changes_nothing and next_says else {}),`

> What this screen has to be good enough FOR.
>
> Only for the rung that judges a step which changes nothing:
> that rung's whole proposition is "the job can go on from here",
> and it cannot be judged without knowing what going on means.
> `CHECK_SCREEN` checks the step's own sentence and has no
> use for it.

## `verify`, [line 370](../../../../../../../backend/src/sro/application/execution/verify.py#L370): Comment

Code: `ensure_ascii=False,`

> The redaction marker is «redacted»; the default ensure_ascii would
> write it into the prompt in a form nothing else in this system uses.

## `verify`, [line 385](../../../../../../../backend/src/sro/application/execution/verify.py#L385): Comment

Code: `aimed = primary_gesture(step, {gesture.id: gesture for gesture in cited})`

> A password is masked, so no picture can say it was typed.
>
> `CHECK_SCREEN` already tells the model not to read success from a
> page with no errors on it, and on 2026-09-22 it did exactly that: step 1
> of `run_2a9d4c7d` was held on "the sign-in form is displayed properly
> without any errors", with the box empty and nobody signed in. A rule the
> prompt states and the model ignores is not a rule.
>
> It is also unfixable by prompting, which is why this is code: the field
> shows dots whether it holds a password or nothing, so the strongest
> honest reading of that screen is "I cannot tell". That is `unclear`, and
> ✓! is the mark this panel already has for it. Nothing is lost by
> refusing: `screen` is not a state belt, so a credential step could never
> earn a job its writes either way.
> The gesture this step is AIMED at, not everything it cites.
>
> A step cites what the operator did while performing it, which on a login
> is both boxes: `Enter username or email` on this deployment cites the
> username's type and the password's. Asking whether ANY citation is a
> credential made the username step unjudgeable too, and the run stopped at
> step 0 saying a masked field cannot be read -- about a field that is not
> masked. Measured 2026-09-22, runs `run_2f59552b` and `run_60a7020e`,
> twenty minutes after the guard shipped.

## `verify`, [line 396](../../../../../../../backend/src/sro/application/execution/verify.py#L396): Comment

Code: `said = " ".join(look_after.digest.split())[:K_SCREEN_SAID]`

> The screen's OWN words beside the model's account of them.
>
> Measured on the deployment, 2026-09-17 at 23:05: `run_21b92747` filled
> the form on the page -- four steps held by the recorded locator -- and
> the Save was refused with "An exception dialog appeared and the record
> has not been created". True, and a paraphrase: the model had the picture
> and the screen text in front of it and the run kept one sentence of
> prose. Whether that dialog said a field was too long, a session had
> expired, or a code was already taken is the whole question, and it was
> thrown away.
>
> Only on a failure. A step that held needs no evidence beyond holding, and
> a digest on every step would be a run record made mostly of screens.
