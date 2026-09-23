# Notes for `backend/src/sro/domain/skill/template.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/template.py`](../../../../../../../backend/src/sro/domain/skill/template.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/template.py#L1): Docstring

> Strings with ``$name`` placeholders. See docs/07-adr/004-diff-parameterisation.md.

## `Template.render`, [line 19](../../../../../../../backend/src/sro/domain/skill/template.py#L19): Docstring

> Substitute values. Raises ``KeyError`` on a missing one.

## `Template`, [line 9](../../../../../../../backend/src/sro/domain/skill/template.py#L9): Comment

Code: `raw: str`

> `$name` rather than `{name}` because recorded payloads are JSON: a
> brace syntax needs every captured body escaped, and one missed escape
> turns a literal into a phantom parameter.
