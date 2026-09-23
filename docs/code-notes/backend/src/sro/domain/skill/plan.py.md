# Notes for `backend/src/sro/domain/skill/plan.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/plan.py`](../../../../../../../backend/src/sro/domain/skill/plan.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/plan.py#L1): Docstring

> The two ways to perform a step. See docs/07-adr/005-dual-recipe.md.

## `HeaderPlan`, [line 16](../../../../../../../backend/src/sro/domain/skill/plan.py#L16): Docstring

> One header the call carried, and how to produce it again.
>
> Every observed header is recorded. What differs is where the value comes
> from: a literal template for semantic headers, a vault reference for
> credentials, a fresh mint for CSRF and trace ids.

## `HeaderPlan`, [line 19](../../../../../../../backend/src/sro/domain/skill/plan.py#L19): Note on the line above

Code: `value: Template | None = None`

> Literal or templated value. ``None`` when the value is resolved at run time.

## `HeaderPlan`, [line 21](../../../../../../../backend/src/sro/domain/skill/plan.py#L21): Note on the line above

Code: `credential_ref: str | None = None`

> Vault key for AUTH and SESSION headers. Resolved by the executor, so the
> real credential is used without being copied into a shared artifact.

## `HeaderPlan`, [line 23](../../../../../../../backend/src/sro/domain/skill/plan.py#L23): Note on the line above

Code: `mint: bool = False`

> True for CSRF and trace headers: the captured value is stale by design and
> a fresh one must be obtained from the live session.

## `HeaderPlan`, [line 25](../../../../../../../backend/src/sro/domain/skill/plan.py#L25): Note on the line above

Code: `managed: bool = False`

> True when the HTTP client owns the value: Host, Content-Length, Referer,
> Origin, the sec-* family. The header is recorded because it was observed,
> but the captured value describes the browser that made the demonstration,
> not the call. Replaying a stale Referer is misleading; replaying a captured
> Content-Length is actively harmful.

## `NetworkPlan`, [line 48](../../../../../../../backend/src/sro/domain/skill/plan.py#L48): Docstring

> Replay of the call the demonstrated action produced.

## `NetworkPlan`, [line 53](../../../../../../../backend/src/sro/domain/skill/plan.py#L53): Note on the line above

Code: `body_blob_uri: str | None = None`

> Set when the captured body was too large to inline. Still replayable.

## `NetworkPlan`, [line 58](../../../../../../../backend/src/sro/domain/skill/plan.py#L58): Note on the line above

Code: `replayable: bool = True`

> False when a template alone cannot reproduce the call -- a client-minted
> signature, a nonce, a websocket frame. Kept as documentation of the step.

## `ToolPlan`, [line 91](../../../../../../../backend/src/sro/domain/skill/plan.py#L91): Docstring

> Perform this step by calling a tool on a connector the tenant configured.
>
> The one kind of plan no demonstration produces. Induction reads recordings
> and a recording holds gestures and the calls they made, so a tool step is
> always somebody's decision: this click on Send is `send_message` on that
> server. Recorded as a decision with a name on it, never inferred -- which
> is ADR 004's rule about identity applied to the thing performing the step
> rather than to the values it carries.

## `ToolPlan`, [line 92](../../../../../../../backend/src/sro/domain/skill/plan.py#L92): Note on the line above

Code: `server: str`

> The connector, by the name the tenant gave it. Resolved to a URL and a
> credential the same way `target_system` is: this is the vocabulary a
> reviewer reads, and the address is configuration.

## `ToolPlan`, [line 95](../../../../../../../backend/src/sro/domain/skill/plan.py#L95): Note on the line above

Code: `arguments: tuple[tuple[str, Template], ...] = ()`

> Argument name to what goes in it, in the order the mapping named them.
> A tuple of pairs rather than a mapping so two versions of one skill are
> comparable and a document round-trips byte for byte.

## `ToolPlan`, [line 97](../../../../../../../backend/src/sro/domain/skill/plan.py#L97): Note on the line above

Code: `writes: bool = False`

> Whether calling this changes something outside this system.
>
> Said by whoever mapped the step, because nothing else can say it. MCP tools
> do not declare it, a name is not a promise, and a system that guessed would
> guess wrong in the direction of sending a mail nobody approved. It is what
> `changes_the_system` reads, so it decides whether a run may send this at
> all below the assisted rung.

## `UiPlan`, [line 117](../../../../../../../backend/src/sro/domain/skill/plan.py#L117): Docstring

> Drive the interface the way the human did.

## `UiPlan`, [line 122](../../../../../../../backend/src/sro/domain/skill/plan.py#L122): Note on the line above

Code: `target_path: str | None = None`

> Ancestry of the target within the AX graph, e.g.
> ``dialog “Release” > form > button “Confirm”``. Disambiguates the third Save
> button on a page, which an accessible name alone cannot.

## `UiPlan`, [line 124](../../../../../../../backend/src/sro/domain/skill/plan.py#L124): Note on the line above

Code: `locators: tuple[ControlLocator, ...] = ()`

> How to find the control again, strongest strategy first.
>
> Separate from ``target`` on purpose: the fingerprint is evidence about one
> moment, and a locator is a decision about what will still be true later.
> Empty means the demonstration produced nothing worth replaying by -- which
> is a fact about that step, not a reason to guess.

## `NetworkPlan.is_mutation`, [line 72](../../../../../../../backend/src/sro/domain/skill/plan.py#L72): Docstring

> Whether replaying this changes the target system.
>
> The same question `CapturedRequest.is_mutation` answers about the call
> that was recorded, spelled out by hand in eight places before this --
> each of them a chance for one of them to disagree about which methods
> are safe.

## `NetworkPlan.required_credentials`, [line 86](../../../../../../../backend/src/sro/domain/skill/plan.py#L86): Docstring

> Vault keys the executor must resolve before this call can be made.

## `UiPlan.replayable`, [line 131](../../../../../../../backend/src/sro/domain/skill/plan.py#L131): Docstring

> Whether a driver could act on this step at all.
