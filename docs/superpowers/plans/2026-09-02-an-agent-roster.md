# Sub-plan 1 — Ladder gates and the Verifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the promotion ladder the thing that opens the door, then make "done" mean a write confirmed by a read-back through a second path — so that autonomy after three verified effects is safe to grant.

**Spec:** `docs/superpowers/specs/2026-09-03-autonomous-workflows-design.md` — this is sub-plan 1 of its roadmap. Decision D2 there (autonomy by verified effect, reads free) is what Tasks 1 to 8 implement. The roster agents this plan first proposed are moved to the end of this file under *Moved and deferred*.

**Architecture:** No new layer, no registry, no framework. Every agent is the pattern this codebase already uses: a use case, a `Protocol` in `application/ports/`, a null adapter under `infrastructure/gemini/`, a fake in `tests/unit/fakes.py`. Phase 0 makes the ladder gate before anything new stands on it. The largest single piece — a write verified by a read-back down a second path — is mostly pure induction and needs no model at all.

**Tech Stack:** Python 3.14 / FastAPI backend, Temporal worker, pytest, ruff, mypy `--strict`, import-linter.

**Origin:** A harsh audit of the backend's agentic and autonomy claims (2026-09-02), plus surveys of published autonomy-governance work and of competing systems. Findings referenced below as H1–H7.

## Global Constraints

- **An agent proposes; evidence disposes; a rung decides who may act on it.** Every proposal in this plan is validated against something that already exists — a captured payload, a settled knowledge entry, a declared enum member, a re-read of the system of record. Nothing an agent says is acted on because it said it.
- **Skill execution stays free of models.** L1 and L2 replay a plan derived from demonstrations. No agent is added to that path by this plan or any other. This is the property that makes the audit trail worth having.
- **Identity is never a model's answer.** `(principal_id, signature)` and exact-equality clustering are untouched. Mining re-runs over evidence it has already read, and anything that answers differently on a second pass makes a candidate that can never pair.
- **Every model call is recorded.** `domain/execution/model_call.py` already carries purpose, destination, bytes, `image_sent`, `redacted_fields` and outcome, and `FakeModelCallRepository` exists. Every agent writes one whether or not the call succeeded.
- **A key is not consent.** Each new agent gets its own egress setting beside `vision_enabled` and `interpretation_enabled`. With every switch off, the system behaves exactly as it does today, and the unit suite must prove it.
- **Phase 0 lands before Phase 2 starts.** Adding agents on top of a ladder that gates nothing multiplies blast radius.
- **A code change is not live until the worker restarts.** Induction and both sweeps run there.
- Never `git add -A`; commit the paths each task names, then `git show --stat HEAD`.

---

## Why

Three findings drove this.

**The audit.** `AUTONOMOUS` is decorative: nothing in the executor branches on it, `execute_skill.py:1605` and `:1616` distinguish only `RECORDED` and `> SHADOW`. What actually makes a run unattended is `Trigger.requires_confirmation`, set by an `auto_approve` flag at `create_trigger.py:132` that never consults the stage. And the three-failure demotion backstop undoes itself — `SkillVersion.earn` clears `demotion_reason` and re-promotes a demoted version to `ASSISTED` after one clean shadow run, with nobody asked. That was verified by exercising the domain objects, not inferred.

**The prior-art survey.** The field has converged on the same four rungs we have, with one universal difference: everywhere else the rung *is* the permission. We built the scoreboard and wired the door to a different switch. The same literature finds that reference-free model judges score plausibility rather than correctness, and that the mitigation is *independence* — the judge commits its own answer before it sees the candidate.

**The competitor survey.** OpenAdapt — MIT-licensed, independently converged on this architecture — measured that **screen-only checks silently accepted 75.0% of wrong effects, and one oracle reading the system of record cut that to 12.5%**. `verify.check_on_screen` is a screen-only check, and it is what L2 and L3 runs are verified by. We already know the stronger technique: `knowledge-base/KNOWLEDGE-BASE.md` §3.2 documents proving a Blue Yonder write by confirming it on a separate `GET`. We did it once, by hand, and wrote it down. It is not a rung.

---

# Phase 0 — Make the ladder gate

### Task 1 — `auto_approve` requires `AUTONOMOUS` (closes H1, H2)

- [ ] `application/trigger/create_trigger.py`: refuse `auto_approve` unless the version resolved at creation is `AUTONOMOUS`. The refusal sentence names `version.not_ready_for_autonomy`, so an operator is told what is missing rather than that the answer is no.
- [ ] `application/trigger/fire_trigger.py`: re-check at fire time, beside the existing `version.changes_the_system and not trigger.writes` guard — that is already the pattern for "the skill moved under this trigger". A demoted version must start asking again.
- [ ] Tests: a trigger refuses auto-approval for a version that has not earned autonomy; a trigger that was auto-approving starts asking after its version is demoted.

This is the highest-leverage edit here. It turns the streak, the verdicts, `earn`, `demote` and `not_ready_for_autonomy` from decoration into the mechanism that opens the door, and makes the sentence at `domain/skill/promotion.py:38-40` true.

### Task 2 — `earn` may not clear a demotion (closes H3)

- [ ] `domain/skill/skill.py`: drop `self.demotion_reason = None` from `earn`. Only `promote` with `from_where != "preview"` clears it — the rule the comment at `:479-497` already defends on the other path.
- [ ] Test in `tests/unit/domain/test_autonomy.py`: three failures, then one clean shadow run, and the version is still carrying its reason.

### Task 3 — One source for autonomy readiness (closes H4)

- [ ] `domain/skill/earned.py`: `earned_stage` re-derives rules `why_not_autonomous` already owns and omits `needs_a_person`. Have it call `why_not_autonomous` and treat a non-`None` answer as "not yet". Two copies of one rule is the defect `apply_verdict`'s own docstring says this codebase refuses to have.

### Task 4 — Bound a batch (closes H5)

- [ ] `interface/http/schemas.py`: `BatchRequest.items` gets `max_length=MAX_ITEMS_PER_BATCH`.
- [ ] `application/execution/batch.py`: pass the remaining item count so the `assess(..., requested_writes=...)` branch at `domain/execution/safety.py:64` finally has a production caller. Its only caller today is a unit test.

---

# Phase 1 — Shared machinery

### Task 5 — `AgentBudget`

- [ ] New `application/agents/budget.py`: a value object holding a call ceiling and what has been spent. Lift the shape from `HealBudget` in `application/execution/self_heal.py`, which already does this for remedies — `take()` answering whether the attempt is permitted. Every agent takes one; no agent has an unbounded loop.
- [ ] `config.py`: one egress setting per new agent, defaulting off, documented the way `vision_enabled` is.

---

# Phase 2 — The Verifier

| # | Agent | Seam | Proposes | Checked by |
|---|---|---|---|---|
| 1 | **Verifier** | after a write | what a read-back should show | a re-read through a second path |
| 2 | **Repairer** | locator drift | a locator | replay against retained evidence |
| 3 | **Diagnostician** | a failure the table has no rule for | a `Remedy` | the `Remedy` enum + the heal budget |
| 4 | **Pathfinder** | a task nobody taught | one gesture | its own committed expectation |
| 5 | **Curator** | a library going stale | a retirement | a person |
| — | Namer, Intent, Interpreter | already built | — | unchanged |

### Task 6 — Verifier, the half that needs no model

- [ ] `domain/skill/assertion.py`: add `AssertionKind.EFFECT_CONFIRMED`, carrying the read's URL shape and the pointer the value must appear at.
- [ ] `application/induction/assertions.py`: it already receives both aligned demonstrations. Where a later frame in both runs carries a `GET` whose response contains the value the write sent, that read *is* the oracle — derived from evidence, `written_by=None`, exactly like every other assertion extracted here.

Build this first. It is pure induction, and it closes most of the gap on its own.

### Task 7 — Verifier, the model half

- [ ] New `application/execution/confirm_effect.py`, for a write whose demonstrations show no read-back. Before the write goes out, the agent is shown the step's intent and its parameters and commits, in one sentence, what a subsequent read should show. **It never sees the response.**
- [ ] Reuse `AskTheSystem` (`application/execution/derived_read.py`) to send the read — `GET`-only by construction, already resolving the skill's own session through `resolve_headers`, already handling paging and the sign-in redirect.
- [ ] Reuse `read_answer` (`application/execution/answer.py`) to parse it: counted and named, never summarised. The comparison is string work, not judgement.

Committing before seeing the candidate is what the reference-free-judge literature measures as taking the false-positive rate on wrong answers from 0.719 to 0.012.

### Task 8 — Let a confirmed effect count

- [ ] `domain/execution/verdict.py`: `_CLEAN_MEDIA` admits a step performed in the interface *whose effect was confirmed over the network*. Today any gesture makes a run `DEGRADED`, which resets the streak, which is why `needs_a_person` skills can never climb. A confirmed effect is better evidence than the medium it was performed in.
- [ ] `domain/skill/track_record.py`: add `verified_effects: int`, incremented only when a run's write steps all carry `EFFECT_CONFIRMED` and every confirmation held. Replace `REQUIRED_CLEAN_RUNS = 10` with `REQUIRED_VERIFIED_EFFECTS = 3`. `earned_stage` climbs to `AUTONOMOUS` on `verified_effects >= 3`, never on `clean_streak` alone.
- [ ] A human doing the task under observation counts: `application/observation/teach.py` and `learn.py`, when they induce or re-induce from a doing whose write was confirmed by a later read in the same episode (Task 6's derivation), record one verified effect on the version. Test: three observed doings with confirmed effects and zero system runs leave the version eligible for `AUTONOMOUS`; three doings without a read-back leave it at `RECORDED`.
- [ ] Reads are free: a version with no write step (`performs_writes` false) is `AUTONOMOUS` from its first successful run. `_check_runnable` and `create_trigger.py` treat it so. Test: a read skill accepts `auto_approve` after one run; a write skill does not.
- [ ] ADR 017 in `docs/07-adr/`: autonomy by verified effect. This changes the ladder's arithmetic and is an architecture decision, not a refactor. It records why 10 became 3 and what "verified" means, with the 75% / 12.5% figure.

---

## Moved and deferred

The four tasks below were this plan's original Phase 2. The spec moves Pathfinder into sub-plan 2, where the pursuit drives the operator's own tab, and defers the other three until the library passes twenty skills or drift is the top failure in the run log. They are kept here so the reasoning is not lost.

### Task 9 — Repairer (deferred)

- [ ] `application/skill/repair_drift.py`: keep every existing branch. Add one — where settled evidence names nothing, a model may **propose** a locator from the retained `ElementFingerprint` in `domain/recording/events.py`.
- [ ] Validate it the way `induction/loops.py` validates a loop guess: it must resolve against demonstration frames it was not built from. A proposal that only explains the frame it was shown is memorisation, and is discarded.
- [ ] A model-proposed repair enters at `RECORDED` with an empty `TrackRecord` like every repair, and additionally may not inherit past `ASSISTED`. A person authorises each run of a version no evidence settled. The existing rule stands: *"a model read pixels and chose, and letting that write the skill is a model marking its own homework."*

### Task 10 — Diagnostician (deferred)

- [ ] `domain/execution/diagnosis.py` and `domain/execution/escalation.py` stay deterministic and stay first. The agent runs only where `next_medium` returns `None` today.
- [ ] It is shown the symptom — status code, redirect, missing headers, failure kind — and must answer with a member of the existing `Remedy` enum or decline. Anything not in the enum is discarded, the way `GeminiIntentParser` drops an undeclared parameter and `computer_use.py` refuses an unmapped action.
- [ ] The proposal goes through `SelfHeal.attempt`, which already enforces `mutating and not safe_for_writes`, the per-step/per-remedy `HealBudget`, and the write-back to the knowledge store. Worst case is one wasted retry.

### Task 11 — Pathfinder (moved to sub-plan 2, closes H6)

- [ ] `application/execution/pursue_goal.py`: before the first gesture, the model commits what the screen will show when the goal is met. `reached` becomes that string appearing in `text_digest`, not `proposed.done`. Keep `proposed.done` recorded as the claim it is.
- [ ] `_keep` induces a skill only on a confirmed goal, never a claimed one. A model declaring its own success is currently the only unverified model opinion in the system that produces a durable artifact.

### Task 12 — Curator (deferred)

- [ ] New `application/skill/curate.py`, run on the existing miner sweep in `infrastructure/temporal/worker.py` beside `learn_what_repeats`.
- [ ] It proposes retirement — never performs it — for versions stale by arithmetic: never run since induction, degraded on every run, superseded by a newer version that has taken over, or induced under an `INDUCTION_VERSION` several generations old.
- [ ] The model's only job is the sentence saying why, exactly as `name_task` works. It lands as an `Ambiguity` through the existing `AskAbout` (`application/knowledge/open_questions.py`).

`LearnWhatRepeats` presses the teach button unattended and nothing ever presses the other one. The self-evolving-agent literature names rollback and monitoring as the two required mitigations for a library that grows on its own.

---

## Docs to update

- [ ] `docs/00-overview.md` — still says "No LLM calls at all" and "No execution or replay". Rewrite to describe the system the spec describes, with a one-line note that Phase A of the original design doc (anomaly agent, Graph RAG, reports) was dropped in favour of passive observation on 2026-08-23.
- [ ] `docs/17-agent-architecture.md` — its "Agent" column names single-shot extractors as agents, which is what prompted this review.
- [ ] `docs/12-execution-and-agents.md` — the roster and the new rung.
- [ ] `docs/16-what-others-have-solved.md` — the OpenAdapt entry predates their pivot onto this thesis; add the 75%/12.5% figure and their compile→verify→replay→repair pipeline.

## Verification

Per phase, not at the end.

**Phase 0** — `cd backend && uv run pytest tests/unit/domain/test_autonomy.py -q` and `uv run pytest -k "promotion or trigger" -q`. Tests named as sentences, per house style.

**Phase 1** — `uv run pytest tests/unit -q`. A deployment with no `gemini_api_key` produces an unchanged run.

**Phase 2** — unit tests against fakes per agent, with each null adapter proving it degrades to today's behaviour. For the Verifier, mirror OpenAdapt's `--break-it` case: `FakeHttpCaller` answers 200 to the write and returns a read-back that does *not* contain the value, and the run must fail rather than report success. That one test is the point of the phase.

**End to end** — `make up`, `make migrate`, `make api`, `make worker`, `make web`. With the extension watching, create a work area in Blue Yonder three times, each followed by opening the list that shows it. Confirm induction derived an `EFFECT_CONFIRMED` assertion from the read that followed each write, that the version shows three verified effects with zero system runs, and that a trigger on it now accepts `auto_approve`. Then create a supplier three times *without* opening the list afterwards, and confirm the same trigger is refused for that version with a sentence naming the missing read-back.

**Before a PR** — `make lint && make test`, plus `make types` if a wire type moved. Restart the worker.

## Out of scope

- **One agent per skill.** These tasks are deterministic replays with no search space; an agent per task is strictly worse than the plan induction already produces, at roughly 15× the tokens, and it discards the two-run diff.
- **An agent runtime, registry or external framework.** Revisit if the roster passes eight.
- **Anything touching L1/L2 execution.**
