# F5 report: target attributes never reach the stored gesture

Branch `d2/f5`, cut from `origin/feat/execution-runtime` at **`84d41633d75f80cf171409e527bbb125a7f545c5`**.
`git merge-base --is-ancestor 339e0f13 HEAD` succeeds.

## Finding: which layer dropped `attributes`

**On this base, no layer drops them.** I traced one gesture end to end. At every
hop, `target.attributes` goes in and comes out whole:

| # | Layer | Evidence |
|---|---|---|
| 1 | Generated extension recorder, `describe` (`new-chrome-extension/src/content/recorder.generated.js:419-470`) | I ran the real `recorder-bridge.main.js` and `recorder.generated.js` in Chromium (Playwright, `/opt/pw-browsers/chromium`) on a sign-in form: an email box (`type=email autocomplete=username aria-haspopup=true`), a password box, and a button. Every `type`, `press` and `click` gesture carried the full `attributes` map. The password box had no `value`. `make gen-recorder` leaves the tree unchanged, so the generated copy is current. |
| 2 | MAIN-world → isolated relay (`recorder-bridge.main.js`, `observe.js`) | The JSON string is forwarded as `JSON.parse(json)` without any projection. |
| 3 | Service worker (`service-worker.js:1607-1694`), `queue.js`, `upload.js` | `{...message.gesture, url: redactUrl(...)}` → IndexedDB row → `events: kept.map(row => row.event)`. `trim` strips only shots, response bodies, and non-gesture events. `considerOffer` reads the gesture and does not mutate it. |
| 4 | Ingest route and schema (`interface/http/v1/routers/observations.py`, `schemas.py:1882` `events: list[dict[str, Any]]`) | Events arrive verbatim. `admit` only accepts or refuses them. `redact_events._element` → `_attributes` redacts values under secret-named keys and keeps the keys. |
| 5 | Wire → domain (`rig_wire.Target` → `correlate.as_action` → `domain/observation/gesture.py` `Target`) | `attributes=dict(target.attributes)` at `correlate.py:175`. `rig_wire.Target` pops `value` when `secret` and then runs `redact_attributes`. |
| 6 | DB mapper (`infrastructure/db/evidence.py` `_gesture_to_row` / `_row_to_gesture`, `TypeAdapter(Action)` into JSONB `gestures.gesture`) | The round trip keeps the map (checked in-process). Proving it against Postgres is the integration test below. |
| – | Steel capture path (`infrastructure/steel/capture.py`) | It writes to the recording plane (`capture/decode.py:232` keeps `attributes`). It never writes to `gestures`. `correlate` in `IngestObservation` is the only constructor of a stored observation `Gesture`. |

I fed the real Chromium recorder output, wrapped the way the service worker
wraps it, through `IngestObservation`. All five gestures were read back with
their attributes.

**The layer that dropped them was `application/observation/correlate.py`
`as_action`, before execution-runtime task E1.** Both
`docs/superpowers/plans/2026-09-24-steel-migration.md:775` and
`docs/superpowers/plans/2026-09-24-execution-runtime.md:469` record it:
"`correlate.py` `as_action` drops `Target.bounds`, `Target.attributes` …". E1
added `attributes=dict(target.attributes)`, which is on this base. This repo's
history begins at `8202fa2` (2026-09-25, an import commit), so git cannot date
E1 more precisely than "by 2026-09-25".

So the empty attributes QA saw on 2026-09-28 are gestures that were **stored
by a backend without E1**. Either they were recorded before E1 was deployed, or
the QA API was running a pre-E1 revision when they arrived. Ingest runs in the
API process, not the worker.

## Backfill: possible, not done

- **What exists.** Each affected `gestures` row keeps `batch_id`, `at`,
  `tab_id` and the rest of its action. Only `gesture->'target'->'attributes'` is
  `{}`. Ingest also wrote the whole batch, after redaction, as NDJSON to the
  blob store *before* correlating (`ingest.py:139-144`,
  `observation_batches.uri`). That copy still holds every event's
  `target.attributes`, redacted exactly as storage policy requires.
- **How it would work.** For each row with empty attributes, read its batch's
  blob. Find the gesture event by `(tab_id, frame_path, at, kind)`, since
  gesture ids are random and not in the blob. Run it through
  `redact_events` → `rig_wire` → `as_action`, and write only that key with
  `jsonb_set` in one statement. A whole-column read-modify-write would break
  invariant 9.
- **The limit.** `SweepRetention` forgets blobs after the tenant's
  `retention_days` (default 30, `domain/observation/policy.py:30`). Rows from
  the E1 era have blobs until about late October 2026 under the default, and
  sooner if greyorange's policy is shorter. After that, the attributes cannot
  be recovered.
- **Check first:** `select count(*) from gestures where tenant_id = … and
  gesture->'target'->'attributes' = '{}'::jsonb`, and
  `select min(at) from gestures where gesture->'target'->'attributes' <> '{}'::jsonb`.
  The second tells you when E1 went live on QA.

## Commits

- `4166232` test(evidence): a target's attributes survive recorder, relay, route and store (F5)
- `docs(cloud-reports): F5 report`

## Files changed

- `new-chrome-extension/src/content/attributes.test.mjs` (new)
- `backend/tests/unit/interface/test_a_target_keeps_its_attributes.py` (new)
- `backend/tests/integration/test_a_target_keeps_its_attributes.py` (new)
- `docs/superpowers/cloud-reports/f5-report.md` (new)

No production code changed. No migration. No wire type change, so `make types`
is not needed. No code notes were touched: the new files are tests.

## Tests added

- **Extension (node, the `observe.test.mjs` / `evidence.test.mjs` pattern):**
  `attributes.test.mjs` lifts the generated recorder's real `describe` and
  `isSecretField`. It runs the real `recorder-bridge.main.js` and `observe.js`
  in one vm world, calls `window.__sroRecord` as `emit` does, and asserts on the
  message sent to the worker:
  - an identity field arrives with `id`, `type=email`, `name`,
    `autocomplete=username` and `aria-haspopup=true`;
  - a password field arrives with its attributes, `secret: true`, and no
    `value` anywhere in the message.
- **Unit (real route, fake store):**
  `tests/unit/interface/test_a_target_keeps_its_attributes.py`. It posts
  gestures captured verbatim from the real recorder in Chromium (invariant 16).
  Only the page URL is moved onto an observed host. The test goes through
  `POST /v1/observations` and reads them back from the gesture repository:
  - the email box has `autocomplete=username`, `type=email` and
    `aria-haspopup=true`, and the password box keeps `type` and
    `autocomplete`;
  - a secret field's `value` attribute never comes back, even when a payload
    carries it.
- **Integration, written, not run (no Docker or Postgres here):**
  `tests/integration/test_a_target_keeps_its_attributes.py`. It posts through
  the real route with `SqlUnitOfWork` and reads the gestures back from
  Postgres. The attributes are present and a secret `value` is absent.

**Rules broken on purpose to prove the tests catch them** (each break was
reverted right after):
- Remove `attributes=dict(target.attributes)` from `correlate.as_action`, which
  is the pre-E1 drop. Both unit tests fail.
- Remove `self.attributes.pop("value", None)` from `rig_wire.Target`. The
  secret-value unit test fails.
- Set `attributes: {}` in the generated recorder's `describe`. Both extension
  tests fail.
- Delete the recorder's `value`-on-secret `continue`. The extension secret test
  fails.

## Gates

- `uv run pytest tests/unit tests/contract -q`: **5006 passed, 83 errors.**
  All 83 are Docker/testcontainers errors: 82 `test_the_repositories_agree.py
  [sql]` cases and `test_openapi.py::TestFuzz`. Each fails with
  `DockerException: Error while fetching server API version`, because there is
  no Docker in this session.
- `uv run mypy src tests`: no issues (835 files).
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 contracts kept.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `make test-extension`: 353 pass, 0 fail (includes the new suite).
- ESLint on the extension was not run: `frontend/node_modules` is not installed
  here.

## Rulings

- Ruling: no production change. There is no layer on this base that drops
  `attributes`; the drop was `correlate.as_action` and E1 already fixed it at
  the root. — Adding a second "fix" somewhere else would be the per-caller
  patch the brief forbids. The new tests pin every hop so a regression cannot
  pass. — If wrong (there is a drop I did not reproduce, for example one that
  only a live Google page triggers), QA keeps seeing `{}` on gestures stored
  *after* this lands. The `min(at)` query above tells the two cases apart.
- Ruling: the secret-`value` backend test posts a `value` attribute on a secret
  target, which the recorder itself never produces. — `observe.js` relays any
  `sro:gesture` a page dispatches (its own comment says nothing there trusts
  the payload), so a page can produce this shape. The storage-side pop in
  `rig_wire.Target` exists for exactly that case, and it is the half this
  route owns. — If wrong, the test covers a defensive layer only. The
  extension test covers the recorder's own omission.
- Ruling: the fixture gestures were captured from the real generated recorder
  in Chromium, rather than regenerated in every unit run. — Unit tests have no
  browser. The captured JSON is byte-for-byte what `emit` sent, with only
  `url` and `at` moved. — If wrong, the recorder's shape can drift from the
  fixture. The extension test, which runs the current `describe`, is the
  guard against that.

## Concerns

- **Confirm QA's deployed revision.** If the QA API process predates E1, every
  gesture it stores today still loses attributes. The fix there is a redeploy,
  not code. Ingest runs in the API, so restarting the worker alone does not
  change this.
- **Backfill has a deadline.** It is possible only while the batch blobs
  survive retention (default 30 days).
- **Unrelated oddity seen while probing:** a gesture with `kind: "input"` was
  admitted (`accepted=1`) but produced no stored gesture. The recorder never
  emits `input` (it emits `type`, `select`, `upload`, `press`, `click` and
  `scroll`), so nothing depends on it. I did not investigate it further.
