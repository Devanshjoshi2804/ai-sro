# Notes for `backend/src/sro/application/observation/segment.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/segment.py`](../../../../../../../backend/src/sro/application/observation/segment.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/segment.py#L1): Docstring

> A day of watching, cut into pieces of work.
>
> Nobody says when a task starts. What is available is when things happened, so a
> piece of work is a run of activity on one host with no long pause in it -- and a
> long pause is a person doing something else, which is exactly the boundary
> wanted.
>
> Pure, and deliberately crude. Every number here should move once there is a
> week of real observation to move it against; none of them is a judgement the
> system makes about a person.

## module, [line 15](../../../../../../../backend/src/sro/application/observation/segment.py#L15): Note on the line above

Code: `IDLE = timedelta(minutes=3)`

> A pause longer than this ends the piece of work. Somebody who came back to
> the same screen after lunch is doing it again, not still doing it.

## module, [line 17](../../../../../../../backend/src/sro/application/observation/segment.py#L17): Note on the line above

Code: `LONGEST = timedelta(minutes=30)`

> And a piece of work is bounded even without a pause, because a screen left
> open all afternoon is not a task.

## module, [line 19](../../../../../../../backend/src/sro/application/observation/segment.py#L19): Note on the line above

Code: `_CALLS = ("xhr", "fetch", "")`

> What counts as the application talking. A stylesheet is not a step.

## `Observed`, [line 23](../../../../../../../backend/src/sro/application/observation/segment.py#L23): Docstring

> One thing an extension saw, flattened to what segmentation needs.

## `Segment`, [line 44](../../../../../../../backend/src/sro/application/observation/segment.py#L44): Note on the line above

Code: `signature: str`

> What makes two of these the same task: the calls it made, in order, with
> their identifiers taken out. The same question induction asks when it
> aligns two demonstrations, asked with the same function -- a second opinion
> here would cluster things induction then refuses to align.

## `read`, [line 47](../../../../../../../backend/src/sro/application/observation/segment.py#L47): Docstring

> One uploaded batch, flattened. Malformed events are skipped rather than
> raising: this reads evidence that was accepted weeks ago by a version of an
> extension nobody can go back and fix.

## `segment`, [line 51](../../../../../../../backend/src/sro/application/observation/segment.py#L51): Docstring

> Pieces of work, in the order they happened.
>
> Each host on its own stream. A run used to end whenever the next event came
> from a different host, which reads a tab the operator is not working in as a
> boundary in the work they are: in a day of real recording, 30 of 37 run
> boundaries were that and nothing else. A mail client polling in the
> background would cut every task in the warehouse system in half.
>
> Episodes were already single-host -- the old rule guaranteed it by ending
> the run -- so this changes no episode's identity. What it changes is that a
> run now ends only for the reasons that are about the work: a pause, or a
> length no piece of work has.

## `_one_change_each`, [line 66](../../../../../../../backend/src/sro/application/observation/segment.py#L66): Docstring

> A run split so that no piece holds two changes.
>
> An operator working for eight minutes without a three-minute pause is one
> run today, however many separate things they did in it -- and a piece of
> work that big is a piece of work that never happens twice: the second time
> they came at it from a different screen, the signature differs, and the two
> doings never meet.
>
> The cut is the first thing the operator touched after something changed.
> What the application does by itself between the save and that touch -- the
> grid refreshing, the record being re-read -- belongs to the task that
> caused it. Nothing here is invented: the boundary is a POST somebody caused
> and the next thing they laid a finger on.
>
> A POST somebody *caused*: a keep-alive or a performance beacon is a POST on
> a timer, and cutting there halves whatever the operator was in the middle
> of. The first real pair this produced was a whole creation and a second
> "doing" that began at the third field of the same form.

## `_repetitions`, [line 80](../../../../../../../backend/src/sro/application/observation/segment.py#L80): Docstring

> A run that is one task done several times, cut back into the several.
>
> A pause is not the only boundary there is. Somebody working through a pile
> takes the next job off it without stopping, so twenty adjustments in an hour
> arrive as one run with no gap in it -- and the piece of work that gets
> counted is "twenty adjustments", seen once, which never reaches the number
> of times that makes a task worth offering. The most repetitive work in the
> warehouse was the work this was blindest to.
>
> Cut where the sequence of calls turns out to be one block repeated: the
> period of the sequence, by its own prefix function. Exact repetition only,
> which is deliberately timid -- a run with one extra click in the middle of
> the third doing is left whole rather than cut somewhere invented. Robotic
> process mining does this by finding the back edges of a control-flow graph
> over the log and tolerating noise between them (Leno et al., ICPM 2020);
> that is the same idea with a budget for imperfection, and it is where this
> should go when there is real observation to tune it against.

## `_period`, [line 98](../../../../../../../backend/src/sro/application/observation/segment.py#L98): Docstring

> The length of the block this sequence repeats, if it repeats whole.
>
> The prefix function of string matching, over call shapes rather than
> characters: the shortest period is the length minus the longest border, and
> it is a real repetition only where it divides the length evenly and does so
> more than once.

## `_runs`, [line 116](../../../../../../../backend/src/sro/application/observation/segment.py#L116): Docstring

> One host's stream cut into runs: a pause, or a length no work has.
>
> `one.host != run[0].host` is unreachable now -- the one caller partitions
> by host first, so every stream reaching here is one host's. Kept as the
> belt on "an episode is one host's", not as the reason for it: the reason is
> the partition above. Nothing else may cite this check as the guarantee that
> two episodes cannot overlap, because they now can and do.

## `_signature`, [line 159](../../../../../../../backend/src/sro/application/observation/segment.py#L159): Docstring

> What makes two doings the same task.
>
> The changes it makes, where it makes any: a task is identified by what it
> did to the system, never by the route somebody took to get there. The same
> creation reached from a menu, from a search and from a bookmark is one task
> done three times, and before this it was three tasks done once each --
> which is the number that never earns anything.
>
> The reads are evidence of the same piece of work; they are just not what it
> *is*. That went for the ones before the change and now goes for the ones
> after it too, which is the same rule and used not to be.
>
> Including the trailing reads made the signature depend on how fast the
> operator clicked next. The segment is cut at the first thing they touch
> after something changed, so an operator who paused after saving kept the
> grid refresh and the re-reads inside it, and one who carried straight on
> did not. Two doings of the identical task, one signature `POST
> workOperations → GET workOperations → GET deviceClassFunctions → ...` and
> the other `POST workOperations`, neither ever reaching a second occurrence.
> That is the failure this function's first paragraph exists to prevent,
> arriving through the back door.
>
> Where nothing changed, the whole run identifies it: reading a screen is a
> task too, and it has nothing else to be known by.

## `_iso`, [line 240](../../../../../../../backend/src/sro/application/observation/segment.py#L240): Docstring

> A protocol timestamp, or ``None`` for one that is not.
>
> ``fromisoformat`` parses an offset-less string too, silently returning a
> naive datetime -- and a naive one sorted against a gesture's always-aware,
> epoch-derived one raises `TypeError` rather than comparing. The protocol
> requires an offset; a string without one is exactly as malformed as one
> that fails to parse at all, and this file already skips those rather than
> crashing a whole sweep over one line an old extension build sent wrong.

## `_repetitions`, [line 89](../../../../../../../backend/src/sro/application/observation/segment.py#L89): Comment

Code: `at = calls[start][0]`

> From the gesture that caused this block's first call: a task begins
> when somebody touches something, not when the page answers.

## `_segment`, [line 133](../../../../../../../backend/src/sro/application/observation/segment.py#L133): Comment

Code: `return None`

> Reading a screen is not a task, and traffic with nobody touching
> anything is a page keeping itself alive.

## `_segment`, [line 139](../../../../../../../backend/src/sro/application/observation/segment.py#L139): Comment

Code: `first_url = next((one.url for one in gestures if one.url), "")`

> Where this doing began, for a panel that has to recognise the page.
>
> A gesture's URL and not any URL: a request's is an API endpoint, and
> nobody ever navigates to one. Matching a nudge against `POST /api/
> suppliers` would be matching against an address the operator's browser
> never shows.
