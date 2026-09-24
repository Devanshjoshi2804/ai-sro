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

## module, [line 18](../../../../../../../backend/src/sro/application/observation/redact.py#L18): Note on the line above

Code: `_URL_KEYS = ("url", "frame_url", "page_url", "location")`

> Every key on any node of the protocol whose value is a URL.
>
> By name rather than by event kind, because they are the same field wearing
> four hats: a page event's `url`, a snapshot's `url`, the `frame_url` a request
> was issued from, the `page_url` a gesture happened on and a redirect hop's
> `location`. Naming them once is what stops the next kind of event from
> arriving with a URL nobody redacts.

## module, [line 20](../../../../../../../backend/src/sro/application/observation/redact.py#L20): Note on the line above

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

## `redact_events`, [line 29](../../../../../../../backend/src/sro/application/observation/redact.py#L29): Docstring

> The same events with every credential-shaped or credential-named value gone.
>
> Copies rather than mutates: the caller's events came off an HTTP request
> body and the rejection report beside them refers to positions in it.

## `_shapes_only`, [line 160](../../../../../../../backend/src/sro/application/observation/redact.py#L160): Docstring

> Every string under here through `redact_shapes`, and nothing else.
>
> Structure is preserved exactly -- a locator is built from this tree, so a
> key or a role that changed would change what a skill can find.

## `_element`, [line 192](../../../../../../../backend/src/sro/application/observation/redact.py#L192): Docstring

> A `target` or the `component` hanging off it -- the same three fields.

## `_attributes`, [line 207](../../../../../../../backend/src/sro/application/observation/redact.py#L207): Docstring

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

## `_headers`, [line 237](../../../../../../../backend/src/sro/application/observation/redact.py#L237): Docstring

> The name kept and the value replaced, so a reader still sees the call was
> authenticated.
>
> `is_secret(classify_header(...))` is the same set the extension's
> `isSecretHeader` answers true for -- exact list, then the CSRF and session
> hints, with an HTTP/2 pseudo-header decided first because `:authority`
> contains "auth". A header nobody named a credential can still carry one:
> the 34 `X-Goog-Api-Key` values in this store are matched by nothing but
> their shape.

## `_hop`, [line 261](../../../../../../../backend/src/sro/application/observation/redact.py#L261): Docstring

> One entry of a redirect chain, whose shape the protocol leaves open.
>
> The extension sends `[]` today and the Steel path sends url/status/location,
> so this reads by key name rather than by a declared type: a hop was the one
> part of a request nothing validated and nothing redacted, and the rig's
> audit put both a `?code=` URL and an `Authorization` header on disk through
> it.

## `_event`, [line 152](../../../../../../../backend/src/sro/application/observation/redact.py#L152): Comment

Code: `out["snapshot"] = _shapes_only(snapshot)`

> The accessibility tree is 27MB of this deployment's 59MB evidence
> plane -- every string a page rendered, which is where a key shown on
> screen would sit. Shapes only, never the name rule: the tree's own
> vocabulary uses `token` and `tokenList` as CDP AXValue TYPE
> descriptors, and a name rule would blank 2,573 of them here for no
> protection at all. Measured across 70,636 real nodes: zero shapes,
> so this costs nothing today and covers the day a page renders one.

## `_event`, [line 156](../../../../../../../backend/src/sro/application/observation/redact.py#L156): Comment

Code: `out["detail"] = redact_body(detail, content_type=None)[0]`

> Free text on a page event -- a title, an error, whatever the page
> said -- so it gets the body rule with no content type to go on. A
> `?magic_link_token=` landed here in the rig's audit.

## `_gesture`, [line 184](../../../../../../../backend/src/sro/application/observation/redact.py#L184): Comment

Code: `out["value"] = None`

> What the operator typed into a password field. Dropped rather than
> marked: `null` is what the extension already sends for one of these,
> so the stored shape is the same whether or not the browser obeyed.

## `_gesture`, [line 186](../../../../../../../backend/src/sro/application/observation/redact.py#L186): Comment

Code: `out["value"] = redact_shapes(value)`

> Not flagged and still a credential: a token pasted into an ordinary
> search box is not typed into an `input[type=password]`, so nothing
> upstream marks it. The shape does.

## `_body`, [line 255](../../../../../../../backend/src/sro/application/observation/redact.py#L255): Comment

Code: `already = out.get("redacted_fields")`

> Beside the names the extension already put there. `redact_body`
> reports a shape as `«shape: jwt»` rather than as a field name,
> because "this went because it looked like a JWT" is a different fact
> from "this went because it was called password".

## module, [line 22](../../../../../../../backend/src/sro/application/observation/redact.py#L22): Note on the line above

Code: `_KEEPS_ITS_VALUE = ("press", "scroll")`

> The gesture kinds whose `value` is not something typed: a key's name (Enter,
> Tab, Escape) and a scroll offset. On a sign-in page every other value goes.

## module, [line 24](../../../../../../../backend/src/sro/application/observation/redact.py#L24): Note on the line above

Code: `_PATHS = frozenset({"cssPath", "xpath", "query", "chain"})`

> The parts of a target that find it again rather than describe it. Built from
> ids, tags and component names, never from anything typed, so a typed value is
> never looked for in them -- a username that happens to be a substring of an id
> would otherwise break the path the sign-in chain is learned from.

## module, [line 26](../../../../../../../backend/src/sro/application/observation/redact.py#L26): Note on the line above

Code: `_ABSOLUTE = ("http://", "https://")`

> A string in a tree that is an absolute URL gets the URL rule, not only the
> shape rule. Chrome writes a page's own URL on the tree's root and a link's on
> the link, and the page an OAuth flow returns to has its `code` in exactly
> that -- found by the real-Chrome proof of §5.6.

## `redact_events`, [line 29](../../../../../../../backend/src/sro/application/observation/redact.py#L29): Docstring

> Spec §5.6, enforced again at the one door every upload comes through. The
> extension decides first, so the values never leave the browser; this does not
> trust it to have. A sign-in event is stored structure-only (`_structure_only`)
> and everything else gets the ordinary redaction.

## `_signing_in`, [line 38](../../../../../../../backend/src/sro/application/observation/redact.py#L38): Docstring

> Which events of a batch are on a sign-in page.
>
> Marked by the browser (`sign_in` on the event or its gesture), or detected
> here: a gesture on a password or one-time-code field (`is_sign_in_field`), or
> anything on a tab inside an OAuth/OIDC flow, followed over the batch's page
> marks with the same `SignInFlow` Steel uses. Then everything else on the same
> page as one of those -- same tab, same visit (page marks of kind `navigated`
> count them) and same URL -- because a browser that did not mark its gestures
> did not mark that page's tree or its calls either.
>
> ponytail: per batch. A sign-in page split across two uploads is judged half by
> half; the browser's own marks carry the other half. The ceiling is a browser
> that marks nothing AND splits a sign-in page across batches; the upgrade is
> remembering open flows per device between batches.

## `_typed`, [line 84](../../../../../../../backend/src/sro/application/observation/redact.py#L84): Docstring

> What was typed on the batch's sign-in pages, longest first, for taking out of
> whatever else those pages rendered it into -- a code echoed into a div, into
> the label of the button that submits it. The join of every value too: a code
> typed one digit per box is echoed whole.
>
> ponytail: a value of one character on its own is not looked for, because
> taking every "a" out of a label says nothing and breaks the label. The
> recorder applies the same floor in the page.

## `_structure_only`, [line 99](../../../../../../../backend/src/sro/application/observation/redact.py#L99): Docstring

> One event of a sign-in page, as §5.6 keeps it: marked `sign_in`; a gesture's
> target and kind, with no typed value and nothing typed left in its prose or
> attributes (and no `value` attribute at all); a call's method, URL, headers
> and status with no body either way; a tree emptied to `{}` -- kept as an
> event, so the batch's counts stay what the browser sent, with nothing in it.
