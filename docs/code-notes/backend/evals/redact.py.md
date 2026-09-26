# Notes for `backend/evals/redact.py`

How a real case becomes one that may be committed.

## `_KEPT`, [line 9](../../../../backend/evals/redact.py#L9): Constant

> Kept as they are: all-lowercase words (the prose of a mail and of the
> evidence, and the schema's own keys) and this system's own ids (`ges_`,
> `wfl_` plus 32 hex), which carry nothing of the customer's and which a
> cite must still name. Everything else -- a capitalised word, a number, a
> host, an address -- becomes its shape. An address is shaped even when its
> parts are lowercase. A lowercase customer word (a site name typed in lower
> case) survives: that is why a person reads every candidate before it moves
> to `ci/`.

## `shape`, [line 13](../../../../backend/evals/redact.py#L13): Function

> Upper case to `A`, other letters to `a`, digits to `9`, anything else kept:
> `GT-0042` is `AA-9999`. A shape keeps what a prompt reasons with (a code, a
> date, a quantity) and drops what the value was.

## `redacted`, [line 56](../../../../backend/evals/redact.py#L56): Design

> One shape map per case, shared by the input, the expected and the recorded
> answer: the same value becomes the same shape everywhere, so a quoted value
> still occurs in its mail and an expected value still matches the answer.
> Two values with one shape get `~2`, `~3`, so two values stay two values.
> Keys are shaped too: a field label can carry a customer's word.
