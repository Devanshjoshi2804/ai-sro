# Notes for `backend/src/sro/domain/observation/seen.py`

Explanations for [`backend/src/sro/domain/observation/seen.py`](../../../../../../../backend/src/sro/domain/observation/seen.py), which carries none (Global Constraint 2).

## `place_kept`, [line 92](../../../../../../../backend/src/sro/domain/observation/seen.py#L92): Function

> Every new text field goes through `said_text` and is dropped, never
> truncated, when it fails: a token cut in half is still a token. Routes go
> through `path_shape` because ids in a route are record ids.

## `effect_kept`, [line 107](../../../../../../../backend/src/sro/domain/observation/seen.py#L107): Function

> Roles, field changes and endings are closed sets; anything else is
> dropped. A toast or dialog that repeats a typed value or a token fails
> `said_text` and its item is dropped whole. Error text has URLs replaced
> by `«url»` first. Timings are capped at a minute. Nothing here ever
> carries a field's value.

## `cookies_kept`, [line 156](../../../../../../../backend/src/sro/domain/observation/seen.py#L156): Function

> A cookie is its name and expiry, matched by name shape and never by value
> (the value never reaches the server). A name that looks like a token (a
> JWT used as a name) is dropped.

## `mail_thread_kept`, [line 182](../../../../../../../backend/src/sro/domain/observation/seen.py#L182): Function

> Only id characters are accepted: anything else (spaces, colons) is mail
> text, and mail text is never kept.

## `place_from`, [line 210](../../../../../../../backend/src/sro/domain/observation/seen.py#L210): Function

> The `*_from` functions build the domain shape from `*_kept`: one
> sanitising path for the wire, the store and live page reads.
