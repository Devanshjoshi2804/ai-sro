# Delegation, playbooks, and what the field has learned

Three research passes — papers and benchmarks, open-source formats, production
practice — read against this system's actual shape. Measured **2026-09-18**.

The short version: **the evidence validates most of what is built and warns
against exactly the two things still on the list.** That is a comfortable
result and it should be read sceptically for that reason, so the caveats are in
§5 rather than at the end.

---

## 1. What the evidence validates

### Structural gates beat prompted ones

ST-WebAgentBench ([arXiv:2410.06703](https://arxiv.org/abs/2410.06703))
measured completion against *completion under policy*: **24.3% → 15.0%**, a 38%
relative collapse, because agents skip required confirmation steps to finish
faster. User consent was the single most-violated dimension.

An agent asked whether to ask permission decides not to. The approval gate here
is not a policy the model is instructed to follow — it is a branch the model
cannot reach around. That distinction is the finding.

### Never retrying after a write that may have landed

The closest documented incident to our own risk: **847 duplicate customer
records in production before anyone noticed a retry loop**
([apptad.com](https://apptad.com/insights/when-your-agent-goes-wrong-a-post-mortem-playbook)).
Also Replit's agent deleting a production database during a code freeze and
then reporting rollback was impossible — it was not
([theregister.com](https://www.theregister.com/2025/07/22/replit_saastr_response/)).

`run_workflow` already says it:

> *A write that went out and was accepted, and then could not be shown to have
> held, is not a step to try again: the second attempt would create the order
> twice.*

Per the practice research this is the single highest-value line in the design.

### The belt order is the direction the field is moving

The verifier literature converges on execution-grounded signals before model
judgement — *"external tool verification provides more reliable,
execution-grounded supervision than LLM self-evaluation, which is prone to
hallucination and cannot verify computational correctness."* Process reward
models are reported as *"noisy, biased, or vulnerable to reward hacking"*
unless grounded in execution.

Status → confirming read-back → screenshot-judged-by-a-model is that order.
Nothing found argues for inverting it; several argue against ever using model
judgement as the only check on a write that matters.

### One agent, one path

- Anthropic's multi-agent research system beats single-agent by **90.2%** on an
  internal eval — at **~15× the token cost**, with token usage alone explaining
  80% of the performance variance.
- Google/MIT: past roughly **45% single-agent accuracy, adding agents makes
  results worse**.
- Three agents at 90% each compound to **72.9%** end to end.
- Cognition's *Don't Build Multi-Agents* (2025) reports parallel sub-agents
  failing on shared implicit context and recommends a single linear agent as
  the default.

One job, one press, one path is the shape the evidence supports.

## 2. What it warns against — both already on the list

### Unattended running

CMU measured agent success dropping from **60% on a single run to 25% over
eight consecutive runs** on ordinary office tasks. On tau-bench the strongest
agents solve **under half** of realistic airline-support tasks *attended*, and
a model at 90% pass@1 falls to **~57% at pass^k** when required to succeed
repeatedly at the same task — which is much closer to "does this job run the
same way every time" than any single-shot number.

This is the field's unsolved problem, not ours. Our "not proven" label is
correctly conservative.

### Composing two jobs

Structurally the same failure as the documented insurance case: an agent acting
confidently on data and paths no demonstration covered. **No framework ships
automatic partial-failure compensation.** The saga pattern is hand-written per
action (real in Temporal, formalised only in 2026 research), and nothing does
it for browser actions at all — there is no compensating "undo this click".

### And one that was not on the list: approval fatigue

Measured at roughly **ten actions per review session** before people stop
reading; by the twentieth *"the reviewer is pattern-matching on surface
features rather than reading the content"*. One real case reached 73 prompts in
a day.

> *"The first confirmation, you read. The tenth, you skim. By the fiftieth,
> you're tapping approve before your eyes have finished the sentence. A
> confirmation you don't read is not a safeguard. It's theater."*
> — [getmrmr.com](https://getmrmr.com/blog/approval-fatigue)

One press per job is fine at today's volume. It does not scale for free. Plus
One Robotics — an actual warehouse robotics vendor — reports human intervention
on **3.8M of 250M picks (~1.5%)**, 2–5 second response times. That is the shape
to aim at, and `earned` standing is the mechanism already here for it.

## 3. Worth stealing

Three concrete things, from reading the repositories rather than the blogs.

**CrewAI's `Task.context: list[Task]`** ([crewAIInc/crewAI](https://github.com/crewAIInc/crewAI))
— a task names the prior task objects whose output it consumes, rather than
reading an implicit shared blackboard. One inspectable line answers "how does
step 2 get step 1's output". Note also that `human_input` and
`checkpoint_original_description` are first-class schema fields there: approval
and "what was demonstrated before repair" are in the type, not bolted on.

**LangGraph's `interrupt()` + checkpointer** ([langchain-ai/langgraph](https://github.com/langchain-ai/langgraph))
— a paused run is a row in Postgres, not a waiting process. Anything holding
the `thread_id` resumes it any number of days later, consuming nothing while it
waits. This is precisely what "a run ends and is resumed by an email reply"
needs. Their docs also carry the warning we would need: *a pause without a
timeout policy is not paused, it is abandoned.*

**`robotframework-selfhealing-agents`** (MarketSquare, small and early) — writes
a healed locator back into the test source as a reviewable diff rather than a
runtime cache. The same discipline as the generated sensitivity JS here: a
learned fact becomes a versioned artifact somebody can read.

And one finding worth recording as an edge rather than a gap: **no open project
captures "a field's limit" as reusable structured metadata** the way
`workflow_learned.holds` now does.

## 4. Playbooks and sub-agents: the framing, assessed

A framing worth addressing directly, because it is the common one:

> Job playbooks are predefined scripts/SOPs that bring predictability and
> governance; sub-agents are isolated instances that handle a context-heavy
> subtask and return a short result; the best architectures use playbooks to
> define the rules and delegate to sub-agents for parallel execution.

That is a fair summary of the discourse. Applied here, **two thirds of it does
not fit, and the part that does is the vocabulary.**

**We are already the playbook half, more strongly than the framing allows.** A
mined workflow *is* a playbook — but derived from evidence rather than
authored. The framing has no category for that, and it is the better position:
nobody writes the SOP, nobody maintains it when the screen moves, and the
identity of a job is decided by arithmetic over what was observed rather than
by a document somebody kept up to date. "Predefined" is the weaker form of what
this does.

**Sub-agents solve a problem this system does not have at runtime.** Their
stated benefit is context isolation — keeping a long-running session from
bloating. A run here is not a conversation with a growing window. Each step is
a fresh, bounded model call carrying the step, its evidence, and the screen;
there is no accumulated context to protect. The research that produced this
document *is* the right use of sub-agents — isolated, parallel, returning a
short result — and that is a development-time tool, not a runtime
architecture.

**"Parallel execution" is actively wrong for this target.** Two sub-agents
driving one operator's browser concurrently is a race on a single tab and a
single session, and §1 above is the measured case against parallel agents under
matched compute.

What *is* useful from it: the word, and the distinction. "Playbook" is a better
name than "workflow" for what a mined job is, and separating *the rules and
sequence* from *the thing that executes them* is exactly the distinction a
composed job needs — a playbook of playbooks, with CrewAI's `context` as the
concrete form. Keep the vocabulary; do not import the architecture.

## 5. What is honest about this

- **The result is flattering, and that is a reason to distrust it.** Three
  passes each found the existing design defensible. They were briefed with that
  design, and a research pass told what a system does will tend to find support
  for it. The warnings in §2 are the load-bearing part of this document; §1 is
  the comfortable part.
- **No head-to-head exists.** Nobody has published a controlled comparison of
  an explicit mined playbook against free re-planning on the same tasks. "Our
  ladder beats planning by X%" is not a claim anyone can make with a number
  today, ours included.
- **Cost numbers in this field are mostly invented.** One of the more honest
  sources says so about its own: *"These are ballpark figures, not measured
  results."* Our **$0.02 a run** is a two-run pilot result and should be
  labelled that, not generalised into unit economics.
- **Benchmarks are not our workload.** WorkArena (GPT-4o ~42.7% against a 78.2%
  human baseline) is the nearest analogue and is vendor-adjacent. Nothing here
  has been benchmarked against any of them.
- One claim from the papers pass is worth acting on and is not yet built:
  **PEAR** (arXiv:2510.07505) finds memory at the *planning* point worth
  10–30pp and memory at the *execution* point worth approximately nothing. Our
  planning point is job-identification-from-email; our execution point is the
  replay ladder. If persistent state is added anywhere, that is where the
  evidence points.

---

## The list, as it stands

Numbered from the field-binding work; `2.x` items were added as faults were
found.

| | | |
|---|---|---|
| 1 | A dropped value is loud | done `f162ec28` |
| 2 | Report supplied values that did not come back | done `f162ec28` |
| 2.5 | Client-side truncation, caught in the page | done `07172ffb` |
| 2.6 | A limit found once is remembered on the job | done `b60a60c2` |
| 2.7 | A value that will not fit is asked about | done `5a2d10b1` |
| 2.8 | The card asks before the press, once the limit is known | done `3b198284` |
| 2.9 | Ask the asker — drafted reply, previewed, one per run | done, untested live |
| 3 | A job declares its fields — `field-dictionary.json` as source | done `0732894d` |
| 3.1 | **A step names the prior steps whose output it uses** (CrewAI) | done `2a2ee2e9`, unused |
| 3.2 | **A dormant pause keyed by an external id** (LangGraph) | done `fcce6029` |
| 3.3 | **Learned facts written back as a reviewable diff** (Robot Framework) | done `48a98d2f` |
| 3.4 | One request, two mails, one card | done `797ed1d0` |
| 3.5 | The card asks in the conversation, not in boxes | done `ca488370` |
| 3.6 | The conversation is the spine — request, question, answer, run | done `37ecc5fb` |
| 3.7 | A finished job is a result, with an OK that ends it | done `1ebb1a86` |
| 3.8 | A card pile nobody answers — ages out after a day | done |
| 3.9 | The wait for a reply is something you can watch | done `42a14ce7` |
| 3.10 | A standing question only takes what is an answer | done `fe5c1f37` |
| 3.11 | A question about the waiting is answered about the waiting | done `111dae90` |
| 3.12 | Home keeps one request; the rest go behind a counted tray | done `65aa1784` |
| 3.13 | An answer that completes a request starts it, without a second card | done `8bb6b2eb` |
| 3.14 | **The page is not the page this step is about — and what kind of not** | done |
| 3.15 | **Credentials for any system, entered once, used unattended** | done `bf4ee957` |
| 4 | Bind a value for a known field into the write | done `6642215e` |
| 5 | An undemonstrated field must prove it landed | done `122a16d2` |
| 6 | The card says what it will write | done `95911139` |
| 7 | Composition — needs 3.1, 3.2, and a compensation story | in progress; see below |

### 4 and 5 — one piece, and why they could not be built apart

A job's parameters are what two demonstrations proved VARY, and the form posts
far more than that: 46 keys in the one real body here, 44 of them
byte-identical across all three recordings. So `Department: Inbound` names a
slot this write already sends -- as the empty string a form sends for a box
nobody touched -- and the value had nowhere to go.

**Why the runs the rig itself does cannot fix this.** They are kept out of the
evidence plane on purpose: *a replay's clicks and the calls they set off, mined
as though somebody had done them, is the system learning a task from a robot
imitating a person -- and then offering it back as something worth automating.*
So a job's parameter set is frozen at whatever two people happened to do, and
forty rig runs teach it nothing. 4 and 5 come at it from the other side.

**4 is a join, and the join `write_plan` refuses.** That refusal is exact and
stands: a body key is not derivable from a label, and a suffix match is
ambiguous on the only real body there is. What is different is the SOURCE. The
dictionary is a declaration somebody wrote down, and reading one is not
inferring a correspondence from the shape of two strings. Where two keys answer
to one label -- `Description` names ten of them here -- it refuses exactly as
the limits do.

**5 is what makes 4 safe, and it is not a separate feature.** Nothing
demonstrated the slot, so a 201 says nothing about it: the request went, and
the field may have been ignored, renamed or dropped. So a value is written only
where the demonstrations' own answers echoed that key, and then the run reads it
back and checks it -- unconditionally, where a demonstrated slot is checked only
when the echo evidence exists. A slot no read can settle is not filled at all.

Three further refusals, each a line between filling a form and inventing an
API: a key no recorded body carries is never added; the evidence wins wherever
both could bind one slot; and demonstrations that answered nothing fill nothing,
because `None` is "no evidence about echoing" and not evidence of echoing.

**Measured over both real tenants' jobs, 2026-09-19.** Standing: recorded — the
plan was built off the stored bodies with a plant value; nothing was sent
anywhere. Five jobs re-aim their write, and they aim it at the body's own keys:

| job | what the plant value reached |
|---|---|
| `new` Create a Customer Type | `customerType`, `longDescription` |
| `new` Create a Warehouse Equipment Type | `vehicleTypeId`, `longDescription`, `voiceCode`, `vehicleLimit` |
| `new` Create a Work Area | `workArea`, `workAreaDescription` |
| acme Create a Work Operation | `operationCode`, `longDescription` |
| acme Create a Carrier Cross Reference | `carrier`, `serviceLevel`, `destinationName` |
| acme Create a Work Area | `workAreaDescription`, `voiceCode` |

And the ceiling, in the same measurement: acme's `Create a Customer Type` aims
nothing, because each of its steps cites ONE doing. `_slots` is the diff
between two bodies sent to the same endpoint, so a job mined from a single
demonstration has no slots — and the declared keys it does have are dropped
with them, since the plan refuses whole when nothing is claimed. Such a job is
performed through the interface, which is safe and works; it is simply never
deterministic. Two doings is what buys the deterministic write, and the mining
pass already prefers them.

### 6 — what is said before the press, and what is not yet

`54926cba` closes the half that was silent. A job's parameters are what two
demonstrations proved VARY and a form has far more fields than that, so a
request naming one the job has no parameter for was answered by a record
without it and nothing anywhere said so. The reading now names what it dropped,
the offer carries it, and the card says it with both buttons still live:
*This job cannot set Department, Region. It will write the rest.* Said and not
enforced, like the limit beside it.

`95911139` closes the other half. `what_it_writes` reads the act off the step's
own recorded call -- the same call `http.send` would replay -- and the card
says it before the press: *It will create a customerTypes record on wms.test.*
One line per writing step, because a job that posts twice makes two records.
POST creates, PUT and PATCH change, DELETE removes, and a method nobody has a
word for is left as itself; a delete names the collection and not the record's
own id, which is `path_shape`'s blanking rule met honestly rather than read
past.

What it still does not say is the FIELDS the write carries -- "with these two
fields, by pressing Save on that screen". The values are on the card already,
one line up; what is missing is the join between them and the body, which is
`write_plan`'s and is only sound where the binding is unambiguous.

### 3.1 — built as scaffolding, and unused on purpose

Built at the operator's request after I argued against it. The argument stands
and is recorded here rather than quietly dropped, because the day this field is
still empty in six months is the day to ask whether composition is really
coming.

The idea is right and the case is absent. Measured on the deployment
2026-09-19: **thirteen runs have made a record and not one has made two.** A
step consuming an earlier step's output has no producer -- mining emits no such
edge -- and no instance to consume. Building `Step.uses` now is a field nothing
writes, read by a binder nothing calls, kept green by tests written against
both.

The half of CrewAI's lesson that pays today is the inspectable one -- *how does
this step get that value* -- and it is already built and already on screen. A
gathered value carries the message it came from and the words it was quoted
from, and the run card says so: `Customer Type: DDLS — read from your mail
("customer type :- DDLS")`. A value an operator typed needs no provenance;
they were standing there and they meant it.

`Step.uses` now exists, is checked, is stored, and binds: what an earlier step
made reaches a later one as `step<order>.<field>`, namespaced so a create
answering `{"id": ...}` and a job with a parameter called `id` are never
silently the same value. A step that uses a later step, or one that is not
there, is refused at the door.

**Nothing writes it.** Measured after deploying it: every step of every job in
this deployment has `uses = []`.

Two things would fill it, and either is the moment the rest becomes real:

1. **A job that makes two records**, where the second needs the first's id.
   Then `RunStep.made` -- which already keeps what the warehouse called each
   record -- becomes something to bind from, and the edge is worth declaring.
2. **Composition (7)**, where a person joins two jobs and has to say how the
   second gets the first's output. That is the same edge, declared by hand
   instead of mined.

And a cheap producer for (1) when it arrives, in this codebase's own style:
the edge is DISCOVERABLE from evidence rather than guessed -- a value typed in
step 5 that equals what step 2's response returned is a `uses` edge, and the
recorded calls already hold both halves.

### The chain nobody was looking at: one Save, several writes

Found while measuring 7, and it is not a composition problem — it is a
correctness one, and it was live.

`KNOWLEDGE-BASE.md` 3b records it from the real host: **creating one client
fires four POSTs behind a single Save** — addresses, clients, clientWarehouse,
packingConfigurations — each carrying an id the one before it returned. The
deterministic replay sends ONE call.

Measured over every mined job of three tenants, 2026-09-19, counting only
writes the verified-writes ledger recognises and counting them per doing:

| job | step | what one doing wrote |
|---|---|---|
| `new` Create a Supplier | 13 | `PUT /wm/addresses/{id}`, `POST /wm/suppliers` |
| acme Create a Carrier Cross Reference | 5, 6 | `POST /wm/carrierCrossReferences` twice |
| acme Create a Work Operation | 11 | `POST /wm/workOperations` twice |

Four steps. Each would have replayed one call, made half of what the operator
made, come back 201, held on the status belt and reported `held` — which is the
worst shape a failure can have, because nothing about it looks like one.

`9f614151` refuses the replay for such a step and lets the ladder click Save,
which is what the page is for: it fires the whole cascade with the ids it has
just received. Two things the rule had to get right and both are checked by
breaking them — counted per DOING (a step cites one gesture per demonstration,
and counting across cites refuses eight steps including the live one), and only
ledger-recognised writes (the same click fires `sessionKeepAlive` and
`webPerformanceEntries/batch`).

**What this says about measurement.** Three defects this week came out of
running the real code over the real store rather than over its own fixtures:
this one, the `uses` edge that was a step on itself (`995a0b53`), and the undo
that compared a path shape as a string (`44652ee2`). The suite was green
through all three.

### What the deployment said, 2026-09-19

Today's work was measured on the deployment it was written for -- tenant
`greyorange`, 18 jobs, 610 gestures, 92 runs -- by running `make press-report`
inside the API container after deploying it.

| | |
|---|---|
| what one press writes | 3 jobs of 18: create a customerTypes, create an equipmentTypes, **remove** a customerTypes |
| a Save that writes twice | none — the cascade refusal changes nothing here |
| which step uses which | 0 edges over 63 steps |
| one job into another | 0 chains over 306 ordered pairs |
| what can be taken back | `Create a Customer Type` is taken back by `Delete a Customer Type` |

**And it found a defect, minutes after deploying.** `Create a Customer Type`
step 1 is "Navigate to the Customer Types screen": the page POSTs the grid's
query, the warehouse answers `200` with `{"name": "customers"}` — the
collection's own name — and `made_by` read it as a record the run had made.
`addresses` accepts exactly one field, which is exactly what that is, so the
result card offered *Undo it* and the press would have aimed a DELETE at
"customers". Three of the tenant's runs carried it; `5da21de3` stops it (a
record is named only out of a `201`) and the three rows were cleared.

**Where the undo stands after that.** The pair is found. No run can offer the
button, because each run's `made` carries two fields — `customerType` and
`longDescription`, the slots the read-back confirmed — and one record named two
ways is a record this cannot name at all.

Which of the two addresses the record is not in the evidence. Every call this
tenant has ever made to that collection is one of three shapes: `POST
customerTypes`, `GET customerTypes`, `DELETE customerTypes/GDD`. The delete
demonstrates `GDD` and the create demonstrates `GGD` and `GKB`, so no value
joins the two jobs, and nothing reads a member back on the create side. A name
join — `customerType` is the singular of `customerTypes` — is the guess
`write_plan` argues against at length.

So the next piece of the compensation story is a question, asked once per job
and kept: *which of these names the record?* That is the shape this system
already uses for the joins a model proposes and a person answers, and
`workflow_learned_history` is where the answer would live.

### 7 — where composition stands

Three preconditions, and the state of each.

**3.1, the binding.** Built, stored, and now proved through the loop it runs
in. `uses_edges` finds the edge off the evidence and `_what_earlier_steps_made`
reads the record; the one line between them — in the loop — decides whether a
value the warehouse minted reaches the step that needs it, and nothing
exercised it until `63680227`. It is driven through a RESUMED row, which is the
case the binding exists for: a run that comes back after a pause reads what it
made from the store, and a binding that only worked out of a local would be
empty for exactly that half of a job.

**3.2, the dormant pause.** Done (`fcce6029`) and proved live: a run parks, the
mail comes back, and the answer starts it.

**The compensation story**, which is the part nothing in the field does for
browser actions. Half of it is now real. `21312266` gave the result card an
undo — a mined DELETE job, run through the same ladder, the same write gate and
the same belts as anything else — and `7aa7645d` links the two runs: a run
records which run it takes back. Without that the delete went off alone, so a
failed undo read as a job that failed on its own rather than as *the record is
still out there*, and two panels showing one card pressed two deletes at one
record. The second press is now refused — but only where the first HELD. An
undo that failed left the record where it was, and refusing the second attempt
because the first did not work refuses the one press that might.

What is left is the chain itself: two jobs run as one piece of work, with the
first's output flowing into the second. Within a job that flow now exists; the
producer that would recognise it ACROSS two jobs does not, and neither does an
instance to recognise. `TeachWorkflow` composes two joined candidates into one
skill on the older plane, and the mined-workflow plane has no equivalent.

**Measured 2026-09-19, over every workflow this machine's store holds.** The
question asked of the evidence directly: does any job take a value another job
produced — same browsing stream, the later job's request carrying a value the
earlier job's response minted?

| tenant | jobs | ordered pairs | chains |
|---|---|---|---|
| acme | 10 | 90 | 0 |
| new | 14 | 182 | 0 |
| rigproof | 35 | 1190 | 0 |

The first run of that probe said **329** on `rigproof`, and every one was the
operator's own typed value coming back: `ACME-4471` and `PO-88213` typed into
the form, echoed by a read-back, and counted as the warehouse's work. Whatever
builds the cross-job producer has to subtract everything typed anywhere earlier
in the stream, not only what the same call sent — the in-job rule's narrower
version of that subtraction is what `995a0b53` fixes.

That fix came out of the same measurement. Run over the store rather than over
its own tests, `uses_edges` found exactly one edge in three tenants' 201 steps
and it was a step depending on itself — two steps citing one click, and a
confirming read counted as a producer. Both are fixed and the honest count is
now zero everywhere, which is what it should have been.

### 3.14 — the page is not the page this step is about

A run that cannot find its control says `control_not_found: no control matched`,
which is true and says nothing about why. `f4cfd4c8` fixed one case of it: a
password field on the page means the session has gone, and the step says so
instead of blaming a selector. That is one special case, and there are at least
four more of exactly the same shape:

- ~~**signed out**~~ — a password box on the page. `f4cfd4c8`, and `bf4ee957`
  signs back in and carries on.
- ~~**a dialog** over the form~~, which every control is behind, including the
  confirmation popup the demonstration never met because the record it was
  demonstrated on did not already exist. `67b6b46c` carries what it said.
- ~~**signed in, wrong screen**~~ — a redirect or a half-finished navigation
  left the browser somewhere else. `a71a5865`.
- ~~**the page never finished loading**~~ — a spinner where a form should be.
  `d6356513`, and it is the only one of the five that is FIXED rather than
  explained: two seconds and the same rung again, once per step.
- ~~**permission denied**~~ — the operator can reach the screen and not the
  action. `e0956418`. Structure could never answer it; the status could, and
  the calls the driven tab made were already being asked for -- just only for
  the step's own endpoint and only for writes, so a 403 on anything else went
  unread. `401` and `403` told apart, because they are two problems with two
  fixes.

Four of the five say what is there and change no verdict: a run that
renamed a failure would be a run deciding it knows why a step failed, and what
it knows is what is on the screen. The original reason is kept beside it,
because the selector may be broken as well.

**Known gap.** The three readings are unit-tested; the loop handing each one
the step's own screen is not. A test that drove the whole loop with an
always-failing control span its rungs, and a hanging test is worse than an
honest hole. Three of the faults that reached the deployment on 2026-09-18 were
this exact shape — the logic right, the wire one layer from where the test
looked — so it is written down rather than left to be rediscovered.

Each has a different answer: sign in and resume, navigate and retry, read the
dialog and stop with what it said, answer the popup, stop and name the
permission. What they share is a question nothing currently asks — *what is on
the screen, if it is not the thing this step is about* — and the case for doing
them together rather than one at a time is that a fifth one will arrive next
week, and a ladder of special cases has no rung for it.

Not Blue Yonder's problem. Every system has a login, a dialog and a permission
model, and a workflow mined on a good day knows about none of them.

### 3.15 — credentials for any system

`KeepSessionsOpen` already signs systems back in before their sessions die:
credentials encrypted in the vault, a half-life learned per system, never while
somebody is demonstrating, never during an outage. Its one driver drives a
Steel browser over a debugger URL, and the runs that matter drive the
operator's own Chrome, which nothing can sign in.

Two halves, and the second is a policy decision rather than a technical one:

1. **Entering them.** Already built, and in the panel rather than a console:
   a step that types a password and finds the vault empty refuses with
   `needs_secret`, and the run card draws the field. `fa8dcd76` connects the
   case that never reached it — a job mined from an already-signed-in session
   has no login step, so nothing ever asked. Never through a chat and never
   through a model, which is the whole reason the vault exists.
2. **Using them in the operator's browser.** `bf4ee957`. The concern raised
   first — that this widens where secrets travel — was wrong, and worth
   recording as wrong: the run has always fetched a vaulted password and typed
   it through the extension for any demonstrated login step, with the record
   scrubbed by `without_secrets`. What was missing was only that a mined job
   has no login step to trigger it.

   Both boxes before either submit (Keycloak puts them on one form, and a
   driver that filled the first it found submitted a password with no username
   five times running). A second factor is refused and said plainly rather than
   attempted. Once per step, because a login that did not take is a wrong
   password or an MFA prompt, and retrying spends an account's lockout budget
   on a credential that is not going to start working.

   `sign_in` is a COMMAND and not a plan `KIND`: a model that could choose to
   sign in is a model that can decide to put a credential on a page. What
   decides it here is a password box on the screen and something in the vault.

### Proven on the deployment, and not

Everything above is unit- and mutation-tested. What that is worth was measured
today: **seven faults reached a running deployment with a green suite behind
them**, and every one was found by an operator looking at a panel.

| proven live 2026-09-18 | |
|---|---|
| A limit read off the captured form, before any run hit one | `Customer Type: 4` |
| The card refusing the press and saying why | round 26–29 |
| The question asked in the conversation, with context | round 26–29 |
| An answer refused for still not fitting | |
| The answer starting the job, and the run reaching 201 | four records |
| The run resuming at the rebuild point | |
| `awaiting` written on the run row | round 28 |
| The spine — run message with its card under it | round 28 |
| The result card naming the record | round 29 |
| A card ending itself when acted on | round 29 |
| The mail to whoever asked — drafted, previewed, sent, threaded | round 32 |
| A reply read for the value IN it, rather than searched for | round 36, `WDSL` |
| The limit on the question the first time it is asked | round 36 |
| A sentence that is not an answer, refused four times running | round 36–37 |
| A question about the waiting, answered about the waiting | round 37 |
| The whole loop, mail with no code to `201` | round 38, `DDLS` |

Round 38 is the one to point at: a request arrived naming a description and no
code, the card could not answer it, the question went into the conversation and
a mail went to whoever asked, the reply came back as `customer type :- DDLS`,
the value was read out of that sentence, and one press drove six steps of a
real WMS to `POST /data/WM/wm/customerTypes 201`. Nothing was typed into the
panel but a press.

### What a green suite was worth, again

Eight more faults reached the deployment on 2026-09-18 with everything passing
behind them. Two were fakes being more agreeable than the real thing -- a test
written with `at` as a NUMBER while the worker stores an ISO string, so
"newest first" sorted nothing and every request dated to 1 January 1970; a
guard asserted on a fake element whose `disabled` does not stop a listener.
Three were wires one layer from where the test looked: the claim keyed on a run
id that is empty on the half with no run, the badge counting a field the panel
had stopped using, the redraw signature with no notion of a clock. Each was
found by an operator looking at a panel, and each is now pinned by a test that
fails when the fix is removed -- checked by removing it.

| built, never exercised against the real thing | |
|---|---|
| The opening naming the mail's subject | fixed `7b379c4f`, untested live |
| A reply carrying a waiting run on (3.2's consumer) | |
| A page repairing itself when it holds nothing | `3b525a0e` |
| The OK that ends a result card | `1ebb1a86` |
| The optimistic echo and thinking mark | only visible on screen |

### What the fakes agreed with, and Postgres did not

Twice today a unit suite passed a defect because a fake was more agreeable
than the store, and both are worth remembering as a class rather than as two
bugs:

- **`SayWhatHappened` wrote questions as `SYSTEM`; `pending_job` reads
  `ASSISTANT`.** Every question this system had ever asked was invisible to
  the door that answers it, since `5a2d10b1`. Every test passed, because each
  built its own question by hand with the speaker the READER wants.
- **`_settle_the_wait` saved and never committed.** `FakeUnitOfWork` counts
  commits and requires none, so it agreed with the code rather than with
  Postgres. Two integration tests now: one for the mechanism, one driving the
  method itself, because the first alone would let anybody delete the commit
  again.

And three times a wire broke one layer from where it was checked — the field
dictionary's screen, the run's `values` through two whitelists, and `about`
through the route. The last was a `str.replace` with no assertion, which
reported success and changed nothing.

3.2 turned out to be half-built already, and the half that was missing was not
the durable part. `asking.py` has always said *the state is the thread*: a run
that comes up short ends, and the question lives in a row carrying everything
established so far. What it had was one address — the panel — and the person
who knows the missing value is usually whoever sent the mail. So a run now
records the outside conversation it answers to, with a deadline (LangGraph's
own warning: a pause without a timeout policy is abandoned, not paused), and a
reply on that thread carries the waiting run on instead of being read as a
fresh request.

That last part fixed a present bug rather than preparing for a future one. A
reply is a new message id, so it was read, understood as naming no job — two
words with no job in them — and dropped, permanently, because the id had
already been claimed. The answer was being lost at the moment it arrived.

3.1 is the smallest useful step toward composition and does not require
building a graph engine.

3.4 was found by looking at a real operator's panel on 2026-09-18, not by a
test. It held two identical `Create a Customer Type — GV2, leaning new SRO type
046` cards, because that request arrived as two messages -- the request, and a
`Confirmed - please create the customer type in WMS as discussed` reply -- and
`_first_time` claims a MESSAGE id, so each was read, each was understood as the
same job, and each was offered. One request, two cards, and pressing both makes
the record twice.

3.2 closes this only once a run is already waiting on the thread. Nothing was
waiting here, so both were offered. What is missing is narrower: a second offer
for a job on a thread that already has an OPEN offer is the same request, not a
new one. The write claim still stands behind it -- two runs cannot both create
the record -- so this is a panel somebody stops trusting rather than a duplicate
in the warehouse.
