# Notes for `backend/src/sro/application/chat/reading_an_answer.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/reading_an_answer.py`](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L1): Docstring

> Ask the model whether a sentence answers the question standing in the thread.
>
> One question, the words that were actually said, and no jobs to choose between:
> which job this is about was settled when the question was asked, and handing a
> reading a decision that is already made is how a settled question gets
> re-opened by two words.
>
> Refuses by saying "this is an answer", never by silence. A deployment with no
> model, a day's cap spent, a door that raised -- all of them mean this system
> behaves exactly as it did before this existed, which is a question that takes
> the next sentence. That is the wrong default and it is the SAFE one to fall
> back to: the alternative is a panel that silently stops accepting answers the
> moment a model is unreachable.

## `Read`, [line 21](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L21): Docstring

> What the sentence turned out to be.

## `Read`, [line 25](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L25): Note on the line above

Code: `about: str = ""`

> What it was instead, where it was not an answer: `the_wait`,
> `another_task`, or `something_else`. Empty where nothing read it.

## `IsItAnAnswer`, [line 30](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L30): Docstring

> Whether to take this sentence as the value the conversation asked for.

## `IsItAnAnswer.execute`, [line 35](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L35): Docstring

> Read it, or say it plainly is one without spending anything.

## `IsItAnAnswer.execute`, [line 58](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L58): Comment

Code: `value = str(data.get("value") or "").strip() or said.strip()`

> The value the reading pulled out, and the whole sentence where it
> named none. A reading that says "this answers" and then hands back
> nothing has not read anything, and the sentence is what was said.

## `IsItAnAnswer.execute`, [line 63](../../../../../../../backend/src/sro/application/chat/reading_an_answer.py#L63): Comment

Code: `about=str(data.get("about") or "") or "the_wait",`

> `the_wait` where the reading named nothing: a person who is
> waiting is usually asking about the waiting, and being answered
> about the wait costs a sentence where being sent to the task
> resolver costs a wall of text about a screen nobody mentioned.
