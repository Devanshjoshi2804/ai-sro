# Notes for `backend/src/sro/application/runtime/fill_field.py`

Comments and docstrings for [`backend/src/sro/application/runtime/fill_field.py`](../../../../../../../backend/src/sro/application/runtime/fill_field.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the text, which says what the code does and why.

## `FillField.fill`, [line 36](../../../../../../../backend/src/sro/application/runtime/fill_field.py#L36): Docstring

> Fills a composed field on the live page by its label, inside the write's
> recorded frame and landmarks, as a non-write (`write: False`; `type`/`select`
> are never repaired by the page code, `REPAIRABLE_ACTIONS`). It never acts on a
> resolve that is not exactly one control: none is `no_field`, more than one is
> `ambiguous`. A frame that cannot be chosen (`frame_ambiguous`,
> `frame_not_found`) is a plain failure, not a question: no label the operator
> picks can resolve a frame (X10a review M3). For a select with listed options,
> the operator's value is resolved once to the outline's exact option label --
> the option it names exactly, else the one it names ignoring case -- and the
> act and the check use that label (the page matches options exactly); no
> match asks `no_option`, two matches ignoring case ask `ambiguous`, both with
> the options. An answer to that question is one exact option, so it lands. The check never carries the learned locator: `holds` re-finds
> the labelled control, the way X7's element check requires (M1). A refused act or
> a value that does not hold goes to sight, whose result counts only when `done`.
> A missing or ambiguous label never goes to sight (spec §6.6 step 5). After a
> fill, the control's held value is read back through `resolve` (`Filled.held`):
> that, not the operator's words, is what the save's new key must carry. `detail`
> is a fixed text: the page's own error ("no option <value>") would carry the
> operator's value into stored reasons (M5). A fill never confirms the field: the
> write's own call does (`keyed`).
>
> `ponytail:` the learned `role_and_name` locator is document-wide -- `byLearned`
> ignores the form's landmarks -- while the check that taught it was scoped to the
> form. Ceiling: a second control with the same role and label outside the form
> (a list filter) makes every later run `ambiguous`. Upgrade path: learn the
> locator with the write's landmarks and scope `byLearned` to them.
