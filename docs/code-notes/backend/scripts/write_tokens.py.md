# Notes for `backend/scripts/write_tokens.py`

Comments and docstrings moved out of [`backend/scripts/write_tokens.py`](../../../../backend/scripts/write_tokens.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/write_tokens.py#L1): Docstring

> Copy the brand palette into the extension.
>
> The console and the extension shipped two different oranges, neither of them the
> brand's, because each surface kept its own copy of the colours. There is no
> bundler here and there should not be one for a stylesheet, so this does the one
> thing that stops them drifting: writes the canonical file into the extension's
> tree with a header saying not to edit it.
>
>     make tokens
>
> `new-chrome-extension/src/tokens.test.mjs` fails if the copy is stale, so the
> question gets asked where the code is rather than in a pipeline nobody watches.
