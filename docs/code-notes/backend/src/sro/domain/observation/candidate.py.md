# Notes for `backend/src/sro/domain/observation/candidate.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/candidate.py`](../../../../../../../backend/src/sro/domain/observation/candidate.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/candidate.py#L1): Docstring

> A task somebody keeps doing.
>
> Derived, and recomputable: an episode is a slice of a day's observation, and a
> candidate is a class of episodes that look like the same piece of work. Both
> come out of evidence that is kept verbatim, so a better miner is re-run over
> what is already stored rather than needing a new week of watching.

## module, [line 11](../../../../../../../backend/src/sro/domain/observation/candidate.py#L11): Note on the line above

Code: `K_GESTURES_IN_A_DOING = 2`

> How much has to happen in a typical doing before it may be OFFERED.
>
> A doing of one gesture is a click, not a task. Without this the panel offered
> an operator "you've created 11 us here -- about 1s each" beside a real job, and
> the bad ones outnumbered the good: `u`, `fd` and `bv` are path segments out of
> Gmail's urls, one gesture and half a second each, repeated because opening mail
> is repetitive.
>
> Two, measured on both tenants rather than chosen. Every candidate a model had
> named and any operator would recognise ran 10 to 19 gestures per doing --
> create a work area 19, create an activity code 18, a carrier cross-reference
> 12, an equipment type 10. Every candidate nobody could read ran EXACTLY one.
> There is no candidate anywhere in this store between 2 and 9, so the floor sits
> in a gap eight wide and the number could move either way without changing what
> it admits.
>
> It gates the offer and nothing else. The candidate is still mined, still
> counted, still joinable, and still there to be taught deliberately -- what this
> refuses is interrupting somebody about it.

## module, [line 13](../../../../../../../backend/src/sro/domain/observation/candidate.py#L13): Note on the line above

Code: `WORTH_OFFERING = 3`

> How many times something has to have been done before it is proposed.
>
> Twice is a coincidence and the operator knows it; being asked about
> coincidences is how a recommendation surface gets ignored. Kept from two so the
> count is already there when the third happens.

## `Episode`, [line 23](../../../../../../../backend/src/sro/domain/observation/candidate.py#L23): Docstring

> One doing of it. Addressed by time rather than by offsets into an upload,
> because a task takes minutes and an upload covers a minute -- the evidence
> for one episode is several batches, and which part of each is a question the
> timestamps already answer.

## `Episode`, [line 31](../../../../../../../backend/src/sro/domain/observation/candidate.py#L31): Note on the line above

Code: `touched_until: datetime | None = None`

> When a person actually had their hands on this, first and last -- as
> opposed to when the page was still talking.
>
> Two tabs are one job when somebody worked in both, and a mail client polling
> in the background is not somebody working. Optional because every episode
> mined before this existed has no answer, and an episode with no answer is
> judged by the rule that mined it.

## `Episode`, [line 33](../../../../../../../backend/src/sro/domain/observation/candidate.py#L33): Note on the line above

Code: `starts_on: str = ""`

> Host and path of the first page this episode was seen on, no query.
>
> The page a task begins on, which is what lets the panel say "you have done
> this here before" the moment somebody lands on it. Without the query,
> because that is where a warehouse system puts session ids and timestamps,
> and a page that is never the same page twice is one nothing recognises.
>
> Empty where no URL was observed -- older evidence, and gestures an extension
> sent before it carried one. A candidate that starts nowhere never nudges,
> which is the honest behaviour rather than a guess at where it began.

## `JoinKind`, [line 48](../../../../../../../backend/src/sro/domain/observation/candidate.py#L48): Note on the line above

Code: `VARIANT = "variant"`

> The same piece of work done two ways -- an extra page, a different
> order. Two candidates because the signature is compared for equality, which
> is the property that keeps identity stable.

## `JoinKind`, [line 50](../../../../../../../backend/src/sro/domain/observation/candidate.py#L50): Note on the line above

Code: `WORKFLOW = "workflow"`

> Two halves of one piece of work, in two systems. Segmentation runs each
> host on its own stream, so an episode is always one host's: this is a shape
> no single candidate can ever have.

## `JoinAnswer`, [line 54](../../../../../../../backend/src/sro/domain/observation/candidate.py#L54): Note on the line above

Code: `SAME = "same"`

> A person looked and said yes. For a variant that means one of the two is
> a duplicate; for a workflow it means the pair is one job done in two
> systems, which no single candidate can represent.

## `JoinAnswer`, [line 56](../../../../../../../backend/src/sro/domain/observation/candidate.py#L56): Note on the line above

Code: `DIFFERENT = "different"`

> A person looked and said no. Kept rather than deleted, for the same
> reason a dismissed candidate is kept: a question somebody has already
> answered must not be asked again next week as though it were new.

## `Join`, [line 60](../../../../../../../backend/src/sro/domain/observation/candidate.py#L60): Docstring

> A suggestion that this candidate and another are one thing, and what a
> person said about it.
>
> Until somebody answers, it is a suggestion and nothing acts on it -- a
> suggestion the system acted on would be a task identity a model decided
> after all. The answer is what turns it into a fact, and it names who said
> so, because "these two are the same task" is a claim about somebody's work.

## `TaskCandidate`, [line 81](../../../../../../../backend/src/sro/domain/observation/candidate.py#L81): Docstring

> An episode class, and what it would be worth automating.
>
> A proposal to a person, never something the system acts on. Nothing here
> starts a run; teaching it produces a recording, which goes through induction
> and the promotion ladder like any demonstration somebody gave on purpose.

## `TaskCandidate`, [line 92](../../../../../../../backend/src/sro/domain/observation/candidate.py#L92): Note on the line above

Code: `joins: tuple[Join, ...] = ()`

> What this candidate might be part of. See `Join`.

## `TaskCandidate`, [line 94](../../../../../../../backend/src/sro/domain/observation/candidate.py#L94): Note on the line above

Code: `named_by_model: bool = False`

> Whether the title is a model's reading of the evidence. It is the only
> part of a candidate anything generated, and it is marked so nobody mistakes
> a sentence for a fact.

## `TaskCandidate`, [line 96](../../../../../../../backend/src/sro/domain/observation/candidate.py#L96): Note on the line above

Code: `starts_on: str = ""`

> The page the first doing of this began on. See `Episode.starts_on`.
>
> Lifted onto the candidate so a panel can ask "is this the page?" against a
> list it already has, rather than loading every episode of every candidate on
> every navigation.

## `TaskCandidate`, [line 98](../../../../../../../backend/src/sro/domain/observation/candidate.py#L98): Note on the line above

Code: `offered_at: datetime | None = None`

> When this was said out loud to the operator, if it has been.
>
> Exists so a conversation does not repeat itself. The offer is a message in
> a thread now rather than a card that vanishes with the panel, and mining
> sweeps run every quarter of an hour over evidence they have already read --
> without this, every one of them would post the same sentence again, and a
> conversation that repeats itself is one nobody reads.
>
> A timestamp rather than a flag, because "when were they asked" is the
> question anybody debugging a re-offer actually has.

## `TaskCandidate`, [line 100](../../../../../../../backend/src/sro/domain/observation/candidate.py#L100): Note on the line above

Code: `learned_from: int = 0`

> How many doings had been seen the last time learning was tried on this.
>
> Unattended learning runs on a sweep, and a candidate whose evidence will
> not induce would otherwise be tried again every quarter of an hour, leaving
> two sealed recordings behind each time. Trying again is only worth it when
> there is something new to try it on.

## `TaskCandidate`, [line 102](../../../../../../../backend/src/sro/domain/observation/candidate.py#L102): Note on the line above

Code: `learned_under: int = 0`

> Which version of the induction rules made that attempt.
>
> The other half of "something new": rules change too. A candidate refused
> under rules that have since been fixed would otherwise sit refused
> forever, silently, while the code that could learn it is already merged.
> Zero means the attempt predates anyone counting.

## `TaskCandidate.worth_learning_again`, [line 115](../../../../../../../backend/src/sro/domain/observation/candidate.py#L115): Docstring

> Whether a fresh attempt would see anything the last one did not.
>
> Two ways it might: a doing arrived that the last attempt never read, or
> induction has learned to read what it already had. The version is given
> rather than known here, because which rules are current is not
> something a task somebody keeps doing has any business knowing.

## `TaskCandidate.median_duration_ms`, [line 131](../../../../../../../backend/src/sro/domain/observation/candidate.py#L131): Docstring

> The middle one, not the mean. One episode where somebody went to
> lunch mid-task would otherwise decide what the task costs.

## `TaskCandidate.status_is_new`, [line 137](../../../../../../../backend/src/sro/domain/observation/candidate.py#L137): Docstring

> Whether anything may still be decided about it. `dismiss` and
> `taught` both refuse otherwise, and a second answer to one join should
> not raise because the first already dismissed the duplicate.

## `TaskCandidate.typical_doing`, [line 149](../../../../../../../backend/src/sro/domain/observation/candidate.py#L149): Docstring

> Gestures in a middling doing of this.
>
> The median and not the mean: one long doing where somebody was
> interrupted should not promote a candidate whose other ten were a
> click, and one click should not demote a real task done ten times.

## `TaskCandidate.observed`, [line 156](../../../../../../../backend/src/sro/domain/observation/candidate.py#L156): Docstring

> Record another doing of it. Answers whether this was new.
>
> Mining runs again over evidence it has already read, so the same
> episode arriving twice must not become two occurrences -- a count of how
> often something happened is the whole reason a candidate exists.

## `TaskCandidate.suggest`, [line 168](../../../../../../../backend/src/sro/domain/observation/candidate.py#L168): Docstring

> Record a suggestion about this candidate. Answers whether it was new.
>
> Replaces an earlier suggestion about the same pair rather than
> accumulating: the question was asked again because the evidence grew,
> and two answers to one question on a screen is a screen nobody trusts.
>
> A pair somebody has already answered is left exactly as it is. Nothing
> a model notices next week overrules a person who looked at these two
> candidates and said what they were.

## `TaskCandidate.answer`, [line 185](../../../../../../../backend/src/sro/domain/observation/candidate.py#L185): Docstring

> Somebody looked at the pair and said what it is.
>
> Answerable only where something was suggested: an answer to a question
> nobody asked has no evidence attached to it, and the reason a person
> was shown these two together is half of what makes the answer readable
> later.

## `TaskCandidate.dismiss`, [line 195](../../../../../../../backend/src/sro/domain/observation/candidate.py#L195): Docstring

> Not worth automating, said by a person. Kept rather than deleted, so
> the miner does not offer it again next week.

## `TaskCandidate._require_new`, [line 207](../../../../../../../backend/src/sro/domain/observation/candidate.py#L207): Docstring

> Both transitions are one-way and terminal. Without this, a stale
> tab's retried teach after a dismissal -- or a second operator's click
> after the first's -- silently overwrites the decision already made:
> a rejected task becomes a skill, or an existing skill's id is replaced
> and every trigger still pointing at it is orphaned.
