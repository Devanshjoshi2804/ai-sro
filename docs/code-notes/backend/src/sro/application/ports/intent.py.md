# Notes for `backend/src/sro/application/ports/intent.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/intent.py`](../../../../../../../backend/src/sro/application/ports/intent.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/intent.py#L1): Docstring

> Turning a sentence into parameter values.
>
> The model's whole job here is extraction: the skill is already chosen, its
> parameters are already declared, and what remains is reading the values out of
> what the operator wrote. It is never asked which skill to run, and it is never
> allowed to invent a parameter -- both of those are decided against the library
> before this is called.
>
> "Update these six SKUs to the counts from this morning" is six parameter sets.
> Getting that wrong is not a wrong answer, it is six wrong writes, so nothing it
> returns is used without an operator confirming the table it produced.

## `Extraction`, [line 9](../../../../../../../backend/src/sro/application/ports/intent.py#L9): Note on the line above

Code: `items: tuple[dict[str, str], ...] = ()`

> One parameter set per thing to do. Empty means the sentence named no
> values, which is a question back to the operator rather than a run.

## `Extraction`, [line 11](../../../../../../../backend/src/sro/application/ports/intent.py#L11): Note on the line above

Code: `missing: tuple[str, ...] = ()`

> Declared inputs the sentence did not supply.

## `Extraction`, [line 13](../../../../../../../backend/src/sro/application/ports/intent.py#L13): Note on the line above

Code: `note: str = ""`

> What the model could not resolve -- "this morning's count" needs a
> source it was not given.

## `Reading`, [line 17](../../../../../../../backend/src/sro/application/ports/intent.py#L17): Docstring

> What a sentence means, before anything is matched against it.
>
> Reading English is what a model is for. Deciding what runs is not: the
> reading is proposed here and validated against the library that actually
> exists, exactly as a proposed gesture is executed against real locators.
> A reading that names a task nobody taught changes nothing.
>
> Everything this replaces was a list of phrases -- "how many", "which",
> "list all" -- and every such list is a guess about wording that the next
> sentence breaks. "Show the list of all transport_mode then" broke one.

## `Reading`, [line 18](../../../../../../../backend/src/sro/application/ports/intent.py#L18): Note on the line above

Code: `wants: str = "act"`

> `ask` when the operator wants to be told something, `act` when they want
> something done. The difference decides whether a skill that writes may
> answer at all.

## `Reading`, [line 20](../../../../../../../backend/src/sro/application/ports/intent.py#L20): Note on the line above

Code: `verb: str = ""`

> What they want done, in their words -- list, create, adjust, release.

## `Reading`, [line 22](../../../../../../../backend/src/sro/application/ports/intent.py#L22): Note on the line above

Code: `entity: str = ""`

> What they want it done to.

## `Reading`, [line 24](../../../../../../../backend/src/sro/application/ports/intent.py#L24): Note on the line above

Code: `continues: bool = False`

> Whether this sentence leans on the one before it for its subject, rather
> than naming one. "I want them in detail" continues; "show the list of all
> transport modes" does not, however conversational it sounds.

## `IntentParser.extract`, [line 33](../../../../../../../backend/src/sro/application/ports/intent.py#L33): Docstring

> Values for ``parameters``, as many sets as the sentence describes.

## `IntentParser.read`, [line 37](../../../../../../../backend/src/sro/application/ports/intent.py#L37): Docstring

> What the sentence means, given the one before it.
>
> Never what to run. The caller matches the reading against the skills
> that exist and refuses anything it cannot account for, so a confident
> misreading costs a clarifying question rather than a wrong write.
