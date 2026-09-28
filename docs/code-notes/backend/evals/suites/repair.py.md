# Notes for `backend/evals/suites/repair.py`

The repair suite (spec §2.2 "Repair", §8 step 7, A9): the sight model and the
UI lane's repair, each asked to find a proven step's control again once its
recorded locator is broken on purpose, on a live page nothing acts on.

## `Repair`, [line 61](../../../../../backend/evals/suites/repair.py#L61): Design

> **Why a live page.** A case must show which control actually held. UI
> repair runs in page code against a DOM, and no DOM is stored (E6 replaced
> tree capture). Recorded `bounds` are document coordinates in the element's
> own frame, so a stored screenshot cannot score a sight point either. Each
> case opens the step's recorded `page_url` on local Steel, in the account's
> own lease (`SessionBroker.account_for`, `acquire`, `release` — the release
> runs whatever the page did), and uses only `resolve`, `screenshot` and
> `hit_test`.
>
> **Nothing acts.** The runtime rule is "Repair never writes". `resolve`
> finds a control and returns it; `hit_test` names the element under a point
> and pins it; `screenshot` reads pixels. None of them clicks, types or sends
> anything, so a case can be run against a signed-in account's real page.
> The suite never calls `act` or `point`.
>
> **The asker is unused.** The sight model is the `VisionDriver` the
> container builds for the sight lane (`SIGHT`), so `asker` returns an inert
> `Replayed(None)` and `run_suite` does not demand `interpretation_enabled`
> for a suite that asks nothing. `repair-sight` needs `vision_enabled` and
> the Gemini key; `repair-ui` needs no model.
>
> **Cost is `0.0`.** `VisionDriver` does not report cost; the metered client
> books it to `model_spend`. The gate compares accuracy and sure-but-wrong
> for the repair suites.

## `Repair.cases`, [line 79](../../../../../backend/evals/suites/repair.py#L79): Design

> One case per step of a job with a held run (`workflows.proofs`), whose
> primary gesture recorded a target with an `xpath` and a `page_url`. The
> payload is `ui_payload`'s — the one the UI lane sends — and the goal is
> `sight_goal`'s, the one the sight lane gives the model. `repair-ui` skips a
> writing step: page code never repairs a write (`payload.write === false`
> is required), so such a case could only fail.
>
> Ceiling: a page reached only through earlier steps (a dialog, a row opened
> from a search) is never measured, because the case opens `page_url` cold
> and the recorded control is not there — it is counted unreachable.
> Upgrade: replay the job's reads up to the step on the eval lease.

## `Repair._scored`, [line 119](../../../../../backend/evals/suites/repair.py#L119): Design

> First the recorded payload is resolved with its `write` flag removed, so
> page code cannot repair it: the page must show exactly one control by the
> recorded locators, and that control's `xpath` is the truth. Anything else
> is **unreachable**: `Scored(passed=False, sure=False, latency_s=-1)`,
> counted in the report's `unreachable` and left out of every rate
> (`evals.run.reachable`). A high count means the recorded pages are not
> reachable by URL, not that repair failed.
>
> Pass rules. `ui`: `resolve` of the `broken` payload answered one control
> whose `xpath` is the recorded control's; `matched_by` is kept in the
> case's answer. For the `repair` break a control found by any strategy but
> `repair` is unreachable, not failed: the kept chain is itself a locator
> when longer than one, and the page then never reaches repair. For the
> `restructured` and `relabelled` breaks any strategy counts: the lane
> landing on the right control is what the runtime needs, and landing on
> another is the sure-but-wrong it must never do. `sight`: the model's
> point, hit-tested and resolved back through the
> hit's own `{strategy, query}` and frame path (the way the sight lane learns
> a locator), is that same control. `sure` is "the lane named a control at
> all": a model with no point, or a repair that found nothing, is unsure.

## `broken`, [line 28](../../../../../backend/evals/suites/repair.py#L28): Design

> Breaks the recorded target three ways (user ruling 2026-09-28). A kept
> direct locator finds the control before anything else runs, so each break
> drops exactly what its change would make stale:
>
> - `restructured` — a new build: `css_path`, `xpath`, `test_id`, the whole
>   `component` and the `id` attribute go; the label (`name`, `text`) and
>   the `name`/`autocomplete` attributes stay.
> - `relabelled` — a new label: `name` is renamed and `text` goes; the
>   structure stays.
> - `repair` — only what `repair`'s score reads and no locator can use:
>   `name`, `text`, the selectors, the component's query and item id, and
>   the `id`/`name`/`autocomplete` attributes go; the chain (+2), bounds
>   (+1) and `placeholder` (+1) stay, so a control can reach
>   `REPAIR_THRESHOLD` (3). The first break alone left at most 2.
