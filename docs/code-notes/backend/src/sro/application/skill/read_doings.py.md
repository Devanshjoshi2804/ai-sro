# Notes for `backend/src/sro/application/skill/read_doings.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/read_doings.py`](../../../../../../../backend/src/sro/application/skill/read_doings.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/read_doings.py#L1): Docstring

> What each demonstration put in each field.
>
> A version stores the *two* doings it diffed -- that is what proves a field
> varies -- and reads the rest for one thing only, whether some field was left
> empty. So a screen asked to show ten doings side by side has values for two of
> them and nothing for the other eight.
>
> Nothing is missing, though: the version holds the call it sends as a template
> with ``$name`` in the slots, and every doing holds the call it actually made.
> Laying one over the other reads the value straight back out. That is a
> measurement, not an inference -- the same rule as everywhere else here. Where
> the template does not fit what a doing sent, this says so rather than guessing.

## `Doing`, [line 26](../../../../../../../backend/src/sro/application/skill/read_doings.py#L26): Note on the line above

Code: `diffed: bool`

> Whether this is one of the two the induction actually diffed. The other
> doings are evidence read back here, and a reviewer should be able to tell
> which is which.

## `Doing`, [line 28](../../../../../../../backend/src/sro/application/skill/read_doings.py#L28): Note on the line above

Code: `values: dict[str, str | None]`

> The value this doing put in each parameter it can be read for. ``None``
> means it sent the field holding nothing -- the absent form -- which is the
> evidence behind an optional field. A name missing from the mapping is a
> field this doing does not answer for, and the screen says so.

## `ReadDoings`, [line 31](../../../../../../../backend/src/sro/application/skill/read_doings.py#L31): Docstring

> Every demonstration behind a version, and what each one filled in.

## `values_in`, [line 69](../../../../../../../backend/src/sro/application/skill/read_doings.py#L69): Docstring

> Read this version's parameters out of one doing's traffic.
>
> Matched by call rather than by step number: only the two diffed doings
> have frames the induction aligned, and an older doing may have taken a
> different route to the same writes. Same method, same endpoint shape --
> the rule the diff itself uses to decide two calls are the same call.

## `_unify`, [line 94](../../../../../../../backend/src/sro/application/skill/read_doings.py#L94): Docstring

> The slot values this request holds, or ``None`` if it is not this call.
>
> The URL decides whether it is the same call at all; only then is the body
> read. A template that does not fit the body of a call that is otherwise
> the right one yields the URL's slots and nothing else -- a doing whose
> payload changed shape still tells you which record it acted on.

## `_slots`, [line 106](../../../../../../../backend/src/sro/application/skill/read_doings.py#L106): Docstring

> What each ``$name`` in ``template`` stands over in ``actual``.
>
> A regex built from the template's literals, with a non-greedy group per
> placeholder. Non-greedy because two slots in one JSON body are separated
> by punctuation the template carries verbatim; greedy matching would let
> the first slot swallow the second.
>
> ``None`` when the literals do not fit, which is this function's whole
> value: it is how a doing that sent something else is reported as unread
> rather than as a wrong value.

## `_read`, [line 127](../../../../../../../backend/src/sro/application/skill/read_doings.py#L127): Docstring

> A slot's contents as a person would read them.
>
> ``None`` for the absent forms -- a JSON ``null``, an empty string, an
> emptied slot -- because "this doing left it out" is the fact behind every
> optional field, and rendering it as the four characters ``null`` hides
> exactly the thing a reviewer is looking for.

## `ReadDoings.execute`, [line 46](../../../../../../../backend/src/sro/application/skill/read_doings.py#L46): Comment

Code: `continue`

> Purged by retention. The version still cites it -- a
> skill's provenance is never rewritten to hide a gap --
> so the doing is simply not among the ones that can be
> read back.

## `values_in`, [line 89](../../../../../../../backend/src/sro/application/skill/read_doings.py#L89): Comment

Code: `found.setdefault(name, value)`

> First reading wins: a task that sends the same call twice in
> one doing gets the value from the first, which is the one the
> step was induced from.

## `_slots`, [line 119](../../../../../../../backend/src/sro/application/skill/read_doings.py#L119): Comment

Code: `return {} if template == actual else None`

> A literal call. It identifies itself or it does not; either way it
> carries no values.
