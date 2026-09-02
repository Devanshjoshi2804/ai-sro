# Work that spans tabs

## Context

An operator reads a mail asking for a supplier to be created, opens the WMS,
creates it, flips back to check a detail, finishes. That is one job. This system
records it as several unrelated fragments, and can never offer it back.

The owner's words: *"the user will constantly move across tabs and do task for
whole task... our goal is to monitor everything so we can exactly do task as
person would do."*

**What already works.** Several tabs are watched at once, every event carries its
tab and host, and cross-system work has a designed answer: mine each host
separately, then propose a `JoinKind.WORKFLOW` — "two halves of one piece of
work, in two systems" — which `TeachWorkflow` induces as one skill whose steps
each run in their own system's tab. That machinery shipped and is not in
question here.

**What does not work is everything upstream of it.** Two defects, both measured
against tenant `new`'s real recordings from 2026-09-02 (282 observations across
10 hosts):

1. **Another tab's traffic cuts a run in half.** `segment._runs` walks ONE
   global time-ordered stream and ends a run whenever the host changes
   (`one.host != run[0].host`). **30 of 37 run boundaries in that data ended
   only because another host spoke** — not from the 3-minute idle bound, not
   from the 30-minute length bound. Partitioning by host first collapses 37 runs
   into 24.

   In that dataset it changes no candidate: the fragments were short, held no
   gesture, and `_segment` discarded them anyway. The repeated signature `PUT
   addresses/* → POST suppliers` is seen 3 times either way. The damage is
   latent — and it becomes real the moment a mailbox is watched beside the WMS,
   because a mail client polls constantly and every poll lands in the middle of
   the work.

2. **Interleaved halves are never counted as done together.** `occurrences`
   requires `timedelta(0) <= later.started_at - earlier.ended_at <=
   TOGETHER_WITHIN`: the second must begin *after* the first ends. An operator
   flipping between two tabs produces overlapping episodes, the gap goes
   negative, and the pair is never counted — so the join that exists for exactly
   this shape is never proposed.

**A defect fixed on the way here**, because nothing above is testable without
it: a host the operator granted was recorded nowhere. `allowsHost` and
`injectInto` both take the grants as a defaulted argument, and all five call
sites in the worker left it off — so pressing "watch this host anyway" injected
nothing, and had it injected, the one gate every event passes through would have
dropped it as excluded. Shipped as `e6e69f1`.

## Decision taken before design

The owner's, chosen against two looser alternatives: **two episodes count as one
job only where the operator actually touched both within the same window.**
Overlap alone is not enough — a mail tab polling in the background while
unrelated WMS work happens would pair them, and two doings of that is all it
takes to be offered. Gestures, not traffic.

## Design

### 1. Each host is segmented on its own stream

`segment()` partitions observations by host, then applies `_runs`,
`_repetitions` and `_one_change_each` to each host's stream independently.

Episodes are already single-host — `_runs` breaking on host change guarantees it
— so nothing about what an episode *is* changes. What changes is that a run is
no longer ended by a tab the operator is not working in.

The idle and length bounds still apply, per host. A genuine pause still ends a
run; a detour through a login host no longer does. This also repairs a
pre-existing fragmentation nobody asked about: an SSO hop (`WMS →
b2clogin → WMS`) is three runs today and one after this.

### 2. An episode records when it was touched

`Episode` gains, beside its existing `gestures: int` count:

```python
touched_from: datetime | None = None
touched_until: datetime | None = None
```

The first and last gesture in the piece — when a person actually had their hands
on it, as opposed to when the page was still talking. Set in `_segment`, which
already has the gestures in hand.

Defaulted to `None` because episodes are stored as documents inside
`task_candidates`, and every episode mined before this change has no such field.
No migration.

### 3. Done together means touched together

`occurrences` keeps its current sequential rule and adds a second way to qualify:

```python
def _together(earlier: Episode, later: Episode) -> bool:
    gap = later.started_at - earlier.ended_at
    if timedelta(0) <= gap <= TOGETHER_WITHIN:
        return True                      # sequential, exactly as today
    return _interleaved(earlier, later)
```

`_interleaved` requires all three:

- the episodes overlap in wall-clock time;
- both carry a touched window (an episode with none cannot qualify this way —
  old episodes keep their old meaning exactly);
- the touched windows are within `TOGETHER_WITHIN` of each other, so the
  operator had hands on both inside one five-minute stretch.

**Directional, deliberately.** Only the episode that started first may be the
`earlier` half. `_workflows` counts `_followed(a, b) + _followed(b, a)` against
`TOGETHER_TIMES = 2`, so a symmetric rule would let a single interleaved pair
satisfy the threshold on its own.

### 4. An episode's evidence is its own host's

`teach._inside` is `episode.started_at <= at <= episode.ended_at` — time only,
no host. That is safe today *because* episodes never overlap. Once they can, the
mail half's recording would sweep in whatever the WMS did inside its window, and
the WMS half would sweep in the mail: both systems' calls in both halves, and an
induced skill that does everything twice.

So `_inside` also requires the event's host to be the episode's.

**This is a no-op today** and must be shown to be one: `_runs` already ends a run
on a host change, so no event of another host can be inside an episode's window
in the first place. It is a guard that becomes load-bearing in step 3, added in
the same change that makes it necessary.

## What this must refuse

- Pairing two episodes that merely coincide — a mailbox open all afternoon while
  unrelated work happens on another host.
- Pairing on background traffic alone. Only gestures qualify an interleave.
- Counting one interleaved pair twice toward `TOGETHER_TIMES`.
- Changing what any already-mined episode means. An episode with no touched
  window is judged by exactly the rule that mined it.
- Letting one host's events into another host's recording.

## Verification

Every new test proved by reverting the rule it defends, per this repo's habit.

- **Per-host segmentation**: a run split only by another host's traffic becomes
  one run; a run split by a real idle gap stays two; an SSO hop no longer
  fragments the work either side of it. Against tenant `new`'s real shape: 37
  runs → 24, and the `PUT addresses/* → POST suppliers` signature still seen 3
  times, because a fix that changed what was already being found would be a
  regression, not an improvement.
- **Touched window**: set from the first and last gesture; absent where the
  piece has no gesture.
- **Interleaving**: overlapping episodes touched within the window pair;
  overlapping episodes where only background traffic overlaps do not; an
  episode with no touched window falls back to the sequential rule; one
  interleaved pair counts once, not twice.
- **Host-scoped evidence**: an event of another host inside an episode's window
  is not in that episode's recording. Also asserted to be a no-op on today's
  data, so the guard's arrival is provably invisible until step 3 needs it.
- End to end: two candidates on two hosts, interleaved, proposed as a
  `WORKFLOW` join.

## Out of scope

- **Making a mail reading a repeatable task.** Reading mail changes nothing, so
  its signature is built from every call it made, and a mail client's URLs are
  dynamic — three mails read is not three doings of one task, and it will never
  reach `WORTH_OFFERING = 3`. Nothing in this document fixes that. Until it is
  fixed there is no mail candidate to join to, which means the owner's Gmail
  example still will not complete. This is the next question, not this one.
- The mail-side watch, matchers, and the MCP mail connector — a separate spec
  already exists for those.
- `_listing_of` unscoped by collection, and the other findings parked on the
  lookup branch.
