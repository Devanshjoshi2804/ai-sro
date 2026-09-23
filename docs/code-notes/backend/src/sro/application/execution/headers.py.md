# Notes for `backend/src/sro/application/execution/headers.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/headers.py`](../../../../../../../backend/src/sro/application/execution/headers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/headers.py#L1): Docstring

> Turn a header plan back into headers that can be sent.
>
> The plan says where each value comes from; this resolves those sources. A header
> whose source cannot be resolved stops the step -- sending the call without it
> would produce a 401 or, worse, a call that succeeds as somebody else.

## `ResolvedHeaders`, [line 18](../../../../../../../backend/src/sro/application/execution/headers.py#L18): Note on the line above

Code: `missing: tuple[str, ...]`

> Names whose value could not be produced. Non-empty means: do not send.

## `resolve_headers`, [line 21](../../../../../../../backend/src/sro/application/execution/headers.py#L21): Docstring

> ``scope`` is the tenant whose session is used, prefixed onto every key.
>
> A skill's credential reference names a system and a site -- `blue_yonder/SG/
> cookie` -- and deliberately not a tenant, because the same skill is meant to
> be usable by whoever owns a login to that system. The tenant is supplied
> here, at the moment of resolution, so a run can only ever reach its own.
> ``session_scope`` is where minted headers live: `<system>/<facility>`.
>
> "Minted" is aspirational for headers whose algorithm is the target system's
> secret. Blue Yonder's `CSRF-ENCRYPT-TOKEN` is issued at login and cannot be
> computed here, so what the executor does is fetch the live one belonging to
> the connected session. That is the same trust boundary as the cookie, and it
> keeps the value out of the skill.

## `client_headers`, [line 78](../../../../../../../backend/src/sro/application/execution/headers.py#L78): Docstring

> Client-managed headers, set for *this* request rather than replayed.
>
> `Referer` and `Origin` are recorded as client-managed because the captured
> values describe the page a demonstration happened on, and replaying those is
> misleading. Omitting them altogether turned out to be worse: Blue Yonder's
> auth filter answers a same-origin API call with no `Referer` by redirecting
> to the login page, so every replayed read came back 302 with a live session
> in hand. A browser would have sent one; the executor sends the one that is
> true of the call it is actually making.

## `_put`, [line 93](../../../../../../../backend/src/sro/application/execution/headers.py#L93): Docstring

> Last spelling wins, case-insensitively.
>
> A capture holds both `Content-Type` and `content-type` because CDP reports
> the request twice over; sending both is at best redundant and at worst two
> conflicting values of one header.

## `resolve_headers`, [line 34](../../../../../../../backend/src/sro/application/execution/headers.py#L34): Comment

Code: `if bearer:`

> A credential built to be held, where one exists. The cookies below are a
> human's browser session: they work, and they expire on the identity
> provider's schedule rather than on anything this system controls. An
> offline token outlives the session that created it, so where there is one
> it is what authenticates the call.

## `resolve_headers`, [line 39](../../../../../../../backend/src/sro/application/execution/headers.py#L39): Comment

Code: `live = await vault.get(f"{scope}/{session_scope}/referer")`

> The page the application makes its calls from, when the session
> recorded one. Blue Yonder's filter reads a per-session
> `libraryContext` out of the Referer and redirects to the login
> page without it -- so the executor sent a live cookie, a live
> token, and still got a 302, which is indistinguishable from being
> signed out. The origin remains the fallback.

## `resolve_headers`, [line 42](../../../../../../../backend/src/sro/application/execution/headers.py#L42): Inline

Code: `continue`

> the HTTP client owns these

## `resolve_headers`, [line 45](../../../../../../../backend/src/sro/application/execution/headers.py#L45): Comment

Code: `continue`

> This call goes out of a page the operator is signed in to, and
> `Cookie` is a forbidden header name for `fetch`: the browser
> drops whatever we set and sends the tab's own. Proved in
> Chrome -- `test_a_session_the_backend_supplies_is_not_what_
> goes_out`. So resolving it is a value that reaches nothing,
> and *requiring* it refuses the one case naming a device exists
> for: a system this deployment holds no credentials for.

## `resolve_headers`, [line 49](../../../../../../../backend/src/sro/application/execution/headers.py#L49): Comment

Code: `continue`

> Both would be sent otherwise, and a stale session cookie
> beside a good token is how a call gets refused for the reason
> that was just fixed.

## `resolve_headers`, [line 52](../../../../../../../backend/src/sro/application/execution/headers.py#L52): Comment

Code: `ref = plan.credential_ref`

> Induction writes one system into every step's reference, because
> a skill had one. A workflow does not, and the reference on its
> second half names the first half's system: resolving it verbatim
> posts the WMS's cookie to the ERP. The calling system, which
> `session_scope` carries, decides -- and no fall back to the
> reference, which would leak the same value by the other door.

## `resolve_headers`, [line 57](../../../../../../../backend/src/sro/application/execution/headers.py#L57): Comment

Code: `secret = await vault.get(f"{scope}/{_system_of(ref)}/cookie")`

> A skill names `<system>/<site>/cookie`; a login is to a
> system. Falling back keeps a skill taught at one site usable
> at another the same connection reaches.
