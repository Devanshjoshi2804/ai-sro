# Notes for `backend/src/sro/application/induction/assertions.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/assertions.py`](../../../../../../../backend/src/sro/application/induction/assertions.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/assertions.py#L1): Docstring

> Post-conditions extracted from what the demonstration proved.
>
> Fields identical across both runs are stable success markers; fields that
> differed are parameters and asserting on them would pin the skill to one run.

## `extract`, [line 23](../../../../../../../backend/src/sro/application/induction/assertions.py#L23): Docstring

> Derive assertions for one aligned step pair.

## `_element_that_appeared`, [line 89](../../../../../../../backend/src/sro/application/induction/assertions.py#L89): Docstring

> First element that showed up after this step in *both* runs.
>
> Requiring both filters out incidentals -- a spinner, a tooltip, a timestamp.

## `_stable_response_fields`, [line 64](../../../../../../../backend/src/sro/application/induction/assertions.py#L64): Comment

Code: `stable.sort(key=lambda item: 0 if _looks_like_a_success_marker(item[0]) else 1)`

> A stable `status` witnesses success better than a stable `pageSize`.
