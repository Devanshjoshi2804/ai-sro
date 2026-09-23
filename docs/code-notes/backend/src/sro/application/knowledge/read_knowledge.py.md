# Notes for `backend/src/sro/application/knowledge/read_knowledge.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/read_knowledge.py`](../../../../../../../backend/src/sro/application/knowledge/read_knowledge.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/read_knowledge.py#L1): Docstring

> What the organisation knows, and how it got there.
>
> Teaching is not a conversation. One person demonstrates a task and the whole
> tenant has it: skills, knowledge and threads are tenant-scoped, so the next
> operator to ask finds what a colleague taught last week without knowing they
> taught it.
>
> That only counts for something if it can be seen. This is the read side: what
> is known about a system, how firmly, where each claim came from, and which
> claims the organisation's own runs have proven since.

## `TaughtSkill`, [line 22](../../../../../../../backend/src/sro/application/knowledge/read_knowledge.py#L22): Note on the line above

Code: `proposed_parameters: int`

> Values a single demonstration proposed and no second run has proven. The
> number a reviewer should want to see fall.

## `KnowledgeSummary`, [line 30](../../../../../../../backend/src/sro/application/knowledge/read_knowledge.py#L30): Note on the line above

Code: `learned_from_runs: int`

> Claims this tenant's own runs proved, as opposed to scraped. The number
> that says the system is learning rather than merely loaded.
