# Notes for `backend/src/sro/domain/skill/workflow.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/workflow.py`](../../../../../../../backend/src/sro/domain/skill/workflow.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/workflow.py#L1): Docstring

> What a proven workflow is, and where it lives.

## module, [line 11](../../../../../../../backend/src/sro/domain/skill/workflow.py#L11): Note on the line above

Code: `K_MIN_VALUE_LENGTH = 3`

> How long a parameter value has to be before a title repeating it is quoting
> it rather than coinciding with it. `DSS` and `DDD` name a customer type and an
> equipment type; a voice code of `2` is a value too, and a title is allowed to
> contain the word "3".

## module, [line 15](../../../../../../../backend/src/sro/domain/skill/workflow.py#L15): Note on the line above

Code: `_DANGLING = frozenset(`

> What a title is left ending on once a value is taken out of it: "Create a
> Carrier Cross Reference for Test Drive LLC" loses the customer and keeps the
> `for`.

## `Step`, [line 32](../../../../../../../backend/src/sro/domain/skill/workflow.py#L32): Note on the line above

Code: `uses: list[int] = field(default_factory=list)`

> The earlier steps whose output this one consumes, by `order`.
>
> CrewAI's `Task.context: list[Task]`, and its argument: a task that names
> the prior tasks it depends on can be READ. One inspectable line answers
> "how does step five get step two's id", where an implicit shared map means
> reading the whole job and guessing.
>
> What an earlier step produced is `RunStep.made` -- what the warehouse
> called the record it created -- and it reaches this step's values under
> `step<order>.<field>`. Namespaced rather than merged flat, because a create
> answering `{"id": ...}` and a job with a parameter called `id` would
> otherwise silently be the same thing.
>
> **Empty on every job mined so far, and honestly so.** Measured on the
> deployment 2026-09-19: thirteen runs have made a record and not one has
> made two, so no mined job has this shape and nothing emits the edge yet.
> It is declared here because composition is what needs it -- a person
> joining two jobs has to say how the second gets the first's output -- and
> the edge is discoverable from evidence rather than guessed when mining
> comes to it: a value typed in step five that equals what step two's
> response returned IS this edge, and the recorded calls hold both halves.

## `Workflow`, [line 53](../../../../../../../backend/src/sro/domain/skill/workflow.py#L53): Note on the line above

Code: `repeat: Repeat | None = None`

> The steps done once per thing on a list, where this job has them.
>
> `None` is every job mined before this existed and every job that does one
> thing once, which is most of them. What repeats is a fact about the JOB;
> how many times is a fact about the request, and a run of a repeating job
> given one item performs exactly like a run of a job with no repeat at all.
> See `domain/skill/repeats`.

## `ordered_cites`, [line 90](../../../../../../../backend/src/sro/domain/skill/workflow.py#L90): Docstring

> Every gesture the workflow cites, in step order.
>
> `cited_ids` is a set, and a shape key made in set order is not this job's
> shape -- the key is a SEQUENCE of (system, control, kind), so the order the
> steps run in is half of what it says. Here rather than beside either
> caller: the mining pass writes a shape key and `rekey_workflows` rewrites
> one, and two spellings of "in step order" is two shapes for one job.

## `Workflow.generalise_title`, [line 57](../../../../../../../backend/src/sro/domain/skill/workflow.py#L57): Docstring

> This job's own parameter values taken out of its name.
>
> The title is written by a model reading ONE doing, so it names that
> doing: "Create Customer Type DSS" for a job whose customer type has
> since been observed as DSS, DPP, CCD and CCF. Every later doing then
> looks like a different job to the person reading the offer card, which
> is the thing the title is for -- and `sro.domain.chat.reading` carries
> a paragraph of prompt whose only job is teaching the chat door to see
> past it.
>
> The moment a value is PROVEN to vary is the moment its presence in the
> title is known to be wrong, so this belongs beside the parameters
> rather than in the prompt alone: a model told to generalise still
> cannot tell a parameter from a constant on one doing. Whole words
> only, longest value first, and a title that turns out to be nothing
> but its values is left alone -- a job with a bad name beats a job with
> no name.

## module, [line 9](../../../../../../../backend/src/sro/domain/skill/workflow.py#L9): Comment

Code: `from sro.domain.skill.repeats import Repeat`

> Under `TYPE_CHECKING` for a cycle, not for load time: `repeats.detect`
> reads a step's recorded call, `evidence` is where that lives, and
> `evidence` imports this module for `Step`. The annotation is a string
> either way -- `from __future__ import annotations` is the first line of
> this file -- and nothing here resolves it at runtime.

## `Step`, [line 29](../../../../../../../backend/src/sro/domain/skill/workflow.py#L29): Comment

Code: `cites: list[str] = field(default_factory=list)`

> Every step cites the gestures that prove it. Free-generated workflow JSON
> hallucinated up to 21% of steps; forced to select from real evidence, that
> fell below 7.5%. An uncited step is a rejected step -- see checks.py.

## `Workflow`, [line 51](../../../../../../../backend/src/sro/domain/skill/workflow.py#L51): Comment

Code: `pass_id: str = ""`

> The pass that found it. A workflow has no cost of its own -- one model
> call proposes all of them -- so it names the row that does rather than
> carrying a copy of the bill that three workflows would then sum to three
> times. Empty for a workflow saved outside a pass, which today is only a
> test.

## `Workflow`, [line 55](../../../../../../../backend/src/sro/domain/skill/workflow.py#L55): Note on the line above

Code: `signs_in: bool | None = None`

> Whether this job signs in: set by the mining pass from its evidence
> (`checks.signs_in`) and healed onto stored jobs, never guessed at run time.
> Read by the run engine -- the only jobs a run may splice in to get back
> through a sign-in page, and the only jobs whose run may end `held` because
> the browser has moved past their page -- and by anything that later has to
> know which jobs sign in to a system.
>
> `None` is undecided: never evaluated against its evidence. Every reader
> treats it as "not known yet" -- never as a sign-in job -- and every mining
> sweep decides it (`mining_pass.decide_sign_ins`). A job starts undecided;
> the mining pass decides a proposal before it is stored.

## `field_key`, [line 94](../../../../../../../backend/src/sro/domain/skill/workflow.py#L94): Docstring

> The body key of a learned field step (X10, `with_field`), or "". Such a step
> cites no gesture and fills one parameter that the job declares with the `key`
> the save's own call confirmed it by -- that `key` exists nowhere else, so it is
> what tells a field nobody demonstrated from a step with its evidence missing.

## `Step.role`, [line 37](../../../../../../../backend/src/sro/domain/skill/workflow.py#L37): Note on the function

> `tab` is None only for a step stored before 0086 and not yet decided by the
> sweep (`tabs.undecided`). Every reader -- the wire, the compile view,
> `unresolved`, the runtime -- asks `role`, which takes that NULL as `main`:
> the one tab every job ran in before steps knew theirs.
