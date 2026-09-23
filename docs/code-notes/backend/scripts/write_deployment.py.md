# Notes for `backend/scripts/write_deployment.py`

Comments and docstrings moved out of [`backend/scripts/write_deployment.py`](../../../../backend/scripts/write_deployment.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/write_deployment.py#L1): Docstring

> Tell the extension which deployment it belongs to.
>
> An operator installing this had to type an API url, a console url and paste a
> token -- three fields, with `localhost` placeholders that are wrong on every
> machine but a developer's. Getting the url wrong does not say so: it presents
> as "cannot reach the deployment", which reads like the deployment is down.
>
> So the build writes the two addresses in, the same way `make gen-recorder`
> writes the page recorder and `make tokens` writes the palette. What is left
> for a person is the one thing that is actually theirs: the credential.
>
>     make gen-deployment api=http://10.11.9.25:8088/api console=http://10.11.9.25:8088
>
> Committed rather than ignored, because the extension has no build step: what
> is in the tree is what gets loaded. That means the file names whichever
> deployment was last generated into it, and a QA build and a production build
> differ by this file -- which is the honest shape of an extension that is
> loaded unpacked and cannot read an environment.

## `_js`, [line 48](../../../../backend/scripts/write_deployment.py#L48): Docstring

> A JS string literal. `json.dumps` would do, and this says why it is safe:
> the value is a url that has already been checked for its scheme.
