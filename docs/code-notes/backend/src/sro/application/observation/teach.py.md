# Notes for `backend/src/sro/application/observation/teach.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/teach.py`](../../../../../../../backend/src/sro/application/observation/teach.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/teach.py#L1): Docstring

> Turning "you keep doing this" into a demonstration.
>
> The evidence for an episode is already stored, verbatim, so teaching a candidate
> does not ask the operator to do the task again -- it reads back what they did the
> last time and hands it to the same induction a deliberate demonstration goes
> through. Everything after this line is code that already existed.
>
> Sometimes it is not enough. Passive capture sees no accessibility tree and only
> the response bodies the page itself could see, so a task whose evidence will not
> induce comes back asking for one deliberate repetition rather than producing a
> skill nobody can trust.

## module, [line 49](../../../../../../../backend/src/sro/application/observation/teach.py#L49): Note on the line above

Code: `MOST_DOINGS = 10`

> How many doings of a task one teach reads.
>
> Well above the two that are diffed and the handful `worth_offering` asks for,
> and far below the number a daily task accumulates. Every doing past this is
> read for one thing -- whether a field was left empty -- and the tenth is
> unlikely to be the first to say so.

## module, [line 403](../../../../../../../backend/src/sro/application/observation/teach.py#L403): Note on the line above

Code: `MOST_PAIRS = 6`

> How many pairs to try before believing the refusal.
>
> Six is every pair among the four freshest doings. Ten doings are forty-five
> pairs, and a candidate that cannot find two runs of one task in six tries is
> saying these are not doings of one task -- which is a real answer, and the one
> `needs_demonstration` exists to give.

## `NothingToTeach`, [line 52](../../../../../../../backend/src/sro/application/observation/teach.py#L52): Docstring

> The evidence for this candidate is gone or was never enough -- or the
> decision about it was already made, by this same request racing itself
> or by whoever clicked before this click landed.

## `TaughtTogether`, [line 233](../../../../../../../backend/src/sro/application/observation/teach.py#L233): Docstring

> One skill from two candidates. Both ids, because both were spent.

## `TeachWorkflow`, [line 242](../../../../../../../backend/src/sro/application/observation/teach.py#L242): Docstring

> Two candidates a person has said are one job, taught as one skill.
>
> Segmentation runs each host on its own stream, so an episode is always one
> host's -- which makes "check the WMS, then record it in the ERP" two
> candidates and always will. What makes it teachable is that
> the operator did both halves together more than once: each of those
> occurrences is one demonstration of the whole job, and two of them are the
> pair induction wants. The two candidates are never diffed against each
> other -- that would compare the WMS half with the ERP half and call the
> difference a parameter.

## `_pairs`, [line 406](../../../../../../../backend/src/sro/application/observation/teach.py#L406): Docstring

> Every pair of doings, freshest first, nearest first.
>
> `recordings` is ordered freshest-first, so (0,1) is the pair that used to be
> the only one tried and stays the first. After that, `near + far` ascending
> prefers pairs that are both recent and adjacent: two doings from this
> morning are likelier to be two runs of one task than this morning and last
> Tuesday, because the screens move.

## `DismissCandidate`, [line 420](../../../../../../../backend/src/sro/application/observation/teach.py#L420): Docstring

> Kept rather than deleted, so the miner does not offer it again next week
> as if it were new.

## `_Evidence`, [line 477](../../../../../../../backend/src/sro/application/observation/teach.py#L477): Docstring

> One episode, read back out of the evidence plane.
>
> Addressed by time rather than by offsets: an episode spans several uploads
> and part of each, and the timestamps already say which part.

## `_Evidence`, [line 479](../../../../../../../backend/src/sro/application/observation/teach.py#L479): Note on the line above

Code: `shots: dict[int, ShotRef]`

> Where each gesture's picture would be, keyed by ``id()`` of the event
> it belongs to. Identity, because `assemble_frames` hands back the very
> objects it was given and two gestures can share a timestamp.

## `_within`, [line 510](../../../../../../../backend/src/sro/application/observation/teach.py#L510): Docstring

> This episode's slice of one batch, each gesture carrying where its
> picture would be.
>
> The counting is `numbered`'s, not this module's: it walks every gesture
> line in the batch, including the ones this episode does not want and the
> ones `_capture` cannot read, because that is what the recorder counted
> when it numbered the pictures (`upload.js`, ``framesOf``). Counting only
> the surviving gestures would slide every later picture onto the wrong one.

## `_inside`, [line 564](../../../../../../../backend/src/sro/application/observation/teach.py#L564): Docstring

> Whether this event belongs to this episode.
>
> Time and host, not time alone. Episodes on two hosts genuinely overlap now
> that `segment` runs each host on its own stream -- an operator flipping
> between a mailbox and the warehouse system produces exactly that -- and a
> window is no longer enough to say which piece of work an event was part of.
>
> Load-bearing, not a guard against a future: one batch with a mail episode
> over 0-11s and a warehouse episode over 5-6s is the whole case. With the
> host check the mail half holds its two mail calls; revert it to time alone
> and the same half also holds `wms.example/api/suppliers`, and the induced
> skill does the warehouse work twice. Anyone deleting this as dead code
> reintroduces exactly that.
>
> No fallback for an event with no URL: an empty host is only ever right for
> a `host=""` episode, and segmentation never mines one -- `_segment` drops
> any run with no calls, and a stream of URL-less events has none. Letting
> `""` slide into a real episode would readmit exactly the contamination
> this guard exists to stop.

## `_when`, [line 568](../../../../../../../backend/src/sro/application/observation/teach.py#L568): Docstring

> Whether this event's time falls in this episode's window.
>
> Host-blind, on purpose: a snapshot uses this instead of `_inside`.
> Segmentation has no snapshot branch -- an episode's window is drawn from
> its gestures and calls alone -- so a snapshot's host was never part of
> what defined an episode, and applying a host rule to it now would invent a
> constraint the partition never had. A snapshot's own `url` is the tab's,
> read by `service-worker.js`'s `takeTreeSoon`, while the episode's host
> comes from the gesture's frame URL -- the two disagree exactly for the
> cross-host iframe portal `_capture`'s gesture branch already documents,
> and host-checking the snapshot there would silently drop it.

## `_at`, [line 572](../../../../../../../backend/src/sro/application/observation/teach.py#L572): Docstring

> The recorder's float seconds, or the ISO string everything else uses.
> Same two rules segmentation applies, because it read the same lines --
> including that an offset-less string is malformed, not naive: comparing
> it against `episode.started_at` in `_inside()` below would raise rather
> than answer, and this candidate's evidence would 500 instead of asking
> for one more demonstration the way thin evidence otherwise always does.

## `_text`, [line 584](../../../../../../../backend/src/sro/application/observation/teach.py#L584): Docstring

> A string field of the payload, or nothing. The blob is whatever the
> browser uploaded, so a shape nobody expected is an absence rather than a
> crash halfway through assembling a demonstration.

## `TeachCandidate._say_yes_was_answered`, [line 138](../../../../../../../backend/src/sro/application/observation/teach.py#L138): Docstring

> Close the loop on an offer, where there was one.
>
> Only where the offer was actually made: a candidate taught from the
> console was never asked about, and answering a question nobody put
> would start a conversation to say something into it.
>
> After the candidate is saved, never with it. If the message fails the
> skill is still taught and the offer merely looks unanswered; the other
> order would record an answer to something that did not happen.

## `TeachCandidate._learn`, [line 152](../../../../../../../backend/src/sro/application/observation/teach.py#L152): Docstring

> A skill from what was watched, by the strongest instrument available.
>
> The two freshest doings are diffed against each other: what differs
> between them is a parameter, proved, and no model is asked. The older
> doings are handed over too -- for the fields somebody left empty, and
> for the steps they made, which is how a task done four different ways
> comes out as one task rather than as whatever two of them shared. One
> doing has nothing to diff, so its narrative -- what varies, what each
> step was for -- is a model reading the same evidence, and every part of
> it is marked as read rather than proven.
>
> The difference matters most to exactly the task this exists for. A
> creation seen once yields a skill that would re-create the same record
> by name; seen twice, the name is a parameter somebody can fill in.

## `TeachCandidate._induce_from_a_pair`, [line 162](../../../../../../../backend/src/sro/application/observation/teach.py#L162): Docstring

> Induce from the first pair that really is two runs of one task.
>
> The two freshest used to be the only pair tried, and one odd doing
> among them sank the whole candidate. A real case: four doings of
> "create a work area", of which the second freshest was a two-frame stub
> where somebody typed one field. Three of the six pairs aligned
> perfectly; induction picked the one that did not, and the operator was
> asked to demonstrate a task the system had watched four times.
>
> So a refusal is no longer the end of it. Freshness is still the
> preference -- the screens move, and the most recent doings are the ones
> most likely to still find their controls -- but it stops being a single
> point of failure. Pairs are tried nearest-to-freshest first, and the
> rest of the history goes along as `others` whichever pair wins, so a
> field somebody left empty and a step most doings make are still read
> from every doing.
>
> Bounded on purpose. Ten doings are forty-five pairs, and a candidate
> that cannot align in a handful of tries is telling us something --
> that these are not doings of one task -- rather than waiting to be
> brute-forced into agreement.
>
> Where every pair refuses, the freshest pair's refusal is the one
> raised: it is the two runs the operator most likely has in mind, so it
> is the explanation that will make sense to them.

## `TeachCandidate._demonstration`, [line 195](../../../../../../../backend/src/sro/application/observation/teach.py#L195): Docstring

> One doing of the task, read back out of the evidence plane as a
> recording. `None` where that doing cannot be replayed at all -- its
> batches have aged out, or nothing in it changed anything.

## `TeachWorkflow._demonstration`, [line 338](../../../../../../../backend/src/sro/application/observation/teach.py#L338): Docstring

> One occurrence of the whole job, as one recording.
>
> Each episode read on its own, so nothing between two halves that
> followed one another is ever read: that gap is where the operator
> answered an email.
>
> It is not one window across both, but it is not two watertight halves
> either, and this is the known trade rather than a surprise. The events
> are concatenated and `assemble_frames` folds them by time alone, so
> where the two halves *overlap* -- an operator flipping tabs, which is
> the shape this whole path exists for -- the other tab's traffic
> attaches to whichever frame is open. A mail poll lands on the warehouse
> click.
>
> Bounded: `diff.align` and `binding` both filter on `is_mutation`, so
> the pair still aligns and still induces the right steps. Not free:
> `understand`, `capabilities`, `_collections_read` and
> `_response_leaves` all read a frame's requests as they are, so a mail
> response's JSON can be offered as a binding source for a warehouse
> step. `is_background_traffic` does not catch it either -- a mail poll
> matches none of its markers, which is the failure its own docstring
> names.
>
> Deliberately left: fixing it means folding per host, and the frame
> boundaries that produces are a bigger question than the one this
> branch answers.

## `TeachWorkflow._name`, [line 386](../../../../../../../backend/src/sro/application/observation/teach.py#L386): Docstring

> What to call the merged skill.
>
> The model's, because neither half's title describes the job: "Update
> adjust on wms" and "Create receipts on erp" are two sentences about one
> piece of work. Nothing about identity rests on it -- the objective key
> is already decided by then.

## `TeachCandidate.execute`, [line 87](../../../../../../../backend/src/sro/application/observation/teach.py#L87): Comment

Code: `raise NothingToTeach(f"this candidate is already {candidate.status}")`

> Checked before gathering evidence and running induction, not
> only at the domain object's own guard at the end of this: a
> stale tab's retried teach, or a second operator's click after
> the first's, should not cost a full induction pass just to be
> refused by it.

## `TeachCandidate.execute`, [line 89](../../../../../../../backend/src/sro/application/observation/teach.py#L89): Comment

Code: `history = list(reversed(candidate.episodes))`

> Freshest first: the screens move, and the most recent doings of a
> task are the ones most likely to still find their controls. That is
> the rule for the two that get *diffed*, and all of them are built:
> whether a field may be left out is a fact about the whole history of
> a task rather than about the last two times somebody did it, and the
> doing that proves the warehouse takes Absolute Priority empty may be
> the first of three.
> Bounded, and the bound is said out loud. A task somebody does every
> morning has fifty sightings by the end of the month, and reading them
> all is fifty blob passes and fifty stored recordings for one teach --
> to answer a question the freshest handful has already answered.
>
> Dropped from the far end, so the two that get diffed are never among
> the losses. What a dropped doing could still have said is that some
> field may be left out, and not hearing it leaves that field required:
> a skill that asks for one value too many, which is the direction to
> be wrong in.

## `TeachCandidate.execute`, [line 106](../../../../../../../backend/src/sro/application/observation/teach.py#L106): Comment

Code: `return Taught(`

> The recordings are kept: they are evidence either way, and the
> deliberate repetition this asks for will be diffed against them.

## `TeachCandidate._induce_from_a_pair`, [line 175](../../../../../../../backend/src/sro/application/observation/teach.py#L175): Comment

Code: `others=tuple(`

> The rest of the history. Read for whether some doing left
> a field empty, and -- since ADR 015 -- for the steps they
> made: a step most doings contain is part of the task even
> when the pair happens not to share it, and a rare one
> that types a field somebody supplied is a branch rather
> than a fumble.

## `TeachCandidate._demonstration`, [line 206](../../../../../../../backend/src/sro/application/observation/teach.py#L206): Comment

Code: `demonstrator=candidate.principal_id,`

> Whose work it was, not who pressed the button. A skill's
> provenance should name the person who actually did the task.

## `TeachCandidate._demonstration`, [line 217](../../../../../../../backend/src/sro/application/observation/teach.py#L217): Comment

Code: `for artifact in await pictures(`

> The pictures of the very gestures these frames describe. Attached
> before the seal, because a sealed recording is evidence nobody may
> add to afterwards.

## `TeachWorkflow.execute`, [line 268](../../../../../../../backend/src/sro/application/observation/teach.py#L268): Comment

Code: `raise NothingToTeach(f"{candidate.title} is already a skill ({candidate.skill_id})")`

> Named, because "already taught" with no skill to go and look
> at reads as a bug, and the person is one click from what they
> were trying to make.

## `TeachWorkflow.execute`, [line 275](../../../../../../../backend/src/sro/application/observation/teach.py#L275): Comment

Code: `pairs = sorted(`

> Every doing, both ways round -- not the larger direction. The miner
> counts both ways before it decides the pair is worth suggesting, and
> an operator flipping between two tabs will not flip the same way
> twice: taking the larger of one each way induces from a single
> recording while two doings sit in the evidence.
>
> Sorted back into order after the concatenation, so `reversed` below
> is still freshest first. `spent` is what stops a pair that somehow
> qualified in both directions from becoming two recordings of one
> doing.
>
> Where the two halves each write, the two directions name different
> objectives and induction refuses them by name. That is the honest
> answer: it is what the operator did, and it is better than diffing
> one recording against itself.

## `TeachWorkflow.execute`, [line 280](../../../../../../../backend/src/sro/application/observation/teach.py#L280): Comment

Code: `recordings: list[Recording] = []`

> Freshest first: the screens move, and the most recent doing is the one
> most likely to still find its controls.
>
> No episode twice. One doing of the WMS half followed by two doings of
> the ERP half is two adjacent pairs and one occurrence: handing both to
> induction would diff a recording against itself on one side, so every
> value the operator typed in the WMS half would be proved constant by
> evidence that is literally the same bytes.

## `TeachWorkflow.execute`, [line 313](../../../../../../../backend/src/sro/application/observation/teach.py#L313): Comment

Code: `others=tuple(recording.id for recording in recordings[2:]),`

> Every doing of the two halves together, not the freshest
> two: the steps of a chained task are decided by the same
> counts as any other, and stopping at two is the intersection
> ADR 015 exists to stop taking.

## `TeachWorkflow.execute`, [line 293](../../../../../../../backend/src/sro/application/observation/teach.py#L293): Comment

Code: `return TaughtTogether(`

> Kept, as a single teach keeps its recording: two halves that will
> not induce are still the evidence a deliberate demonstration gets
> diffed against.

## `TeachWorkflow._demonstration`, [line 348](../../../../../../../backend/src/sro/application/observation/teach.py#L348): Comment

Code: `naming = list((read if earlier.host <= later.host else late).events)`

> Snapshotted before the two are joined, because `extend` folds the
> second half into the first and the naming half may be either of them.

## `TeachWorkflow._demonstration`, [line 364](../../../../../../../backend/src/sro/application/observation/teach.py#L364): Comment

Code: `objective = derive_objective_key(assemble_frames(naming).frames) or derive_objective_key(`

> Named from one half, and always the same half.
>
> No `system=`, because the candidate's host would name whichever half
> the operator opened. But the frames of the whole recording will not do
> either: `derive_objective_key` takes the LAST write, and
> `assemble_frames` folds by time, so the half the operator happened to
> finish with names the job. Somebody who closes waves and then records
> the receipt gets `close`; the week they had the ERP open already and
> did it the other way round gets `create` -- two names for one job, and
> `_check_pairable` then refuses its own pair by name.
>
> An operator flipping between two tabs does not flip the same way
> twice, and interleaving made that ordinary rather than odd.
>
> So the naming half is chosen by host, which is the one thing about
> these two that neither the operator nor the caller can vary: not the
> order they were done in, and not the order somebody named them when
> asking for the merge. Alphabetical is arbitrary and says so -- what
> matters is that a job spanning two systems is named by one of them by
> a rule that cannot depend on how anybody did it or asked for it.
>
> Falls back to the whole recording where that half asked the server
> nothing: a half that made no call cannot name anything, and a doing
> that names nothing is dropped a line below rather than kept unnamed.

## `DismissCandidate.execute`, [line 437](../../../../../../../backend/src/sro/application/observation/teach.py#L437): Comment

Code: `if candidate.offered_at is not None and self._clock and self._ids:`

> Said only where it was asked, and only where there is a clock and ids
> to say it with -- a deployment without them dismisses exactly as it
> did before rather than failing over a sentence.

## `_capture`, [line 528](../../../../../../../backend/src/sro/application/observation/teach.py#L528): Comment

Code: `if at is None or not _inside(at, _host(str(gesture.get("url") or "")), episode):`

> The same field segmentation bucketed this gesture by (`segment._observed`
> reads `gesture.url`, not the top-level `page_url` this event also
> carries for `InputEvent.page_url`) -- using a different one here would
> let this guard disagree with the partition that already decided which
> episode this gesture belongs to.

## `_capture`, [line 533](../../../../../../../backend/src/sro/application/observation/teach.py#L533): Comment

Code: `page_url=_text(event.get("page_url")),`

> The tab's URL, not the frame's. A gesture inside a portal that
> hosts its screens in an iframe reports the frame's src, and a run
> told to open that would load the frame's document on its own,
> outside the shell that gives it its session. What has to be
> reproduced is the address an operator would type.

## `_capture`, [line 526](../../../../../../../backend/src/sro/application/observation/teach.py#L526): Comment

Code: `return None`

> An exchange this deployment's domain will not accept. Skipped
> rather than failing the teach: one malformed call out of forty is
> not a reason to make somebody do the task again.

## `_capture`, [line 549](../../../../../../../backend/src/sro/application/observation/teach.py#L549): Comment

Code: `snapshot = event.get("snapshot")`

> Read here as well as on the demonstration path, because this is where
> a task the operator never deliberately taught becomes a skill -- which
> is the way this product is meant to work. Passing over the trees here
> meant a mined skill got the weaker locator ladder however many trees
> had been captured for it: a css path of framework ids assigned in
> render order, different on the next page load.

## `_capture`, [line 554](../../../../../../../backend/src/sro/application/observation/teach.py#L554): Comment

Code: `if at is None or not _when(at, episode):`

> By time alone -- see `_when`'s docstring. A snapshot's `url` is the
> tab's, not the frame's whose host the episode carries.
