# Notes for `backend/src/sro/application/observation/propose.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/propose.py`](../../../../../../../backend/src/sro/application/observation/propose.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/propose.py#L1): Docstring

> What a model may say about a task the miner found.
>
> Three things, and they are all *about* candidates rather than part of them:
> a sentence a person would recognise, a suggestion that two candidates are one
> task done two ways, and a suggestion that two are halves of one workflow across
> systems.
>
> None of it touches identity. A candidate is `(principal, signature)` compared
> for equality, because mining re-runs and induction pairs on exact keys -- and a
> model that answers slightly differently on a second pass would produce a second
> candidate whose demonstrations can never pair. See `docs/15-observation-to-tasks.md`.
>
> Every model call here is behind a deterministic filter that has already decided
> the question is worth asking. A day's candidates crossed with each other is a
> lot of pairs, and most of them are obviously unrelated to a `for` loop.

## module, [line 29](../../../../../../../backend/src/sro/application/observation/propose.py#L29): Note on the line above

Code: `MOST_PAIRS = 20`

> How many pairs one sweep will ask about. A ceiling rather than a budget: the
> answer is a sentence on a screen, and nobody's model bill should scale with how
> many tabs somebody had open.

## module, [line 31](../../../../../../../backend/src/sro/application/observation/propose.py#L31): Note on the line above

Code: `TOGETHER_WITHIN = timedelta(minutes=5)`

> How close two episodes in different systems have to be to look like halves of
> one piece of work.

## module, [line 33](../../../../../../../backend/src/sro/application/observation/propose.py#L33): Note on the line above

Code: `TOGETHER_TIMES = 2`

> And how often. Once is two things happening to be done in a row.

## module, [line 35](../../../../../../../backend/src/sro/application/observation/propose.py#L35): Note on the line above

Code: `ENOUGH_OVERLAP = 0.6`

> How much of the smaller signature has to appear in the larger before two
> candidates in one system are worth asking about.

## module, [line 37](../../../../../../../backend/src/sro/application/observation/propose.py#L37): Note on the line above

Code: `MOST_DOINGS = 8`

> How many of a candidate's readings are put in front of the model. Enough to
> say what the work was; short enough that a candidate seen ninety times does not
> arrive as ninety lines saying the same thing.

## module, [line 39](../../../../../../../backend/src/sro/application/observation/propose.py#L39): Note on the line above

Code: `Readings = dict[tuple[str, str], list[str]]`

> What the per-gesture pass made of a tenant's evidence, by `(batch, system)`.
> Both halves of the key matter: see `_doings`.

## `Proposed`, [line 46](../../../../../../../backend/src/sro/application/observation/propose.py#L46): Note on the line above

Code: `offered: int = 0`

> Offers written into an operator's thread. Each one is said exactly once
> in the life of a candidate, so a sweep reporting anything but zero here is a
> sweep that found something new to say.

## `Proposed`, [line 47](../../../../../../../backend/src/sro/application/observation/propose.py#L47): Note on the line above

Code: `asked: int = 0`

> Model calls made. Reported because this is the one part of the pipeline
> that costs money per candidate.

## `ProposeAboutCandidates`, [line 50](../../../../../../../backend/src/sro/application/observation/propose.py#L50): Docstring

> The three model slots, run over one tenant's candidates.

## `AnswerJoin`, [line 160](../../../../../../../backend/src/sro/application/observation/propose.py#L160): Docstring

> A person saying what two candidates are to each other.
>
> This is the line `docs/15` draws. A model may notice that two candidates
> look like one piece of work and say why; it may not decide that they are,
> because a candidate's identity is what makes mining re-runnable and pairing
> exact. So the suggestion waits until somebody looks.
>
> Answering `same` about a variant does the one thing that follows from it:
> the other candidate is dismissed as a duplicate of this one, naming it. Not
> deleted -- a dismissed candidate is kept precisely so the miner does not
> offer it again next week as though it were new -- and not merged, because
> merging two signatures would mean inventing a third that neither was.
>
> Answering `same` about a workflow records exactly that and nothing more.
> Two candidates in two systems being one job is a shape nothing here can
> represent yet, and a fact recorded honestly is worth more than a merge that
> would have to be undone.

## `_variants`, [line 190](../../../../../../../backend/src/sro/application/observation/propose.py#L190): Docstring

> Same operator, same system, nearly the same steps.
>
> The filter is a plain overlap of call shapes: the same task done with one
> extra page shares most of its signature, and two unrelated tasks on one
> system share the screen they both start from and little else.

## `_workflows`, [line 206](../../../../../../../backend/src/sro/application/observation/propose.py#L206): Docstring

> Same operator, different systems, done together more than once.
>
> Together in either shape `occurrences` counts: one after the other, or both
> tabs open and worked in at once.
>
> Segmentation runs each host on its own stream, so an episode is always one
> host's -- which makes this the shape no candidate can have on its own:
> "check the WMS, then record it in the ERP" is two candidates and always
> will be.

## `_settled`, [line 219](../../../../../../../backend/src/sro/application/observation/propose.py#L219): Docstring

> Whether a person has already said what this pair is.

## `occurrences`, [line 229](../../../../../../../backend/src/sro/application/observation/propose.py#L229): Docstring

> Each time an episode of `second` belongs with one of `first`.
>
> Two shapes, because a person does a job across two systems in two ways.
> They finish in the mail and move to the warehouse -- sequential, which is
> what this counted before. Or they keep both open and go back and forth,
> which produces episodes that overlap and which this counted as nothing at
> all, so the join built for exactly that shape was never proposed.
>
> The pairs themselves, because teaching the two candidates as one skill needs
> the halves that actually belong together: two doings a fortnight apart are
> two doings, and reading one window across both would sweep up whatever the
> operator did in between.
>
> Oldest first, which is how episodes are stored; the caller takes from the
> end when it wants the freshest.

## `_interleaved`, [line 245](../../../../../../../backend/src/sro/application/observation/propose.py#L245): Docstring

> Overlapping in time, and touched by a person in the same stretch.
>
> Overlap alone would pair a mailbox somebody left open with whatever else
> they did that hour: the tab was there, the client polled, and none of it
> was work. So the windows compared are the ones an episode records for when
> somebody actually had their hands on it.
>
> Directional -- only the episode that started first may be the earlier half.
> `_workflows` counts both directions against `TOGETHER_TIMES`, so a
> symmetric rule would let one interleaved pair reach the threshold alone.
>
> Ordered on `(started_at, ended_at, host)` rather than on `started_at`
> alone, because both timestamps come from event data and two tabs starting
> in the same second is not exotic. That is a total order for two episodes of
> two candidates -- their hosts differ, which is what makes them a workflow
> at all -- so exactly one direction of any pair qualifies, ties included.

## `_followed`, [line 267](../../../../../../../backend/src/sro/application/observation/propose.py#L267): Docstring

> How often an episode of `second` belongs with one of `first` -- either
> beginning just as it ended, or overlapping it with somebody's hands in both.

## `_plainly`, [line 271](../../../../../../../backend/src/sro/application/observation/propose.py#L271): Docstring

> The reason, when nothing was asked to write one.
>
> Says what was counted, so a person can weigh it: a suggestion whose reason
> is "the system thinks so" is one nobody can answer.

## `_overlap`, [line 290](../../../../../../../backend/src/sro/application/observation/propose.py#L290): Docstring

> How much of the smaller signature the larger one contains, by step.

## `_describe`, [line 297](../../../../../../../backend/src/sro/application/observation/propose.py#L297): Docstring

> What the model is shown about a candidate.
>
> Its shape, its cost, and what the rig already made of the gestures behind
> it. Still no bodies, no responses and no payloads: the readings below are
> sentences a model wrote when the gesture was captured, so putting them here
> sends nothing anywhere it has not already been.
>
> They are here because a signature is not always a description. The derived
> title reads the entity off the last changing call, which is exact for
> `POST data/WM/wm/equipmentTypes` and empty for `POST mail/u/*` -- Gmail's
> paths carry no nouns, so every mail candidate arrived at the model called
> "Create u" with one opaque step under it, and was named and judged on that.
> A pair asked "is reading mail part of creating an equipment type" could only
> be answered no. The readings are what the operator was doing, which is the
> thing the question is actually about.

## `_doings`, [line 313](../../../../../../../backend/src/sro/application/observation/propose.py#L313): Docstring

> This candidate's readings, in order, without repeats.
>
> Keyed on the system as well as the batch: one upload carries every tab the
> operator had open, and that is the whole point of it -- so a mail candidate
> keyed on the batch alone would be described with the warehouse work that
> arrived beside it, and every cross-system pair would look like one job
> because both halves were handed the same sentences.

## `_already_read`, [line 326](../../../../../../../backend/src/sro/application/observation/propose.py#L326): Docstring (debt)

> What the per-gesture pass already understood, by batch and by system.
>
> Read once per sweep rather than per candidate, and joined on the batch id
> because a candidate's episodes name their batches exactly -- no clock
> arithmetic between a browser's clock and ours.
>
> ponytail: whole-tenant read, indexed in memory. One sweep, not one per
> candidate, so it is a single pass over a tenant's evidence; a tenant with
> a year of gestures wants this narrowed to the batches the candidates name.

## `_offered`, [line 339](../../../../../../../backend/src/sro/application/observation/propose.py#L339): Docstring

> The offer, worded the way the panel words it today.
>
> A port of `plainly()` in `new-chrome-extension/src/panel/panel.js`, which
> still says this sentence over the candidate rows. Two surfaces saying the
> same thing in two wordings is how an operator learns that one of them is
> lying, so this is the same three branches and the same words.
>
> The panel's singular case ("once", "one receipt") is not ported: nothing
> below `WORTH_OFFERING` is ever offered, so `times_seen` here is at least
> three. The panel needs it because its rows show every `new` candidate
> whatever its count.

## `_noun`, [line 357](../../../../../../../backend/src/sro/application/observation/propose.py#L357): Docstring

> The noun for this task, off the signature's own path.
>
> A numeric or otherwise substituted segment (`workOperations/*`) carries no
> word, so this walks back past it looking for one that is. Empty says none
> was found, which is true of some signatures and is a case the caller words
> around rather than papering over with a placeholder.

## `_plural`, [line 363](../../../../../../../backend/src/sro/application/observation/propose.py#L363): Docstring

> Naive (`s`-only) on purpose: everything `_noun` hands this came off a
> REST path, and that is English's regular case throughout.

## `ProposeAboutCandidates._name`, [line 76](../../../../../../../backend/src/sro/application/observation/propose.py#L76): Docstring

> Slot 1: the sentence on the front.
>
> Only for candidates nothing has named yet. A title a person edited is
> theirs, and a title a model already wrote is not worth paying for
> twice.

## `ProposeAboutCandidates._join`, [line 93](../../../../../../../backend/src/sro/application/observation/propose.py#L93): Docstring

> Slots 2 and 3: what this candidate might be part of.

## `ProposeAboutCandidates._offer`, [line 121](../../../../../../../backend/src/sro/application/observation/propose.py#L121): Docstring

> Say it out loud, in the conversation the operator is already in.
>
> An offer used to be a card in the panel: it appeared, and when the panel
> closed it was gone. It is a `SYSTEM` message now -- something that
> happened rather than something anybody said -- so it survives the panel
> closing and the console sees the same exchange.
>
> **Posting one starts nothing.** The message carries the candidate and
> its counts so the panel can draw the two buttons it has always drawn,
> and pressing one makes the call it has always made. A message is a thing
> said; the press is the authorisation, and that separation is what an
> assisted run records as consent.
>
> Two rules, one property: `worth_offering` is false below
> `WORTH_OFFERING` and false for anything but a `NEW` candidate, so a task
> done twice and a task the operator dismissed are both passed over here.
> `offered_at` is the third: it is the whole reason a quarter-hourly sweep
> does not repost the same sentence forever.

## `ProposeAboutCandidates.execute`, [line 71](../../../../../../../backend/src/sro/application/observation/propose.py#L71): Comment

Code: `named, asked = await self._name(worth, said) if self._interpreter.available else (0, 0)`

> A deployment that may not call a hosted model still mines, still
> offers candidates, still teaches. It gets duller titles -- and duller
> reasons, but it still gets the suggestions: which two candidates go
> together is decided by adjacency in the evidence, and only the
> sentence about it was ever the model's.

## `ProposeAboutCandidates.execute`, [line 73](../../../../../../../backend/src/sro/application/observation/propose.py#L73): Comment

Code: `offered = await self._offer(ctx, candidates)`

> Last, so the sentence said out loud is the one the naming slot just
> wrote. Over every new candidate rather than over `worth`, because the
> two rules an offer has to obey -- often enough, and not dismissed --
> are the ones this checks for itself.

## `ProposeAboutCandidates._name`, [line 80](../../../../../../../backend/src/sro/application/observation/propose.py#L80): Comment

Code: `continue`

> The model was told to say nothing rather than guess. The
> derived title stands, which is dull and correct. Stripped
> here rather than trusting the adapter to have done it: a
> blank title would fail the candidate's own invariant, deep
> inside a sweep, over a sentence nobody needed.

## `ProposeAboutCandidates._join`, [line 97](../../../../../../../backend/src/sro/application/observation/propose.py#L97): Comment

Code: `if not _settled(first, second, kind)`

> A pair somebody has already looked at is not a question any more.
> Asking the model again would spend a call to re-suggest what a
> person answered, and `suggest` would refuse to store it anyway.

## `ProposeAboutCandidates._join`, [line 111](../../../../../../../backend/src/sro/application/observation/propose.py#L111): Comment

Code: `because, by_model = _plainly(kind, first, second), False`

> What the evidence says, in the plainest words there are. The
> model reads a pair better than a rule does and is why this
> asks it where it can -- but a suggestion nobody can make
> without one is a feature that exists only for deployments
> that pay for a model, and the pairing was never the model's
> decision to make.

## `ProposeAboutCandidates._join`, [line 112](../../../../../../../backend/src/sro/application/observation/propose.py#L112): Comment

Code: `first.suggest(Join(other_id=second.id, kind=kind, because=because, by_model=by_model))`

> On both, because a suggestion visible from only one of two
> candidates is a suggestion half the people who look will miss.

## `ProposeAboutCandidates._offer`, [line 123](../../../../../../../backend/src/sro/application/observation/propose.py#L123): Inline

Code: `return 0`

> a deployment with no clock or ids to write a message with

## `ProposeAboutCandidates._offer`, [line 129](../../../../../../../backend/src/sro/application/observation/propose.py#L129): Comment

Code: `owner = RequestContext(ctx.tenant_id, candidate.principal_id)`

> The candidate's operator, never the sweep's: `MineEverything`
> runs this as `miner`, which is nobody's conversation.

## `ProposeAboutCandidates._offer`, [line 130](../../../../../../../backend/src/sro/application/observation/propose.py#L130): Comment

Code: `found = await read.current(owner) or await start.execute(owner)`

> Started where there is none, because the moment an offer is worth
> making is not the moment to wait for the operator to speak first.
> `StartThread` is still the only way a thread comes into being.

## `ProposeAboutCandidates._offer`, [line 140](../../../../../../../backend/src/sro/application/observation/propose.py#L140): Comment

Code: `decision={`

> The prose is for the operator; this is for the panel,
> which draws its buttons from `kind == "offer"` and
> hands `candidate_id` straight back to the call that
> already existed.
>
> The last three are what the ask box opens with when
> the offer is accepted: the panel words that sentence
> off the candidate's own title, or off its signature
> where no model named it. Without them the press
> opens an empty box, which asks for nothing and so
> ranks nothing.

## `ProposeAboutCandidates._offer`, [line 152](../../../../../../../backend/src/sro/application/observation/propose.py#L152): Comment

Code: `candidate.offered_at = said_at`

> In the same transaction as the message. Written and not
> recorded means the next sweep says it again; recorded and not
> written means it is never said at all.

## `AnswerJoin.execute`, [line 178](../../../../../../../backend/src/sro/application/observation/propose.py#L178): Comment

Code: `if other.join_with(candidate_id, kind) is not None:`

> On both, because the pair is the thing being answered and a
> screen showing one of them must not still be asking.

## `_variants`, [line 197](../../../../../../../backend/src/sro/application/observation/propose.py#L197): Inline

Code: `continue`

> the same candidate; the miner would not have made two

## `_interleaved`, [line 251](../../../../../../../backend/src/sro/application/observation/propose.py#L251): Comment

Code: `return False`

> Mined before an episode recorded this. It keeps the meaning it had.

## `_plainly`, [line 273](../../../../../../../backend/src/sro/application/observation/propose.py#L273): Comment

Code: `forwards, backwards = occurrences(first, second), occurrences(second, first)`

> Both directions, because both are what `_workflows` counted: an
> operator flipping tabs will not flip the same way twice, so a pair
> that qualified once each way is proposed on 1 + 1 -- and reporting
> the larger direction alone says "1 times" for something that
> happened twice.

## `_plainly`, [line 276](../../../../../../../backend/src/sro/application/observation/propose.py#L276): Comment

Code: `order = (first, second) if len(forwards) >= len(backwards) else (second, first)`

> The order named is the one it more often went in. With one doing each
> way there is no such order, and the sentence for that case does not
> claim one: it says both tabs were open at once.

## `_plainly`, [line 277](../../../../../../../backend/src/sro/application/observation/propose.py#L277): Comment

Code: `at_once = sum(1 for earlier, later in pairs if _interleaved(earlier, later))`

> Which shape it was, because "one after the other" is simply false about
> somebody who kept both tabs open, and a reason a person cannot weigh is
> a reason nobody answers.

## `_doings`, [line 322](../../../../../../../backend/src/sro/application/observation/propose.py#L322): Comment

Code: `step = len(found) / MOST_DOINGS`

> Evenly spaced rather than the first or the last of them. A task opens with
> navigation and closes on whatever the page did afterwards, so both ends
> are the parts that say least: the first eight readings of creating an
> equipment type are a logo, a menu and a tab, and the write itself is in
> the middle. Spacing keeps the shape of the whole doing without judging
> which sentences are interesting, which would be a second model's job.

## `_already_read`, [line 333](../../../../../../../backend/src/sro/application/observation/propose.py#L333): Comment

Code: `host = urlsplit(gesture.system or gesture.url or "").hostname or ""`

> `system` is an origin and `host` is a hostname; compared as hostnames
> so `https://mail.google.com` and `mail.google.com` are one system.

## `_offered`, [line 343](../../../../../../../backend/src/sro/application/observation/propose.py#L343): Comment

Code: `return (`

> A model writes a full sentence, conjugated as one. It can only be
> said back as itself, never spliced into a noun's slot.

## `_offered`, [line 348](../../../../../../../backend/src/sro/application/observation/propose.py#L348): Comment

Code: `if not what:`

> No word survived the signature's path. Vaguer is better than visibly
> broken: "this" reads as ordinary English whatever the endpoint looked like.

## `_noun`, [line 360](../../../../../../../backend/src/sro/application/observation/propose.py#L360): Comment

Code: `return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", word).lower()`

> `workOperations` is two words to everybody except a URL. Left plural or
> singular exactly as the path spelled it; `_plural` decides what is read.
