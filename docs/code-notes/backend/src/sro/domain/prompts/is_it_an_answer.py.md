# Notes for `backend/src/sro/domain/prompts/is_it_an_answer.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/is_it_an_answer.py`](../../../../../../../backend/src/sro/domain/prompts/is_it_an_answer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 50](../../../../../../../backend/src/sro/domain/prompts/is_it_an_answer.py#L50): Comment

Code: `"required": ["answers", "value", "why", "about"],`

> No `additionalProperties`: the developer API refuses a schema carrying
> it, and `test_no_schema_in_the_package_uses_what_the_developer_api_refuses`
> walks every `*_SCHEMA` in the package to keep it that way.
