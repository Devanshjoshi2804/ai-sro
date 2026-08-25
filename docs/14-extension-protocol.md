# The extension protocol

The contract between the Chrome extension (in an operator's own browser) and the
SRO backend. **Frozen on agreement.** Changing anything here is a conversation
between whoever owns the extension and whoever owns the backend, never a
unilateral edit — the whole point of writing it down is that two people can build
the two halves without reading each other's code.

Background: [`docs/07-adr/008-passive-observation.md`](07-adr/008-passive-observation.md),
[`docs/07-adr/009-the-extension-is-an-adapter.md`](07-adr/009-the-extension-is-an-adapter.md).

## Shape of the thing

The extension does two jobs and nothing else:

1. **It is a capture source.** It uploads what the operator did, in the same
   event shapes the server-side capture adapter already produces
   (`application/capture/events.py`).
2. **It is a driver.** It performs one gesture, or sends one request, when the
   backend asks over a websocket, and answers with the result.

Everything else — deciding what is a task, inducing a skill, the promotion
ladder, the circuit breaker, verification — happens on the backend and is out of
this document's scope.

## Transport and authentication

- Base URL: `SRO_API_URL`, no trailing slash. All paths below are relative to it.
- Every HTTP request carries `Authorization: Bearer <token>`. The token is minted
  by `make token tenant=<t> principal=<p>` and pasted into the extension by the
  operator, exactly as the console does it. There is no login endpoint and no
  refresh; an expired token means paste a new one.
- The websocket authenticates with the subprotocol list, not a header:
  `new WebSocket(url, ["bearer", token])`. The server accepts with
  `subprotocol: "bearer"` or closes with `1008` **before** accepting.
- The backend must list `chrome-extension://<extension id>` in its CORS origins
  (`SRO_CORS_ORIGINS`). Until it does, every request from the extension fails at
  the browser, before it reaches a router.
- Errors are RFC 9457 problem documents (`application/problem+json`) with
  `type`, `title`, `status`, `detail`, `instance`. `401` means the token is not
  accepted — drop it and return to the paste screen. `503` means the deployment
  cannot check credentials; it is never permission.

## Identifiers

| Name | Shape | Minted by |
|---|---|---|
| `device_id` | `dev_<32 hex>` | backend, at registration |
| `batch_id` | `bat_<32 hex>` | **extension**, so a retry is idempotent |
| `command_id` | `cmd_<32 hex>` | backend |
| `episode_id`, `candidate_id`, `trigger_id` | `epi_`/`cnd_`/`trg_` + 32 hex | backend |

Timestamps are **RFC 3339 with an offset**, always. Durations are integer
milliseconds. Gesture `at` inside a captured event keeps the recorder's existing
format — Unix **seconds as a float** — because that is what `recorder.js` emits
and what `capture.decode.epoch_to_datetime` parses.

---

## 1. Device registration

### `POST /v1/agents/register`

```jsonc
// request
{
  "label": "devansh-macbook / Chrome 141",   // human-readable, for the device list
  "extension_version": "0.1.0",
  "user_agent": "Mozilla/5.0 …"
}
// 201
{
  "device_id": "dev_…",
  "policy": { /* Policy, below */ },
  "policy_version": 7
}
```

Registration is per browser profile. The extension stores `device_id` in
`chrome.storage.local` and reuses it; registering again with the same token and
label returns the same device.

### `POST /v1/agents/{device_id}/heartbeat`

```jsonc
// request
{ "queued_events": 412, "queued_bytes": 2280310, "paused": false }
// 200
{ "policy_version": 7, "policy": null, "pause": false }
```

`policy` is `null` when `policy_version` is unchanged, the full object when it is
not. `pause` is the server telling the extension to stop capturing — an
administrator's kill switch. The extension honours it immediately and says so in
its UI. Heartbeat every 60s while awake.

### Policy

```jsonc
{
  "capture_enabled": true,
  "exclude_hosts": ["*.bank.example", "payroll.corp", "mail.google.com"],
  "include_hosts": [],                // empty = everything not excluded
  "capture_screenshots": true,
  "screenshot_max_per_minute": 20,
  "capture_response_bodies": true,
  "max_body_bytes": 262144,           // matches SRO_INLINE_BODY_LIMIT_BYTES
  "daily_budget_bytes": 524288000,
  "retention_days": 30
}
```

`exclude_hosts` is enforced by **not registering the content script** on those
hosts (`chrome.scripting.registerContentScripts` with `excludeMatches`), so an
excluded page is never touched at all — not captured and then filtered. The
operator may add to the list locally; they may not remove a server entry.

---

## 2. Uploading observations

### `POST /v1/observations`

`Content-Type: application/json`. One batch per request.

```jsonc
{
  "batch_id": "bat_…",
  "device_id": "dev_…",
  "started_at": "2026-08-23T09:14:02.113+05:30",
  "ended_at":   "2026-08-23T09:19:02.550+05:30",
  "mode": "passive",            // "passive" | "teaching"
  "recording_id": null,         // set only when mode == "teaching"
  "events": [ /* Event, below */ ]
}
// 202
{ "batch_id": "bat_…", "accepted": 318, "rejected": 2,
  "problems": [{ "index": 44, "reason": "element fingerprint carries no usable signal" }] }
```

- **Idempotent on `batch_id`.** A retry of a batch already accepted answers `202`
  with the original counts and stores nothing twice.
- A rejected event does not reject the batch. The extension does not retry
  individual events; a rejection is a bug to fix, not a transient failure.
- Events within a batch need not be sorted; the backend sorts by `at`.
- Recommended flush: 500 events, 2 MB, or 60 seconds, whichever comes first.
  Persist the queue in IndexedDB — an MV3 service worker is evicted while idle
  and anything held only in memory is gone.

### Events

Four kinds, discriminated by `kind`.

**`gesture`** — emitted verbatim by `recorder.js`. Do not reshape it; the backend
parses it with `capture.decode.to_input_action` and any change here is a change to
that function.

```jsonc
{
  "kind": "gesture",
  "gesture": {
    "kind": "click",              // click | type | select | press | upload | scroll
    "target": { "tag": "input", "role": null, "name": "Client Code",
                "secret": false, "text": null, "testId": null,
                "cssPath": "div.x-panel > input:nth-of-type(2)",
                "xpath": "/html[1]/body[1]/div[3]/input[2]",
                "bounds": {"x":0,"y":0,"width":0,"height":0},
                "attributes": {"type":"text"},
                "component": { "framework": "extjs", "xtype": "textfield",
                               "itemId": "clientCode", "name": "clientCode",
                               "fieldLabel": "Client Code", "text": null,
                               "query": "panel#clients textfield#clientCode",
                               "chain": ["viewport","panel#clients","textfield#clientCode"] } },
    "value": "ACME",              // null when the field was a credential
    "secret": false,
    "modifiers": ["ctrl"],
    "at": 1787654321.901,         // Unix seconds, float
    "url": "https://wms.example/…"
  },
  "tab_id": 8, "frame_url": "https://wms.example/…"
}
```

A `target` **must** carry at least one of `role`, `name`, `text`, `testId`,
`cssPath`, or `xpath`. The domain refuses a fingerprint with none of them, and
the batch will report it as rejected.

**`request`** — one network exchange, shaped as `domain/recording/network.py`
holds it.

```jsonc
{
  "kind": "request",
  "request": {
    "request_id": "1234.5",
    "method": "POST",
    "url": "https://wms.example/api/equipment",
    "resource_type": "xhr",
    "started_at": "2026-08-23T09:15:11.004+05:30",
    "request_headers": {"content-type": "application/json"},
    "request_body": {"text": "{\"code\":\"TESTSRO\"}", "size_bytes": 21,
                     "mime_type": "application/json", "encoding": null,
                     "redacted_fields": []},
    "status": 200, "status_text": "OK",
    "response_headers": {"content-type": "application/json"},
    "response_body": {"text": "{…}", "size_bytes": 812,
                      "mime_type": "application/json", "encoding": null,
                      "redacted_fields": []},
    "redirect_chain": [], "duration_ms": 344,
    "from_cache": false, "failure_reason": null, "blocked_reason": null
  }
}
```

Fields the passive tier cannot obtain (`initiator`, `timing`, `protocol`,
`remote_address`, `cookies_sent`, `cookies_set`) are omitted, not faked. The
teaching tier, which attaches `chrome.debugger`, supplies them.

A body larger than `max_body_bytes` is uploaded as an artifact and referenced by
`{"blob_uri": "…", "size_bytes": N}` instead of `text`.

**`snapshot`** — an accessibility tree, teaching tier only. The payload is CDP's
`Accessibility.getFullAXTree` result plus `url` and `taken_at`; the backend
parses it with `capture.decode.to_ax_graph`.

**`page`** — navigation and lifecycle.

```jsonc
{ "kind": "page", "at": "…", "page_kind": "navigated",
  "url": "https://…", "detail": null, "tab_id": 8 }
```

`page_kind` ∈ `navigated · loaded · dialog_opened · dialog_handled ·
download_started · frame_attached · frame_detached · popup_opened`.

### `POST /v1/observations/artifacts`

`multipart/form-data`: `device_id`, `batch_id`, `kind` (`screenshot` | `payload`
| `video`), `file`, optional `frame_index`, `label`, `duration_ms`.
Answers `201` with `{"uri": "s3://…", "size_bytes": N}`.

Screenshots are `image/png` from `chrome.tabs.captureVisibleTab`, keyed to the
gesture they follow by `frame_index` — the index the extension assigned in this
batch, counting gestures from 0.

### `DELETE /v1/observations?since=<rfc3339>`

The operator's own evidence, from their own devices, for the tenant on their
token — deleted, and the deletion recorded. Answers `200` with
`{"batches": 4, "events": 1180, "artifacts": 92}`. This is what the extension's
"purge the last hour" button calls. It never touches another principal's rows.

---

## 3. The command channel

### `WS /v1/agents/{device_id}/commands`

Subprotocol auth as above. The backend sends commands; the extension answers.
Every message is one JSON object with an envelope:

```jsonc
// server → extension
{ "command_id": "cmd_…", "kind": "ui.perform", "run_id": "run_…",
  "deadline_ms": 15000, "payload": { … } }

// extension → server
{ "command_id": "cmd_…", "ok": true,  "result": { … } }
{ "command_id": "cmd_…", "ok": false, "error": { "kind": "control_not_found",
                                                  "detail": "no visible match" } }
```

The extension answers **every** command exactly once, including with an error.
A command with no answer by `deadline_ms` is failed by the backend as
`UiUnavailable` / `TargetUnreachable`, and a late answer is discarded.

The extension may also send unsolicited:

```jsonc
{ "kind": "hello", "extension_version": "0.1.0", "tabs": 12 }
{ "kind": "busy",  "reason": "operator is typing", "for_ms": 5000 }
{ "kind": "ping" }                                    // keepalive; the backend drops it
```

`ping` every 20s while the channel is open. It is not politeness: Chrome closes
an idle extension service worker after 30 seconds and takes the socket with it,
and traffic on a WebSocket is what resets that timer. The backend already
ignores any message with no `command_id`, so nothing has to be done with it.

`busy` carries its own end. The backend holds new commands for that long, or
until half the command's own deadline has gone, whichever is shorter — a device
asking for politeness must not be able to veto the work. It is sent when the
operator makes a gesture, rate-limited to one message per burst of typing rather
than one per keystroke, and it is renewed by the next gesture. It arrives only
where observation is on, since it is the operator's own input that produces it;
a tenant with capture switched off gets a channel that never says it is busy,
and the backend acts immediately.

### `ui.perform`

```jsonc
// payload
{ "action": "click",                 // click | type | select | press | upload | scroll | hover
  "value": "TESTSRO",
  "locators": [
    { "strategy": "component",     "query": "panel#clients textfield#clientCode",
      "within": null, "visible_only": true },
    { "strategy": "role_and_name", "query": "textbox|Client Code",
      "within": null, "visible_only": true },
    { "strategy": "text",          "query": "Client Code", "within": null, "visible_only": true },
    { "strategy": "test_id",       "query": "client-code",  "within": null, "visible_only": true },
    { "strategy": "css_path",      "query": "div.x-panel > input:nth-of-type(2)",
      "within": null, "visible_only": true }
  ] }
// result
{ "performed": true, "matched_by": "component", "candidates": 1, "detail": null }
```

Every command that acts on a page — `ui.perform`, `ui.perform_at`, `ui.url`,
`screenshot`, `navigate` — carries `origin` on its payload: the scheme and host
of the system the skill was taught on, read off the first recorded call that
names one. The extension acts in a tab on that origin, preferring the visible
one, and answers `no_tab_for_system` when the browser has none open. An operator
has a dozen tabs and one of them is the WMS; without being told which, the only
thing the extension can do is take the frontmost page, and a warehouse gesture
performed on somebody's email is a real thing that happened to a real person.

`origin` is absent only where the skill has no call to read it from — one taught
entirely through the interface. Then the extension falls back to the page in
front of the operator, which is the best a guess can do.

`allow_focus` rides beside it, and is sent **only when true**: it is the run
saying the operator asked for this and is watching, so the named tab may be
brought to the front. It comes from the trigger (`may_take_focus`) or from the
caller of `POST /v1/skills/{id}/runs`, is carried on the run because the process
that performs a step is not the one that decided it was allowed, and defaults to
no. A `screenshot` of a tab that is not the visible one needs it — the picture
would otherwise come from a different page than the coordinates beside it — and
is refused with `focus_not_permitted` without it.

Locators are tried **in the order given** and the first that resolves is used.
`matched_by` must name the one that worked — a step that only ever matches on the
last fallback is a step about to break, and the backend records that.
`candidates` is how many controls the winning locator matched; more than one is a
warning, not an error, and the extension acts on the first visible match.
`role_and_name` queries are `role|name`. `within` is a component query the match
must sit inside.

Failure kinds: `control_not_found`, `not_visible`, `not_actionable`,
`no_tab_for_system`, `aborted`.

### `http.send`

Sends from the page context of a tab on that origin, so the operator's own
cookies and session apply.

```jsonc
// payload
{ "method": "POST", "url": "https://wms.example/api/equipment",
  "headers": {"content-type": "application/json"},
  "body": "{\"code\":\"TESTSRO\"}" }
// result
{ "status": 200, "headers": {…}, "body": "…", "duration_ms": 210 }
```

Failure kinds: `unreachable`, `no_tab_for_origin`, `timeout`.

### `ui.perform_at`

```jsonc
// payload
{ "action": "click", "x": 812, "y": 344, "value": null }
// result — the same shape ui.perform answers with
{ "performed": true, "matched_by": null, "candidates": 1, "detail": null }
```

What the vision rung sends: a coordinate is not a control the demonstration
identified, so it is a different command and the run's record can never confuse
the two. `x` and `y` are **CSS pixels in the viewport**, the same space
`screenshot` reports its `width` and `height` in. Not device pixels: on any
retina display the two differ by the scale factor, which is a click a quarter of
the way up the page.

Failure kinds: `control_not_found` (nothing at that point), `not_actionable`,
`no_tab_for_system`, `aborted`.

### `ui.url`

```jsonc
{ "kind": "ui.url", "payload": {} }   → { "url": "https://wms.example/orders" }
```

Where the driven browser is, for the run's record.

### `screenshot`, `navigate`, `abort`

```jsonc
// Always inline, which is what the vision rung asks for: it is looking at the
// picture now, and a round trip through object storage to read back what was
// just asked for is two more places for it to be delayed or lost. There is no
// stored form -- a run keeps no screens, and an observation artifact is filed
// against a batch a run does not have. The day something wants to read a run's
// screens back, the thing to build is a run-scoped artifact endpoint, and this
// command grows a payload flag then.
{ "kind": "screenshot", "payload": {"inline": true} }
   → { "image_base64": "iVBORw0…", "mime_type": "image/png",
       "width": 1600, "height": 1000, "text_digest": "Save: 100,200" }
{ "kind": "navigate",   "payload": {"url": "https://wms.example/…", "allow_focus": false} }
   → { "navigated": true }
{ "kind": "abort",      "payload": {"run_id": "run_…"} }
   → { "aborted": true }
```

`navigate` and any command that would take focus are refused unless the run's
trigger allows it. The trigger's decision arrives as `allow_focus` on the
payload, absent meaning no. The extension
refuses with `error.kind = "focus_not_permitted"` rather than doing it anyway --
and only where it would actually cost the operator their screen: navigating a
tab they are not looking at is not taking focus.

`width` and `height` on a screenshot are the **CSS viewport**, not the picture's
own pixels: they are the space `ui.perform_at` acts in, and on a retina display
the two differ by the display's scale factor.

---

## 4. Candidates, triggers, analytics

Read-mostly, consumed by the side panel. Full schemas come from the generated
OpenAPI; the shapes the extension depends on are:

```jsonc
// GET /v1/candidates?status=new&limit=20
[{ "id": "cnd_…", "title": "Create a warehouse equipment type",
   "target_system": "blue_yonder", "occurrences": 11,
   "median_duration_ms": 232000, "first_seen": "…", "last_seen": "…",
   "status": "new", "skill_id": null,
   "evidence": [{"episode_id": "epi_…", "at": "…"}] }]

// POST /v1/candidates/{id}/teach  → 202
{ "recording_id": "rec_…", "needs_demonstration": false }
// needs_demonstration true = the passive evidence is too thin; the panel asks the
// operator to do it once more with the teaching tier on.

// POST /v1/candidates/{id}/dismiss → 204   { "reason": "not worth automating" }

// GET /v1/triggers  ·  POST /v1/triggers  ·  PATCH /v1/triggers/{id}
{ "id": "trg_…", "skill_id": "skl_…", "kind": "schedule",
  "spec": {"cron": "0 */2 * * 1-5", "timezone": "Asia/Kolkata"},
  "parameter_bindings": {"facility": "DC1"},
  "enabled": true, "requires_confirmation": true,
  "may_take_focus": false, "authorized_by": "devansh", "next_fire_at": "…" }

// GET /v1/analytics/summary?since=…
{ "tasks_observed": 41, "candidates": 9, "skills_taught": 3,
  "runs": {"clean": 22, "degraded": 3, "failed": 1, "withheld": 6},
  "estimated_minutes_saved": 148 }
```

Existing endpoints the panel uses unchanged: `/v1/threads*` (chat),
`/v1/runs/{id}/stream` (SSE, one event per step).

`POST /v1/skills/{id}/runs` gains one field:

```jsonc
{ "parameters": {…}, "medium": "ui", "device_id": "dev_…", "authorized_by": true }
```

Naming a device performs the run in that browser: gestures over `ui.perform`,
and calls over `http.send` from the operator's own page, so the request carries
their session. Such a run is performed by the API process rather than handed to
a durable worker — a run whose browser is a laptop cannot be resumed after a
restart into a Chrome that may be closed, on a page that has moved, halfway
through a task. `RunModel.device_id` says which browser it went through.

---

## 5. Fixtures — how the two halves are proved to fit

The extension commits golden payloads to `new-chrome-extension/fixtures/`:

| File | Contains |
|---|---|
| `gesture-click.json` · `gesture-type.json` · `gesture-select.json` · `gesture-press.json` · `gesture-upload.json` | one `gesture` event each |
| `gesture-secret.json` | a password field — `value` null, `secret` true, no `value` attribute |
| `request-get.json` · `request-post.json` · `request-failed.json` | one `request` event each |
| `page-navigated.json` | one `page` event |
| `snapshot.json` | one `snapshot` event (teaching tier) |
| `batch.json` | a complete `POST /v1/observations` body |
| `command-ui-perform-reply.json` · `command-http-send-reply.json` | extension → server replies |

`backend/tests/contract/test_observation_payloads.py` loads those exact files and
asserts each parses into the domain object it claims to be and satisfies every
invariant. Neither side edits the other's code; a break in either half shows up
in both people's `make check`.
