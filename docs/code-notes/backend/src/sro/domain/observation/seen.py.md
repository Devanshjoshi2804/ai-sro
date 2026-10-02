# Notes for `backend/src/sro/domain/observation/seen.py`

Explanations for [`backend/src/sro/domain/observation/seen.py`](../../../../../../../backend/src/sro/domain/observation/seen.py), which carries none (Global Constraint 2).

## `place_kept`, [line 108](../../../../../../../backend/src/sro/domain/observation/seen.py#L108): Function

> Every new text field goes through `said_text` and is dropped, never
> truncated, when it fails: a token cut in half is still a token. Routes go
> through `path_shape` because ids in a route are record ids, then through
> `said_text`; the route is percent-decoded (until it stops changing, at most 8 rounds, else the route is dropped; from at most 1000
> characters) first, and a hash fragment with `=` in it is an OAuth return and
> drops the route.

## `effect_kept`, [line 123](../../../../../../../backend/src/sro/domain/observation/seen.py#L123): Function

> Roles, field changes and endings are closed sets; anything else is
> dropped. A toast or dialog that repeats a typed value or a token fails
> `said_text` and its item is dropped whole. Error text is capped, then has URLs replaced
> by `«url»`. Timings are capped at a minute. Nothing here ever
> carries a field's value.

## `cookies_kept`, [line 172](../../../../../../../backend/src/sro/domain/observation/seen.py#L172): Function

> A cookie is its name and expiry, matched by name shape and never by value
> (the value never reaches the server). A name that fails `said_text`, a
> domain that is not a plain hostname, and an expiry that is not a number
> between 0 and 2100 (compared, never converted, so a 10**400 cannot raise) are dropped.

## `mail_thread_kept`, [line 205](../../../../../../../backend/src/sro/domain/observation/seen.py#L205): Function

> Only an id is kept: 16 or more of letters, digits, `_` and `-`, and nothing
> `redact_shapes` would change. Anything else is mail text, never kept.

## `place_from`, [line 238](../../../../../../../backend/src/sro/domain/observation/seen.py#L238): Function

> The `*_from` functions build the domain shape from `*_kept`: one
> sanitising path for the wire, the store and live page reads.
