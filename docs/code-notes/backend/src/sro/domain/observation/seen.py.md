# Notes for `backend/src/sro/domain/observation/seen.py`

Explanations for [`backend/src/sro/domain/observation/seen.py`](../../../../../../../backend/src/sro/domain/observation/seen.py), which carries none (Global Constraint 2).

## `place_kept`, [line 103](../../../../../../../backend/src/sro/domain/observation/seen.py#L103): Function

> Every new text field goes through `said_text` and is dropped, never
> truncated, when it fails: a token cut in half is still a token. Routes go
> through `path_shape` because ids in a route are record ids, then through
> `said_text`; the route is percent-decoded (up to three times, from at most 1000
> characters) first, and a hash fragment with `=` in it is an OAuth return and
> drops the route.

## `effect_kept`, [line 118](../../../../../../../backend/src/sro/domain/observation/seen.py#L118): Function

> Roles, field changes and endings are closed sets; anything else is
> dropped. A toast or dialog that repeats a typed value or a token fails
> `said_text` and its item is dropped whole. Error text has URLs replaced
> by `«url»` first. Timings are capped at a minute. Nothing here ever
> carries a field's value.

## `cookies_kept`, [line 167](../../../../../../../backend/src/sro/domain/observation/seen.py#L167): Function

> A cookie is its name and expiry, matched by name shape and never by value
> (the value never reaches the server). A name that fails `said_text`, a
> domain that is not a plain hostname, and an expiry that is not a number
> between 0 and 2100 (compared, never converted, so a 10**400 cannot raise) are dropped.

## `mail_thread_kept`, [line 200](../../../../../../../backend/src/sro/domain/observation/seen.py#L200): Function

> Only an id is kept: 16 or more of letters, digits, `_` and `-`, and nothing
> `redact_shapes` would change. Anything else is mail text, never kept.

## `place_from`, [line 233](../../../../../../../backend/src/sro/domain/observation/seen.py#L233): Function

> The `*_from` functions build the domain shape from `*_kept`: one
> sanitising path for the wire, the store and live page reads.
