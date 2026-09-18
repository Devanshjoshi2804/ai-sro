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
| 3.1 | **A step names the prior steps whose output it uses** (CrewAI) | stolen |
| 3.2 | **A dormant pause keyed by an external id** (LangGraph) | done `fcce6029` |
| 3.3 | **Learned facts written back as a reviewable diff** (Robot Framework) | stolen |
| 3.4 | One request, two mails, one card | done `797ed1d0` |
| 3.5 | The card asks in the conversation, not in boxes | done `ca488370` |
| 3.6 | The conversation is the spine — request, question, answer, run | done `37ecc5fb` |
| 3.7 | A finished job is a result, with an OK that ends it | done `1ebb1a86` |
| 3.8 | A card pile nobody answers — ages out after a day | done |
| 4 | Bind a value for a known field into the write | |
| 5 | An undemonstrated field must prove it landed | |
| 6 | The card says what it will write | |
| 7 | Composition — needs 3.1, 3.2, and a compensation story | last |

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
