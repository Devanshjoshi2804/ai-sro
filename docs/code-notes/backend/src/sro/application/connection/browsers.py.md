# Notes for `backend/src/sro/application/connection/browsers.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/browsers.py`](../../../../../../../backend/src/sro/application/connection/browsers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/browsers.py#L1): Docstring

> Every browser this system opens, finds or hands back, and whose it is.
>
> The provider has no tenants and must not learn about any -- Steel hands out an
> id and knows nothing else about it. Ownership is a fact *this* system records
> about that id, so it lives on this side of the port, in a table both processes
> read: the API and the Temporal worker each build their own container, and both
> open and close browsers.
>
> Before this existed, a session id was a bare string. Six paths took one from a
> URL, from the provider's list of live sessions, or from a query parameter, and
> drove it or emptied its cookies into the caller's vault -- none of them able to
> tell one customer's browser from another's.
>
> Borrowing survives, because it was always the right behaviour on a provider with
> one browser: asking for a second does not produce one. What changed is the set
> it borrows from -- this tenant's browsers rather than the deployment's.

## `Browsers.open`, [line 24](../../../../../../../backend/src/sro/application/connection/browsers.py#L24): Docstring

> A new browser, claimed for this tenant before it is handed over.
>
> When the provider has none to give, one this tenant already holds and
> nobody is demonstrating in. Raises ``BrowserUnavailable`` if neither.

## `Browsers.take`, [line 28](../../../../../../../backend/src/sro/application/connection/browsers.py#L28): Docstring

> The browser, and whether it was borrowed rather than opened.
>
> Callers that close what they took need the second half: a borrowed
> browser belongs to whoever signed into it, and closing it logs a
> warehouse operator out mid-shift. It is also already signed in, so
> restoring stored cookies over the top of it is at best redundant.

## `Browsers.attach`, [line 42](../../../../../../../backend/src/sro/application/connection/browsers.py#L42): Docstring

> A browser the operator already has open, owned like any other.
>
> The id is ours rather than the provider's -- it never issued one. It was
> a single shared constant before, so every attached recording of every
> tenant collided on it. Releasing it is a no-op at the provider, which is
> correct: closing somebody's own Chrome was never ours to do.

## `Browsers.mine`, [line 47](../../../../../../../backend/src/sro/application/connection/browsers.py#L47): Docstring

> This tenant's browsers that are still live.
>
> The intersection is the point. A claim on a session the provider has
> forgotten is not a browser, and a live session this tenant never claimed
> is not theirs to look at.

## `Browsers.session`, [line 60](../../../../../../../backend/src/sro/application/connection/browsers.py#L60): Docstring

> This tenant's browser, by id.
>
> ``NotFound`` when it is not theirs, deliberately the same answer as an id
> that never existed: every other resource here 404s across tenants, and
> this must not become the one that says which ids are real.

## `Browsers.release`, [line 66](../../../../../../../backend/src/sro/application/connection/browsers.py#L66): Docstring

> Close it and drop the claim. Both idempotent, and not tenant-scoped:
> the stray sweep and crash recovery are nobody's request.

## `Browsers._spare`, [line 81](../../../../../../../backend/src/sro/application/connection/browsers.py#L81): Docstring

> One of this tenant's browsers that nobody is demonstrating in.
>
> Never one a recording is capturing: two things driving one screen record
> each other's gestures, and the demonstration is the evidence everything
> else is built from.

## `Browsers._live`, [line 94](../../../../../../../backend/src/sro/application/connection/browsers.py#L94): Comment

Code: `return ()`

> A provider that cannot be asked is not a provider holding a browser
> of yours. Nothing is released and nothing is offered.
