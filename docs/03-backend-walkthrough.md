# Backend walkthrough

## Adding a use case, end to end

Worked example: "list a tenant's recordings". Follow it literally — if a step
does not work as written, this document is wrong and fixing it is part of the
change. That has already happened once: following it end to end is what found
three routers reading from repositories directly instead of through a use case.
`ListRecordings`, `GetRecording`, `ListSkills` and `GetSkill` exist because this
document said they should.

### 1. Does the domain already say it?

Read `domain/` first. Most new requirements are a method on an existing entity,
not a new use case. A rule added in a use case is enforced only on the paths that
remember to call it.

For this example the domain needs nothing new.

### 2. Does a port already cover it?

`RecordingRepository.list_for_tenant` exists. If it did not, you would add the
method to the Protocol in `application/ports/repositories.py` — and read
[02-code-standards.md#ports](02-code-standards.md#ports) before adding a *new*
port rather than a method.

### 3. Write the use case

`application/recording/list_recordings.py` — one file, one class, dependencies in
`__init__`, `RequestContext` first:

```python
class ListRecordings:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> tuple[Recording, ...]:
        async with self._uow as uow:
            return await uow.recordings.list_for_tenant(
                ctx.tenant_id, limit=limit, offset=offset
            )
```

### 4. Test it against fakes

`tests/unit/application/test_list_recordings.py`, using `FakeUnitOfWork` and
`tests/factories.py`. No Docker. Prove the tenant filter holds — seed two tenants
and assert only one comes back.

### 5. Implement the adapter

`infrastructure/db/repositories.py`. `tenant_id` goes in the `WHERE` clause, not
in a Python filter afterwards.

Add an integration test in `tests/integration/` against testcontainers Postgres.
This is the only place the SQL is actually proved.

### 6. Expose it

- `interface/http/schemas.py` — a response model. Domain objects never cross the
  wire.
- `interface/http/v1/routers/recordings.py` — the route.
- `container.py` — wire the use case. This is the only module that imports
  `infrastructure`.

A router never touches `container.unit_of_work()`. A read that looks too small
to deserve a use case is exactly how the application layer gets bypassed, and
the next reader cannot tell which rules apply to it. The check is mechanical:

```bash
grep -rn "unit_of_work()" backend/src/sro/interface/   # must return nothing
```

### 7. Regenerate the frontend contract

```bash
make types
```

The backend OpenAPI document is the source of truth. A schema change that breaks
the frontend build is the mechanism working.

### 8. Check the gates

```bash
make lint    # ruff, mypy --strict, import-linter, eslint
make test
```

---

## Frame assembly

`application/capture/assemble.py`

Raw CDP is thousands of unordered messages across three domains. Assembly
collapses them into a short ordered list of frames, where each frame is one
thing the human did plus everything the page did in response.

The rules:

- An **input** event opens a frame. Nothing else does.
- A **request** attaches to the most recent open frame. Requests are effects of
  clicks, so they follow them.
- A **snapshot** attaches to the most recent frame that has none. A second
  snapshot on the same frame is discarded — the first was taken at action time,
  which is the state the human was looking at when they decided to act.
- A request with no preceding input **in this batch** is not automatically
  noise. Capture is drained on an interval, so a response that finishes just
  after a drain arrives alone in the next one. If the recording already has
  frames, the call belongs to the most recent action and is absorbed into it
  (`Recording.absorb_late_evidence`); only when there is no frame at all is it
  page-load noise, dropped but **counted**. Getting this wrong silently costs a
  step the very call the skill would replay.

Events are sorted by timestamp first, because CDP guarantees no ordering across
domains. Ties break input-first, so a snapshot taken at click time lands on the
frame the click opened rather than the one before it.

**Known limitation:** a request that starts before its click — a debounced
keystroke handler firing late — is attributed to the previous frame. The capture
adapter now records CDP initiator stack traces, so the evidence to fix this
exists; assembly does not yet use it. `ActionFrame.primary_request` already
ranks script-initiated mutations first, which is enough to pick the right call
within a frame but not to move one between frames.

The function is pure. Given the same events it returns the same frames, with no
clock, storage or browser involved — which is what keeps these rules cheap to
tune against real WMS traffic.

---

## Migrations

```bash
make revision m="add recording label"   # autogenerate
# read the generated file before committing -- autogenerate is a draft
make migrate
```

Every table gets `tenant_id` and an index leading with it.

---

## How aggregates are stored

`infrastructure/db/`

Frames and skill versions are deep, immutable, and always read whole. They are
stored as JSONB documents; the fields anything queries by — tenant, objective,
status, timestamps — are lifted into real columns.

The JSON conversion in `codec.py` is derived from the domain's own type
annotations by a pydantic `TypeAdapter`. There is no second definition of the
shape to keep in step: a field added to a domain dataclass is persisted the
moment it exists. `tests/unit/infrastructure/test_codec.py` proves the round
trip, including the read-only header mappings.

`mappers.py` converts rows to aggregates and back. Rehydration writes the private
frame and artifact lists directly rather than calling `append_frame`, because a
sealed recording rejects appends and loading is not a state transition.

---

## Capture adapter

`infrastructure/steel/`

- `client.py` — Steel's sessions API. Implements `BrowserProvider`.
- `capture.py` — attaches to the session over CDP, enables `Network`, `Page`,
  `Runtime`, `DOM` and `Accessibility`, and buffers everything. `drain()` hands
  over the batch and clears.
- `recorder.js` — injected into every frame. CDP reports what the *page* did; it
  does not report what the *human* did. This is the only source of input events.
- `supervisor.py` — the loop that keeps a session running for the life of a
  recording: attach on start, drain on an interval, drain once more and detach
  on finish. Draining on an interval is what makes a crashed API process cost
  one interval instead of the whole demonstration.
- `cdp_mapping.py` — pure dict-to-domain functions, so every CDP shape is tested
  without a browser. These are the parts most likely to move under a Chrome
  upgrade, and `tests/unit/infrastructure/test_cdp_mapping.py` is where that
  breakage surfaces.

Two things about the injected recorder are load-bearing and were both learned
the hard way against a real browser:

- Its listeners go on `window`, and installation is idempotent by *construction*
  (remove-then-add) rather than by a boolean flag. `document.open()` — how a page
  replaces its content without navigating — unregisters every listener on the
  window while keeping both the window and document object identity, so a flag on
  either one reports "installed" after the listeners are gone.
- The adapter re-injects on every `domcontentloaded`, because init scripts do not
  re-run for a document rewrite.

Without both, capture goes quiet partway through a session and the recording
silently loses its remaining steps.

An exchange still in flight when capture ends -- the operator closed the tab the
moment the WMS confirmed -- never reaches `loadingFinished` and would sit in the
pending map until the process forgot it. `flush_incomplete()` emits those with
whatever was observed and a `failure_reason` saying why they are partial. The
method, URL, headers and initiator are already known, and that is most of what a
skill is built from.

The drain loop logs what it saw on every pass:

```
capture drain: recording=rec_… events=6 frames=+1 (1 total) absorbed=0 orphaned=3 artifacts=1
```

A recording that ends up thin is diagnosed there or not at all; by review time
the only evidence left is whatever survived. `sro.observability.configure_logging`
exists because uvicorn configures only its own loggers, and without it every one
of those lines goes nowhere.

### Video

`video.py`, fed by `Page.startScreencast`.

CDP sends a JPEG whenever the page changes, at whatever rate it changes. Holding
a demonstration's worth of those in memory to encode later is how a long session
takes the API process down with it, so frames are decoded and encoded to H.264 as
they arrive, into a temp file, at their real timing. Memory stays flat and the
result is an ordinary MP4 that any browser plays without a custom player.

Two details are load-bearing:

- `stream.codec_context.time_base` must be set, not just `stream.time_base`.
  Without it libx264 has no timebase, buffers everything, and fails the final
  flush with a bare `EINVAL` -- losing every frame still inside the encoder.
- Video frames are *taken*, not streamed. `Page.startScreencast` is the obvious
  API and the wrong one: Chrome allows a single screencast consumer per page and
  the newest wins, so subscribing steals the stream from Steel's live view and
  freezes the browser the operator is driving — capture keeps working, the human
  goes blind. `Page.captureScreenshot` is request/response and takes nothing
  from anyone. The cost is sampling rather than repaint-accurate frames, which
  for reviewing a demonstration is not worth the breakage.

Video is the least important capture channel and the only skippable one: an
encoding failure disables video for the session and is logged, never raised,
because losing it must not cost the network, accessibility or input evidence.

Playback goes through `GET /v1/recordings/{id}/media`, which mints presigned
URLs that expire in 30 minutes. A recording holds live customer traffic, so a
link that outlives the page it was rendered on is an untracked copy of the
evidence.

Response bodies over `SRO_INLINE_BODY_LIMIT_BYTES` are written to object storage
and the `Body` keeps the URI. A `Body` that is neither inline nor pointing at a
blob raises — see [11-capture-completeness.md](11-capture-completeness.md).
