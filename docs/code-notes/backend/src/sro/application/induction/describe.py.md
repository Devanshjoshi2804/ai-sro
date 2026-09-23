# Notes for `backend/src/sro/application/induction/describe.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/describe.py`](../../../../../../../backend/src/sro/application/induction/describe.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/describe.py#L1): Docstring

> What a skill does, in a sentence, and when to reach for it.
>
> Composed from the evidence rather than written by a model: the objective, the
> call the skill writes with, the parameters the diff found, and — where the
> operator narrated — their own closing sentence, quoted rather than paraphrased.
>
> These two fields are not decoration. They are what an operator's sentence is
> matched against when they ask for work later, so a skill nobody can find is a
> skill that does not exist.

## `_write`, [line 53](../../../../../../../backend/src/sro/application/induction/describe.py#L53): Docstring

> Every mutating call the skill makes, named by method and path.
>
> All of them, because one Save can create a record and address it, and a
> summary naming only the first tells a reviewer the skill does half of what
> it does.

## `_closing_words`, [line 62](../../../../../../../backend/src/sro/application/induction/describe.py#L62): Docstring

> What the operator said last. It is usually what the task was for.

## `compose`, [line 34](../../../../../../../backend/src/sro/application/induction/describe.py#L34): Comment

Code: `summary += f' In the demonstrator\'s words: "{spoken}"'`

> The operator's own words outrank ours: they describe the task as the
> warehouse describes it, which is the vocabulary a request will use.

## `compose`, [line 38](../../../../../../../backend/src/sro/application/induction/describe.py#L38): Comment

Code: `when += (`

> The words people actually use to ask a read for something. Retrieval
> matches an operator's sentence against this text, and a description
> that never says "how many" loses to one that does -- which is how
> regenerating these descriptions made "how many addresses are there"
> start hedging at a skill that answers exactly that.
