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

## `unknown_targets`, [line 94](../../../../../../../backend/src/sro/domain/lookup/plan.py#L94): Docstring

> The targets no entry in the knowledge base names.
>
> Checked against the keys the planner was actually SHOWN, not against the
> whole store: a model that names a real endpoint it was never given has
> still guessed, and the fact that the guess happened to exist somewhere is
> luck rather than evidence. The same reading `validate` takes of a citation.

## `uncited`, [line 99](../../../../../../../backend/src/sro/domain/lookup/plan.py#L99): Docstring

> Lookups whose citations name nothing the planner was shown.

## `open_question_for`, [line 106](../../../../../../../backend/src/sro/domain/lookup/plan.py#L106): Docstring

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

## `_stops`, [line 133](../../../../../../../backend/src/sro/domain/lookup/plan.py#L133): Docstring

> Whether this ambiguity is about what was asked.

## `_listed`, [line 148](../../../../../../../backend/src/sro/domain/lookup/plan.py#L148): Docstring

> A JSON column's list, or nothing. `body` is `jsonb`, so every field in
> it is `object` until something checks -- and a guard that assumed a list
> would raise on the one entry somebody wrote by hand.

## `_stem`, [line 154](../../../../../../../backend/src/sro/domain/lookup/plan.py#L154): Docstring

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

## module, [line 46](../../../../../../../backend/src/sro/domain/lookup/plan.py#L46): Comment

Code: `"properties": {`

> `why` first for `reading.INTENT_SCHEMA`'s reason: a structured answer is
> written left to right, so a model asked for the reason first has to name
> the evidence before it commits to a target. Asked for the target first it
> picks an endpoint and then writes the sentence that defends it.

## `open_question_for`, [line 109](../../../../../../../backend/src/sro/domain/lookup/plan.py#L109): Comment

Code: `settled = {`

> An answer is a separate entry under the same key rather than a field on
> the question, so "is this settled" is a question about the store and not
> about one row. Read once here: a question whose answer sits two rows
> further down would otherwise stop a plan the deployment has an answer for.

## `_stops`, [line 142](../../../../../../../backend/src/sro/domain/lookup/plan.py#L142): Comment

Code: `return bool(words & entity)`

> `blue_yonder/supplier/collection` against "which suppliers are at SG".
> Split on the separator: the key writes `transport_mode` where an
> operator writes "transport modes".

## `_stops`, [line 144](../../../../../../../backend/src/sro/domain/lookup/plan.py#L144): Comment

Code: `return parts[3].lower() in asked.lower()`

> The word, not the entity. Substring rather than a stem match because
> the word came out of a demonstration and lands inside the operator's
> own sentence in whatever form they wrote it.

## `_stops`, [line 136](../../../../../../../backend/src/sro/domain/lookup/plan.py#L136): Comment

Code: `return False`

> `create/<parameter>`, and anything a later pass invents. A read is not
> ambiguous about what a write should send, and an ambiguity whose shape
> this does not know is one it cannot say is about this question.
