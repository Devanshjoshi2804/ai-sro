# Notes for `backend/src/sro/domain/chat/reading.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/reading.py`](../../../../../../../backend/src/sro/domain/chat/reading.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/reading.py#L1): Docstring

> What the chat door's reading cost.
>
> The words and the response schema are the `READ_REQUEST` record, in
> ``sro.domain.prompts.read_request``, where
> ``tests/unit/domain/rig/test_planning.py::test_no_schema_in_the_package_uses_what_the_developer_api_refuses``
> walks every record's schema. The half that asks is
> ``sro.application.chat.understand``.

## `new_chat_id`, [line 7](../../../../../../../backend/src/sro/domain/chat/reading.py#L7): Docstring

> The shape every other id in the backend has. The rig minted this inside
> its ``/v1/chat`` route; here the reading is a record before it is a row.

## `ChatReading`, [line 12](../../../../../../../backend/src/sro/domain/chat/reading.py#L12): Docstring

> One sentence the chat door read, and what the reading cost.
>
> The sentence is not kept: it is an operator's words about a warehouse,
> and the bill is what this record is for.
