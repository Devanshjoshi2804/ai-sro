# Notes for `backend/src/sro/application/capture/decode.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/decode.py`](../../../../../../../backend/src/sro/application/capture/decode.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/decode.py#L1): Docstring

> Wire payloads to domain objects.
>
> The shapes are Chrome's -- ``Network.*``, ``Accessibility.getFullAXTree``, and
> the records the page recorder emits -- and they arrive from two places now: the
> capture adapter attached to a browser this deployment owns, and an extension in
> an operator's own. One definition, so evidence gathered either way becomes the
> same ``ActionFrame``.
>
> Pure: dictionaries in, domain out, no I/O and no clock. It lives here rather
> than beside the adapter because the second caller is a use case, and because
> what it translates is this system's own protocol (docs/14-extension-protocol.md)
> rather than anything Steel decides.

## `epoch_to_datetime`, [line 58](../../../../../../../backend/src/sro/application/capture/decode.py#L58): Docstring

> CDP wall-clock timestamps are Unix seconds as a float.

## `to_headers`, [line 62](../../../../../../../backend/src/sro/application/capture/decode.py#L62): Docstring

> Every header, verbatim. Nothing filtered -- see docs/11-capture-completeness.md.

## `to_initiator`, [line 68](../../../../../../../backend/src/sro/application/capture/decode.py#L68): Docstring

> The 'why' of a request: what caused the browser to make it.

## `to_timing`, [line 95](../../../../../../../backend/src/sro/application/capture/decode.py#L95): Docstring

> CDP timings are offsets in milliseconds from ``requestTime``.
>
> Negative offsets mean the phase did not happen -- a reused connection has no
> DNS or TLS -- so they collapse to ``None`` rather than to a bogus zero.

## `to_cookies`, [line 123](../../../../../../../backend/src/sro/application/capture/decode.py#L123): Docstring

> All cookie attributes, including the ones that decide replayability.

## `to_console_message`, [line 149](../../../../../../../backend/src/sro/application/capture/decode.py#L149): Docstring

> ``Runtime.consoleAPICalled``. A logged validation failure is a branch reason.

## `to_input_action`, [line 194](../../../../../../../backend/src/sro/application/capture/decode.py#L194): Docstring

> A record emitted by the injected page recorder: role and accessible name
> come from the recorder's own DOM reading (page-code.js `roleOf`/`labelOf`),
> not a separate accessibility-tree snapshot -- there is none any more (the
> screen outline, spec §4.6, replaced it). This carries the selectors that
> reading alone gives: bounds, css path, xpath, component identity.

## `_said`, [line 257](../../../../../../../backend/src/sro/application/capture/decode.py#L257): Docstring

> A three-state answer kept as three states.
>
> The recorder says `true`, `false` or `null`, and the difference between
> "the page said this is optional" and "the page said nothing" is the whole
> point of capturing it: `false` is a statement and `null` is a silence, and
> coercing the second to the first would be this system claiming a form said
> something it never said.

## `to_captured_request`, [line 264](../../../../../../../backend/src/sro/application/capture/decode.py#L264): Docstring

> A network exchange in the shape this system's own protocol uses.
>
> Not the CDP one: an extension has already done that translation in the
> browser, so what arrives is the domain's field names. Validated rather than
> trusted -- the invariants are the same ones a recording made here obeys.

## `to_input_action`, [line 201](../../../../../../../backend/src/sro/application/capture/decode.py#L201): Comment

Code: `value=(`

> Belt and braces: the page already dropped it, and a page is not a
> trustworthy place to enforce this.
