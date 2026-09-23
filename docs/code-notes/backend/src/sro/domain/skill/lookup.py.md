# Notes for `backend/src/sro/domain/skill/lookup.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/lookup.py`](../../../../../../../backend/src/sro/domain/skill/lookup.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/lookup.py#L1): Docstring

> Where the values of a field come from, when the screen offered a list.
>
> A demonstration writes to `/wm/addresses/A000144886`. Replayed literally, every
> run writes to that one address. Turned into a parameter, an operator is asked
> for an id nobody has ever memorised -- which is the same failure with a politer
> face, because the answer they would have to look up is on the screen the
> demonstration already read.
>
> The screen is the answer. That address was a dropdown, and the dropdown was
> filled by a call this recording captured -- session, site parameters, filter
> dialect and all. So the field stays a dropdown: the console asks the system
> what the options are, the operator picks one the way they did when they taught
> it, and the id nobody remembers travels with the pick.
>
> Which call, which fields to show and which field the create actually needs are
> all read off the demonstration. Nothing is inferred at run time.

## `Options`, [line 10](../../../../../../../backend/src/sro/domain/skill/lookup.py#L10): Docstring

> Where the values of a parameter come from, live.
>
> The field the operator is filling in was a dropdown on the screen, and that
> dropdown was filled by a call. Asking somebody to type the address line, or
> the id behind it, is asking them to reproduce from memory what the form
> would have handed them -- and the call that fills it is in the recording,
> with its session, its site parameters and its filter dialect.
>
> So a parameter carries where its options come from, the console asks for
> them when it draws the field, and what the operator picks is the record's
> own id. The mandatory fields of a create stop being things to remember and
> go back to being things to choose.

## `Options`, [line 11](../../../../../../../backend/src/sro/domain/skill/lookup.py#L11): Note on the line above

Code: `url: str`

> The listing call, as the demonstration made it. ``${query}`` where the
> operator's own search terms went, if the endpoint took any.

## `Options`, [line 13](../../../../../../../backend/src/sro/domain/skill/lookup.py#L13): Note on the line above

Code: `label: tuple[str, ...]`

> Fields to show, in order. An address is `APPLIANCE HAUS -- 10880 BAYVIEW
> AVENUE`, because one field alone was not enough to tell four of them apart.

## `Options`, [line 15](../../../../../../../backend/src/sro/domain/skill/lookup.py#L15): Note on the line above

Code: `value: str`

> The field the call underneath actually needs: `addressId`.

## `Options`, [line 17](../../../../../../../backend/src/sro/domain/skill/lookup.py#L17): Note on the line above

Code: `search: str | None = None`

> The field the endpoint filters on, where it filters at all. Without one
> the whole page is fetched and narrowed here.

## `Options`, [line 19](../../../../../../../backend/src/sro/domain/skill/lookup.py#L19): Note on the line above

Code: `headers: tuple[HeaderPlan, ...] = ()`

> What the demonstration sent with it -- the session cookie, the site, the
> anti-forgery token -- resolved the same way every other call in the skill
> resolves them. Without these the collection answers with a login page, and
> a dropdown that is silently empty is worse than one that fails.
