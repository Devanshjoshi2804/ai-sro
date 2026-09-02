# The panel is a conversation

## Context

The panel today is a stack of cards: a watching card that occupies the top
third whatever it says, a "tasks you keep doing here" list, a large empty
middle, and a console that opens over the lot when you press "Ask for a task".
The offer an operator most wants — *"you've done this 3 times, want me to do the
next one?"* — is a card that appears, and is gone when the panel closes.

The owner's words: *"this whole will be chat interface all notification would
you like me too do or this task done 3 times etc will be shown in chat and it
will interact wholely with our browser."*

**Most of this exists.** There is a chat system server-side and the console
already uses it:

- `domain/chat/thread.py` — `Thread`, `Message`, and a `Speaker` enum whose
  `SYSTEM` member is documented as *"Things that happened rather than things
  anybody said: a run finished, a skill was induced."* That is what an offer is.
- `Message.decision: dict[str, object]` — structured, beside the prose, because
  *"why did it do that" is answered by the resolution, not by the sentence that
  reported it*. That is where an offer's candidate, its count and its timing go,
  and what the panel renders buttons from.
- `application/chat/converse.py`, `read_threads.py`, and
  `POST /v1/threads/{id}/messages`, which answers with the whole thread.

So the panel is not getting a chat system. It is becoming a client of the one
the console already talks to.

## Decisions taken before design

Both the owner's:

- **An offer is a real message in the thread**, not a panel-only card. One
  conversation: the same offer appears in the panel and in the console's
  Threads view, survives the panel closing, and the answer is recorded as part
  of it.
- **One continuous thread** per operator, across every tab. Not one per host —
  a job that spans a mailbox and the warehouse system belongs in one place, and
  splitting it by host is the exact failure being fixed elsewhere.

## Design

### 1. The watching card collapses

The panel's first row becomes a single line: the dot, the host, and its state —
`● localhost · not watching` or `● bf56-kms… · watching, 53m`. A chevron expands
it to what the card says today, buttons included.

Collapsed by default when the state is steady and the operator has been told it
once. Expanded when it needs an answer — not watching a host that is excluded,
a grant that has run out, calls that cannot be recorded. The rule is that the
row expands itself when there is something to press, and stays a line when
there is not.

`panel.js` is 1679 lines. The transcript goes in its own module rather than
growing it further; the collapsed row stays in `panel.js` because it is the same
state machine that renders there today.

### 2. The panel renders one thread

Below the row: the transcript, oldest at the top, and a composer at the bottom.

Three speakers, three shapes:

- **operator** — what they typed.
- **assistant** — what the system answered, with whatever `decision` it reached.
- **system** — things that happened. An offer, a run that finished, a skill that
  was induced.

The composer posts to `POST /v1/threads/{id}/messages`, which already returns
the whole thread, so the panel re-renders from the answer rather than appending
locally and hoping.

The existing "Ask for a task" console is this, and is replaced by it. Its
suggestion list becomes the composer's placeholder and its first assistant
message on an empty thread.

### 3. An offer is written into the thread, once

Where a candidate crosses `WORTH_OFFERING`, a `SYSTEM` message is appended to
the operator's thread:

```
text:     "You've created a carrier cross-reference here 3 times, about 51s
           each. Want me to do the next one?"
decision: {"kind": "offer", "candidate_id": ..., "times": 3,
           "seconds_each": 51, "host": ...}
```

The panel renders `decision.kind == "offer"` with the two buttons it shows
today, and pressing one is the same call it makes today. Nothing about how a
run is authorised changes: the offer is a message, the press is still the
operator's confirmation, and an assisted run still records it as such.

**Written once.** `TaskCandidate` gains `offered_at: datetime | None`, set when
the message is posted and checked before posting. Candidates are documents
inside `task_candidates`, so this is a defaulted field and no migration — the
same precedent as `skill_id` and the episode counters. Without it every mining
sweep would repost the same offer, and a conversation that repeats itself is
one nobody reads.

`ProposeAboutCandidates` is where this belongs: it is already the use case that
decides what is worth saying to an operator, and it already names candidates and
proposes joins.

### 4. The thread the panel shows

One per operator, continuous. `GET /v1/threads` lists; the panel needs "the
current one, making it if there is none", which is one endpoint —
`GET /v1/threads/current` — rather than the panel guessing from a list.

The panel holds the id in `chrome.storage` so a reopened panel returns to the
same conversation, and re-resolves it if the stored one is gone.

## What this must refuse

- Posting the same offer twice.
- Posting an offer for a candidate the operator already dismissed.
- Running anything because a message says so. A message is a thing said; the
  press is the authorisation, and that separation is what an assisted run
  records.
- Showing a thread from another operator or another tenant — the endpoint is
  scoped by the request context like every other.
- Losing the watching state. The collapsed row must still say, in one line,
  whether this tab is evidence — an operator who cannot tell is the failure this
  panel already has a test for.

## Verification

- **Collapsed row**: renders the host and state in one line; expands when there
  is an action; stays collapsed when there is not.
- **Transcript**: the three speakers render distinctly; an `offer` decision
  renders its buttons; an unknown `decision.kind` renders its prose and no
  buttons rather than breaking.
- **Composer**: posting re-renders from the returned thread.
- **Offer written once**: a second mining sweep over the same candidate posts
  nothing; a candidate that has not reached `WORTH_OFFERING` posts nothing; a
  dismissed candidate posts nothing.
- **Thread continuity**: the panel reopens onto the same thread; a stored id
  that no longer resolves is replaced rather than erroring.
- **Browser**: the existing panel tests must keep passing — in particular the
  one asserting the operator can tell whether this tab is being recorded.

## Out of scope

- The console's Threads view, which already renders threads and is not changed.
- Making the assistant *do* anything new. This is a surface over the existing
  intent, offer and run paths.
- Mail, MCP, and cross-tab mining — separate specs.
