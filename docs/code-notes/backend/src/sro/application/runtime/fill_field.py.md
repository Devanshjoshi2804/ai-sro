# Notes for `backend/src/sro/application/runtime/fill_field.py`

Comments and docstrings for [`backend/src/sro/application/runtime/fill_field.py`](../../../../../../../backend/src/sro/application/runtime/fill_field.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the text, which says what the code does and why.

## `FillField.fill`, [line 35](../../../../../../../backend/src/sro/application/runtime/fill_field.py#L35): Docstring

> Fills a composed field on the live page by its label, inside the write's
> recorded frame and landmarks, as a non-write (`write: False`). It never acts on
> a resolve that is not exactly one control: none, or a repair (a repair is a
> scored guess at SOME control, and the label is this field's only identity), is
> `no_field`; more than one, or more than one frame holding it, is `ambiguous`.
> For a select, a live outline that lists options without the value asks
> `no_option` with those options. The value must then hold on the pinned control.
> A refused act or a value that does not hold goes to sight, whose result counts
> only when `done`: `unknown` from sight is the model's word alone. A missing or
> ambiguous label never goes to sight (spec §6.6 step 5). A fill never confirms
> the field: the write's own call does (`keyed`).

