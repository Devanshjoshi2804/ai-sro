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

### The post-condition is not always the state change

Measured on the target task. Every inventory adjustment demonstrated on the Blue
Yonder QA instance — including a change of one case — came back with *"The
Adjustment requested is greater than permitted limit - An Approval is Required.
The Location has been Locked."* The `PUT /data/WM/wm/inventory/adjust` returns
200, the LPN's on-hand quantity does **not** change, and a row appears in
Inventory ▸ Adjustments ▸ Approvals for a supervisor to approve or reject.

So a read-back asserting "on-hand is now the requested quantity" fails on a
successful run, and a verifier written to that assumption would classify every
correct execution as a failure. The post-condition for this task is *an
adjustment exists, pending approval, with these values*, and reaching the real
quantity needs a second human step this system does not perform.

Read as a rule rather than a Blue Yonder quirk: **the post-condition belongs to
the demonstration, not to the writer's intent.** What the operator's read-back
looked at after the write is the only honest source for it.

## Writes

Every mutating step carries an idempotency key derived from the run and the
step. A retried `POST /adjust` is otherwise a double adjustment, and a Temporal
activity retry is a completely ordinary event.

Mutation is already a domain property (`CapturedRequest.is_mutation`), so this
is enforced where the plan is built rather than remembered at the call site.

## L1 as built

A **run** (`domain/execution/run.py`) is the audit record: the skill version, the
stage it was at, the parameters it was given, the values it read out of the
system as it went, and one outcome per step. It is written after every step and
nothing in it is ever rewritten.

**What the stage means, concretely.** This is the difference the ladder makes,
and it lives in one property:

| Stage | Reads | Writes |
|---|---|---|
| `recorded` | refused | refused — nobody has reviewed it |
| `shadow` | sent for real | produced in full, **withheld** |
| `assisted` | sent for real | sent, and the run names the human who authorised it |
| `autonomous` | not available | — |

A withheld write is recorded with its URL and its idempotency key, so a
supervisor reviews the exact request before allowing the rung above.

**One step per activity.** `ExecutionWorkflow` calls `start_run`, then
`execute_step` per index, then `finish_run`. The step is the unit of durability
because it is the unit of damage: a worker that dies after step 7 resumes at
step 8, and an activity asked to repeat a step the run already records returns
what happened rather than doing it again. Retries are capped at one attempt for
every step, not only the writing ones — whether a step writes is knowable only
after it has been built, and a read losing a retry costs less than a write
gaining one.

**Where the credentials come from.** A skill's header plan holds references, not
values: `<blue_yonder/SG/cookie>` for the session, `<minted per run>` for CSRF.
The executor prefixes the tenant and resolves both out of the vault, so one
skill is usable by any tenant holding a login to that system and by no other.
A header that cannot be resolved stops the step; the call never goes out
degraded, because a request missing its session is a request as somebody else.

The honest gap: "minted" is aspirational. Blue Yonder issues
`CSRF-ENCRYPT-TOKEN` at login and no page, cookie or storage key exposes it, so
it is supplied through `POST /v1/connections/{id}/session-headers` by whoever can
read one — an operator, or the capture adapter, which sees every request header
of the session it is attached to. It expires with the session, and a run whose
header has expired fails at its first write rather than doing half a task.

## L2 as built

The measured problem first, because it decides the design: on this WMS the
accessibility tree carries no `button` role on three of four screens and never
carries a field's payload key, while the DOM ids are handed out in render order
— `ext-gen4443` is a different control after a reload. Replaying a demonstration
by CSS path or by role would find the wrong control or none.

So capture now also records **what the application calls the control**. The
recorder walks from the clicked element to its ExtJS component and stores the
`xtype`, the `itemId` and a two-segment `Ext.ComponentQuery` — the selector
language the application's own code uses. Induction turns that into an ordered
list of `ControlLocator`s: component query, test id, role and name, text, CSS
path. A signal that differs between the two demonstrations describes the record
rather than the control, so it becomes the parameter the diff already created
(the row for *this* LPN) or is dropped.

The driver resolves a component query by asking ExtJS, filtering to the visible
instance — this SPA keeps every screen it has ever shown — and then acts on the
resulting element through Playwright, so the gesture is a real click with real
actionability checks rather than a synthetic event the application may ignore.
Each step records which strategy matched: a step that only ever matches on the
last fallback is a skill about to break.

### The task is the unit that changes rung

A run that swapped medium half way through would leave the browser without the
screen state the earlier steps never produced, and a lone UI step would not find
its control. So the medium is a property of the **run**: `network` replays the
calls, `ui` performs the whole task in a browser. The escalation table in
`domain/execution/escalation.py` says which failures make the second choice
sensible; choosing it automatically belongs with Phase 5, because it is the same
decision as the circuit breaker.

Two refusals in that table are worth naming. A missing credential never
escalates — a browser cannot invent a session either. A system that did not
answer never escalates — pointing a browser at it turns an outage into a heavier
one. And a shadow run never drives the interface at all: a click is
indistinguishable from a call once it has happened.

## Teaching entry: the task names itself

An operator starts a demonstration by naming a URL. Nothing else is asked.

What the task *is* — its objective key — is read off the evidence when the run is
sealed. The call the demonstration ended on names the entity and the verb
(`PUT /data/WM/wm/inventory/adjust` is `inventory` / `adjust`), the query
parameter every call carried names the facility (`siteId=SG`), and the connection
that owns the host names the system (`blue_yonder`, which is what the vault scope
and the knowledge base call it — `bf56-kms-wms-web-np2.jdadelivers.com` is not).

This replaces a five-field form, and the reason is measured rather than
aesthetic: there were two such forms, they disagreed on the default direction,
and two people describe one task two ways. Induction pairs on **exact** equality,
so every disagreement produced two objectives that could never pair. Deriving
makes the key a property of what was done. Run 2 is started under run 1's derived
key, so a pair pairs by construction.

Same rule as parameter naming: no model is asked. Record ids are skipped when
naming (`/waves/W-8817/release` is about `wave`, not about `W-8817`), routing
segments (`data`, `api`, `v1`, `wm`) are skipped as facts about how the server is
wired, and background traffic never names anything because the frame excludes it
already.

A demonstration that asked the server nothing cannot be named this way. Sealing
it raises `unnamed_demonstration` and asks the operator for one line — the
exception, not the entry point.

## Narration

Clicks record what was done. They cannot record *why*: which branch the operator
was checking for, what they would have done had the count not matched, where they
would stop and ask a supervisor. None of that is recoverable from the network
trace afterwards, so the microphone is offered during the demonstration — opt-in
per session, with a live level meter, because a muted microphone looks exactly
like a working one until the run cannot be repeated.

Audio is uploaded before the seal (a sealed recording rejects attachments),
transcribed into **timed segments**, and placed on the recording's own clock
using the moment the microphone started. Alignment is half-open at both ends: a
sentence finishing exactly as the next click lands belongs to the action it was
describing. The last frame's window stays open, because "and that is queued for
approval now" arrives after the final click and is usually the best sentence in
the recording.

**The rule that makes this safe: narration labels, evidence decides.** What was
said becomes a note on a step, a branch a reviewer is asked about, and a flag
that a human belongs in the loop. It never becomes a parameter, a step or a
request — those come only from the two-run diff. A test asserts that inducing the
same pair with and without narration produces identical parameters, steps and
network plans.

The separation is kept in the data as well as in the rule: `SkillStep.intent`
stays derived from what was observed, and the words go in `SkillStep.narration`.
One field holding either would make a transcript indistinguishable from evidence
at review time, which is exactly where the difference matters.

A branch hint is never executable. The demonstration walked one path; the other
one has no evidence, so it is a question for a reviewer rather than a plan.

Transcription is the first egress in the system, so it takes two switches:
`SRO_GEMINI_API_KEY` and `SRO_TRANSCRIPTION_ENABLED`. A key is not by itself a
decision to send a customer's operators' voices to a hosted model. With either
absent the binding is `NullTranscriber` and demonstrations are silent, which is a
supported deployment rather than a degraded one.

## A skill says what it is for

Every version carries two sentences: `summary` (what it does) and `when_to_use`.
They are composed at induction from evidence — the objective, the mutating call
the skill exists to make, the parameters the diff found, whether a step needs a
human, any branch the operator described but did not demonstrate, and their own
closing sentence where they narrated, quoted rather than paraphrased.

No model writes them. A model would produce better prose and worse retrieval:
the warehouse's own words are already in the payloads and in the narration, and
those are the words a request will arrive in.

**These two fields are the retrieval surface.** When an operator asks for work,
their sentence is matched against them — so they are editable, by anyone
reviewing the skill, through `POST /v1/skills/{id}/describe`. Editing changes
what finds the skill and never what it does; the plans, parameters and
assertions are untouched. A skill described in words nobody uses is a skill
nobody finds.

`summary` is carried on the skills list as well as the detail, because a list
that hides it hides the skill.

## The knowledge store

`knowledge-base/blue-yonder-sce/` was a folder nothing read. It is now loaded
into `knowledge_entries` by `make ingest-kb`: **1,917 claims** — 551 endpoints,
398 fields, 316 screens, 216+ status observations, 84 create forms, 21 recorded
quirks.

**Every entry carries the evidence behind it**, at the level the base itself
recorded: `asserted` (written down, no stored exchange), `observed` (seen once),
`reproduced` (re-run and matched), `round_trip` (created, read back, changed,
deleted). Flattening these to "we know this" is precisely what the base's own
audit caught — six documented behaviours turned out to be fiction, one of them
"verified" against a route that never existed. So help-text fields land as
`asserted` and a re-run probe battery lands as `reproduced`, and
`automation_only` retrieval refuses anything below `reproduced`: an asserted
claim may inform a human and may not build a request. That floor is a `WHERE`
clause, not a filter over the page, because filtering after the limit hides
strong claims behind weak ones that happened to sort first.

**Nothing is ever overwritten.** A claim that replaces another leaves it in
place pointing forward (`superseded_by`), because "we used to believe this" is
the only way to explain an incident afterwards. Retrieval never returns
superseded rows.

**Evidence decides, not arrival order.** `domain/knowledge/supersede.py` is the
whole learning loop in three verdicts: an identical claim from the same source
is *unchanged* (which is what makes ingest re-runnable — proved by ingesting a
frozen copy twice for 1,917 rows both times); stronger-or-equal evidence
*supersedes*; weaker evidence contradicting stronger is *recorded but not
believed*. Without that last rule a nightly re-scrape would silently erase
everything execution had learned.

**Runs write back.** `LearnFromRun` hangs off `FinishRun`, where the in-process
and durable paths converge, and records what each verified step proved: this
method and path answered this status, cited to the run. Three things teach it
nothing — a withheld shadow write (built, never sent, status unknown), a step
whose assertions failed (the skill and the system disagree; recording it would
teach the store the skill's bugs), and a run that did not succeed. What is
recorded is `reproduced`, never `round_trip`: the call was made and checked,
which is not the same as creating, reading back, changing and deleting. Claiming
the higher level is exactly the inflation the base's audit was about.

**Retrieval is structured first, similar second.** System, kind and evidence
narrow with `WHERE`; the vector only orders what survives. A nearest neighbour
over the whole store answers with another system's endpoint, confidently. Both
embeddings and transcription follow the same two-switch rule: a key is not
consent to send, so `SRO_KNOWLEDGE_EMBEDDINGS_ENABLED` is a separate decision
and retrieval works without it.

Flows (`http/flows/*.json`) are deliberately not ingested: no key appears in all
35 files, so any reader would be guessing. They stay as human evidence.

## L3 as built

Reached when L2 finds nothing: the control the demonstration recorded is gone,
and what is on the screen instead is a question about pixels rather than about
selectors. The escalation table now says so, and says that nothing follows
vision — a human is the rung above, and there is no rung above a human.

**The model proposes one gesture. It never touches the browser.** Everything it
returns is executed by the same driver that executes a taught step, so real
actionability checks and trusted events still apply, and the run records the
same shape of outcome either way. `perform_at` is deliberately a separate method
from `perform`: a coordinate is not a control the demonstration identified, and
the record must never be able to confuse the two.

Bounded on every side, because this is the least predictable thing in the system
pointed at a live warehouse:

| Bound | Why |
|---|---|
| Five gestures per step | A model that has not finished in five is not about to |
| Allowed actions = the step's own gesture + scroll/hover | A demonstrated click must not become "navigate somewhere else and try there" |
| No writes without authorisation | Same rule as every rung: a click cannot be withheld once made, so a shadow run never reaches for the model at all |
| Every call recorded | `model_calls` holds run, step, destination, bytes, what was redacted, and the outcome — written whether or not the call succeeded |

**The model may not decide it succeeded.** `done` is stored as a claim, with its
reasoning, and the step's own assertions are what verify. Anything the driver
cannot map — a `drag_and_drop`, an action outside the allowed set, an answer
that is not JSON — is a refusal rather than a nearest match, because a `drag`
approximated as a click is a different gesture performed confidently.

**Redaction happens before sending, never after.** A screen whose text mentions
a password, PIN or token field is not sent at all — the image is withheld and
the refusal is logged. Otherwise any line naming a credential field is dropped
from the digest and the dropped names (never values) go into the call record,
because a silent redaction is indistinguishable from a bug.

`SRO_VISION_ENABLED` is a separate switch from the API key, and the more
consequential of the two: this one sends a picture of a customer's live WMS. Off
by default, and with it off a step whose control has vanished fails with that
reason rather than quietly reaching for a model.

## Retrieval decides what; the ladder decides how

`POST /v1/intent/resolve` turns a sentence into a decision. It starts no run.

**Structural before semantic.** A skill is a candidate only if something on its
objective key matches — system, entity, facility or verb — and wording only
orders what survived. Wording alone never matches: a sentence about carriers
must not find the wave skill because both descriptions say "release".

**A partial match is the dangerous one.** Measured live: *"count inventory in
SG"* hit an inventory-adjust skill's entity and facility, scored well, and the
one word that says what to do — *count* — matched nothing. So every candidate
carries the words it cannot account for, and a candidate with any is offered as
a question rather than presented as an answer:

> Did you mean Adjust LPN quantity (blue_yonder/SG)? Nothing it does accounts
> for count.

**Ambiguity is offered, not resolved.** Two candidates within two points are
returned together, distinguished by their keys — three skills called "Release
Wave" are told apart as `blue_yonder/DC07`, `/DC05`, `/DC03`, which is what the
key exists for. Guessing between them is the wrong-match failure with extra
steps.

**Nothing taught falls to the knowledge base, never to the ladder.** The
tempting mistake is to run the nearest skill in a browser and let vision sort it
out — a confident wrong action. Instead the planner answers from ingested
knowledge, with its sources and evidence levels attached:

```
> add a carrier
  no skill — proposal from index/app-map.json, index/api-endpoints.json
    open Configuration ▸ Partners ▸ Carriers ▸ Transport Modes   [observed]
    the screen calls /data/WM/rpux/filter/columns/WMCarrierProNumber [observed]
  "…review it, or teach me the task and I will do it exactly as you do."
```

A proposal is not a skill and carries a caveat saying so: it cites screens and
endpoints rather than two demonstrations, so nobody has ever performed it here.
It is read, not run — provenance comes from doing the task, not from reading
about it.

The resolver makes no model call. Ranking is a pure function of the library and
the sentence, so every match is explainable after the fact — which is what
`why` records. Parsing a messier sentence with a model belongs with chat, and
its output lands here to be validated against a skill that exists.

## Chat as built

`POST /v1/threads/{id}/messages` takes a sentence and returns the whole thread.
The reply is never improvised: it is a rendering of the `Resolution` — the skill
that matched and what it still needs, the choice between two too close to
separate, or what the knowledge base knows about a task nobody taught.

**The decision is stored beside the prose.** Every assistant message carries the
structured resolution: which skill, which version, whether it was confident,
what is missing, and what matched. An operator reads the sentence; anybody
asking "why did it pick that" reads the decision. A thread is append-only,
titled by what was asked first, and survives a reload — the console's transcript
used to live only in the browser.

**Saying something performs nothing.** A matched skill is *offered*; starting it
is the operator's next request. That separation is what makes their
confirmation the authorisation an assisted run records, rather than a checkbox
somewhere earlier.

No model is called here yet. The reply is composed from a deterministic
resolution, which is why every message can be explained afterwards. Parsing a
messier sentence with a model plugs in at the front of this and lands in the
same validator: a key that resolves to a skill that exists, and parameters that
skill declares.

### Optional means optional

Measured with a bad Gemini key: embeddings were enabled, the call 401'd, and it
took down every conversation and every ingest — for a feature whose entire job
is to *order* candidates a structured filter already chose. Embedding is now
wrapped once (`application/knowledge/vectors.py`) and a failure costs the caller
its ordering and nothing else. The same rule holds for any optional rung: the
system without it must be the system, degraded, not the system, broken.

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
