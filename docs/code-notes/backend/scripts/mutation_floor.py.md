# Notes for `backend/scripts/mutation_floor.py`

Comments and docstrings moved out of [`backend/scripts/mutation_floor.py`](../../../../backend/scripts/mutation_floor.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/mutation_floor.py#L1): Docstring

> The mutation score per area, against each area's floor.
>
>     uv run mutmut run
>     uv run mutmut export-cicd-stats
>     uv run python scripts/mutation_floor.py
>
> A passing suite says the code does what the tests say. A mutation score says
> whether the tests would notice if it stopped.
>
> **Two areas, two floors, one sweep.** `sro/application/skill/` is the bridge:
> it turns a model's reading of a captured day into a Skill the runner executes,
> parsing untrusted JSON out of a column at every step. `sro/domain/execution/`
> is the ladder: what counts as a write, what counts as proof that one landed,
> what a job has to do before it may write unattended. A surviving mutant in the
> bridge is a field that silently vanishes; a surviving mutant in the ladder is a
> safety rule nothing would notice losing.
>
> They are scored apart because one number over both hides the one that matters.
> The bridge has twice the mutants, so a ladder that fell ten points would move a
> combined score by three -- inside the noise a person would shrug at.
>
> Widening this to `src/sro/` would mutate 297 files. That is a different tool
> with a different cost; this one has to stay cheap enough to run while a change
> is still in the working tree.
>
> Each floor is a ratchet, not a target. It is set just under the measured
> baseline, so the number can only go up: a change that leaves more mutants alive
> than the last measurement fails here, and raising a floor after genuinely
> improving the suite is a deliberate edit to the table below.
>
> Do NOT lower one to make a build pass. If the score dropped, the tests got
> weaker -- that is the finding, not the obstacle.

## module, [line 17](../../../../backend/scripts/mutation_floor.py#L17): Note on the line above

Code: `RESULT = re.compile(r"^\s+(?P<name>\S+): (?P<status>.+)$")`

> One line of `mutmut results`: an indented dotted name, a colon, a verdict.

## `_results`, [line 20](../../../../backend/scripts/mutation_floor.py#L20): Docstring

> Every mutant and its verdict, from mutmut itself.
>
> The exported CI/CD stats are one total over the whole sweep and cannot be
> split by area, and the cache they come from is mutmut's own format. Asking
> the tool is cheaper than reading its cache and cannot drift from it.

## module, [line 8](../../../../backend/scripts/mutation_floor.py#L8): Comment

Code: `FLOORS = {`

> Measured 2026-09-05 over the then 1,489-test unit suite: 1,622 mutants, 1,371
> killed, 251 survived, 58 with no test covering them. **84.5%**.
>
> The first sweep of the four bridge modules read far worse -- `from_rig` 57.8%,
> `network_from_rig` 63.3% -- and almost every survivor was a JSON key spelled
> in the wrong case. Unlike SQL keywords or `sqlite3.Row` keys, a Python dict is
> case-sensitive, so `component.get("ITEMID")` returns None and the field simply
> vanishes into a perfectly valid object built around the hole. `fingerprint_for`
> assembles eight signals a driver finds a control by, `_component` seven more
> and `request_from_rig` about fifteen, and not one of them was asserted end to
> end. Field-by-field round trips took those two to 90.0% and 86.3%.
>
>     from_rig             90.0%      network_from_rig     86.3%
>     repair_drift         87.3%      adopt_rig_workflow   86.1%
>     map_step_to_tool     82.0%      read_doings          81.6%
>     version_from_rig     80.5%      read_skills          78.6%
>     add_assertion        75.7%      promote_skill        69.6%
>
> Re-measured 2026-09-13 over the 2,895-test unit suite: 2,294 mutants, 1,943
> killed, 293 survived. The bridge read **85.8%** unchanged by any work here --
> the floor rises to just under it, which is what a ratchet is for.
>
> Re-measured 2026-09-24 after the bridge (`from_rig`, `network_from_rig`,
> `version_from_rig`, `adopt_rig_workflow`) and `map_step_to_tool`,
> `read_doings`, `add_assertion`, `promote_skill` were removed with no
> production caller. What `sro.application.skill` holds now -- `counsel`,
> `describe_skill`, `read_skills`, `read_workflows`, `record_offer`,
> `repair_drift`, `retire_workflow`, `serve_shapes` -- read 555 mutants, 489
> killed, 53 survived, 13 unreached: **90.2%**. The floor is 90.0, just under
> it, so one mutant flipping (a timeout, a harmless test change) does not fail
> the build.
>
> The ladder's first sweep, the same day, read **83.9%** with two modules far
> under it: `diagnosis` 49.2% and `safety` 60.6%. Both were the same kind of
> hole. Every `safety` boundary was a number nothing stood on -- `>` for `>=`
> on both caps, `<=` for `<` on both windows -- and `diagnosis` never asserted
> `safe_for_writes` on three of its five branches, which is the one field that
> module's own docstring calls non-negotiable. Tests on each of those, plus the
> three judge/apply_verdict branches nothing looked at, took the area to
> **91.8%**:
>
>     belts                98.7%      evidence             97.1%
>     verdict              94.3%      verified_writes      89.4%
>     safety               81.8%      diagnosis            77.0%
>     workflow_run         75.0%      planning/escalation 100.0%
>
> What is left in `safety` and `diagnosis` is almost entirely the reason TEXT
> -- a sweep upper-cases a sentence and nothing notices. Asserting prose
> verbatim would buy the number and not the safety, so those survive on
> purpose.

## module, [line 11](../../../../backend/scripts/mutation_floor.py#L11): Comment

Code: `"sro.application.execution": (92.8, "the step -- what this run sends, and what settles it"),`

> `plan_step` and `verify` only, not the 7,184-line package around them.
> These two are the ladder's other half: the rules say what may be sent and
> what counts as proof, and these two decide it for one real step in front
> of a real browser.
>
> First sweep 2026-09-13: **86.8%**, and two holes worth the whole exercise.
> `plan_step` 86.0% -- the two-click pick added that same day had no
> planner test at all, so `opened`'s default could flip, `opens` could stop
> being set, and the click payload's `allow_focus` and `starts_on` could be
> dropped. `verify` 88.2% -- `check` and `check_text` were reached only
> through `execute_skill`, where one status assertion stood in for all four
> kinds, and inverting `RESPONSE_FIELD_PRESENT` in both left the suite
> green. Tests on each took the area to **93.0%** (plan_step 92.0,
> verify 94.7).
>
> `verify`'s RIG half needed nothing: eleven survivors, every one reason
> text or JSON indentation. That is the half that gates a live write.

## module, [line 12](../../../../backend/scripts/mutation_floor.py#L12): Comment

Code: `"sro.domain.skill.shape": (99.8, "the offer -- which jobs a browser is shown, and where"),`

> The offer side of the wire, added the day it was found serving a shape
> the matcher could never match. First sweep 2026-09-14: **96.2%**, and all
> five survivors were in that morning's own dropdown-pick code -- `seen &
> put_by(gesture)` read as a union, and `put_by`'s three-way `and` read as
> `or`, both of them the rule that stops a button label becoming somebody's
> parameter value. **100.0%** with those pinned.
>
> And the caution this whole table needs: `shape.py` scored 96.2% while
> shipping an off-by-one that made every two-step job unofferable. A
> mutation score cannot see a rule that is wrong the same way on both
> sides of a wire -- the code said `< K_OFFER_AFTER`, fifteen fixtures
> agreed with it, and only a real browser disagreed.

## `_results`, [line 22](../../../../backend/scripts/mutation_floor.py#L22): Comment

Code: `[sys.executable, "-m", "mutmut", "results", "--all", "true"],`

> `--all true`, and the value is not optional: mutmut's flag is an
> ordinary option with a default, so a bare `--all` swallows the next
> word. Without it the listing is survivors only, every area reads 0%,
> and the floor fails over a suite that got stronger.

## `main`, [line 53](../../../../backend/scripts/mutation_floor.py#L53): Comment

Code: `considered = killed + survived`

> Killed over killed-plus-survived, so a mutant nothing could reach --
> skipped, timed out, no test covers the line -- neither flatters the
> score nor is silently counted as a pass.

## `main`, [line 70](../../../../backend/scripts/mutation_floor.py#L70): Comment

Code: `print(f"FAILED: {len(results) - named} mutants are in no scored area")`

> A source path mutmut was pointed at that this table does not score.
> Silent, it would read as a passing sweep over code nobody measured.
