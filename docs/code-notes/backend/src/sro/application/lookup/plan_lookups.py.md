# Notes for `backend/src/sro/application/lookup/plan_lookups.py`

Comments and docstrings moved out of [`backend/src/sro/application/lookup/plan_lookups.py`](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L1): Docstring

> One question, turned into where to go and look for the answer.
>
> The read half of this system. `read_chat` resolves a sentence against the jobs
> an operator was seen DOING; this resolves one against what the systems KNOW,
> which is a different question with a different answer and no overlap in the
> vocabulary. A job is mined from evidence; a lookup is planned from knowledge.
>
> Nothing here touches a system. The plan says where the answer lives and stops;
> executing it is the next seam, and keeping them apart is what lets a plan be
> read by a person before anything is asked of anybody's warehouse.
>
> **Structural retrieval first, similarity second**, which is `Retrieve`'s own
> rule and its argument: a nearest neighbour over the whole store returns another
> system's endpoint with total confidence, and a confident fast wrong answer is
> what this design is arranged against. So the planner is shown endpoints,
> screens, fields and quirks -- filtered by kind -- and the model orders what
> survived rather than choosing from everything.

## module, [line 31](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L31): Note on the line above

Code: `WHAT_TO_SHOW = (`

> The kinds a lookup can be built from, and one that stops it.
>
> `QUESTION` is in the list precisely because it is not knowledge the plan may
> use: an unanswered one is where the next confident answer would be a guess, and
> it has to be retrieved to be noticed. `STATUS` and `FORM` are left out -- what a
> code means and how a form is shaped matter when reading an answer, not when
> deciding where to ask.

## module, [line 39](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L39): Note on the line above

Code: `K_SHOWN = 40`

> How much knowledge the planner sees.
>
> Wide enough to hold the endpoint and the screen for two systems with their
> fields; narrow enough that the model is choosing rather than searching. The
> store holds 7,985 entries and a prompt carrying them would be a prompt nobody
> has read.

## `Planned`, [line 45](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L45): Note on the line above

Code: `answer: Answer | None = None`

> What the reading cost. Beside the plan rather than inside it: a plan is
> a domain object and a bill is not, and `MineResult` learned that the hard
> way when three workflows from one call summed to three times its cost.

## `PlanLookups`, [line 50](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L50): Docstring

> Where to look, for one question, over one tenant's knowledge.

## `_read`, [line 146](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L146): Docstring

> The model's answer as lookups, dropping anything malformed.
>
> Dropped rather than refused: a shape the schema should have caught is the
> model failing to answer, and the refusals above are about what it SAID.
> Losing one malformed lookup out of four still leaves a plan somebody can
> read; the count is what `unknown_targets` and `uncited` then judge.

## `_shown`, [line 173](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L173): Docstring

> What the planner is given, grouped by kind.
>
> Grouped because the kinds answer different questions -- an endpoint is a
> place to ask, a quirk is a reason to distrust the answer -- and a flat list
> makes the model sort them before it can use them. The key is first on every
> line, because the key is what a citation has to name.

## `PlanLookups.__init__`, [line 62](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L62): Comment

Code: `self._asker = asker`

> `Asker | None` rather than through `asker_or_refuse` at construction,
> for `ReadChat`'s reason: a factory that raised would make a
> deployment with no key unbuildable rather than refusing the one call
> that needs a model.

## `PlanLookups.execute`, [line 78](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L78): Comment

Code: `raise OverCap(why)`

> Before the retrieval and long before the call, which is where
> `mining_pass` checks it: a cap read after the work is a cap that
> has already paid for what it stops.

## `PlanLookups.execute`, [line 94](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L94): Comment

Code: `return Planned(Plan(question=asked, asks=stopped, why=stopped.question))`

> Asked once, and not answered here. The operator settles it and
> the answer supersedes the question, so the next reading of the
> same word reads the answer instead of asking again.

## `PlanLookups.execute`, [line 111](../../../../../../../backend/src/sro/application/lookup/plan_lookups.py#L111): Comment

Code: `return Planned(`

> A path that looks like the others is the failure this refuses.
> Refused whole rather than filtered: a plan that quietly drops one
> of its systems answers a narrower question than the one asked,
> and says nothing about having done so.
