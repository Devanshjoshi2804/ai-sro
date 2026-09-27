# Notes for `backend/src/sro/application/intent/resolve.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/resolve.py`](../../../../../../../backend/src/sro/application/intent/resolve.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/resolve.py#L1): Docstring

> A sentence to a decision: run this skill, choose between these, or neither.
>
> Retrieval decides *what* is performed. The medium ladder decides *how*. Keeping
> them apart is the point: escalating from network to UI to vision is a fallback
> for a task we are sure about, and it must never stand in for being unsure which
> task was asked for.

## module, [line 27](../../../../../../../backend/src/sro/application/intent/resolve.py#L27): Note on the line above

Code: `_READ_FLOOR = 0.5`

> Below this the reading is not used and the words are matched literally.
>
> A model that says it is unsure is more useful than one that is confidently
> wrong, and a deployment with no model at all falls here by construction --
> which is worse, and is meant to be. Reading a sentence literally is an honest
> kind of worse; pretending to understand it is not.

## module, [line 29](../../../../../../../backend/src/sro/application/intent/resolve.py#L29): Note on the line above (debt)

Code: `_LIBRARY_PAGE = 200`

> Skills are ranked in memory. A tenant's library is dozens, not millions.
>
> ponytail: when a library outgrows one page, this becomes a query -- the ranking
> is already a pure function of (skills, utterance), so only the fetch moves.

## `Resolution`, [line 35](../../../../../../../backend/src/sro/application/intent/resolve.py#L35): Note on the line above

Code: `verb: str = ""`

> What the reading said they want done. Carried so nothing downstream
> mistakes it for a value: "count the addresses" is not a question about a
> field called Count Type.

## `Resolution`, [line 37](../../../../../../../backend/src/sro/application/intent/resolve.py#L37): Note on the line above

Code: `matched: Candidate | None = None`

> The one skill this asks for, if exactly one does.

## `Resolution`, [line 39](../../../../../../../backend/src/sro/application/intent/resolve.py#L39): Note on the line above

Code: `choices: tuple[Candidate, ...] = ()`

> Offered when two candidates are too close to separate. Choosing for the
> operator here is the wrong-match failure with extra steps.

## `Resolution`, [line 41](../../../../../../../backend/src/sro/application/intent/resolve.py#L41): Note on the line above

Code: `missing_parameters: tuple[str, ...] = ()`

> Declared inputs with no value yet. A run cannot start without them, and
> asking is cheaper than a half-performed task.

## `Resolution`, [line 43](../../../../../../../backend/src/sro/application/intent/resolve.py#L43): Note on the line above

Code: `runnable: bool = False`

> Whether the matched version may be performed at all. A `recorded` skill
> has not been reviewed by anybody.

## `Resolution`, [line 45](../../../../../../../backend/src/sro/application/intent/resolve.py#L45): Note on the line above

Code: `confident: bool = False`

> False when the best skill cannot account for part of the sentence. The
> match is still offered -- it is probably right -- but as a question, because
> a partial match on a warehouse write is how the wrong thing gets done fast.

## `Resolution`, [line 47](../../../../../../../backend/src/sro/application/intent/resolve.py#L47): Note on the line above

Code: `pursuit: Pursuit | None = None`

> What to do when nothing was taught: a goal composed from what is known,
> to be worked out on the screen. Never a dead end -- a person put in front of
> an unfamiliar screen does not refuse, and neither should this.

## `Resolution`, [line 49](../../../../../../../backend/src/sro/application/intent/resolve.py#L49): Note on the line above

Code: `proposal: Proposal | None = None`

> When no skill matched: what the knowledge base says such a task would
> involve, with its sources. Never executed as though it were taught.

## `Resolution`, [line 51](../../../../../../../backend/src/sro/application/intent/resolve.py#L51): Note on the line above

Code: `question: str | None = None`

> What to ask, when the honest answer is a question.

## `Resolution`, [line 53](../../../../../../../backend/src/sro/application/intent/resolve.py#L53): Note on the line above

Code: `items: tuple[dict[str, str], ...] = ()`

> Parameter sets read out of the sentence. One per thing to do — "these
> six SKUs" is six. Shown as a table and confirmed before anything is sent,
> because getting this wrong is not a wrong answer, it is six wrong writes.

## `Resolution`, [line 55](../../../../../../../backend/src/sro/application/intent/resolve.py#L55): Note on the line above

Code: `note: str = ""`

> What the extraction could not resolve.

## `_names_another`, [line 242](../../../../../../../backend/src/sro/application/intent/resolve.py#L242): Docstring

> Whether this sentence is plainly about something else.
>
> Answering a question with a new request is allowed: an operator who asked
> for a transport mode and then said "actually, release the wave" means the
> second thing. What is not allowed is a pinned skill quietly swallowing it.

## `_describe`, [line 256](../../../../../../../backend/src/sro/application/intent/resolve.py#L256): Docstring

> Name plus what distinguishes it. Three skills called "Release Wave" are
> told apart by their facility, which is exactly why the key has one.

## `ResolveIntent._read`, [line 65](../../../../../../../backend/src/sro/application/intent/resolve.py#L65): Docstring

> What the sentence means, or nothing when there is nobody to ask.

## `ResolveIntent._nothing_taught`, [line 195](../../../../../../../backend/src/sro/application/intent/resolve.py#L195): Docstring

> No skill was taught for this. Ask the knowledge base, not the ladder.
>
> The tempting mistake is to run the nearest skill in the browser and hope
> vision sorts it out. That is a confident wrong action; a proposal the
> operator can read is a slow correct one.

## `ResolveIntent.execute`, [line 98](../../../../../../../backend/src/sro/application/intent/resolve.py#L98): Comment

Code: `reading = await self._read(utterance, after)`

> What the sentence means, read by something that reads sentences. The
> phrase lists this replaces -- "how many", "which", "list all" -- were
> each a guess about wording, and every one of them was broken by the
> next thing somebody typed. "Show the list of all transport_mode then"
> is a question by any reading and matched none of them.
>
> The reading decides nothing. It is matched against the skills that
> exist and discarded where it names something that does not, so a
> misreading costs a clarifying question rather than a wrong write.

## `ResolveIntent.execute`, [line 100](../../../../../../../backend/src/sro/application/intent/resolve.py#L100): Comment

Code: `pending = next((s for s in skills if pinned and s.id.value == pinned), None)`

> A skill already under discussion, waiting for values it asked for.
> Without this the answer to "what should the code be?" was resolved as
> a fresh request, matched nothing, and the operator was asked the same
> question again -- which is how a system teaches people not to answer
> its questions.

## `ResolveIntent.execute`, [line 102](../../../../../../../backend/src/sro/application/intent/resolve.py#L102): Comment

Code: `asking = reading.wants == "ask" if reading.confidence >= _READ_FLOOR else asks(utterance)`

> What the sentence wants, read before anything is matched against it:
> a question never matches a skill that writes, and which sentences are
> questions is something a model reads better than a phrase list.

## `ResolveIntent.execute`, [line 103](../../../../../../../backend/src/sro/application/intent/resolve.py#L103): Comment

Code: `subject = reading.entity if reading.confidence >= _READ_FLOOR else ""`

> The subject, where the reading was confident enough to name one. A
> skill that explains the verb and not the subject answers about the
> wrong thing, however well it scores.

## `ResolveIntent.execute`, [line 105](../../../../../../../backend/src/sro/application/intent/resolve.py#L105): Comment

Code: `interrupted = (`

> A question is never an answer. "How many transport modes are there,
> list them all" was swallowed by the create skill that was waiting for
> a code and a description, because it named no other task confidently
> -- so the operator asked for a list and was shown a form twice.
>
> Being asked something is the clearest possible signal that the last
> question is no longer what is being talked about, and a pinned skill
> that writes has no business answering one.
> Asked something, or plainly about something else. Read rather than
> pattern-matched: a pinned skill that writes has no business answering
> a question, however the question happens to be phrased.

## `ResolveIntent.execute`, [line 118](../../../../../../../backend/src/sro/application/intent/resolve.py#L118): Comment

Code: `if not candidates and after and (reading.continues or refers_back(utterance)):`

> A follow-up carries none of its own nouns: "I want them in detail"
> says nothing about transport modes, and resolving it alone sent the
> operator back to the knowledge base for a subject they had just been
> shown. The previous sentence supplies the subject; this one still has
> to match something, so nothing is invented -- only remembered.

## `ResolveIntent.execute`, [line 121](../../../../../../../backend/src/sro/application/intent/resolve.py#L121): Comment

Code: `if (`

> A verb nothing does. "Delete all suppliers" shares its entity with
> every supplier skill and scores well on all of them, so the reply was
> "did you mean create or list?" -- offering two things that are not
> what was asked, one of which writes. Nothing taught deletes anything,
> and saying so is the only true answer.
> Only for an instruction. A question is served by any read of the
> entity -- "how many", "count", "show" and "list" are one another's
> synonyms to everybody except a string comparison, and gating them on
> the verb sent every question to the planner.

## `ResolveIntent.execute`, [line 140](../../../../../../../backend/src/sro/application/intent/resolve.py#L140): Comment

Code: `if ambiguous(candidates) and not carrying_on:`

> Not while carrying on: the skill under discussion is not one of
> several possibilities, it is the one that asked the question being
> answered. Offering a choice here made the operator pick the same
> skill again and lose what they had just typed.

## `ResolveIntent.execute`, [line 153](../../../../../../../backend/src/sro/application/intent/resolve.py#L153): Comment

Code: `understood = reading.confidence >= _READ_FLOOR and (`

> A skill accounts for a sentence when it does what the sentence asked
> for, not when it contains every word of it. "Show the list of all
> transport modes" was read as list/transport mode with confidence, the
> right skill was matched, and the reply still asked "did you mean?"
> because "show" and "all" appear in no objective key -- hedging at the
> operator about words the reading had already resolved.

## `ResolveIntent.execute`, [line 155](../../../../../../../backend/src/sro/application/intent/resolve.py#L155): Comment

Code: `or (asking and not writes(best.version))`

> A question answered by a read is understood, whatever verb they
> used: "count the addresses" is served by the skill that lists
> them, and hedging about the word "count" is hedging about a
> synonym the reading already resolved.

## `ResolveIntent.execute`, [line 167](../../../../../../../backend/src/sro/application/intent/resolve.py#L167): Comment

Code: `items: tuple[dict[str, str], ...] = ()`

> Values second, and only for the skill that was chosen. Asking a model
> which skill to run is the wrong-match failure with a model attached.

## `ResolveIntent._nothing_taught`, [line 199](../../../../../../../backend/src/sro/application/intent/resolve.py#L199): Comment

Code: `pursuit = Pursuit.of(ctx, compose(utterance, proposal))`

> Not "teach me first". Everything known about the task is composed into
> a goal, and the browser is driven toward it -- slowly, watched, and
> captured, so the next time it is a taught skill over the API.

## `ResolveIntent._nothing_taught`, [line 202](../../../../../../../backend/src/sro/application/intent/resolve.py#L202): Comment

Code: `return Resolution(`

> A question that reached here did so because every skill that
> matched it writes, and those were excluded rather than ranked.
> Saying "teach me that task" to somebody who asked how many there
> are would be answering a question with a form.

## `ResolveIntent._nothing_taught`, [line 221](../../../../../../../backend/src/sro/application/intent/resolve.py#L221): Comment

Code: `(pursuit.question if pursuit.goal.facts else None)`

> A pursuit with nothing known behind it is not a pursuit: there
> is no screen to open and no field to fill, and pointing a model
> at a blank browser is guessing with extra steps.

## `Resolution`, [line 59](../../../../../../../backend/src/sro/application/intent/resolve.py#L59): Note on the line above

Code: `about_what_stands: bool = False`

> The sentence named no job while something stood in the conversation, so it
> is about what stands (F2). Nothing was planned and nothing is proposed; the
> caller answers from the run or the question.

## `ResolveIntent.execute`, [line 135](../../../../../../../backend/src/sro/application/intent/resolve.py#L135): Comment

Code: `if not candidates and not _work_on_a_thing(reading) and standing and await standing():`

> The explore fallback, closed where it is reached. Measured on the
> deployment: "check now", "have you recived mail", "what did you fetch from
> mail" and "i will type it here", each under a standing run or question,
> went to `_nothing_taught` and came back "Nobody has demonstrated that…".
>
> Code decides, in this order:
> 1. no candidate: the sentence names no job;
> 2. the reader's own intent does not confidently say "act on a thing"
>    (`_work_on_a_thing`) -- such a sentence asks for work, so it falls to
>    "nothing has been taught", which only offers the explore card;
> 3. something stands. `standing` is the caller's check and is awaited
>    last, so the thread's run is only read for a sentence that named
>    nothing (F2 round 1, M6).
>
> The model is never asked whether a sentence is a status question. A
> sentence that names a job is still that job; with nothing standing, the
> fallback is what it was.

## `_work_on_a_thing`, [line 233](../../../../../../../backend/src/sro/application/intent/resolve.py#L233): Docstring

> The reader, at or above the floor, says the sentence acts on a named thing:
> `wants == "act"` with a verb and an entity. "create a warehouse zone called
> Z1" reads that way; "check now" (no entity) and "what did you fetch from
> mail" (`ask`) do not. The reading only ever sends a sentence AWAY from the
> status line, towards an answer that performs nothing.

## `Resolution`, [line 61](../../../../../../../backend/src/sro/application/intent/resolve.py#L61): Note on the line above

Code: `pursuable: bool = False`

> Set only on the "nothing has been taught" replies (`_nothing_taught`, both
> the knowledge-base proposal and the "teach me the task once" variant). The
> chat decision carries it, and it is the one thing the console's explore card
> is drawn under (`offersToExplore`).
