# Notes for `backend/src/sro/cli/mint.py`

Comments and docstrings moved out of [`backend/src/sro/cli/mint.py`](../../../../../../backend/src/sro/cli/mint.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../backend/src/sro/cli/mint.py#L1): Docstring

> Issue a credential for an operator. Shell access only, on purpose.
>
> Lives beside the composition root rather than under `interface`, because it
> binds to an adapter by name and `interface` may not: a router reaching an
> adapter directly is how a deployment ends up unable to swap one.
>
> There is no self-service sign-up and no password store: somebody who can run
> this on the box hands a token to somebody who needs one, and it expires. That
> is the right amount of identity for a system whose customers will bring their
> own SSO, and it is enough to make the tenant boundary real.
>
>     python -m sro.cli.mint acme clerk --days 30

## `main`, [line 32](../../../../../../backend/src/sro/cli/mint.py#L32): Comment

Code: `print(token)`

> The token itself on stdout and nothing else, so it can be piped without
> a human having to cut a banner off it.
