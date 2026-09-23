# Notes for `backend/src/sro/cli/observe.py`

Comments and docstrings moved out of [`backend/src/sro/cli/observe.py`](../../../../../../backend/src/sro/cli/observe.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../backend/src/sro/cli/observe.py#L1): Docstring

> Switch passive observation on or off for one tenant. Shell access only.
>
> Not an endpoint, and the reason is the same one that keeps ``mint`` here: there
> is no role model, so every credential for a tenant can do everything that tenant
> can do. A route that enabled observation would let any operator consent on their
> colleagues' behalf, and ADR 008 makes this a contract conversation.
>
>     python -m sro.cli.observe acme --on --exclude payroll.acme.com --keep-days 30
>     python -m sro.cli.observe acme --off
>     python -m sro.cli.observe acme            # just read it back

## `_run`, [line 49](../../../../../../backend/src/sro/cli/observe.py#L49): Comment

Code: `principal_id=PrincipalId("shell"),`

> The shell is the authority here; the name is for the record, not a check.

## `_run`, [line 57](../../../../../../backend/src/sro/cli/observe.py#L57): Comment

Code: `print(`

> Said every time, because the deny-list is the shape that fails
> quietly: it protects the hosts somebody thought of, and a browser has
> every host in it. Naming the systems is a minute's work and it is the
> difference between observing a warehouse and observing a person.
