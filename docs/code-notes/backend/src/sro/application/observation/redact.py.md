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

## module, [line 16](../../../../../../../backend/src/sro/application/observation/redact.py#L16): Note on the line above

Code: `_URL_KEYS = ("url", "frame_url", "page_url", "location")`

> Every key on any node of the protocol whose value is a URL.
>
> By name rather than by event kind, because they are the same field wearing
> four hats: a page event's `url`, a snapshot's `url`, the `frame_url` a request
> was issued from, the `page_url` a gesture happened on and a redirect hop's
> `location`. Naming them once is what stops the next kind of event from
> arriving with a URL nobody redacts.

## module, [line 18](../../../../../../../backend/src/sro/application/observation/redact.py#L18): Note on the line above

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

## `redact_events`, [line 21](../../../../../../../backend/src/sro/application/observation/redact.py#L21): Docstring

> The same events with every credential-shaped or credential-named value gone.
>
> Copies rather than mutates: the caller's events came off an HTTP request
> body and the rejection report beside them refers to positions in it.

## `_shapes_only`, [line 44](../../../../../../../backend/src/sro/application/observation/redact.py#L44): Docstring

> Every string under here through `redact_shapes`, and nothing else.
>
> Structure is preserved exactly -- a locator is built from this tree, so a
> key or a role that changed would change what a skill can find.

## `_element`, [line 76](../../../../../../../backend/src/sro/application/observation/redact.py#L76): Docstring

> A `target` or the `component` hanging off it -- the same three fields.

## `_attributes`, [line 91](../../../../../../../backend/src/sro/application/observation/redact.py#L91): Docstring

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

## `_headers`, [line 121](../../../../../../../backend/src/sro/application/observation/redact.py#L121): Docstring

> The name kept and the value replaced, so a reader still sees the call was
> authenticated.
>
> `is_secret(classify_header(...))` is the same set the extension's
> `isSecretHeader` answers true for -- exact list, then the CSRF and session
> hints, with an HTTP/2 pseudo-header decided first because `:authority`
> contains "auth". A header nobody named a credential can still carry one:
> the 34 `X-Goog-Api-Key` values in this store are matched by nothing but
> their shape.

## `_hop`, [line 145](../../../../../../../backend/src/sro/application/observation/redact.py#L145): Docstring

> One entry of a redirect chain, whose shape the protocol leaves open.
>
> The extension sends `[]` today and the Steel path sends url/status/location,
> so this reads by key name rather than by a declared type: a hop was the one
> part of a request nothing validated and nothing redacted, and the rig's
> audit put both a `?code=` URL and an `Authorization` header on disk through
> it.

## `_event`, [line 36](../../../../../../../backend/src/sro/application/observation/redact.py#L36): Comment

Code: `out["snapshot"] = _shapes_only(snapshot)`

> The accessibility tree is 27MB of this deployment's 59MB evidence
> plane -- every string a page rendered, which is where a key shown on
> screen would sit. Shapes only, never the name rule: the tree's own
> vocabulary uses `token` and `tokenList` as CDP AXValue TYPE
> descriptors, and a name rule would blank 2,573 of them here for no
> protection at all. Measured across 70,636 real nodes: zero shapes,
> so this costs nothing today and covers the day a page renders one.

## `_event`, [line 40](../../../../../../../backend/src/sro/application/observation/redact.py#L40): Comment

Code: `out["detail"] = redact_body(detail, content_type=None)[0]`

> Free text on a page event -- a title, an error, whatever the page
> said -- so it gets the body rule with no content type to go on. A
> `?magic_link_token=` landed here in the rig's audit.

## `_gesture`, [line 68](../../../../../../../backend/src/sro/application/observation/redact.py#L68): Comment

Code: `out["value"] = None`

> What the operator typed into a password field. Dropped rather than
> marked: `null` is what the extension already sends for one of these,
> so the stored shape is the same whether or not the browser obeyed.

## `_gesture`, [line 70](../../../../../../../backend/src/sro/application/observation/redact.py#L70): Comment

Code: `out["value"] = redact_shapes(value)`

> Not flagged and still a credential: a token pasted into an ordinary
> search box is not typed into an `input[type=password]`, so nothing
> upstream marks it. The shape does.

## `_body`, [line 139](../../../../../../../backend/src/sro/application/observation/redact.py#L139): Comment

Code: `already = out.get("redacted_fields")`

> Beside the names the extension already put there. `redact_body`
> reports a shape as `«shape: jwt»` rather than as a field name,
> because "this went because it looked like a JWT" is a different fact
> from "this went because it was called password".
