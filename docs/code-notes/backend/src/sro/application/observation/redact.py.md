# Notes for `backend/src/sro/application/observation/redact.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/redact.py`](../../../../../../../backend/src/sro/application/observation/redact.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/redact.py#L1): Docstring

> Take the credentials out of an upload, once, before any of it is stored.
>
> The extension redacts before it sends, and demonstrably does -- the stored
> batches are full of `«redacted»` where an `Authorization` header was. But a
> rule that runs only in a browser is one a browser can be made not to run, and
> the audit measured what that costs: a live JWT and the `&code=` that carried it
> reached `s3://sro-artifacts/acme/...` with zero markers on that URL, because
> `admit()` screens by host policy and `_ndjson()` serialises, and nothing
> between them looked at a value.
>
> **One boundary, not several call sites.** Everything an operator's browser
> uploads passes through `IngestObservation.execute`, so this runs there, on the
> whole batch, and no future writer of an event field has to remember a rule.
>
> What is deliberately NOT redacted is as much of the point as what is. `itemId`,
> `query`, `xtype`, `testId`, `role` and `cssPath` are what locators and workflow
> shape keys are built from: redacting one silently changes a workflow's identity
> between occurrences, so the same job stops matching itself and the mining run
> sees two rare tasks instead of one common one. Only the free-text plane --
> what a person could read on the screen -- gets the shape rule, because that is
> where a page can render a credential.

## module, [line 37](../../../../../../../backend/src/sro/application/observation/redact.py#L37): Note on the line above

Code: `_URL_KEYS = ("url", "frame_url", "page_url", "location")`

> Every key on any node of the protocol whose value is a URL.
>
> By name rather than by event kind, because they are the same field wearing
> four hats: a page event's `url`, a snapshot's `url`, the `frame_url` a request
> was issued from, the `page_url` a gesture happened on and a redirect hop's
> `location`. Naming them once is what stops the next kind of event from
> arriving with a URL nobody redacts.

## module, [line 39](../../../../../../../backend/src/sro/application/observation/redact.py#L39): Note on the line above

Code: `_PROSE = ("name", "text", "fieldLabel")`

> The free-text fields of an element fingerprint and its ExtJS component.
>
> `label(el)` in the recorder falls back to `innerText`, so a screen showing a
> token puts that token here -- and it reached both the per-gesture prompt and
> the umbrella prompt in the rig before this was fixed there.
>
> Only the SHAPE rule runs on these, never the name rule: a `fieldLabel` reading
> "Password" is a LABEL, and it is the single most useful thing in the evidence
> for telling a model what the operator was doing. Measured over the 926 distinct
> URLs and 5,422 events in this store: no label moves.

## `_EVENT_KEYS`, [line 44](../../../../../../../backend/src/sro/application/observation/redact.py#L44): Constant

> The keys an event of each kind may carry into the blob, read off the wire
> models (`GestureEvent`, `RequestEvent`, `PageEvent`, `SnapshotEvent`), with
> `_GESTURE_KEYS` the same for the gesture inside a gesture event. Anything
> else is dropped before the blob is written. The blob used to pass unknown
> keys through verbatim, so a forged outline under a near key --
> `gesture.outline`, `gesture.snapshot`, a top-level `outlines` on a page
> event -- escaped the shape rule that `gesture.outlines` gets (E6 review,
> M2). Reading the models rather than listing keys here means a field the
> protocol adds is kept the day it is declared, and never before.
>
> **Ceiling:** the objects inside a gesture or request (`target`, `request`,
> `prior`) are not allowlisted here; each is redacted by its own rule and the
> parsed store copies only declared fields.

## `redact_events`, [line 81](../../../../../../../backend/src/sro/application/observation/redact.py#L81): Docstring

> The same events with every credential-shaped or credential-named value gone.
>
> Copies rather than mutates: the caller's events came off an HTTP request
> body and the rejection report beside them refers to positions in it.

## `_element`, [line 190](../../../../../../../backend/src/sro/application/observation/redact.py#L190): Docstring

> A `target` or the `component` hanging off it -- the same three fields.

## `_attributes`, [line 209](../../../../../../../backend/src/sro/application/observation/redact.py#L209): Docstring

> Every DOM attribute of the element the operator touched, by all three rules.
>
> `attributes` is whatever the page happened to put on the element, so no
> single rule reaches it: `data-auth-token` goes by its NAME,
> `href="/cb?access_token=..."` by the URL rule inside its value, and an
> `X-Acme-Ticket` copied onto a `data-` attribute only by its SHAPE.
> `redact_url` ends in `redact_shapes`, so a string leaf gets the last two
> from one call.
>
> The field rule and not the header one, deliberately: an attribute named
> `placeholder` whose value is "Password" is a label. The key is kept and the
> value replaced, so a reviewer still sees what was taken out.

## `_headers`, [line 239](../../../../../../../backend/src/sro/application/observation/redact.py#L239): Docstring

> The name kept and the value replaced, so a reader still sees the call was
> authenticated.
>
> `is_secret(classify_header(...))` is the same set the extension's
> `isSecretHeader` answers true for -- exact list, then the CSRF and session
> hints, with an HTTP/2 pseudo-header decided first because `:authority`
> contains "auth". A header nobody named a credential can still carry one:
> the 34 `X-Goog-Api-Key` values in this store are matched by nothing but
> their shape.

## `_hop`, [line 263](../../../../../../../backend/src/sro/application/observation/redact.py#L263): Docstring

> One entry of a redirect chain, whose shape the protocol leaves open.
>
> The extension sends `[]` today and the Steel path sends url/status/location,
> so this reads by key name rather than by a declared type: a hop was the one
> part of a request nothing validated and nothing redacted, and the rig's
> audit put both a `?code=` URL and an `Authorization` header on disk through
> it.

## `_event`, [line 118](../../../../../../../backend/src/sro/application/observation/redact.py#L118): Comment

Code: `out.pop("snapshot", None)`

> An accessibility tree is never kept. The extension no longer takes one
> (E6 replaced it with the screen outline, which rides on the gesture), but
> an older extension may still send a `snapshot` event. The event is still
> admitted and counted in `snapshots_ignored`; its tree is removed here,
> before the blob is written, unread. The tree's names carried whatever the
> operator typed -- an editable node's name, its `StaticText` children, a
> mirror, a `?token=` in a link's url property -- and no per-string rule
> made that safe (the E6 tree review, 2026-09-25).

## `_event`, [line 122](../../../../../../../backend/src/sro/application/observation/redact.py#L122): Comment

Code: `out["detail"] = redact_body(detail, content_type=None)[0]`

> Free text on a page event -- a title, an error, whatever the page
> said -- so it gets the body rule with no content type to go on. A
> `?magic_link_token=` landed here in the rig's audit.

## `_gesture`, [line 158](../../../../../../../backend/src/sro/application/observation/redact.py#L158): Comment

Code: `out["value"] = None`

> What the operator typed into a password field. Dropped rather than
> marked: `null` is what the extension already sends for one of these,
> so the stored shape is the same whether or not the browser obeyed.

## `_gesture`, [line 160](../../../../../../../backend/src/sro/application/observation/redact.py#L160): Comment

Code: `out["value"] = redact_shapes(value)`

> Not flagged and still a credential: a token pasted into an ordinary
> search box is not typed into an `input[type=password]`, so nothing
> upstream marks it. The shape does.

## `_body`, [line 257](../../../../../../../backend/src/sro/application/observation/redact.py#L257): Comment

Code: `already = out.get("redacted_fields")`

> Beside the names the extension already put there. `redact_body`
> reports a shape as `«shape: jwt»` rather than as a field name,
> because "this went because it looked like a JWT" is a different fact
> from "this went because it was called password".

## `_made`, [line 91](../../../../../../../backend/src/sro/application/observation/redact.py#L91): Docstring

> Which gesture a `ref` names: the same tab, the same frame path, the same
> `ref`, as `correlate` joins them. A string key because the values are the
> client's raw JSON and a hostile one need not be hashable.

## `_state`, [line 166](../../../../../../../backend/src/sro/application/observation/redact.py#L166): Docstring

> What is kept of a gesture's `prior`, the after-state of the gesture before
> it. Written to the evidence blob before `correlate` runs, so this is where
> it is judged -- the wire `AfterState` validator only ever sees the copy
> `correlate` reads. Only the three fields of an after-state survive, and
> `visible` / `enabled` only as booleans.

## `_setting`, [line 177](../../../../../../../backend/src/sro/application/observation/redact.py#L177): Docstring

> The server's half of the E5 ruling (2026-09-25): an after-state never holds
> free text, whatever the client sent. A value is kept only when the gesture
> it claims to describe (`prior_of`) is in this batch, on the same tab and
> frame, is not secret, and its target is a state control: a checkbox, radio
> or switch, and then only as `checked` / `unchecked`; or a select, as the
> label of what is chosen, with credential shapes redacted. Anything else --
> a text field, a password field, a custom control, a value whose gesture was
> dropped or never sent -- stores `None`. Judged by the target the backend
> received with that gesture, not by anything in the `prior` itself.


## `_event`, [line 97](../../../../../../../backend/src/sro/application/observation/redact.py#L97): Note on the branch

> The `effect` branch keeps only what `seen.effect_kept` lets through. The
> whitelist trap: `_EVENT_KEYS` and `_GESTURE_KEYS` come from the `rig_wire`
> model fields, so a key the recorder sends but the wire does not declare is
> dropped silently. Every new key is declared in `rig_wire` first.

## `_gesture`, [line 133](../../../../../../../backend/src/sro/application/observation/redact.py#L133): Note on the branch

> `place` and `choice` are sanitised through `seen.py` here and again by the
> wire validators: the blob is written from these redacted dicts, the rows from
> the parsed models, so each path must be safe on its own.
