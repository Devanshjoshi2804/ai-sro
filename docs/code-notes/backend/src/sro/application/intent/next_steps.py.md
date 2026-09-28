# Notes for `backend/src/sro/application/intent/next_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/next_steps.py`](../../../../../../../backend/src/sro/application/intent/next_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/next_steps.py#L1): Docstring

> What to ask next, worked out rather than written into the console.
>
> The chips under a result used to be three sentences hard-coded in the browser:
> "show me one X in detail", "create a new X", "which X are used for parcel". The
> last one was written for a transport-mode demo and then offered under every
> result in the system, including for entities where nothing can answer it. A
> suggestion the system cannot act on is worse than no suggestion: it advertises
> a capability that does not exist and teaches operators to distrust the ones
> that do.
>
> So a suggestion has to be earned, the same way everything else here is:
>
> - **a taught skill for this entity** can obviously be asked for, by name;
> - **a column in the answer with a handful of values** can be filtered on,
>   because the narrowing path composes exactly that request and the values come
>   from records this system just read;
> - **an identifying column** can be asked about one record at a time.
>
> The model's job is the wording -- turning `smallPackageFlag=Y` into something a
> warehouse says out loud. It cannot add a suggestion, remove one, or change what
> any of them will do: every phrasing is checked against the evidence that
> produced it, and anything that drifts falls back to the plain wording.

## module, [line 12](../../../../../../../backend/src/sro/application/intent/next_steps.py#L12): Note on the line above

Code: `MOST = 3`

> Three. A row of chips is a nudge, not a menu.

## module, [line 15](../../../../../../../backend/src/sro/application/intent/next_steps.py#L15): Note on the line above

Code: `TOO_MANY_TO_FILTER = 8`

> A column worth offering as a filter has a few values, not one and not forty:
> one is not a choice, and forty is a list nobody scans.

## `Suggestion`, [line 21](../../../../../../../backend/src/sro/application/intent/next_steps.py#L21): Note on the line above

Code: `because: str`

> What makes this answerable. Never shown as a caption -- it is here so a
> suggestion cannot exist without evidence behind it.

## `_kept`, [line 118](../../../../../../../backend/src/sro/application/intent/next_steps.py#L118): Docstring

> The model's wording, when it is still the suggestion that was earned.

## `SuggestNext.after`, [line 29](../../../../../../../backend/src/sro/application/intent/next_steps.py#L29): Docstring

> Follow-ups this system can actually answer, best first.

## `SuggestNext._other_skills`, [line 48](../../../../../../../backend/src/sro/application/intent/next_steps.py#L48): Docstring

> Things somebody taught for this entity, other than reading it.

## `SuggestNext._filters`, [line 62](../../../../../../../backend/src/sro/application/intent/next_steps.py#L62): Docstring

> Narrowings the data itself supports.
>
> Every one of these is a request the composing path can build, because
> the column and the value both came out of the answer being suggested
> under.

## `SuggestNext._labels`, [line 79](../../../../../../../backend/src/sro/application/intent/next_steps.py#L79): Docstring

> What the screens call these fields, so a chip reads like the screen.

## `SuggestNext._phrase`, [line 86](../../../../../../../backend/src/sro/application/intent/next_steps.py#L86): Docstring

> The same suggestions, in words a warehouse uses.
>
> Checked, not trusted: a phrasing that drops the value or the entity is
> no longer the suggestion that was earned, and the plain wording is used
> instead. The model never decides what is offered -- only how it reads.

## `SuggestNext._filters`, [line 68](../../../../../../../backend/src/sro/application/intent/next_steps.py#L68): Comment

Code: `continue`

> As many values as records: an identifier, not a category.

## `SuggestNext._filters`, [line 73](../../../../../../../backend/src/sro/application/intent/next_steps.py#L73): Comment

Code: `text=f"which {entity.replace('_', ' ')} records have {column} {held[0]}",`

> "Which supplier records have countryName CAN" rather
> than "which supplier have": grammatical without guessing
> at a plural, and still the operator's own vocabulary.

## `SuggestNext._phrase`, [line 93](../../../../../../../backend/src/sro/application/intent/next_steps.py#L93): Comment

Code: `described = "; ".join(`

> The wording only. The reason each one is answerable is not part of
> what the model sees, because the last version put it in the chip.

## `_kept`, [line 122](../../../../../../../backend/src/sro/application/intent/next_steps.py#L122): Comment

Code: `literals = [`

> Every value in the plain wording has to survive: a chip that drops the
> value it was built from is a different request wearing its face.

## `_kept`, [line 126](../../../../../../../backend/src/sro/application/intent/next_steps.py#L126): Comment

Code: `return earned.text`

> A phrasing carrying its own justification is not a request anybody
> would type.
