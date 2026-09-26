# Notes for `backend/src/sro/application/chat/understand.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/understand.py`](../../../../../../../backend/src/sro/application/chat/understand.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/understand.py#L1): Docstring

> The chat door. Saying it offers the work; pressing start authorises it.
>
> The model reads the utterance against the workflows this tenant holds and
> answers which one, with which values, and what is still missing. Nothing
> performs from here: the answer is an offer the form renders, and starting a run
> is the press.
>
> Ported from `new_agent_arch/src/rig/entry.py`, plus the half of the rig's
> `/v1/chat` route that writes the bill down. The words and the response schema
> are `sro.domain.chat.reading`; this is the half that asks.
>
> The day's cap is the route's, not this module's: the rig answered 429 before it
> reached `understand`, and a cap checked after the call is a cap that has
> already paid for the call it stops.

## `Understood`, [line 22](../../../../../../../backend/src/sro/application/chat/understand.py#L22): Docstring

> What one sentence came to, and what reading it cost.
>
> `answer` has no default and is never None: every way out of `understand`
> -- named a job, named one nobody holds, or came back with nothing at all --
> went through the model and has to be billed for. A reading the caller
> cannot bill is a model call nobody can defend at the end of the month.

## `Understood`, [line 27](../../../../../../../backend/src/sro/application/chat/understand.py#L27): Note on the line above

Code: `sure: bool = True`

> Whether the sentence plainly named ONE of this tenant's jobs.
>
> `True` by default so a reading built by anything that predates this -- a
> test, an older row -- reads as it always did. What `False` means is the
> caller's: the panel asks a person which job was meant rather than pressing
> on, because a guess that creates one wrong record is a nuisance and the
> same guess against a list of twenty is twenty wrong records.

## `Understood`, [line 29](../../../../../../../backend/src/sro/application/chat/understand.py#L29): Note on the line above

Code: `also: list[str] = field(default_factory=list)`

> The other jobs it nearly said, ids only, for the question a person is
> asked. Filtered to jobs this tenant actually holds, like `workflow_id`.

## `Understood`, [line 31](../../../../../../../backend/src/sro/application/chat/understand.py#L31): Note on the line above

Code: `items: list[dict[str, str]] = field(default_factory=list)`

> The things this job is to be done for, where the operator named several.
>
> Empty for one thing, which is most sentences -- and a job run for one item
> performs exactly as a job run for none, so a caller that ignores this is
> not wrong, only limited to the first thing somebody asked for.

## `Understood`, [line 33](../../../../../../../backend/src/sro/application/chat/understand.py#L33): Note on the line above

Code: `aside: dict[str, str] = field(default_factory=dict)`

> What those fields were given, kept beside their names.
>
> A form posts far more fields than a job varies, so where the dictionary
> names the slot the write can fill it after all -- and it cannot fill a
> value this threw away. Set aside rather than in `values`, because `values`
> is what the job itself declares and this is not that.

## `Understood`, [line 35](../../../../../../../backend/src/sro/application/chat/understand.py#L35): Note on the line above

Code: `unasked: list[str] = field(default_factory=list)`

> What the request asked for that this job has no parameter for.
>
> Dropped from `values`, which is right -- a key the workflow never declared
> is a value nothing asked for. Named here because the silence was the fault:
> a job's parameters are what two doings proved VARY and the form has far
> more fields than that, so `code GV3, description X, Department Inbound` is
> a reasonable request answered by a record with no Department in it and
> nothing anywhere saying so.
>
> The run already says this after the press. Nobody can consent to a write
> they cannot see, and after the press is after the record.

## `understand`, [line 38](../../../../../../../backend/src/sro/application/chat/understand.py#L38): Docstring

> Which of these jobs the operator meant, with what values, missing what.
>
> `asked_by` is the mails each job was asked for by, where the demonstration
> recorded any -- see `domain.chat.asked_by`. It is the one thing this door
> was never shown and the one thing that says what a REQUEST for a job looks
> like, as opposed to what the job is called. A job with none is matched on
> its title and narrative exactly as it always was.

## `_fills`, [line 116](../../../../../../../backend/src/sro/application/chat/understand.py#L116): Docstring

> Whether this sentence named every parameter that job declares.
>
> Names only, because that is what the reading has: the model returns the
> slots it recognised, and a job asking for a slot nobody named cannot be
> what the sentence was about. A job that declares nothing is filled by
> anything, which is honest -- there is nothing in it to tell apart.
>
> **Only the slots the page demands.** An optional one nobody named says
> nothing about whether the sentence was about this job: the form does not
> ask for it, so a request that does not mention it is a complete request.
>
> Measured on the deployment 2026-09-22 at 07:06. `Create a Customer Type`
> grew from two parameters to four the night before, as Department and
> Manufacturer became parameters. A mail giving customer type and
> description -- everything the form demands -- then failed to fill it, the
> reading's alternative (`Reply to Email`) was never eliminated, and the
> request was dropped with "asked for a job this tenant holds more than one
> of". Learning two fields cost the job the ability to be recognised at all.

## `_things`, [line 125](../../../../../../../backend/src/sro/application/chat/understand.py#L125): Docstring

> One set of values per thing the operator named, in the order they named
> them.
>
> Filtered exactly as `values` is, and for the same reason: a key this job
> never declared is a value nothing asked for, arriving from a sentence a
> stranger could have written.
>
> A thing that survives the filter with nothing left in it is kept HERE and
> dropped by the caller, which is not a contradiction: it counts for what is
> missing -- the operator said "these two" and a thing naming nothing leaves
> every parameter of that thing unanswered -- and it is not something a run
> can be handed, because the body performed for it would repeat the previous
> thing's values.

## `read_utterance`, [line 145](../../../../../../../backend/src/sro/application/chat/understand.py#L145): Docstring

> One sentence, read against this tenant's jobs, with the bill written down.
>
> The bill, and not the sentence: there is no column for an operator's words
> about their own warehouse, and the row exists for the cap and the spend
> line, neither of which needs them.
>
> A row is written on every reading, a refusal included -- that is the case
> that matters, because it is then the only record left of a call that cost
> money and returned nothing. `now` is the caller's clock rather than one
> read here, so a test can move it.

## `understand`, [line 54](../../../../../../../backend/src/sro/application/chat/understand.py#L54): Comment

Code: `**({"asked_by": list(said)} if (said := asked_by.get(w.id)) else {}),`

> Omitted rather than empty where there are none: a field reading
> `[]` invites "this job is never asked for by mail", which is a
> claim about the tenant's history and not about the job.

## `understand`, [line 68](../../../../../../../backend/src/sro/application/chat/understand.py#L68): Comment

Code: `by_id = {w.id: w for w in workflows}`

> A job the rig does not hold is not a job: the model naming one is a
> hallucination, not an offer, and the form has nothing to render for it.

## `understand`, [line 72](../../../../../../../backend/src/sro/application/chat/understand.py#L72): Comment

Code: `declared = {p.get("name") for p in chosen.parameters if isinstance(p, dict)}`

> Values are what the run is performed with. A key the workflow never
> declared is a value nothing asked for, arriving from a sentence a stranger
> could have written -- so the offer carries only the parameters this
> workflow itself names.

## `understand`, [line 81](../../../../../../../backend/src/sro/application/chat/understand.py#L81): Comment

Code: `unasked = sorted({k for k, _ in read if k not in declared})`

> What the request asked for that this job cannot write.
>
> The dropping above is right: a key the workflow never declared is a value
> nothing asked for, arriving in a sentence a stranger could have written.
> The SILENCE is the fault. A job's parameters are what two doings proved
> VARY, and the form has far more fields than that -- so a mail saying
> "code GV3, description X, Department Inbound" is a perfectly reasonable
> request, and this made a record with no Department in it and said nothing
> anywhere.
>
> A run says so after the press (`run.unasked`). Nobody can consent to a
> write they cannot see, and after the press is after the record.

## `understand`, [line 82](../../../../../../../backend/src/sro/application/chat/understand.py#L82): Comment

Code: `aside = {k: v for k, v in read if k not in declared}`

> And what they SAID, not only which fields they named.
>
> The names alone let the card say "this job cannot set Department". The
> values are what makes it sometimes untrue: a form posts far more fields
> than a job varies, so where the dictionary names the slot the write can
> fill it after all -- and it cannot fill what was thrown away here.

## `understand`, [line 84](../../../../../../../backend/src/sro/application/chat/understand.py#L84): Comment

Code: `nearly = answer.data.get("also")`

> Read and ignored. `missing` stays in the schema because a model asked to
> name what is absent picks values more carefully than one that is not --
> but a parameter it leaves out of `missing` is a parameter the form never
> asks for, and the run then performs with whatever the recording happened
> to contain. What is missing is not an opinion: it is `declared` minus what
> arrived, sorted, because `declared` is a set and a form whose fields
> reorder between two identical sentences is a form nothing can screenshot.
>
> With several things named, a parameter is missing when some THING lacks
> it: three equipment types of which one has no voice code is a form that
> has to ask for the voice code, and a check against the job's shared
> values alone would say every parameter was supplied by somebody.
> Sure unless the model said otherwise, and never sure where it named
> another job it might have meant instead: a reading that offers an
> alternative has already said it was choosing.

## `understand`, [line 90](../../../../../../../backend/src/sro/application/chat/understand.py#L90): Comment

Code: `named = {name for name, _ in read}`

> An alternative the sentence cannot fill is not an alternative.
>
> Measured on the deployment 2026-09-19. A mail saying `customer type :-
> GZ2 / description :- undo round two` was read as `Create a Customer
> Type` -- the only job of that name, with eighty-seven runs behind it --
> and the model named `Forward an Email` as one it might have meant
> instead. `sure` went false and the mail path said nothing at all, so the
> request sat unread in a mailbox while the tenant held the job it asked
> for.
>
> The sentence settles it. `Forward an Email` declares recipients, and the
> mail names none of them; `Create a Customer Type` declares a code and a
> description, and the mail gives both. A job whose parameters this
> sentence cannot supply is not a job this sentence was asking for --
> which is a fact about the two, not a confidence.
>
> Only where the CHOSEN job is itself fully supplied: a sentence that
> fills neither is genuinely ambiguous, and this must not make it sure by
> eliminating everything.

## `understand`, [line 96](../../../../../../../backend/src/sro/application/chat/understand.py#L96): Comment

Code: `sure = (bool(answer.data.get("sure", True)) or settled) and not also`

> `settled` overrides the model's own hedge, and only in the case it was
> measured on: it named alternatives, and the sentence fills this job's
> parameters and none of theirs. A model unsure for some OTHER reason
> names nothing to be unsure between, and is left exactly as it was.

## `understand`, [line 98](../../../../../../../backend/src/sro/application/chat/understand.py#L98): Comment

Code: `items = [item for item in items if item]`

> A thing the filter emptied still counts here. The operator said "these
> two", and a run that quietly does one of them is a run that did not do
> what was asked -- so the parameters that thing did not name are missing,
> the form asks for them, and nothing starts on a guess.

## `understand`, [line 99](../../../../../../../backend/src/sro/application/chat/understand.py#L99): Comment

Code: `wanted = {`

> And only the ones the PAGE asks for.
>
> `declared` is every parameter the job has learnt, and a job learns a
> parameter from two doings that varied a field -- which says the operator
> filled it twice, not that the form demands it. Measured on the
> deployment 2026-09-22 at 11:35: `Create a Customer Type` asked for
> Department after the same run's own question had said "I can also set
> Department and Manufacturer ... or I will run without". Two doors, two
> answers, and the one the operator met first was the wrong one.
>
> `demanded` is the rule the runner and the run's question already read.
> This is the third reader and the last: `1f136432` changed what stops a
> run and `581b0941` what its question says, and neither reached the door
> that places a sentence against the jobs.

## `read_utterance`, [line 154](../../../../../../../backend/src/sro/application/chat/understand.py#L154): Comment

Code: `cited = await uow.gestures.gestures_for(`

> The mails behind each job, read off the gestures they cite. One query for
> every job the tenant holds, before the model call rather than per job:
> the alternative is a round trip per workflow on the door an operator
> waits at.

## `read_utterance`, [line 168](../../../../../../../backend/src/sro/application/chat/understand.py#L168): Comment

Code: `workflow_id=got.workflow_id,`

> What the offer came to, which is None when the model named a job
> nobody holds. The sentence it read is not here and has nowhere to
> go: `ChatReading` has no field for it.

## `understand`, [line 63](../../../../../../../backend/src/sro/application/chat/understand.py#L63): Comment

Code: `"request": json.dumps({"said": utterance, "jobs": held}, indent=2, ensure_ascii=False)`

> The redaction marker is «redacted», and the default ensure_ascii
> writes it into the prompt as \u00abredacted\u00bb -- a form
> nothing else in this system uses. Every json.dumps on a path to a
> prompt or to the store says so.
