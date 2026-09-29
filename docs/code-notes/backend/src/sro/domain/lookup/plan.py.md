# Notes for `backend/src/sro/domain/lookup/plan.py`

Comments and docstrings moved out of [`backend/src/sro/domain/lookup/plan.py`](../../../../../../../backend/src/sro/domain/lookup/plan.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/lookup/plan.py#L1): Docstring

> Where to look for the answer to a question, and what may never be guessed.
>
> A question arrives -- typed into the panel, or sitting in a mail the operator
> has open -- and the answer is somewhere in the systems they work in. This is
> the plan for going and getting it: one lookup per system that could answer,
> each naming either a call to make or a screen to open.
>
> **Not a graph, and deliberately not.** The alternative design keeps a reconciled
> copy of every system's records and answers from that; it needs an entity model,
> a resolver, conflict rules, and a sync that is wrong the moment it lags. This
> one goes and looks, using what the knowledge base already holds: 1,663
> endpoints with their parameters, 1,025 screens with their routes, the field
> dictionary, and the quirks that say where a system lies about its own data. An
> answer costs a call rather than a schema, and it is never stale because it was
> read when it was asked for.
>
> **A read is not a job, and that is why this exists at all.** `umbrella`'s
> instructions are explicit that looking something up is a STEP of a job and not
> a job -- somebody who searches for the record they just created is finishing
> one. That rule is right and it means the miner will never produce a read, so a
> read has to be planned rather than mined.
>
> Three refusals, and they are the whole of the discipline here:
>
> **A lookup cites knowledge or it is refused.** `validate` refuses a workflow
> step that cites no gesture, for the reason that free-generated steps
> hallucinated at 21% and evidence-selected ones below 7.5%. The same rule, one
> plane over: a lookup naming an endpoint this deployment has never seen is a
> guess with a URL in it.
>
> **An ambiguous word is asked about, once.** `knowledge.open_questions` already
> holds this: two endpoints answered "how many transport modes", the system
> picked the first it saw, and an operator found out by counting rows on a
> screen. Where the question the operator asked lands on an open question, this
> plans nothing and returns the question instead.
>
> **A read may not write.** Every lookup is a GET or a screen. The planner cannot
> express a write, so no prompt injected into a mail can talk it into one.

## module, [line 8](../../../../../../../backend/src/sro/domain/lookup/plan.py#L8): Note on the line above

Code: `HOW = ("call", "screen")`

> The two ways to find out. `call` is a GET the extension makes from inside
> the operator's own session; `screen` is a page it opens and reads. A system
> with a known endpoint gets the call -- it is cheaper, it does not move anybody's
> tab, and its answer is data rather than a picture of data.

## module, [line 10](../../../../../../../backend/src/sro/domain/lookup/plan.py#L10): Note on the line above

Code: `K_MAX_LOOKUPS = 6`

> How many systems one question may be asked of.
>
> Not a cost ceiling -- a read is cheap. It is a fan-out ceiling: a question that
> plausibly reaches seven systems is a question nobody framed, and answering it
> everywhere buys noise. Measured against what this deployment holds: the widest
> real question touches the WMS and a mailbox.

## `Lookup`, [line 14](../../../../../../../backend/src/sro/domain/lookup/plan.py#L14): Docstring

> One place to go and one thing to ask it.

## `Lookup`, [line 17](../../../../../../../backend/src/sro/domain/lookup/plan.py#L17): Note on the line above

Code: `target: str`

> The endpoint path for a call, the route for a screen. Both are keys the
> knowledge base holds, which is what `unknown_targets` checks.

## `Lookup`, [line 21](../../../../../../../backend/src/sro/domain/lookup/plan.py#L21): Note on the line above

Code: `cites: tuple[str, ...] = ()`

> The knowledge keys this lookup was built from. A lookup that cites
> nothing cannot be checked, and is refused for the reason an uncited step
> is.

## `Asked`, [line 25](../../../../../../../backend/src/sro/domain/lookup/plan.py#L25): Docstring

> A question this deployment will not answer by guessing.
>
> Returned instead of a plan, never beside one: a plan that proceeds on five
> systems while asking about the sixth has already answered the question it
> claims to be asking.

## `Plan`, [line 33](../../../../../../../backend/src/sro/domain/lookup/plan.py#L33): Docstring

> Where the answer to one question lives, or the question that stops it.

## `unknown_targets`, [line 44](../../../../../../../backend/src/sro/domain/lookup/plan.py#L44): Docstring

> The targets no entry in the knowledge base names.
>
> Checked against the keys the planner was actually SHOWN, not against the
> whole store: a model that names a real endpoint it was never given has
> still guessed, and the fact that the guess happened to exist somewhere is
> luck rather than evidence. The same reading `validate` takes of a citation.

## `in_declared_slots`, [line 49](../../../../../../../backend/src/sro/domain/lookup/plan.py#L49): Note

> The model picks VALUES for the slots an endpoint declares (the knowledge
> entry's `params`) and nothing else. A key it invents is dropped here, where
> the model's answer enters the system, so it can neither add a parameter a
> warehouse acts on nor overwrite a recorded query key that is not a declared
> slot -- `libraryContext`, a paging parameter -- on a read that now runs with
> nobody watching (L1 review M4). A declared slot the recording also carries
> is the point: it is the question being asked now.

## `uncited`, [line 64](../../../../../../../backend/src/sro/domain/lookup/plan.py#L64): Docstring

> Lookups whose citations name nothing the planner was shown.

## `open_question_for`, [line 71](../../../../../../../backend/src/sro/domain/lookup/plan.py#L71): Docstring

> The unanswered question this one lands on, if it lands on one.
>
> `open_questions` records the ambiguity this deployment refuses to guess at
> and supersedes it with an answer naming who gave it. An open one here stops
> the plan: two endpoints answered "how many transport modes", the system
> picked the first it saw, and the operator found out by counting rows.
>
> **Which ambiguity stops which question is decided by the key's shape, and
> that is the measured part.** The store holds three:
>
> `<system>/<entity>/collection` -- which collection an entity lives in.
> About the entity itself, so any question naming that entity is stopped by
> it. This is the transport-modes case, and the reason this function exists.
>
> `<system>/<entity>/value/<word>` -- which field of an entity a word in a
> demonstration named. About the WORD. A question naming the entity and not
> the word is not ambiguous at all, and stopping it is a refusal the
> operator cannot act on.
>
> `<system>/<entity>/create/<parameter>` -- whether a value both
> demonstrations used is fixed or asked for each time. About a WRITE, and a
> read cannot be ambiguous in that way.
>
> The first rule alone was what this had, and against the real store it
> stopped three of five ordinary questions, every one of them falsely: "which
> clients are set up" stopped on which field of client the word 'full' names,
> "list the transport modes" on 'all', "where do I see customer types" on
> 'system'. A refusal nobody can act on is worse than the guess it prevents,
> because it stops the question AND teaches the operator to ignore the one
> stop that was real.

## `_stops`, [line 98](../../../../../../../backend/src/sro/domain/lookup/plan.py#L98): Docstring

> Whether this ambiguity is about what was asked.

## `_listed`, [line 113](../../../../../../../backend/src/sro/domain/lookup/plan.py#L113): Docstring

> A JSON column's list, or nothing. `body` is `jsonb`, so every field in
> it is `object` until something checks -- and a guard that assumed a list
> would raise on the one entry somebody wrote by hand.

## `_stem`, [line 119](../../../../../../../backend/src/sro/domain/lookup/plan.py#L119): Docstring

> A word as it is compared: lowered, unpunctuated, and singular.
>
> Singular because the ledger writes the entity and an operator writes the
> plural -- `blue_yonder/supplier/collection` against "which suppliers are
> set up at SG" -- and a literal comparison walks past an ambiguity somebody
> has already written down, which is the one thing this function exists to
> stop.
>
> A trailing `s` and nothing cleverer. A stemmer would match `code` to
> `coded` and `barcode`, and matching too much here stops every question on
> the first open ambiguity in the store. Short words are dropped whole: `at`,
> `set` and `the` are in every question ever asked.

## `open_question_for`, [line 74](../../../../../../../backend/src/sro/domain/lookup/plan.py#L74): Comment

Code: `settled = {`

> An answer is a separate entry under the same key rather than a field on
> the question, so "is this settled" is a question about the store and not
> about one row. Read once here: a question whose answer sits two rows
> further down would otherwise stop a plan the deployment has an answer for.

## `_stops`, [line 107](../../../../../../../backend/src/sro/domain/lookup/plan.py#L107): Comment

Code: `return bool(words & entity)`

> `blue_yonder/supplier/collection` against "which suppliers are at SG".
> Split on the separator: the key writes `transport_mode` where an
> operator writes "transport modes".

## `_stops`, [line 109](../../../../../../../backend/src/sro/domain/lookup/plan.py#L109): Comment

Code: `return parts[3].lower() in asked.lower()`

> The word, not the entity. Substring rather than a stem match because
> the word came out of a demonstration and lands inside the operator's
> own sentence in whatever form they wrote it.

## `_stops`, [line 110](../../../../../../../backend/src/sro/domain/lookup/plan.py#L110): Comment

Code: `return False`

> `create/<parameter>`, and anything a later pass invents. A read is not
> ambiguous about what a write should send, and an ambiguity whose shape
> this does not know is one it cannot say is about this question.
