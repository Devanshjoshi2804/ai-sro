# Work that spans tabs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A job an operator does across two tabs is mined as two halves that can be offered as one, instead of as fragments that are never offered at all.

**Architecture:** Four changes to the mining core. Each host is segmented on its own stream so another tab cannot cut a run in half; an episode records when a person actually touched it; two episodes count as one job when those touches overlap; and an episode's evidence is scoped to its own host so overlapping episodes cannot contaminate each other.

**Tech Stack:** Python 3.14, pytest, ruff, mypy. No new dependency, no wire change, no migration — episodes are documents inside `task_candidates`.

**Spec:** `docs/superpowers/specs/2026-09-02-work-that-spans-tabs-design.md`

## Global Constraints

- **Nothing already mined changes meaning.** An episode with no touched window is judged by exactly the rule that mined it. Every new field is defaulted; every new rule is additive.
- **Gestures, not traffic.** Only a gesture qualifies an interleave. Background polling must never pair two episodes — that is the owner's decision and the whole point of the chosen rule.
- **No migration.** `Episode` lives inside the `episodes` JSONB document on `task_candidates`. Adding a defaulted field is the same precedent as `gestures` and `calls`.
- **Hexagonal boundaries.** `Episode` is domain (`sro/domain/observation/candidate.py`) and may be edited; it must gain no dependency on application code. `segment.py`, `propose.py`, `teach.py` are application. import-linter enforces this and `make lint` runs it.
- **Prove each new rule by reverting it.** A test that still passes with the rule removed is not a test.
- Run a file: `cd backend && uv run pytest <path> -q`. Full gate: `make lint`, `make types`, `make test-unit` (1327 passing at HEAD).
- Never `git add -A`; commit the paths each task names, then `git show --stat HEAD`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/src/sro/domain/observation/candidate.py` | What a candidate and an episode are | `Episode` gains `touched_from` / `touched_until` |
| `backend/src/sro/application/observation/segment.py` | A day of watching, cut into pieces of work | `segment()` partitions by host; `_segment` records the touched window |
| `backend/src/sro/application/observation/propose.py` | What to offer, and what looks like one job | `occurrences` accepts an interleave |
| `backend/src/sro/application/observation/teach.py` | Building a recording from an episode | `_inside` also matches the host |
| `backend/tests/unit/application/test_work_that_spans_tabs.py` | New | Every rule in this plan |

---

## Task 1: Each host is segmented on its own stream

**Files:**
- Modify: `backend/src/sro/application/observation/segment.py`
- Test: `backend/tests/unit/application/test_work_that_spans_tabs.py` (create)

**Interfaces:**
- Produces: `segment(observed)` unchanged in signature and return type; only the grouping inside changes.

- [ ] **Step 1: Write the failing test**

```python
from datetime import UTC, datetime, timedelta

from sro.application.observation.segment import Observed, segment
from sro.domain.shared.identifiers import BatchId

AT = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
BATCH = BatchId("bat_one")


def _gesture(seconds: int, host: str) -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds), kind="gesture", host=host,
        batch_id=BATCH, url=f"https://{host}/screen",
    )


def _call(seconds: int, host: str, method: str = "POST") -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds), kind="request", host=host, batch_id=BATCH,
        method=method, url=f"https://{host}/api/suppliers", mutating=method != "GET",
    )


def test_another_tab_talking_does_not_cut_the_work_in_half() -> None:
    """A mail client polls while somebody works in the warehouse system. The
    poll is not a boundary in their work -- it is not even their work."""
    work = [
        _gesture(0, "wms.example"),
        _call(1, "wms.example"),
        _call(2, "mail.example", "GET"),   # another tab, mid-task
        _gesture(3, "wms.example"),
        _call(4, "wms.example"),
    ]

    pieces = segment(work)

    wms = [piece for piece in pieces if piece.episode.host == "wms.example"]
    assert len(wms) == 1, f"the warehouse work was cut into {len(wms)} pieces"
    assert wms[0].episode.gestures == 2


def test_a_real_pause_still_ends_the_work() -> None:
    """Partitioning by host must not swallow the bound that says a person went
    away and came back to do it again."""
    work = [
        _gesture(0, "wms.example"),
        _call(1, "wms.example"),
        _gesture(60 * 20, "wms.example"),  # twenty minutes later, past IDLE
        _call(60 * 20 + 1, "wms.example"),
    ]

    assert len(segment(work)) == 2
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/unit/application/test_work_that_spans_tabs.py -q`
Expected: FAIL on the first test — the warehouse work is cut into 2 pieces.

- [ ] **Step 3: Implement**

In `segment.py`, replace the body of `segment()`:

```python
def segment(observed: Sequence[Observed]) -> tuple[Segment, ...]:
    """Pieces of work, in the order they happened.

    Each host on its own stream. A run used to end whenever the next event came
    from a different host, which reads a tab the operator is not working in as a
    boundary in the work they are: in a day of real recording, 30 of 37 run
    boundaries were that and nothing else. A mail client polling in the
    background would cut every task in the warehouse system in half.

    Episodes were already single-host -- the old rule guaranteed it by ending
    the run -- so this changes no episode's identity. What it changes is that a
    run now ends only for the reasons that are about the work: a pause, or a
    length no piece of work has.
    """
    by_host: dict[str, list[Observed]] = {}
    for one in observed:
        by_host.setdefault(one.host, []).append(one)
    pieces = [
        found
        for stream in by_host.values()
        for run in _runs(sorted(stream, key=lambda one: one.at))
        for block in _repetitions(run)
        for piece in _one_change_each(block)
        if (found := _segment(piece)) is not None
    ]
    return tuple(sorted(pieces, key=lambda piece: piece.episode.started_at))
```

`_runs` keeps its host check untouched: it is now always false within a stream, and it is the guarantee that an episode is single-host.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit -q`
Expected: the new tests pass and the whole unit suite passes.

- [ ] **Step 5: Prove the rule**

Revert `segment()` to the single global stream and confirm `test_another_tab_talking_does_not_cut_the_work_in_half` fails. Restore by editing back, never by `git checkout` — the change is not committed yet.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro/application/observation/segment.py backend/tests/unit/application/test_work_that_spans_tabs.py
git commit -m "feat(observation): a tab you are not working in is not a boundary in your work"
```

---

## Task 2: An episode records when it was touched

**Files:**
- Modify: `backend/src/sro/domain/observation/candidate.py`, `backend/src/sro/application/observation/segment.py`
- Test: `backend/tests/unit/application/test_work_that_spans_tabs.py`

**Interfaces:**
- Produces: `Episode.touched_from: datetime | None`, `Episode.touched_until: datetime | None`

- [ ] **Step 1: Write the failing test**

```python
def test_an_episode_says_when_somebody_had_their_hands_on_it() -> None:
    """When the page was still talking is not when a person was working. Only
    the second can say two tabs were one job."""
    work = [
        _call(0, "wms.example", "GET"),    # the screen loading
        _gesture(5, "wms.example"),
        _gesture(9, "wms.example"),
        _call(10, "wms.example"),
        _call(30, "wms.example", "GET"),   # the grid refreshing afterwards
    ]

    (piece,) = segment(work)

    assert piece.episode.touched_from == AT + timedelta(seconds=5)
    assert piece.episode.touched_until == AT + timedelta(seconds=9)
    assert piece.episode.started_at == AT, "the episode still covers the whole piece"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL with `AttributeError: 'Episode' object has no attribute 'touched_from'`

- [ ] **Step 3: Implement the field**

In `domain/observation/candidate.py`, beside `gestures` and `calls`:

```python
    touched_from: datetime | None = None
    touched_until: datetime | None = None
    """When a person actually had their hands on this, first and last -- as
    opposed to when the page was still talking.

    Two tabs are one job when somebody worked in both, and a mail client polling
    in the background is not somebody working. Optional because every episode
    mined before this existed has no answer, and an episode with no answer is
    judged by the rule that mined it.
    """
```

- [ ] **Step 4: Implement the recording**

In `segment.py`'s `_segment`, which already holds `gestures`:

```python
            gestures=len(gestures),
            calls=len(calls),
            touched_from=gestures[0].at,
            touched_until=gestures[-1].at,
```

`_segment` returns `None` when there is no gesture, so the list is never empty here.

- [ ] **Step 5: Run the tests**

Run: `cd backend && uv run pytest tests/unit -q`

- [ ] **Step 6: Prove the rule**

Set `touched_from=run[0].at` (the piece's start rather than the first gesture) and confirm the test fails: the first call is a screen loading, not a person.

- [ ] **Step 7: Commit**

```bash
git add backend/src/sro/domain/observation/candidate.py backend/src/sro/application/observation/segment.py backend/tests/unit/application/test_work_that_spans_tabs.py
git commit -m "feat(observation): an episode says when somebody had their hands on it"
```

---

## Task 3: An episode's evidence is its own host's

**Files:**
- Modify: `backend/src/sro/application/observation/teach.py`
- Test: `backend/tests/unit/application/test_work_that_spans_tabs.py`

This guard is a no-op today and must be shown to be one. It becomes load-bearing in Task 4, and lands first so that task cannot introduce contamination.

**Interfaces:**
- Consumes: `Episode.host`
- Produces: `_inside(at, episode)` becomes `_inside(at, host, episode)` — or the host check moves into `_capture`; the implementer picks whichever reads better, provided every call site is covered.

- [ ] **Step 1: Write the failing test**

```python
import json

from sro.application.observation.teach import _within
from sro.domain.observation.candidate import Episode


def test_a_recording_holds_only_its_own_host_s_calls() -> None:
    """Once two episodes can overlap in time, slicing a batch by time alone
    puts the warehouse's calls in the mail half and the mail's in the
    warehouse's -- and the induced skill does everything twice."""
    episode = Episode(
        started_at=AT, ended_at=AT + timedelta(seconds=10), host="wms.example",
        batch_ids=(BATCH,), gestures=1, calls=1,
    )
    payload = b"\n".join(
        json.dumps(line).encode()
        for line in (
            {"kind": "request", "request": {
                "request_id": "a", "method": "POST", "started_at": AT.isoformat(),
                "url": "https://wms.example/api/suppliers"}},
            {"kind": "request", "request": {
                "request_id": "b", "method": "GET", "started_at": AT.isoformat(),
                "url": "https://mail.example/sync"}},
        )
    )

    kept = _within(payload, episode, BATCH)

    urls = [str(getattr(event, "url", "")) for event, _ in kept]
    assert not any("mail.example" in url for url in urls), (
        "another host's call landed in this episode's recording"
    )
```

**Read `_within` and `_capture` before writing this test** — the shape of what `_within` returns (`list[tuple[CaptureEvent, ShotRef | None]]`) and how a request event's URL is reachable off the decoded object may differ from the sketch. Adjust the assertion to the real shape; do not adjust it to whatever the code happens to do.

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — the mail call is in the recording.

- [ ] **Step 3: Implement**

`_inside` gains the host, and every `_capture` branch passes the event's own host:

```python
def _inside(at: datetime, host: str, episode: Episode) -> bool:
    """Whether this event belongs to this episode.

    Time and host, not time alone. Episodes on two hosts can overlap now -- an
    operator flipping between a mailbox and the warehouse system produces
    exactly that -- and a window is no longer enough to say which piece of work
    an event was part of.
    """
    return host == episode.host and episode.started_at <= at <= episode.ended_at
```

The host of a gesture and of a request is the hostname of its own URL, read the same way `segment._host` reads it. Reuse that function rather than writing a second one.

- [ ] **Step 4: Prove it is a no-op on today's data**

```python
def test_scoping_by_host_changes_nothing_that_was_already_mined() -> None:
    """`_runs` ends a run on a host change, so no event of another host was
    ever inside an episode's window. This guard is invisible until episodes
    can overlap -- and that is the point: it arrives before it is needed."""
    episode = Episode(
        started_at=AT, ended_at=AT + timedelta(seconds=10), host="wms.example",
        batch_ids=(BATCH,), gestures=1, calls=1,
    )
    payload = json.dumps({"kind": "request", "request": {
        "request_id": "a", "method": "POST", "started_at": AT.isoformat(),
        "url": "https://wms.example/api/suppliers"}}).encode()

    assert len(_within(payload, episode, BATCH)) == 1
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && uv run pytest tests/unit -q` — the whole suite, because `teach.py` is on the path of every teaching test.

- [ ] **Step 6: Prove the rule**

Drop the `host == episode.host` clause and confirm the first test fails and the second still passes.

- [ ] **Step 7: Commit**

```bash
git add backend/src/sro/application/observation/teach.py backend/tests/unit/application/test_work_that_spans_tabs.py
git commit -m "feat(observation): an episode's evidence is its own host's"
```

---

## Task 4: Done together means touched together

**Files:**
- Modify: `backend/src/sro/application/observation/propose.py`
- Test: `backend/tests/unit/application/test_work_that_spans_tabs.py`

**Interfaces:**
- Consumes: `Episode.touched_from`, `Episode.touched_until` from Task 2

- [ ] **Step 1: Write the failing test**

```python
from sro.application.observation.propose import occurrences


def _episode(start: int, end: int, host: str, touched: tuple[int, int] | None) -> Episode:
    return Episode(
        started_at=AT + timedelta(seconds=start),
        ended_at=AT + timedelta(seconds=end),
        host=host, batch_ids=(BATCH,), gestures=1, calls=1,
        touched_from=AT + timedelta(seconds=touched[0]) if touched else None,
        touched_until=AT + timedelta(seconds=touched[1]) if touched else None,
    )


def test_flipping_between_two_tabs_is_one_job() -> None:
    """The halves overlap because the operator went back to the mail while the
    warehouse screen was still open. That is one job, not two."""
    mail = _episode(0, 120, "mail.example", touched=(0, 100))
    wms = _episode(60, 200, "wms.example", touched=(70, 190))

    assert occurrences(_candidate(mail), _candidate(wms))


def test_a_mailbox_left_open_is_not_part_of_the_work() -> None:
    """Overlapping in time proves nothing on its own: the tab was open, the
    client polled, and nobody touched it."""
    mail = _episode(0, 3600, "mail.example", touched=(0, 30))
    wms = _episode(1800, 2000, "wms.example", touched=(1810, 1990))

    assert not occurrences(_candidate(mail), _candidate(wms))


def test_an_episode_with_no_touched_window_keeps_the_rule_that_mined_it() -> None:
    mail = _episode(0, 100, "mail.example", touched=None)
    wms = _episode(60, 200, "wms.example", touched=None)

    assert not occurrences(_candidate(mail), _candidate(wms)), (
        "an old overlapping pair must not start pairing retroactively"
    )


def test_one_interleaved_pair_counts_once_not_twice() -> None:
    """`_workflows` sums both directions against TOGETHER_TIMES, so a symmetric
    rule would let a single pair clear the bar on its own."""
    mail, wms = _candidate(_episode(0, 120, "mail.example", (0, 100))), _candidate(
        _episode(60, 200, "wms.example", (70, 190))
    )

    assert len(occurrences(mail, wms)) + len(occurrences(wms, mail)) == 1
```

`_candidate(*episodes)` builds a `TaskCandidate` holding those episodes, in that order — variadic, because Task 5 needs one holding two. **Look for an existing builder first** — `backend/tests/factories.py` and the existing candidate tests almost certainly have one; reuse it rather than adding a second way to build a candidate.

- [ ] **Step 2: Run it to verify it fails**

Expected: the two interleaving tests fail — `occurrences` requires a non-negative gap.

- [ ] **Step 3: Implement**

```python
def occurrences(first: TaskCandidate, second: TaskCandidate) -> list[tuple[Episode, Episode]]:
    """Each time an episode of `second` belongs with one of `first`.

    Two shapes, because a person does a job across two systems in two ways.
    They finish in the mail and move to the warehouse -- sequential, which is
    what this counted before. Or they keep both open and go back and forth,
    which produces episodes that overlap and which this counted as nothing at
    all, so the join built for exactly that shape was never proposed.
    """
    return [
        (earlier, later)
        for earlier in first.episodes
        for later in second.episodes
        if _together(earlier, later)
    ]


def _together(earlier: Episode, later: Episode) -> bool:
    gap = later.started_at - earlier.ended_at
    if timedelta(0) <= gap <= TOGETHER_WITHIN:
        return True
    return _interleaved(earlier, later)


def _interleaved(earlier: Episode, later: Episode) -> bool:
    """Overlapping in time, and touched by a person in the same stretch.

    Overlap alone would pair a mailbox somebody left open with whatever else
    they did that hour: the tab was there, the client polled, and none of it
    was work. So the windows compared are the ones an episode records for when
    somebody actually had their hands on it.

    Directional -- only the episode that started first may be the earlier half.
    `_workflows` counts both directions against `TOGETHER_TIMES`, so a
    symmetric rule would let one interleaved pair reach the threshold alone.
    """
    if earlier.started_at > later.started_at:
        return False
    if not (later.started_at < earlier.ended_at):
        return False
    hands = (earlier.touched_from, earlier.touched_until, later.touched_from, later.touched_until)
    if any(when is None for when in hands):
        # Mined before an episode recorded this. It keeps the meaning it had.
        return False
    return (
        later.touched_from - earlier.touched_until <= TOGETHER_WITHIN
        and earlier.touched_from - later.touched_until <= TOGETHER_WITHIN
    )
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit -q`

- [ ] **Step 5: Prove the rules**

Three reverts, one at a time, each breaking exactly one test:
1. Drop the `hands` check → the no-touched-window test fails.
2. Drop the directional guard → the counts-once test fails.
3. Compare `started_at`/`ended_at` instead of the touched windows → the mailbox-left-open test fails.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro/application/observation/propose.py backend/tests/unit/application/test_work_that_spans_tabs.py
git commit -m "feat(observation): two tabs are one job when somebody worked in both"
```

---

## Task 5: The whole shape, end to end

**Files:**
- Test: `backend/tests/unit/application/test_work_that_spans_tabs.py`

No production code. This is the composition check: Tasks 1-4 each proved one rule; this proves they add up to the thing the owner asked for.

- [ ] **Step 1: Write the test**

```python
def test_a_job_done_across_two_tabs_is_offered_as_one() -> None:
    """The shape the owner described: read the mail, create the supplier, flip
    back. Before these rules the mail half was cut to pieces by the warehouse
    tab, the warehouse half by the mail tab, and the two were never counted as
    done together because they overlapped."""
    work: list[Observed] = []
    for doing in range(2):
        base = doing * 3600
        work += [
            _gesture(base + 0, "mail.example"),
            _call(base + 1, "mail.example", "GET"),
            _gesture(base + 5, "wms.example"),
            _call(base + 6, "wms.example"),          # the write
            _call(base + 7, "mail.example", "GET"),  # the mail tab, still polling
            _gesture(base + 9, "mail.example"),      # back to the mail
        ]

    pieces = segment(work)
    hosts = {piece.episode.host for piece in pieces}

    assert hosts == {"mail.example", "wms.example"}
    mail = [p.episode for p in pieces if p.episode.host == "mail.example"]
    wms = [p.episode for p in pieces if p.episode.host == "wms.example"]
    assert len(mail) == 2 and len(wms) == 2, "each doing should give one episode per host"
    assert occurrences(_candidate(*mail), _candidate(*wms)), (
        "the two halves were not counted as done together"
    )
```

Adjust the fixture to whatever `_candidate` really takes. If the assertion cannot pass without a production change, STOP and report it — that would mean Tasks 1-4 do not compose, which is exactly what this task exists to discover.

- [ ] **Step 2: Run it**

Run: `cd backend && uv run pytest tests/unit/application/test_work_that_spans_tabs.py -q`

- [ ] **Step 3: Full gate**

Run: `make lint && make types && make test-unit && make test-integration && make test-contract`

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/application/test_work_that_spans_tabs.py
git commit -m "test(observation): a job done across two tabs is offered as one"
```

---

## Verification against the real recordings

Not a task — a check to run by hand afterwards, because it is the only thing that proves this works on data nobody wrote for it. Read-only; it writes nothing.

Re-run the fragmentation measurement from the spec against tenant `new`:

- **Before:** 37 runs, 30 of whose boundaries ended only because another host spoke; 8 segments.
- **Expected after:** 24 runs, 6 segments, and `PUT data/WM/wm/addresses/* → POST data/WM/wm/suppliers` still seen **3** times.

That last number is the one that matters. A change that found *more* candidates than before would be inventing them; what this must do is stop losing the boundaries it should never have drawn, while finding exactly what it already found.
