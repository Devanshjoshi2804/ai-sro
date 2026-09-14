# What others have solved, and what we should take

Read after [`docs/15-observation-to-tasks.md`](15-observation-to-tasks.md). This
is a survey of published work and open-source systems that solve problems this
one has, written against **our** code: every entry names the file it would
change and what it would cost.

Nothing here is a plan. It is the reading, the mapping and a recommendation, so
that the next capability is chosen against what is already known rather than
invented from scratch.

## The short version

| What | Where it comes from | What it fixes here | Size |
|---|---|---|---|
| Segment a run into its repetitions | Leno et al., ICPM 2020 | **Done** — `segment.py`; the miner was blind to back-to-back work | — |
| Derived values that are *transformed*, not copied | Leno et al., 2020 (Foofah, A*) | **Done** — `induction/transform.py`, gated on both runs agreeing (ADR 004 v1) | — |
| Loops in a skill ("for every short-shipped line") | WebRobot, PLDI 2022 | **Done** — `induction/loops.py` and `execution/plan.py`, validated the way they validate: a guessed loop must predict what it was not built from | — |
| Element identity by similarity, not by one locator | Ringer, OOPSLA 2016 | `UiPlan` locators plus a healer; Ringer scores *all* candidates on many features | M |
| A store of healed locators with confidence | Healenium | **Done, our way** — which locator actually found each control is written back as knowledge; the skill is never rewritten | — |
| Synchronisation triggers, inferred | Ringer | `wait_for` is captured and read by nothing; the screen check settles by looking again, which needs no protocol change but is the cruder half | M |
| A validator as a separate rung | Skyvern 2.0, WebJudge | **Partly done** — L2 and L3 now check the demonstration's own `UI_TEXT_VISIBLE` post-conditions against the screen | S |
| Failure taxonomy for runs | AgentRx | We have `FailureKind`; theirs is nine categories over a critical-step attribution | S |

## Robotic process mining: the log is not segmented

*Identifying candidate routines for RPA from unsegmented UI logs* — Leno,
Augusto, Dumas, La Rosa, Maggi, Polyvyanyy (ICPM 2020),
[arXiv:2008.05782](https://arxiv.org/abs/2008.05782).

Their pipeline is ours, one step further on:

1. **Normalise** each UI event into *context* parameters (where it happened)
   and *data* parameters (what was typed). Ours is `_signature` in
   `segment.py`: method plus `url_shape`, identifiers removed. Same idea,
   narrower input — we have no desktop events, only calls and gestures.
2. **Segment** by building a control-flow graph over normalised events and
   cutting at its **back edges** — found with strongly connected components and
   a dominator tree. Everything between segments that does not match is
   discarded as noise.
3. **Mine** closed frequent sequential patterns with gaps (CloFast), rank them
   by frequency, length, coverage and *cohesion* (length minus median gap),
   then take the best, remove its occurrences, and repeat.

We segmented only on a pause (`IDLE`, three minutes), a host change, or a
half-hour cap. An operator clearing a queue never pauses, so twenty adjustments
arrived as **one** piece of work seen **once** — under a signature that was the
task twenty times over, so the fourth doing that afternoon made a different
candidate again. The most repetitive work in the warehouse was the work the
miner was least able to see.

`_repetitions` in `segment.py` now cuts a run where its call sequence is one
block repeated, found by the prefix function of string matching (period = length
minus longest border, and only where it divides evenly). That is the back-edge
idea with no tolerance for noise: exact repetition or nothing. Three doings with
one extra click in the second are still left whole.

**What is still theirs and not ours:** noise between repetitions, interleaved
routines, and ranking by coverage. CloFast over our episode signatures is the
next step, and it belongs as a *suggestion*, never as identity —
`docs/15` fixes identity as an exact signature so that mining is re-runnable,
and a pattern miner that answers slightly differently on the next sweep would
break exactly that.

## Parameters that are transformed rather than copied

*Automated Discovery of Data Transformations for RPA* — Leno et al.,
[arXiv:2001.01007](https://arxiv.org/abs/2001.01007).

They synthesise the transformation between a source field and a target field
**by example**, with Foofah (A* over split/join/replace operations). Two
optimisations make it usable: project the examples **per target field**, and
group examples by **token shape** — alphabetic runs to `<a>+`, digits to `<d>+`.
Baseline found 0 of 9 transformations in an hour; both optimisations found 9 of
9 in 131 seconds.

Ours is `_find_produced` in `induction/diff.py`, and it links a value to the
response that produced it **by exact string equality** (`str(leaf) == value`).
So the WMS's `42` becoming the ERP's `LPN-00042` is invisible: the diff sees a
value that varies and nothing that explains it, and the operator is asked for a
number the previous step already knew. **This is the commonest shape of the
cross-system workflow we just built** — a workflow is usually a data transfer.

**Built** — `application/induction/transform.py` and `domain/skill/transform.py`,
recorded as ADR 004 v1. Six operations (trim, recase, zero-pad, prefix, suffix),
no search: the rewriting is read off one run and has to explain the other run's
pair from the same pointer, verbatim links always win first, a single character
is not evidence, and a digit touching a digit is not a boundary. What is still
theirs and not ours is the search — Foofah's A* over split/join/replace finds
transformations these six cannot express, and their per-target-field projection
and `<a>+`/`<d>+` token grouping are what made it fast enough to use. That is
the shape to take when a real system wants something these six refuse.

## Loops: the shape we cannot express

*WebRobot: Web RPA using Interactive Programming-by-Demonstration* — Dong,
Huang, Lam, Chen, Wang (PLDI 2022),
[arXiv:2203.09993](https://arxiv.org/abs/2203.09993).

Their program model has selector loops (over DOM matches), value-path loops
(over input data) and while loops (pagination, "click until the button is
gone"). The synthesis idea is **speculative rewriting**: guess that the first
two iterations of a suspected loop are a loop by anti-unifying them
(`Click(//a[1])` and `Click(//a[2])` generalise to `Click(//a[i])`), then
**validate** the guess by replaying it against the recorded DOM trace and
requiring it to predict *more* actions than were demonstrated. A guess that only
reproduces what it was built from is memorisation and is rejected.

Our `SkillVersion.steps` is a flat tuple. "Adjust every short-shipped line on
this order" is either taught once per line or not at all. Their validation rule
is the one that makes this safe for us: the loop must correctly predict the
*next* demonstrated action, against evidence we already keep frame by frame.

**Built** — `domain/skill/loop.py`, `application/induction/loops.py`,
`application/execution/plan.py`. Narrower than theirs, because our evidence is
calls and answers rather than a DOM trace: a loop is an earlier response's list,
a block of steps run once per element, and values that are fields of the element.
Their validation rule is the one that made it safe to keep — the guess must
explain both runs' counts and every value sent, not the run it was read from.
Their while-loops (pagination) are still theirs: `_rest_of` already walks paging,
and value-path loops are what `run_batch` is.

## Element identity, and healing it

*Ringer: Web Automation by Demonstration* — Barman, Chasins, Bodík, Gulwani
(OOPSLA 2016), [paper](https://schasins.com/assets/papers/ringer.pdf). Three
abstractions: actions, **triggers** (inferred, to synchronise a replay with the
page's state) and **elements**, identified at replay time by a **similarity
metric over many features** rather than one locator. It replayed four times more
benchmarks than the state of the art.

*Rousillon / Helena* — Chasins, Mueller, Bodík (UIST 2018),
[paper](https://schasins.com/assets/papers/rousillon.pdf),
[helena-lang.org](https://helena-lang.org/). Built on Ringer, and the closest
published relative of the thing we just shipped: it scrapes **hierarchically
across many pages and sites** from one demonstration of the first row.

*Healenium* ([github](https://github.com/healenium/healenium-web)) is the
industrial version of the same instinct: store the DOM path and attributes of
every element that was found, and on `NoSuchElement` compare the stored tree to
the current one by **longest common subsequence**, generate a new selector, score
it, and keep the healed locator in a database so the next run starts from what
was learned.

For us: `domain/recording/events.py` already keeps a rich fingerprint, and
`application/execution/self_heal.py` repairs a *session*, not a locator. Locator
drift was handled silently: a skill carries several ways to find a control,
strongest first, the driver takes the first that resolves, and which one won was
recorded on every run and read by nobody. A step that has quietly fallen through
to its last-resort CSS path — or that no locator finds at all any more, so only
a model looking at the screen can reach it — looks exactly like a step that
works. It does work, and it is one screen change from not working.

`LearnFromRun` now writes that back as knowledge, keyed by the control rather
than by the skill: two skills clicking one button are two observations of where
that button is. Deliberately *not* Healenium's other half — it rewrites the
test's locator, and here a locator is evidence from a demonstration, which the
healer's own rule says is changed by demonstrating again, not by a tool guessing
in the night.

## Agents, and where the line is

Skyvern 2.0 runs planner → actor → **validator**, and reports 85.85% on
WebVoyager; browser-use is DOM-first, indexing interactive elements (including
`div`s with listeners, found through CDP's `getEventListeners`) into a numbered
selector map. Verification is now its own research area: **WebJudge** extracts
key points from the task, scores screenshots for relevance and judges from the
top-k, reaching 85.7% agreement with humans against WebVoyager's 78.7%.

The line this system draws is different and, where it applies, better: our
post-conditions are **extracted from the demonstration**
(`induction/assertions.py`), so a step is checked against what the system itself
did last time rather than against a model's opinion of a screenshot.

Reading this is what turned up that those post-conditions were only ever
evaluated at L1. A step performed in the interface, or finished by a model
looking at a screenshot, was verified by nothing — while carrying assertions
derived for exactly that purpose. They are checked now
(`verify.check_on_screen`). What is still worth borrowing is WebJudge's insight
for the case where the demonstration proves nothing visible: extract the key
points of the task, score screenshots for relevance, judge from the top-k. That
is a model judging a run, which this system should reach for last rather than
first.

**OpenAdapt** ([OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt))
is the nearest sibling in the open: record a demonstration, compile it to "an
inspectable, deterministic program", verify the effect before reporting success,
zero model calls on a healthy run, halt rather than guess. That is our thesis,
on the desktop. Their split into capture / compile / privacy repositories is
worth reading before we grow ours; their honest statement that browser support
is beta and that qualification evidence is per-task rather than per-platform is
worth reading twice.

## Privacy, and what everyone else has learned the hard way

Task-mining vendors converge on **on-device anonymisation**: sensitive values
never leave the machine, because a screenshot of a WMS is customer data whether
or not anybody looks at it. We already redact by field name at capture and keep
three planes (`docs/10`, `docs/11`), and screenshots are bounded (A4). The
gap worth naming: our redaction is name-based at the recorder, and a *value*
that is sensitive in an unnamed field — a free-text note — is kept verbatim.
That is a deliberate choice (ADR 004 forbids classifying by inspecting values)
and it should be re-argued the first time a customer's legal team reads it,
because the industry's answer is the opposite one.

## Sources

- Leno, Augusto, Dumas, La Rosa, Maggi, Polyvyanyy. *Identifying candidate
  routines for RPA from unsegmented UI logs*. ICPM 2020. https://arxiv.org/abs/2008.05782
- Leno, Dumas, La Rosa, Maggi, Polyvyanyy. *Automated Discovery of Data
  Transformations for RPA*. 2020. https://arxiv.org/abs/2001.01007
- Leno et al. *Robotic Process Mining: Vision and Challenges*. BISE 2021.
  https://link.springer.com/article/10.1007/s12599-020-00641-4
- Dong, Huang, Lam, Chen, Wang. *WebRobot: Web RPA using Interactive
  Programming-by-Demonstration*. PLDI 2022. https://arxiv.org/abs/2203.09993
- Barman, Chasins, Bodík, Gulwani. *Ringer: Web Automation by Demonstration*.
  OOPSLA 2016. https://schasins.com/assets/papers/ringer.pdf
- Chasins, Mueller, Bodík. *Rousillon: Scraping Distributed Hierarchical Web
  Data*. UIST 2018. https://schasins.com/assets/papers/rousillon.pdf
- Li et al. *SUGILITE* (CHI 2017) and *PUMICE* (UIST 2019) — demonstration plus
  natural language, and conditionals learned from speech.
  https://github.com/tobyli/Sugilite_development
- Healenium. https://github.com/healenium/healenium-web
- OpenAdapt. https://github.com/OpenAdaptAI/OpenAdapt
- Skyvern 2.0 architecture and WebVoyager results. https://www.skyvern.com/
- browser-use interactive element detection.
  https://deepwiki.com/browser-use/browser-use/5.3-interactive-element-detection
- *Multimodal Auto Validation for Self-Refinement in Web Agents*.
  https://arxiv.org/pdf/2410.00689 — Tables 1 and 2: a validator reading the
  run's own text scores 84.24% against 70.04% for one reading screenshots
  (83.00% with the final response beside it), over the benchmark's 643 tasks, with
  over 84% agreement with human annotators. Read from the paper on 2026-09-14,
  because the figures this repository had been quoting for it -- 86.9/78.8,
  94% agreement, "artifact verification 192 of 321 tasks" -- are in no version
  of it and in nothing else that could be found. The ladder's order stands on
  the real numbers; six files carried the invented ones.
