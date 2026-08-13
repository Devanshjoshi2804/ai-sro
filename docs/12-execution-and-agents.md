# Execution and agents

How a taught skill becomes work performed against a live WMS, and what stops it
doing the wrong thing. This is §3 of the solution design; the Workflow Builder
(§2) is what produced the skills it runs.

## The loop

```
utterance ──▶ intent ──▶ resolve ──▶ per item: execute ──▶ verify ──▶ record
                                          │                  │
                                          └── escalate ◀─────┘
```

An operator says what they want. Intent turns it into an objective key and
parameter values. Resolution finds the skill version and checks its stage.
Each item then runs through the medium ladder, and every attempt is verified
the same way regardless of which rung produced it.

## The medium ladder

| Rung | Medium | Comes from | Cost | Determinism |
|---|---|---|---|---|
| L1 | Network replay | `network_plan` | milliseconds | total |
| L2 | UI replay | `ui_plan` + AX graph | seconds | high |
| L3 | Vision | Gemini computer use | tens of seconds | none |

Each rung is slower, less predictable and more expensive than the one above.
That ordering *is* the product: a system that only had L3 would be a browser
agent, and a system that only had L1 would break on the first UI change.

**The ladder inverts safety, and that is worth saying plainly.** L1 is the most
trustworthy rung and the most likely to break when the WMS is upgraded. L3 is
the most capable and the least predictable. Auto-escalation means that when
things are *most* broken, the least deterministic medium takes control of a live
system. The decision to allow that was taken deliberately (see Decisions), and
it is the reason verification is built the way it is.

## Verification is the control, not a component

With all rungs escalating automatically and skills promoting themselves after N
clean runs, nothing else stands between a model and a live warehouse. Every
attempt is verified by:

1. **Assertions** extracted at induction — status, response fields, UI text.
2. **Read-back** — the demonstration almost always contains the `GET` the
   operator did *after* the mutation, to confirm it worked. That call is
   captured, parameterised by the same diff, and replayed to ask the WMS what it
   believes the state now is.
3. **Equivalence** — the outcome of an L2 or L3 attempt is checked against what
   L1 would have produced, not against "the model said it was done".

**Rule: a skill with no verifiable post-condition cannot become autonomous.** It
can run assisted indefinitely. Autonomy is earned by being checkable, not by
succeeding quietly.

## Writes

Every mutating step carries an idempotency key derived from the run and the
step. A retried `POST /adjust` is otherwise a double adjustment, and a Temporal
activity retry is a completely ordinary event.

Mutation is already a domain property (`CapturedRequest.is_mutation`), so this
is enforced where the plan is built rather than remembered at the call site.

## Agents

| Agent | Job | Model |
|---|---|---|
| Intent | utterance → objective key + parameters | Gemini Flash, structured output |
| Resolver | objective → skill version, stage, missing parameters | none |
| Executor | run one step at the highest rung that works | none for L1/L2 |
| Vision executor | L3 only | Gemini computer use |
| Verifier | did it hold, did the WMS actually change | none, plus model for ambiguity |
| Escalator | rung failed → next rung, or stop | policy as data |

**A Temporal workflow never calls a model.** Every LLM call is an activity.
A workflow is replayed after a restart, and a model that answers differently on
replay produces a different history — which destroys the audit trail, the one
thing an enterprise cannot lose here. This is not a style preference; it is what
makes the system explainable after an incident.

**Intent output is validated, never trusted.** The model returns a structure
that must resolve to an objective key we already know and parameters the skill
already declares. An utterance that resolves to nothing is a question back to
the operator, not an improvised call.

## Generated workflows

A skill induced from two demonstrations cites them: which recordings, who
performed them, when. A skill generated from a knowledge base cites nothing —
there is no evidence it was ever performed successfully.

Generated skills are therefore a distinct kind, visible as such, and they do not
enter the promotion ladder by the same door. The first time a generated skill
runs successfully against the live system *with verification passing*, it has
earned its first piece of provenance, and only then does it start counting.

## Egress

L3 sends screenshots and DOM of a customer's live WMS to Google; intent parsing
sends the operator's words. The enterprise agreed to *capture* everything — that
is storage, and it stays in their infrastructure. Egress is a different
conversation and is treated as one:

- Redaction before egress, not after: secrets, password fields, and the fields
  marked secret at capture time never leave.
- Every model call is logged with what was sent, what came back, and which run
  it belonged to.
- The set of destinations is configuration, so a deployment that may not use a
  hosted model can run L1 and L2 with L3 disabled.

## Decisions taken

| Decision | Choice | Consequence accepted |
|---|---|---|
| Write approval | Autonomous after N clean runs | The verifier is the only gate; it must be right |
| Escalation | All rungs automatic, verifier gates the result | Vision can drive a live WMS unattended |
| Knowledge base | Live sandbox + recorded traffic only | No spec to validate a generated call against |
| First slice | Full ladder on one task | Depth before breadth; one task proves the machinery |
| Target task | Blue Yonder inventory adjust | A write, with a natural read-back |
| Secrets | Env vars behind a port, real manager later | One adapter swap, not a migration |

A **clean run**, for promotion counting: every assertion passed, read-back
verified, and no escalation past L1. A run that needed vision is evidence the
skill is drifting from the system it was taught on — it resets the counter
rather than advancing it.

## Phases

0. **Secret capture hardening.** Blocking: passwords are captured verbatim today.
1. **L1 execution.** Execution domain, HTTP executor, idempotency, verification,
   deterministic workflow, audit.
2. **L2 UI replay.** Ancestry-based control finding, escalation policy as data.
3. **L3 vision.** Gemini computer use, redaction, egress logging.
4. **Chat and intent.** Thread, teach entry point, validated intent, batch preview.
5. **Autonomy.** Counters, circuit breaker, blast-radius limits.
