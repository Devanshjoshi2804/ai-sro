# Learning and agents (design 2)

Status: approved in brainstorming 2026-09-25. Nothing below is built.

This is design 2 of the Steel migration. The execution runtime
(`2026-09-24-execution-runtime-design.md`, built on `feat/execution-runtime`)
runs a learned job step by step on backend Steel: tool, API, UI, then sight.
Design 2 improves what the runtime is given: which job a request means, which
values go where, whether a job can run, and the prompts that decide these. It
takes stream A of the Steel migration plan (A1-A9) and the two items the
runtime plan deferred: wording to fields, and a learned key in the replay
template. Design 3 ("Operator surface") owns everything the panel draws.

## 1. Decisions

| # | Decision |
| --- | --- |
| L1 | **No stored recipes.** The runtime keeps reading the learned job directly: its cited evidence, learned locators, the verified-write ledger and the known-broken list. Design 2 adds a **compile check** that says whether a job can run and why not, plus a read-only YAML view. There is no second copy of a job to keep in sync. This overrides parent spec D6's recipe table. |
| L2 | **Evaluation gate: local real cases, plus redacted cases in CI.** `make eval` runs on real cases from the local database and must pass before a prompt change merges; its report goes in the PR. A small redacted set (values replaced by their shapes) is committed and runs in CI, so a broken prompt file or schema fails fast. Real cases never leave the machine. |
| L3 | **Wording to fields: the model proposes, the operator's answer teaches.** The request reader matches a mail's wording to a field label from candidates. Code validates the match. When the reader is unsure, the run asks, and the operator's answer is saved as an alias for that job. Only aliases the operator confirmed are ever saved; the model never writes one. |
| L4 | **Multi-tab jobs run across tabs.** Code, not a model, learns each step's tab role. The runtime opens and switches tabs by role inside the run's one lease. |

## 2. Prompts and evaluation (A1, A2, A9)

### 2.1 One file per prompt

Every model prompt lives in `backend/src/sro/domain/prompts/` as a `Prompt` record: `name`, `version`, `model`, `thinking`, `role`, `task`, `input_contract`, `output_schema`, `rules`, and 3-5 `edge_cases` drawn from real data (redacted). The Gemini adapters build their request from the record; no prompt text lives in an adapter.

Rules every prompt follows:
- **Untrusted input is fenced.** Mail, page text, outlines and snapshots sit inside a marked quoted block, and the rules say that nothing inside it is an instruction.
- **Code validates every answer.** It checks the schema, checks every citation (a quoted value must occur in the input), and checks that every value comes from the allowed input. An answer that fails validation counts as "unsure", never as an answer.
- **Minimal context.** The prompt gets the candidate jobs rather than every job, and the relevant outline region rather than the whole page.

### 2.2 The harness

`backend/evals/` holds the runner (in git) and the cases and results (gitignored: they hold operator data). Three suites build their cases from the local database:

| Suite | Case | Expected |
| --- | --- | --- |
| Mining | A job's cited gestures plus neighbouring noise | One proposed job covering at least 80% of the cites |
| Request reader | A real request mail behind a job (that mail excluded from any examples) | The job, whether the reader is sure, and each value's field |
| Repair | A proven step with its recorded locator broken on purpose | The control that actually held |

Metrics per suite: accuracy, sure-but-wrong rate, cost per case, and latency p50/p95. A prompt change merges only if accuracy holds or improves, sure-but-wrong does not rise, and cost does not rise. `make eval` writes the report; `make eval-ci` runs the committed redacted set.

The repair suite measures the sight lane's model and the UI lane's repair. Neither may write (runtime rule), so a case passes only if the proposed control is the one that held and nothing was acted on.

## 3. The compile check (A4, A5)

`compile(job) -> Compiled(runnable: bool, reasons: list[Reason], view: dict)` is a pure function over what the runtime already loads. A job is runnable only if:
- every required parameter is bound to a step, directly or through an alias;
- every write step has a proof: a recorded call with an expected status, plus a read-back where one is known;
- every UI step has at least one locator, recorded or learned;
- every step's tab role resolves (§5);
- no step is in the known-broken list for its current cites on every lane.

A job that does not compile is not offered to requests, and the reasons show in the console. `make recipe job=<id>` prints `view` as YAML for reading. It is not an import format (L1).

**Optional fields (A5).** Each optional field gets a class from its evidence: *always* (filled in every doing), *sometimes*, or *never*. Each field also gets limits taken from the page: maximum length, allowed options (the outline's option list when it is small), and whether it is required on screen. The request reader uses the limits to reject a value that cannot fit. The panel's offering of optional fields is design 3's.

## 4. Agents

### 4.1 Request reader (A6)

Input: the top-K candidate jobs, ranked in code by title and parameter overlap with the request; duplicate titles are hidden behind the canonical job. It also gets the whole mail thread, the open question if one is standing, and each candidate's parameters with their aliases and outline field labels.

Output: `{job, sure: bool, values: [{field, value, quote}]}`.

Code validates the output:
- `field` must be one of the candidate's parameters, aliases or outline labels;
- `quote` must occur in the thread, and `value` must be taken from it;
- a value that breaks the field's limits (§3) is dropped and asked for.

A reply in a thread with a standing question is read as an answer to that question, never as a new request.

### 4.2 Wording to fields (L3)

When the reader is not sure which field a value belongs to, it returns the value unattached, and the run asks the operator with the candidate fields as choices (runtime X10's `field` question). The operator's answer is saved as an alias on that job: `(wording, field, confirmed_by, at)`. The next request that uses the same wording binds it without asking. Aliases are per job, never global. A confirmed alias outranks the model's guess.

### 4.3 Miner (A7)

- Fence page text as untrusted.
- Remove schema fields no code reads. Before removing each field, grep for its readers. `workflow.same_as` is stored (`infrastructure/db/workflows.py:52`); find out whether anything reads it. The gesture-reading `continues` column (`infrastructure/db/models.py:528`) is a different field from the request intent's `continues`, which is read (`application/intent/resolve.py:102`) and stays.
- Resolve the "say which values appear in two systems" sentence: either remove it, or add a schema field that code reads.

### 4.4 Mail agent (A8)

`write_the_mail` (`application/execution/mail_job.py:46`) gets a prompt record. Code checks the draft before the tool lane sends it:
- every value in the body is cited to a message in the thread;
- recipients are the thread's participants, plus the addresses the job's own recorded evidence sent to when it was demonstrated (decided 2026-09-25); any other address asks. An address the mail's text names is never enough, because mail text is untrusted;
- the body carries no value that is absent from the thread or from the run's results.

A draft that fails is not sent: the run asks.

## 5. Tab roles (A3, L4)

**Learning.** Code gives each step a tab role from its cited gestures' `tab_id` and the popup opener that A0 stores (`opener_tab_id`, `domain/observation/gesture.py:133`). The first tab is `main`. A tab opened by a click is `opened_from:<role>`. A second tab the operator opened on the same system is `tab_2`, and so on. The role is stored on the step, and the mining evidence shows it, so a two-tab doing reads as one job.

**Running.** A run holds one lease (one browser context) and a map from role to tab.
- A step whose role has no tab yet opens one. For `opened_from`, it acts in the opener and waits for the new tab whose opener is the current tab.
- Each step acts in its role's tab and records that tab on its progress mark, so a resumed run returns to the right tab.
- `release` closes every tab of the run.
- Nothing about the own-call rule changes: a call counts only if it comes from the tab and frame that acted.

## 6. A learned key in the replay template

When runtime X10 has learned a new field's body key, and the write that carried it was confirmed by its own call, the key becomes a slot in the API lane's body template for that step: `{..., "<key>": "{<field>}"}`. From then on a write that follows the field can go through the API lane. Until a key is learned this way, X10 keeps the API lane closed for that write, as it does today. A slot is removed when the known-broken list records the API lane for the step's current cites.

## 7. Out of scope

- **Design 3:** the panel's offering of optional fields, drawing a `field` question, the per-job report, and "checked N s ago".
- **Dropped by L1:** stored, versioned recipes and YAML import.
- **Not planned:** a global synonym table (L3 keeps aliases per job).

## 8. Build order

1. Prompt records (A1), then the eval harness with the redacted CI set (A2). Every later prompt change runs through it.
2. The compile check and optional-field classes (A4, A5).
3. Request reader and wording-to-fields aliases (A6, L3).
4. Tab roles, learned and run (A3, L4).
5. Miner fixes (A7) and mail agent guards (A8).
6. Learned key in the replay template (§6).
7. Repair suite (A9), measured against the runtime's sight lane.
