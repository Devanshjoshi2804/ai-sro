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

## `epoch_to_datetime`, [line 74](../../../../../../../backend/src/sro/application/capture/decode.py#L74): Docstring

> CDP wall-clock timestamps are Unix seconds as a float.

## `to_headers`, [line 78](../../../../../../../backend/src/sro/application/capture/decode.py#L78): Docstring

> Every header, verbatim. Nothing filtered -- see docs/11-capture-completeness.md.

## `to_initiator`, [line 84](../../../../../../../backend/src/sro/application/capture/decode.py#L84): Docstring

> The 'why' of a request: what caused the browser to make it.

## `to_timing`, [line 111](../../../../../../../backend/src/sro/application/capture/decode.py#L111): Docstring

> CDP timings are offsets in milliseconds from ``requestTime``.
>
> Negative offsets mean the phase did not happen -- a reused connection has no
> DNS or TLS -- so they collapse to ``None`` rather than to a bogus zero.

## `to_cookies`, [line 139](../../../../../../../backend/src/sro/application/capture/decode.py#L139): Docstring

> All cookie attributes, including the ones that decide replayability.

## `to_ax_graph`, [line 165](../../../../../../../backend/src/sro/application/capture/decode.py#L165): Docstring

> ``Accessibility.getFullAXTree`` to a graph with its edges intact.
>
> Ignored nodes are kept: an element becoming ignored is itself a state change,
> and dropping them would break the parent chain for everything beneath.

## `to_console_message`, [line 226](../../../../../../../backend/src/sro/application/capture/decode.py#L226): Docstring

> ``Runtime.consoleAPICalled``. A logged validation failure is a branch reason.

## `to_input_action`, [line 271](../../../../../../../backend/src/sro/application/capture/decode.py#L271): Docstring

> A record emitted by the injected page recorder.
>
> The element description here is DOM-side and deliberately shallow: roles and
> accessible names come from the AX tree taken at the same instant, which is
> authoritative. This carries the selectors the AX tree cannot give.

## `_said`, [line 334](../../../../../../../backend/src/sro/application/capture/decode.py#L334): Docstring

> A three-state answer kept as three states.
>
> The recorder says `true`, `false` or `null`, and the difference between
> "the page said this is optional" and "the page said nothing" is the whole
> point of capturing it: `false` is a statement and `null` is a silence, and
> coercing the second to the first would be this system claiming a form said
> something it never said.

## `to_captured_request`, [line 341](../../../../../../../backend/src/sro/application/capture/decode.py#L341): Docstring

> A network exchange in the shape this system's own protocol uses.
>
> Not the CDP one: an extension has already done that translation in the
> browser, so what arrives is the domain's field names. Validated rather than
> trusted -- the invariants are the same ones a recording made here obeys.

## `to_input_action`, [line 278](../../../../../../../backend/src/sro/application/capture/decode.py#L278): Comment

Code: `value=(`

> Belt and braces: the page already dropped it, and a page is not a
> trustworthy place to enforce this.
