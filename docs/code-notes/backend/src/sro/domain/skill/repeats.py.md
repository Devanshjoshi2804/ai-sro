# Notes for `backend/src/sro/domain/skill/repeats.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/repeats.py`](../../../../../../../backend/src/sro/domain/skill/repeats.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/repeats.py#L1): Docstring

> A job whose middle is done once per thing on a list.
>
> "Add these three equipment types" is one job. Until this existed the rig could
> only say it was a job that adds ONE -- so a mail carrying three rows produced
> one run that created the first, and an operator did the other two by hand while
> watching a browser that had just proved it could do them.
>
> **The list is a person's, and that is the whole of the first version.** The
> items come from what somebody wrote -- a mail the browser matched, a sentence
> typed into the panel -- so the count is a human's rather than a guess, and
> getting the block wrong costs three wrong records instead of forty. The other
> source, the list a page fetched for itself, is the more powerful one and is
> deliberately not this: it needs the list call to have been captured, it needs a
> re-read at run time, and its count is whatever the warehouse answers that day.
> `domain/skill/loop.py` is that shape, for skills, and is where it goes when the
> machinery here has done real work.
>
> **The body is contiguous.** A block with a hole in it is two blocks somebody
> has to be able to see separately, which is the same rule `Loop` states for the
> same reason.
>
> **Nothing here is the runner's decision.** What repeats is a fact about the
> job; how many times is a fact about the request. A workflow with a `Repeat` and
> a run given one item runs exactly like a workflow without one.

## module, [line 11](../../../../../../../backend/src/sro/domain/skill/repeats.py#L11): Note on the line above

Code: `K_MOST_ITEMS = 25`

> How many times one run may do the body before a person is asked again.
>
> Not a performance limit -- a limit on what one press can mean. An operator
> pressing yes on "add these" has read a mail with a handful of rows in it; a
> list of two hundred is either a mistake or a different decision, and the run
> that would make two hundred records is not the one they authorised. The cap is
> here rather than in the runner because it is part of what a repeat IS: the
> runner asks the domain rather than carrying a number of its own.

## module, [line 33](../../../../../../../backend/src/sro/domain/skill/repeats.py#L33): Note on the line above

Code: `K_CREATED = 201`

> What a record being made looks like on the wire.
>
> The whole of the difference between a job that repeats and a page that talks.
> Measured over this tenant's own jobs: the three that create something -- work
> areas, customer types, warehouse equipment types -- each POST their endpoint
> and get 201 back, while Gmail's `POST /mail/u/*/` came back 200 fourteen times
> in one doing and creates nothing anybody asked for. A detector counting
> mutations would have called drafting one message a job done fourteen times.

## module, [line 35](../../../../../../../backend/src/sro/domain/skill/repeats.py#L35): Note on the line above

Code: `K_SETTLE_S = 120.0`

> How long a pause ends a doing.
>
> The same number `mine_lately` settles on and for the same evidence: a doing of
> a real task runs 35 to 180 seconds of continuous gestures. Restated rather
> than imported, because that one is about when a sweep may READ a tenant's day
> and this one is about where one doing stops -- two questions that happen to
> have one answer today, and a shared constant would hide the day they diverge.

## `Repeat`, [line 15](../../../../../../../backend/src/sro/domain/skill/repeats.py#L15): Docstring

> The steps of a job that are done once per item, inclusive.

## `detect`, [line 38](../../../../../../../backend/src/sro/domain/skill/repeats.py#L38): Docstring

> The steps this job did more than once in the doing it was mined from.
>
> `one_occurrence` has already struck every citation but one doing's by the
> time this runs, so the job in hand describes one pass through the work --
> and an operator who added three equipment types in a row produced exactly
> that: a job with the body once, and evidence with it three times.
>
> What is counted is the CREATE, not the clicks. Real evidence never repeats
> a gesture sequence exactly -- somebody scrolls, checks a row, clicks the
> grid between one record and the next -- and matching on sequences found
> nothing at all on this tenant's day. The endpoint the create goes to is the
> same every time, the recorder captured it, and 201 is what separates a
> record being made from a page talking to itself.
>
> Four things have to hold, and each one is a way this can be wrong:
>
> **The job creates something.** Its last mutating step came back 201. A 200
> is a page saving a draft, syncing a mailbox, or updating what is already
> there, and none of those is a thing to be done again per item.
>
> **It happened twice in ONE doing.** Not twice today: a task done once this
> morning and once after lunch is a task done twice, not a job with a
> repeated block. The doing is the citations' own span, grown outwards until
> a pause longer than `K_SETTLE_S`.
>
> **The creates are different records.** Two identical bodies are one record
> posted twice -- a double submit, a retry -- and repeating a body for a list
> of one thing typed twice is not a job, it is a mistake being learnt.
>
> **The body is on the system the create is on.** A job that reads a mail and
> then makes a record repeats the making, not the reading: the mail was read
> once and says what all three records are.

## `_the_doing`, [line 71](../../../../../../../backend/src/sro/domain/skill/repeats.py#L71): Docstring

> Everything the operator did in the sitting these citations came from.
>
> Outwards from the citations rather than the citations themselves, because
> the thing being looked for is by definition what the job does NOT cite: the
> model summarised one pass and the second and third are past its last
> citation. It stops where the operator did, at a pause.

## `detect`, [line 63](../../../../../../../backend/src/sro/domain/skill/repeats.py#L63): Comment

Code: `first = made.order`

> The body is the run of steps up to the create that share its system: the
> mail was read once and says what all of the records are.
