# Notes for `backend/src/sro/application/induction/jsonutil.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/jsonutil.py`](../../../../../../../backend/src/sro/application/induction/jsonutil.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L1): Docstring

> Minimal JSON Pointer (RFC 6901) support.
>
> Three operations are all this codebase needs, so it is a few lines rather than a
> dependency. Reach for ``jsonpointer`` if that stops being true.

## `leaves`, [line 30](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L30): Docstring

> Yield ``(pointer, scalar)`` depth first. Containers are not yielded --
> "the object changed" is never actionable on its own.

## `as_text`, [line 41](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L41): Docstring

> One rendering of a JSON scalar, used by whoever writes an expectation and
> by whoever checks it.
>
> Python's ``str`` renders JSON ``true`` as ``"True"``. Induction wrote that
> into an assertion and the executor read the live response back as ``"true"``,
> so a run that did exactly the right thing reported a mismatch against
> itself. The rendering has to be the same rule on both sides, so it is one
> function.

## `set_value`, [line 56](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L56): Docstring

> Mutate in place. Caller owns the copy.

## `is_empty`, [line 70](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L70): Docstring

> Whether this leaf is a field somebody left alone.
>
> A form sends its whole record: what the operator skipped arrives as `null`,
> or as `""` from a text control that was never focused. Both are absence
> wearing the type the application chose for it.

## `same_shape`, [line 74](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L74): Docstring

> Whether two bodies are the same request with different values in it.
>
> Stricter than it looks. Every key must be in both -- a key one run did not
> send is a different request, and the pair is refused. What is allowed is a
> leaf that is empty on one side: the same field, filled once and skipped
> once, which is the ordinary way two people fill one form.

## `same_shape`, [line 80](../../../../../../../backend/src/sro/application/induction/jsonutil.py#L80): Comment

Code: `return is_empty(a) or is_empty(b)`

> A group emptied on one side is still one request with a different
> value in it, so it is the same shape. Whether the *diff* can express
> it is a separate question, answered no: `_diff_body` refuses the pair
> rather than handing the group's absent form to each leaf inside it.
> `is_empty` of a dict or list is always False, so this only fires when
> the *other* side is the one left empty.
