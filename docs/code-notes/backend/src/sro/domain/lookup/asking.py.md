# Notes for `backend/src/sro/domain/lookup/asking.py`

Comments and docstrings moved out of [`backend/src/sro/domain/lookup/asking.py`](../../../../../../../backend/src/sro/domain/lookup/asking.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/lookup/asking.py#L1): Docstring

> Whether a sentence is asking for something to be DONE or to be FOUND OUT.
>
> One box, two worlds behind it. `read_chat` resolves a sentence against the
> jobs an operator was seen doing; `plan_lookups` resolves one against what the
> systems know. Sending a question to the first produces "no job matched" and
> sending an instruction to the second produces a plan to read a page nobody
> asked about, so something has to decide, and the deciding is here rather than
> in the extension for the reason every rule in this codebase lives on one side
> of the wire: `shape_of` served a shape `recognise.js` could never match for
> weeks because each side was only ever read against itself.
>
> **No model.** A model call to decide which model call to make doubles the
> latency of every sentence somebody types to answer a question whose evidence
> is the first word. This is a word rule, it is wrong sometimes, and the cost of
> being wrong is bounded in both directions: a question read as a job is
> answered "no job matched" and a job read as a question comes back with a plan
> and no press. Neither writes anything.
>
> **A job verb wins over a question mark.** "Can you add demo values?" is an
> instruction with a polite shape, and reading it as a question is the failure
> that matters: the operator waits for something to happen and nothing does.
>
> **What is left over is a job.** Not because most sentences are jobs, but
> because a lookup drives the browser on its own -- it opens tabs and reads
> pages -- and a job stops at an offer somebody has to press. When the rule
> cannot tell, the path that waits for a person is the one to take.

## module, [line 3](../../../../../../../backend/src/sro/domain/lookup/asking.py#L3): Note on the line above

Code: `DOING = frozenset(`

> Verbs that ask for the world to change. First word only: "update" in "which
> suppliers were updated today" is a tense, not an instruction, and a rule
> reading it anywhere would send every question about changed records to the
> miner.

## module, [line 34](../../../../../../../backend/src/sro/domain/lookup/asking.py#L34): Note on the line above

Code: `ASKING = frozenset(`

> First words that open a question.

## module, [line 58](../../../../../../../backend/src/sro/domain/lookup/asking.py#L58): Note on the line above

Code: `LOOKING = frozenset(`

> First words that ask to be told something. `get` and `fetch` sit here
> rather than in `DOING` on purpose: they are the words an operator uses for a
> read, and the HTTP verb they share a name with is the read one.

## `is_a_question`, [line 75](../../../../../../../backend/src/sro/domain/lookup/asking.py#L75): Docstring

> Whether this sentence wants an answer rather than an action.

## `is_a_question`, [line 84](../../../../../../../backend/src/sro/domain/lookup/asking.py#L84): Comment

Code: `if first in ("please", "could", "would", "can", "pls", "plz", "hey", "ok") and len(words) `

> "please check the supplier list", "could you find out how many" -- the
> courtesy is not the sentence, so it is stepped over before the rule runs.
