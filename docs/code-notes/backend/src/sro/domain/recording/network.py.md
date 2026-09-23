# Notes for `backend/src/sro/domain/recording/network.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/network.py`](../../../../../../../backend/src/sro/domain/recording/network.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/network.py#L1): Docstring

> Complete record of one network exchange. See docs/11-capture-completeness.md.

## `InitiatorKind`, [line 13](../../../../../../../backend/src/sro/domain/recording/network.py#L13): Docstring

> Why the browser made this call. The 'why' half of the capture.

## `Initiator`, [line 31](../../../../../../../backend/src/sro/domain/recording/network.py#L31): Docstring

> CDP initiator information.
>
> The JS stack is what turns "a click and then some requests happened" into
> "this handler issued this call", which is how a step's causality survives
> into the recipe.

## `Initiator`, [line 36](../../../../../../../backend/src/sro/domain/recording/network.py#L36): Note on the line above

Code: `parent_request_id: str | None = None`

> Set for redirects and for calls chained from another request.

## `Body`, [line 63](../../../../../../../backend/src/sro/domain/recording/network.py#L63): Docstring

> A request or response payload.
>
> Payloads over the inline threshold are written to object storage and the
> ``blob_uri`` is kept. Nothing is truncated away -- see
> docs/11-capture-completeness.md.

## `Body`, [line 68](../../../../../../../backend/src/sro/domain/recording/network.py#L68): Note on the line above

Code: `encoding: str | None = None`

> ``base64`` when the payload is binary.

## `Body`, [line 70](../../../../../../../backend/src/sro/domain/recording/network.py#L70): Note on the line above

Code: `redacted_fields: tuple[str, ...] = ()`

> Fields whose values were replaced before the body was ever stored.
>
> Only credentials, matched by field name. Recorded so a reviewer can see that
> something was removed and what it was called -- a silent redaction is
> indistinguishable from a capture bug.

## `CapturedRequest`, [line 88](../../../../../../../backend/src/sro/domain/recording/network.py#L88): Docstring

> One complete exchange: what was sent, what came back, and why it happened.

## `primary_of`, [line 152](../../../../../../../backend/src/sro/domain/recording/network.py#L152): Docstring

> The call a gesture is about, out of the analytics and prefetch noise.
>
> Preference order: a successful mutation whose initiator is a script (the
> click handler), then any successful mutation, then any success, then the
> first call at all. Script-initiated is the strongest signal available -- it
> is the one the human's click actually caused. A source with no initiator
> information degrades to the second rung rather than losing the ranking.
>
> Background traffic is excluded outright rather than ranked last. A
> keep-alive fires on a timer, so it lands on whichever step happens to be
> open; letting it stand as a step's primary call makes two runs of one task
> look like they diverged, and induction refuses the pair. The evidence keeps
> it -- this is about which call the step is *about*.
>
> A function rather than only a property on ActionFrame, because a second
> source of captured requests now needs the identical rule and two copies of
> it would be two rules the day one of them is edited.

## `CapturedRequest.header`, [line 144](../../../../../../../backend/src/sro/domain/recording/network.py#L144): Docstring

> Case-insensitive lookup. HTTP/2 lowercases; HTTP/1.1 does not.

## `primary_of.order`, [line 169](../../../../../../../backend/src/sro/domain/recording/network.py#L169): Comment

Code: `return (rank(request), request.url.split("?", 1)[0], request.started_at.timestamp())`

> Path before time on purpose. One gesture on a grid screen fires
> several reads at once, and which of them starts first is a race: the
> same demonstration twice picked `inventoryItems` in one run and
> `inventoryLocations` in the other, and the diff read that as two
> different steps. Ranking by path makes the choice a property of what
> the step did rather than of how the network went that day.
