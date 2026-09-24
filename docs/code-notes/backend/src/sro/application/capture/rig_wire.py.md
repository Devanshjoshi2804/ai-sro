# Notes for `backend/src/sro/application/capture/rig_wire.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/rig_wire.py`](../../../../../../../backend/src/sro/application/capture/rig_wire.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L1): Docstring

> The extension's batch protocol, as the rig defined it. Pydantic, because it is a wire format.
>
> Copied rather than imported: see 'Decision: no path dependency' in the plan.
> Proved against new-chrome-extension/fixtures/, which a real browser produced.

## `_a_timestamp`, [line 30](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L30): Docstring

> An RFC3339 string, checked here rather than where it is finally read.
>
> correlate._epoch parses these strictly, and it runs *after* parse_batch --
> so one unparseable `started_at` raised out of the ingest route and cost the
> whole batch a 500, taking the three hundred good events beside it. Worse
> than the loss: a 500 is not a permanent 4xx, so the extension keeps the
> rows queued and retries forever while that device's capture stalls in
> silence. The batch boundary already owns 'a rejected event does not reject
> the batch'; the format check belongs there with it, so the bad event
> becomes one named RejectedEvent and nothing downstream has to defend.

## `Component`, [line 54](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L54): Note on the line above

Code: `required: bool | None = None`

> Ext's own `allowBlank: false`, where the component said.

## `Target`, [line 87](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L87): Note on the line above

Code: `required: bool | None = None`

> Whether the PAGE says this field must be filled -- `aria-required`, the
> HTML5 attribute, or a star on its label. Three states kept as three: None
> is a page that said nothing, and coercing it to False would be this system
> claiming a form said something it never said.

## `is_secret_header`, [line 193](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L193): Docstring

> Whether a header called this carries a credential.

## `redact_attributes`, [line 200](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L200): Docstring

> Every DOM attribute of the element the operator touched, by all three rules.
>
> `Target.attributes` is `dict[str, Any]` -- whatever the page happened to put
> on the element -- so no single rule reaches it. `data-auth-token` is caught
> by its NAME, `href="/cb?access_token=..."` by the URL rule inside its value,
> and an `X-Acme-Ticket` copied onto a `data-` attribute only by its SHAPE.
> Round 1: a string leaf used to get redact_shapes only as redact_url's own
> tail call, which never runs when urlparse refuses the string -- an
> attribute is not a URL and need not parse as one, so a shaped credential
> beside a stray `[` rode straight through. Both rules now run
> unconditionally on every string leaf.
>
> redact_data one clause longer, rather than a change to redact_data: that one
> runs over request bodies, where the shape pass already follows it in
> redact_body and a URL rule on every JSON string leaf would be a behaviour
> change to every stored body. Here nothing else runs at all -- this field was
> write-only, read by nothing and redacted by nothing.
>
> The field rule and not the header one, deliberately: an attribute named
> `placeholder` whose value is "Password" is a LABEL. Measured over the acme
> capture -- 13 distinct attribute names, 95 distinct values -- none move.

## `parse_batch`, [line 344](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L344): Docstring

> Parse a batch, keeping every event that parses and naming those that do not.
>
> The protocol is explicit: "A rejected event does not reject the batch." One
> unrecognised gesture kind must cost one event, not the three hundred good ones
> beside it. Losing a morning of evidence because the extension shipped a new
> gesture is the failure this system exists to prevent.

## `Component.a_credential_on_the_control_is_dropped_here`, [line 60](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L60): Docstring

> The DOM plane's half of the rule every other model here already has.
>
> `fieldLabel` and `text` are stored verbatim in `gestures.gesture_json`
> AND go through trim() into the per-gesture reading prompt and
> as_evidence() into the umbrella prompt -- so a token rendered as a label
> reached both models and the disk. Same boundary as its five siblings,
> for the reason they give: a rule applied at a call site is a rule the
> next caller walks past.

## `Target.must_carry_some_signal`, [line 95](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L95): Docstring

> The protocol refuses a fingerprint with nothing to match on.

## `Target.a_credential_on_the_element_is_dropped_here`, [line 101](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L101): Docstring

> `name` and `text` are prose; `attributes` is an open dump.
>
> Runs after must_carry_some_signal, and cannot defeat it: redact_shapes
> substitutes, so a name that was entirely a JWT comes back as the marker
> -- still a signal, and still stable across occurrences because the
> substitution is deterministic. A control whose only name is a credential
> has no identity worth keeping anyway.

## `Target.a_credential_on_the_element_is_dropped_here`, [line 106](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L106): Note on the line above

Code: `if self.secret:`

> Round 1: `secret` is the operator's own signal that this is a password
> field, and it is the one the two rules below cannot see. Neither
> `is_secret_name` nor `redact_shapes` has any reason to flag a key literally
> named `value` -- the word carries none of the signal `is_secret_name`
> checks for, and a live DOM value like a plain, low-entropy password rarely
> has the shape `redact_shapes` looks for. Nothing else catches this, so the
> server trusts the client's `secret` and never the client's redaction --
> whatever a page-code change or a bug sends here, a secret target keeps no
> `value` attribute at all.

## `Gesture.a_credential_value_is_dropped_here`, [line 154](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L154): Docstring

> AGENTS.md: credential values never reach storage. This is the boundary.

## `Gesture.a_credential_in_the_url_is_dropped_here`, [line 162](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L162): Docstring

> The same boundary, one field over. `#access_token=...` on a gesture
> url reached disk while the typed value beside it was guarded -- which
> is the shape of every credential defect this codebase has had: a rule
> applied at one field is a rule the next field walks past.

## `GestureEvent.a_credential_in_a_url_is_dropped_here`, [line 176](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L176): Docstring

> frame_url has its own column on `gestures`; both are stored.

## `Request.a_credential_header_is_dropped_here`, [line 265](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L265): Docstring

> Same boundary, same reason, as the typed credential above.
>
> trim._call() already keeps headers out of the prompt, so this is about
> the store: save_batch writes the request verbatim, and an Authorization
> header or a session cookie sitting in a row is the thing AGENTS.md
> forbids. The extension redacts these client-side and demonstrably does
> -- 270 markers in the real acme capture -- but a rule that runs only in
> a browser is one a browser can be made not to run.
>
> The name is kept and the value replaced, so a reader can still see that
> a call was authenticated.

## `Request.a_credential_elsewhere_on_the_call_is_dropped_here`, [line 275](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L275): Docstring

> The header rule above covered one field of this model's eight.
>
> A `?session_token=` in the url, a `{"password": ...}` in either body,
> and a hop in redirect_chain are the same credential by another route,
> and the audit proved all of them on disk with the header rule right
> there in the same class. Both belts run at the parse boundary, once,
> because a rule that runs at a call site is a rule the next caller does
> not run.

## `RequestEvent.a_credential_in_a_url_is_dropped_here`, [line 292](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L292): Docstring

> An orphan request is stored as the whole event, frame_url included.

## `PageEvent.a_credential_on_a_page_event_is_dropped_here`, [line 308](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L308): Docstring

> A page event is stored whole -- attached to a gesture, or in
> orphan_pages -- and the audit landed a `?magic_link_token=` in url and
> a credential in detail, which is free text and so gets the body rule.

## module, [line 15](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L15): Comment

Code: `from sro.domain.observation.redaction import SECRET_HEADER_HINTS as SECRET_HEADER_HINTS`

> The credential vocabulary and the rules that act on it, imported rather than
> held here: they live in `sro.domain.observation.redaction`, because the other
> belt -- `sro.domain.observation.trim.body_keys`, which applies the same three
> rules to every body that reaches a prompt -- is in the domain, the domain may
> not import this module, and one rule with two copies is the thing that has
> already gone wrong once. Re-exported under their own names so this module
> stays the one address for the wire's redaction.

## `_a_timestamp`, [line 36](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L36): Comment

Code: `raise ValueError(f"timestamp has no timezone: {value!r}")`

> The parseable-but-zone-less case, which is worse than the
> unparseable one because nothing raises. correlate._epoch calls
> .timestamp() on this, and a naive datetime is read as LOCAL time --
> so on a machine at +05:30 the same instant as
> '2026-08-31T08:40:04.812Z' lands 19800s away, every request detaches
> from its gesture, and every gesture is read with no evidence at all.
> Silently: no error, no orphan count that looks wrong, just worse
> readings. AGENTS.md requires timezone-aware timestamps and this is
> the boundary that can still say so.

## module, [line 43](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L43): Comment

Code: `_COMPONENT_PROSE = ("name", "fieldLabel", "text")`

> The free-text fields of the two models below: what a person can read on the
> screen, and therefore what a page can render a credential into. `label(el)` in
> the extension's recorder falls back to innerText, so a screen showing a key
> puts that key here.
>
> Everything NOT on these lists is left alone on purpose. `itemId`, `query`,
> `xtype`, `testId`, `role` and `cssPath` are what shape.target_identity and
> shape_key are built from, and a redaction there would silently change a
> workflow's shape key so the same job stopped matching itself across
> occurrences. `chain`, `tag`, `xpath` and `bounds` are locators and geometry by
> the same argument.
>
> Only the SHAPE rule runs on these, never the name rule: a fieldLabel reading
> "Password" is a NAME, and is the single most useful thing in the evidence for
> telling a model what the operator was doing. Measured over the 83-gesture acme
> capture: 56 distinct real labels, 0 blanked.

## `Target`, [line 91](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L91): Inline

Code: `component: Component | None = None`

> null on plain HTML; only ExtJS has one

## `Gesture`, [line 140](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L140): Comment

Code: `target: Target | None = None`

> A scroll has no target: you scroll a page, not an element. Real capture
> from the acme tenant carries scrolls with the key absent entirely, and
> requiring it rejected every one of them -- 15% of that sample's gestures.

## `Gesture`, [line 141](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L141): Inline

Code: `value: str | None = None`

> absent on click and press

## `Gesture`, [line 142](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L142): Inline

Code: `secret: bool = False`

> absent on everything but a credential field

## `Gesture`, [line 147](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L147): Inline

Code: `at: float`

> Unix seconds, float — recorder.js's format

## `Gesture.a_credential_value_is_dropped_here`, [line 158](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L158): Comment

Code: `object.__setattr__(self, "value", redact_shapes(self.value))`

> Not flagged, and still a credential: a token pasted into an
> ordinary search box is not typed into an input[type=password],
> so nothing upstream marks it. The shape does.

## `is_secret_header`, [line 195](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L195): Comment

Code: `if lowered.startswith(":"):`

> An HTTP/2 pseudo-header is the request line, not a header, and never a
> credential -- but `:authority` (the host) contains the hint "auth", so the
> hints below redacted it and the stored request lost its host. Mirrors the
> same first check in the extension's isSecretHeader.

## `Request`, [line 254](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L254): Inline

Code: `status: int | None = None`

> null on a failed request

## `Request.a_credential_header_is_dropped_here`, [line 268](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L268): Comment

Code: `if is_secret_header(name):`

> A header nobody named a credential can still carry one: an
> `X-Acme-Ticket` holding a JWT is the same secret as an
> Authorization holding it, and only the value says so.

## `Request.a_credential_elsewhere_on_the_call_is_dropped_here`, [line 279](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L279): Comment

Code: `shaped = shapes_in(body.text)`

> Read off the original text, before redact_body replaces it:
> a body that lost a value to the SHAPE rule says so in
> redacted_fields, beside the names the extension put there for
> the ones that went by name. Same marker in the text either
> way; different fact about why.

## `parse_batch`, [line 346](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L346): Comment

Code: `return Batch.model_validate(raw), ()`

> A batch whose events cannot even be enumerated is a malformed
> ENVELOPE, not a batch containing bad events. Defaulting to [] here
> answers 202 for a truncated body and -- because save_batch is
> idempotent on batch_id -- permanently poisons that id, so the real
> retry is discarded as "already had it". Silent, total loss of a batch.
> Let the envelope model refuse it and say why; the route turns that
> into a 422.

## `parse_batch`, [line 357](../../../../../../../backend/src/sro/application/capture/rig_wire.py#L357): Comment

Code: `where = ".".join(str(part) for part in first.get("loc", ()))`

> The location, not only the message: "Input should be a valid
> number" names nothing a person can act on, and the whole point of
> a RejectedEvent is that somebody can find out what the extension
> sent that this could not read.
