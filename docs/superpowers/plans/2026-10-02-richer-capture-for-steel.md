# Richer Demonstration Capture for Steel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The extension records more of what a person saw while doing a job once (what changed after each action, where they were, richer element identity, readiness timing, sign-in cookie names, dialogs, required fields, combo options, app version, and — opt-in — the mail thread a job came from), and Steel runs read it in shadow beside today's verdicts, so the four measured failure classes (unconfirmed write, sign-in, control/page not found, duplicates) and wrong resumes can be cut one promoted check at a time.

**Architecture:** Additions only. Every new datum is an optional field with a default on the wire (`rig_wire`), on the domain (`Action`/`Target`/`PageMark`) and in the JSONB `gestures.gesture` column, so old rows load unchanged and no migration touches `gestures`. A new `effect` event kind carries "what changed after the action" and is joined to its gesture by `ref` in-batch and by `(stream, tab, frame_path, at)` across batches. Steel consumers are lane-level `StepResult` notes (`shadow:<check>:<verdict>`) written into `workflow_run_steps.notes`; each runs only for tenants named in `steel_shadow_checks[<check>]` and changes behaviour only for tenants named in `steel_promoted_checks[<check>]`, both empty by default.

**Tech Stack:** Python 3.12 (FastAPI, pydantic v2, SQLAlchemy async, Temporal, Playwright over CDP to Steel), `uv`; Chrome MV3 extension in plain ES modules tested with `node --test`; page code in `new-chrome-extension/src/page/page-code.js` (injected by Steel runs, and its `readers` block spliced into the recorder by `make gen-recorder`).

**Spec:** `docs/superpowers/specs/2026-10-02-richer-capture-for-steel-design.md` (binding; its "binding rule: additions only" and "Owner decisions" sections override anything in this plan).

## Global Constraints

Every task's requirements include all of these.

- **Additions only**: nothing is removed or behaves differently; every gesture field captured today stays with the same meaning and values; old recordings (every job learned before this ships) run exactly as today.
- **New data never feeds identity/shape keys** (`targetIdentity`, `screenOf`, shape keys, `domain/observation/identity.py`, `application/capture/identity.py`): the golden fixtures `new-chrome-extension/fixtures/shape-identity.json` and `new-chrome-extension/fixtures/screen-of.json` stay **byte-identical** (`git diff --exit-code` on both after every `make gen-recorder` / `make fixtures`).
- **Every Steel consumer starts in shadow behind a per-tenant flag defaulting empty** (`steel_shadow_checks`, `steel_promoted_checks`, both `{}`), and a promoted consumer may only **turn unknown into confirmed, add waits, or add locators tried after all of today's** (or add an ask that would otherwise not happen). The two stopping promotions (`C2-stop`, `C9-stop`) are built in shadow only and need their own owner yes.
- **No data is removed** (retention/deletion unchanged), so every new field is safe to keep forever: **no field values, no cookie values, no mail text, capped text through `outline._said`** (exposed as `outline.said_text`; capped at 120 characters, inside the spec's 200).
- **Generated files only via `make gen-recorder`** (`recorder.generated.js`, `sensitivity.generated.js`, `sensitivity.module.js`, `background/shape.generated.js`, the `SECRET_WORDS` line in `page-code.js`). Never hand-edit them.
- **Backend ships before the extension**: Tasks 2–4 are merged and deployed (API **and** worker restarted) before any extension build from Tasks 5–7 is packaged; an old extension keeps working against the new server (all new fields optional).
- **The `redact.py` whitelist trap**: a new top-level gesture key is silently dropped unless it is declared on `rig_wire.Gesture` first; a new event kind is passed through unexamined unless it is in `redact._EVENT_KEYS`; a new event kind is refused unless it is in `admit.KINDS`. Every new key is declared on `rig_wire` before the extension sends it, and Task 3 pins this with a test.
- **No LLM in `domain/` or in a Temporal workflow body.** Every consumer is pure domain arithmetic plus page reads inside activities.
- **ADR** for the architecture decision: `docs/07-adr/016-richer-capture-is-additions-only.md` (Task 2).
- **Backend source carries no comments or docstrings** (except `interface/http/` and pydantic schema classes, and tool directives). The why goes in `docs/code-notes/<source path>.md` under a heading naming the function/class and line. `page-code.js` follows the same rule (its notes file exists). Migrations keep their docstring header as the existing ones do.
- **Mail hosts stay excluded**: nothing on a mail page is captured, screenshotted or uploaded; only the thread id visible in the mail tab's URL is noted, only for a tenant whose policy has `note_mail_thread` on (Owner decision 2).
- **Cookies**: names and expiry only, behind the `cookies` permission declared in `optional_permissions` and requested at runtime from the options page; a tenant/browser that declines gets everything else.
- Never `git add -A` / `git add .`; never touch untracked files in the main checkout (`designof-panel/`, `docs/21-*`, `extra-work/`). Every commit message ends with these two lines (Tasks 5–17 show only the subject line; add them):
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01RNYbCzVj7p76GmLhf2MBKL`
- Merge to `main` only on the owner's explicit "merge"; no deploys or SSH by an agent unless the owner hands over QA access for that step.
- A code change is not live until the **worker** restarts (runs, mining and sweeps run there).
- A wire type change is not finished until `make types` has run and its output (`frontend/openapi.json`, `frontend/src/lib/api/generated.ts`) is committed when it changed.

## Review Focus

The five input classes the spec implies that no task's happy-path tests exercise, most likely to bite first. Each has a pinned test in the owning task.

1. **A gesture's effect arrives in the next minute's batch** (the action was the last thing before a flush — typically the Save). Expected: the effect still lands on the stored gesture, never on a different one, and never overwrites an effect already there. Pinned: Task 4 `test_an_effect_in_the_next_batch_lands_on_the_stored_gesture` and `test_an_effect_matching_two_stored_gestures_lands_on_neither`.
2. **A toast or dialog that repeats a typed value or a token** ("Saved customer ABC", "Session 3f9a…e1 expired"). Expected: the value is compared as a parameter, never stored beyond `said_text`'s rules; anything shaped like a token is dropped, not stored. Pinned: Task 2 `test_effect_text_shaped_like_a_token_is_dropped` and Task 9 `test_a_toast_naming_the_run_s_own_value_confirms`.
3. **An old recording run with every shadow check switched on** (no `effect`, no `place`, no cookies). Expected: identical verdicts and reasons to today, and notes that say `n/a`, never an exception. Pinned: Task 14 `test_a_recording_without_new_data_runs_as_today_with_every_check_shadowed` (every `ui_lane` check) and Task 9 `test_an_old_recording_with_c1_c4_c6_shadowed_says_n_a_and_acts_as_today`.
4. **The extension running in a tenant that declined the `cookies` permission, or with `note_mail_thread` off.** Expected: no `cookies_set` / `mail_ref` page events at all, everything else captured. Pinned: Task 7 `cookie marks need the permission` and Task 15 `no mail ref without the tenant's yes`.
5. **A promoted consumer meeting a page that disagrees with the recording** (different toast wording, renamed tab, different option order). Expected: today's verdict stands (unknown stays unknown, today's locators still run first); a promotion never turns today's pass into a failure. Pinned: Task 9 `test_a_promoted_c1_never_turns_a_failed_or_done_write_around`, Task 11 `test_more_locators_are_tried_only_after_today_s_fail`.

## File structure (decided before the tasks)

| File | Responsibility | Tasks |
|---|---|---|
| `backend/scripts/measure.py` | Failure-class baseline and shadow-agreement report | 1, 17 |
| `backend/src/sro/domain/observation/gesture.py` | New optional dataclasses and fields | 2 |
| `backend/src/sro/domain/observation/outline.py` | Public `said_text` (the `_said` rule) | 2 |
| `backend/src/sro/domain/observation/seen.py` (new) | Server-side sanitising + decoding of every new datum (`*_kept`, `*_from`) | 2 |
| `backend/src/sro/application/capture/rig_wire.py` | Wire declarations (the whitelist) | 3 |
| `backend/src/sro/application/observation/admit.py` | `effect` kind admitted under the URL policy | 3 |
| `backend/src/sro/application/observation/redact.py` | New keys redacted through `seen.py` | 3 |
| `backend/src/sro/application/observation/correlate.py` | Mapping + effect join | 4 |
| `backend/src/sro/application/observation/ingest.py` | Cross-batch effect attach | 4 |
| `backend/src/sro/application/ports/repositories.py`, `infrastructure/db/evidence.py`, `tests/unit/fakes.py` | `GestureRepository.attach_effect` | 4 |
| `new-chrome-extension/src/page/page-code.js` | Readers (`placeOf`, `fullNameOf`, `siblingOf`, `choiceOf`, `versionOf`, `watchEffect`) and `sroPage.look` | 5, 6, 8, 9, 11 |
| `backend/src/sro/infrastructure/steel/recorder.js` | Attach place/choice/extras; emit effects | 5, 6 |
| `new-chrome-extension/src/content/recorder-bridge.main.js`, `observe.js` | `__sroEffect` → `sro:effect` relay | 6 |
| `new-chrome-extension/src/background/page-marks.js` (new) | Pure builders: cookie marks, focus marks, mail thread from URL | 7, 15 |
| `new-chrome-extension/src/background/service-worker.js` | Effect enqueue; cookie/focus/mail-ref listeners | 6, 7, 15 |
| `new-chrome-extension/manifest.json`, `src/options/*` | `optional_permissions: ["cookies"]`, runtime request | 7 |
| `backend/src/sro/domain/execution/checks.py` (new) | Check names, `Checks`, `CheckFlags`, notes, promotion gate | 8, 17 |
| `backend/src/sro/domain/execution/lanes.py` | `StepResult.notes` | 8 |
| `backend/src/sro/application/runtime/step.py` | `LaneContext.checks` | 8 |
| `backend/src/sro/application/ports/page.py`, `infrastructure/steel/driver.py` | `PageDriver.look`, `PageDriver.clear_cookies` | 8, 12 |
| `backend/src/sro/application/runtime/run_steps.py` | Notes onto `RunStep`; C2, C8, C9 hooks | 8, 10, 13, 16 |
| `backend/src/sro/application/runtime/ui_lane.py` | C1/C4/C6, C3/C10, C5 dialog, C11 hooks | 9, 11, 12, 14 |
| `backend/src/sro/domain/execution/effects.py` (new) | C1/C4/C6 arithmetic | 9 |
| `backend/src/sro/domain/execution/place.py` (new) | C2 arithmetic | 10 |
| `backend/src/sro/domain/execution/staying_in.py` (new) | C5 arithmetic | 12 |
| `backend/src/sro/domain/skill/proven.py` (new) | C8 arithmetic | 13 |
| `backend/src/sro/domain/execution/existence.py` (new), `application/lookup/answer.py`, `application/runtime/existence_check.py` (new) | C9 | 16 |
| `backend/src/sro/domain/observation/policy.py`, `interface/http/schemas.py`, `cli/observe.py` | `note_mail_thread` opt-in | 15 |
| `backend/src/sro/domain/execution/mail_pairing.py` (new), `application/observation/pair_mail.py` (new), `mail_pairings` table | C7 mining notes | 15 |
| `docs/07-adr/016-richer-capture-is-additions-only.md` (new) | The decision | 2 |

## Task conflict scan (for the executor)

Tasks run **in order**. These share files or interfaces and must not run in parallel:

- **Tasks 2 → 3 → 4** chain on the same names: domain dataclasses (2) are what `seen.py` builds (2), what `rig_wire` declares (3) and what `correlate` maps (4). Run strictly in order.
- **`tests/unit/fakes.py`**: Tasks 4 (`FakeGestureRepository.attach_effect`), 8 (`FakePageDriver.look`), 12 (`FakePageDriver.clear_cookies`), 15 (`FakeMailPairingRepository`, `FakeUnitOfWork.mail_pairings`). Different classes, same file — sequential; resolve any conflict hunk by hunk.
- **`page-code.js`**: Tasks 5, 6 (readers), 8, 9, 11 (`sroPage.look` asks). Tasks 5 and 6 both end in `make gen-recorder`; regenerate again after rebasing either. Tasks 8/9/11 each add one `ask` branch to `look` — keep each branch in its own `if`.
- **`recorder.js`**: Tasks 5, 6. **`service-worker.js`**: Tasks 6, 7, 15 (each adds its own `case`/listener).
- **`ui_lane.py`**: Tasks 9, 11, 12, 14. Each adds a separate private method and one call site; Task 9 restructures `_perform` (adds `watching`, `effect`, the `waited` deadline) and the later tasks build on Task 9's version.
- **`run_steps.py`**: Tasks 8 (notes onto `RunStep` in `_advance`/`_ask`, `_lane_context`), 10 (C2 before `executor.run`), 13 (C8 at the `required` check), 16 (C9 before a create). Each adds a `_shadow_*` method; the shared seam is the `pre` notes list Task 8 introduces in `step()`.
- **`tests/integration/test_runs_on_local_steel.py`**: Tasks 9–14, 16 append one test each; append at the end of the file.
- **`backend/scripts/measure.py`** and its code-notes: Tasks 1 and 17.
- **`config.py`/`container.py`**: Tasks 8 (check flags into `RunSteps`), 15 (`PairMail` into `MineLately`).
- **Migration numbering** (Task 15 only): take the next free revision at execution time (`ls backend/migrations/versions | tail -1`); other branches (e.g. `feat/channels-through-brain`) may have claimed `0093` by then.
- **Deploy gate**: Tasks 2–4 deployed before Tasks 5–7 are packaged; Task 8's `sroPage.look` ships with the backend (Steel reads `page-code.js` from the repo via `page_code_path`), so it needs no extension release.

---

## Phase 1 — Baseline

### Task 1: Failure-class baseline in `measure.py`

**Files:**
- Modify: `backend/scripts/measure.py` (new `class_of`, new section `failure_classes`, called from `_measure`)
- Test: `backend/tests/unit/scripts/test_failure_classes.py` (new)
- Modify: `docs/code-notes/backend/scripts/measure.py.md`
- Create: `docs/measurements/2026-10-02-capture-baseline.json` (output of the QA run)

**Interfaces:**
- Consumes: nothing new.
- Produces: `class_of(verdict: str, reason: str) -> str` returning one of `CLASSES = ("unconfirmed_write", "sign_in", "not_found", "duplicate", "timing", "wrong_resume", "other")`; `async def failure_classes(db: AsyncConnection, tenant: str | None, *, days: int = 30) -> Section`. Task 17 reuses `class_of` and `Section`/`Line`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/scripts/test_failure_classes.py
import pytest

from scripts.measure import CLASSES, class_of


@pytest.mark.parametrize(
    ("verdict", "reason", "expected"),
    [
        ("unclear", "'Save' was sent and nothing confirms it; check it and answer", "unconfirmed_write"),
        ("failed", "sign-in failed: TimeoutError", "sign_in"),
        ("failed", "the page asked for a password nobody gave", "sign_in"),
        ("failed", "control_not_found", "not_found"),
        ("failed", "the recorded frame is no longer on the page", "not_found"),
        ("failed", "no recorded control to act on", "not_found"),
        ("failed", "the system rejected the write: already exists", "duplicate"),
        ("failed", "the page did not settle", "timing"),
        ("unclear", "sent by an earlier attempt, never settled", "wrong_resume"),
        ("failed", "the operator says it was not done; it is tried again", "wrong_resume"),
        ("failed", "something nobody classified", "other"),
    ],
)
def test_a_step_s_reason_names_its_failure_class(verdict: str, reason: str, expected: str) -> None:
    assert class_of(verdict, reason) == expected


def test_a_held_step_has_no_failure_class() -> None:
    assert class_of("held", "") == ""


def test_every_class_the_spec_names_is_counted() -> None:
    assert set(CLASSES) >= {
        "unconfirmed_write", "sign_in", "not_found", "duplicate", "timing", "wrong_resume"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/scripts/test_failure_classes.py -q`
Expected: FAIL with `ImportError: cannot import name 'CLASSES' from 'scripts.measure'`

- [ ] **Step 3: Write minimal implementation**

Add near the top of `backend/scripts/measure.py`, after `LOCAL_HOSTS`:

```python
CLASSES = (
    "unconfirmed_write",
    "sign_in",
    "not_found",
    "duplicate",
    "timing",
    "wrong_resume",
    "other",
)

_CLASS_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("unconfirmed_write", ("nothing confirms it", "outcome was lost", "never confirmed")),
    ("wrong_resume", ("earlier attempt, never settled", "operator says it was not done")),
    ("sign_in", ("sign-in", "signed out", "sign in", "password", "still a sign-in page")),
    ("duplicate", ("already exists", "duplicate", "already there")),
    ("not_found", ("control_not_found", "frame_not_found", "frame_ambiguous",
                   "no longer on the page", "no recorded control", "no field", "no option")),
    ("timing", ("did not settle", "timed out", "timeout")),
)


def class_of(verdict: str, reason: str) -> str:
    if verdict in ("held", "withheld", "skipped", "not_needed"):
        return ""
    said = reason.lower()
    return next(
        (name for name, words in _CLASS_WORDS if any(word in said for word in words)), "other"
    )
```

Add the section (beside `running`):

```python
async def failure_classes(db: AsyncConnection, tenant: str | None, *, days: int = 30) -> Section:
    into = Section(
        "3b. Failure classes",
        f"Steps that did not hold in the last {days} days, by the class the capture spec targets."
        " Re-derived from workflow_run_steps, never assumed.",
    )
    rows = await _rows(
        db,
        "select s.verdict, s.reason from workflow_run_steps s join workflow_runs r on r.id = s.run_id"
        f" where r.started_at >= now() - make_interval(days => :days) and {MINE.replace('tenant_id', 'r.tenant_id')}",
        tenant=tenant,
        days=days,
    )
    counted: Counter[str] = Counter(
        named for verdict, reason in rows if (named := class_of(verdict or "", reason or ""))
    )
    for name in CLASSES:
        into.add(Line(f"steps in class {name}", counted[name], len(rows) or None, "recorded"))
    broken = await _rows(
        db,
        "select lane, count(*) from known_broken where at >= now() - make_interval(days => :days)"
        f" and {MINE} group by lane",
        tenant=tenant,
        days=days,
    )
    for lane, number in sorted(broken):
        into.add(Line(f"known_broken fingerprints on lane {lane}", number, standing="recorded"))
    return into
```

In `_measure`, insert `await failure_classes(db, tenant),` right after `await running(db, tenant),`.

Add to `docs/code-notes/backend/scripts/measure.py.md` a heading `## \`class_of\`` explaining: the first matching class wins, in `_CLASS_WORDS` order; `wrong_resume` is checked before `sign_in` because a resumed step's reason names the earlier attempt; "other" is reviewed by a person, never re-bucketed silently; `known_broken` carries only digests, so it is counted per lane, not classed.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/scripts/test_failure_classes.py -q && uv run ruff check scripts/measure.py && uv run mypy scripts/measure.py`
Expected: PASS, no lint or type errors.

- [ ] **Step 5: Take the baseline on QA**

Run against the QA database (the executor runs it where it has QA access; otherwise hand this exact command to the owner and wait):

```bash
cd backend && uv run python scripts/measure.py --tenant <qa-tenant> --json ../docs/measurements/2026-10-02-capture-baseline.json
```

Expected: section "3b. Failure classes" prints a count per class. Compare with the proposal's numbers (6 of 15 unconfirmed, 3, 3, 2) and write the real numbers, and the size of `other`, into the ADR in Task 2 ("Baseline" section). Do not assume the proposal's numbers anywhere.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/measure.py backend/tests/unit/scripts/test_failure_classes.py docs/code-notes/backend/scripts/measure.py.md docs/measurements/2026-10-02-capture-baseline.json
git commit -m "feat(measure): failure classes over the last 30 days, the capture baseline

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RNYbCzVj7p76GmLhf2MBKL"
```

---

## Phase 2 — Server accepts and stores (ships first)

### Task 2: Domain shapes, the server-side sanitiser, and the ADR

**Files:**
- Modify: `backend/src/sro/domain/observation/gesture.py` (new dataclasses; new defaulted fields on `Target`, `Action`, `PageMark`)
- Modify: `backend/src/sro/domain/observation/outline.py` (add `said_text`)
- Create: `backend/src/sro/domain/observation/seen.py`
- Test: `backend/tests/unit/domain/rig/test_seen.py` (new), `backend/tests/unit/domain/rig/test_identity.py` (add one test)
- Test: `backend/tests/unit/infrastructure/test_an_old_gesture_row_loads.py` (new)
- Modify: `backend/tests/unit/interface/test_workflows_route.py:~640-662` (the enumerated `Action` dump gains the new keys with `None`/empty)
- Create: `docs/07-adr/016-richer-capture-is-additions-only.md`
- Create: `docs/code-notes/backend/src/sro/domain/observation/seen.py.md`; Modify: `docs/code-notes/backend/src/sro/domain/observation/gesture.py.md`, `docs/code-notes/backend/src/sro/domain/observation/outline.py.md`

**Interfaces:**
- Consumes: `outline._said`, `outline.K_OUTLINE_TEXT`, `trim.path_shape`, `sensitivity.redact_url`, `sensitivity.redact_shapes`.
- Produces (exact names every later task uses):
  - `gesture.Place(route: str|None=None, title: str|None=None, headings: tuple[str,...]=(), tabs: tuple[str,...]=(), grid: str|None=None, landmarks: tuple[str,...]=(), version: str|None=None)`
  - `gesture.Seen(role: str, text: str|None=None, title: str|None=None, buttons: tuple[str,...]=())`
  - `gesture.FieldChange(label: str, change: str)` (`change` ∈ `FIELD_CHANGES`)
  - `gesture.Effect(appeared: tuple[Seen,...]=(), vanished: tuple[Seen,...]=(), route_before: str|None=None, route_after: str|None=None, fields: tuple[FieldChange,...]=(), requests_ms: int|None=None, mask_ms: int|None=None, quiet_ms: int|None=None, ended: str|None=None, errors: tuple[str,...]=(), shortcuts: tuple[str,...]=())`
  - `gesture.Choice(chosen: str|None=None, index: int|None=None, options: tuple[str,...]=())`
  - `gesture.CookieSeen(name: str, expires_at: float|None=None, domain: str|None=None, session: bool=False)`
  - `Target.label_text: str|None=None`, `Target.sibling_index: int|None=None`, `Target.sibling_count: int|None=None`, `Target.full_name: str|None=None`
  - `Action.place: Place|None=None`, `Action.effect: Effect|None=None`, `Action.choice: Choice|None=None`
  - `PageMark.cookies: tuple[CookieSeen,...]=()`, `PageMark.mail_thread: str|None=None`
  - `outline.said_text(raw: object) -> str | None`
  - `seen.place_kept(raw: object) -> dict[str, object] | None`, `seen.effect_kept(raw: object) -> dict[str, object] | None`, `seen.choice_kept(raw: object) -> dict[str, object] | None`, `seen.cookies_kept(raw: object) -> list[dict[str, object]]`, `seen.mail_thread_kept(raw: object) -> str | None`, `seen.extras_kept(target: Mapping[str, object]) -> dict[str, object]`
  - `seen.place_from(raw: object) -> Place | None`, `seen.effect_from(raw: object) -> Effect | None`, `seen.choice_from(raw: object) -> Choice | None`, `seen.cookies_from(raw: object) -> tuple[CookieSeen, ...]`
  - Constants in `seen.py`: `SEEN_ROLES`, `FIELD_CHANGES`, `ENDINGS`, `K_SEEN_ITEMS = 20`, `K_FIELD_CHANGES = 40`, `K_ERRORS = 10`, `K_SHORTCUTS = 10`, `K_CHOICE_OPTIONS = 50`, `K_PLACE_HEADINGS = 3`, `K_PLACE_ITEMS = 10`, `K_BUTTONS = 8`, `K_MS = 60_000`, `K_COOKIES = 40`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/rig/test_seen.py
from sro.domain.observation.gesture import Choice, CookieSeen, Effect, FieldChange, Place, Seen
from sro.domain.observation.seen import (
    K_SEEN_ITEMS,
    choice_from,
    cookies_from,
    effect_from,
    effect_kept,
    extras_kept,
    mail_thread_kept,
    place_from,
    place_kept,
)


def test_a_place_keeps_what_a_person_reads_and_shapes_the_route() -> None:
    raw = {
        "route": "/wms/customers/12345#!/edit/987654321",
        "title": "Customer Types",
        "headings": ["Customer Types", "Edit", "Details", "More"],
        "tabs": ["General"],
        "grid": "Customer Types",
        "landmarks": ["New Customer Type"],
        "version": "Ext 7.6.0",
    }
    assert place_from(raw) == Place(
        route="/wms/customers/{id}#!/edit/{id}",
        title="Customer Types",
        headings=("Customer Types", "Edit", "Details"),
        tabs=("General",),
        grid="Customer Types",
        landmarks=("New Customer Type",),
        version="Ext 7.6.0",
    )


def test_a_place_with_nothing_said_is_no_place() -> None:
    assert place_kept({"route": None, "headings": []}) is None
    assert place_kept("not a mapping") is None


def test_effect_text_shaped_like_a_token_is_dropped() -> None:
    kept = effect_kept(
        {
            "appeared": [
                {"role": "status", "text": "Session 3f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c expired"},
                {"role": "status", "text": "Customer type ABC saved"},
                {"role": "alert", "text": "see https://idp.example/login?code=xyz"},
            ]
        }
    )
    assert kept is not None
    assert kept["appeared"] == [
        {"role": "status", "text": "Customer type ABC saved", "title": None, "buttons": []}
    ]


def test_an_effect_keeps_roles_changes_and_timings_and_nothing_else() -> None:
    effect = effect_from(
        {
            "appeared": [
                {"role": "dialog", "title": "Delete?", "text": "Delete this row?", "buttons": ["Yes", "No"]},
                {"role": "banner", "text": "not a role we keep"},
            ],
            "vanished": [{"role": "mask"}],
            "route_before": "/a/1",
            "route_after": "/a/2",
            "fields": [{"label": "Code", "change": "invalid"}, {"label": "Code", "change": "exploded"}],
            "requests_ms": 830,
            "mask_ms": 1200.7,
            "quiet_ms": 999999,
            "ended": "quiet",
            "errors": ["TypeError: x is undefined at https://wms.example/app.js:1:2"],
            "shortcuts": ["ctrl+s", "ctrl+password"],
            "value": "anything typed",
        }
    )
    assert effect == Effect(
        appeared=(Seen("dialog", "Delete this row?", "Delete?", ("Yes", "No")),),
        vanished=(Seen("mask"),),
        route_before="/a/{id}",
        route_after="/a/{id}",
        fields=(FieldChange("Code", "invalid"),),
        requests_ms=830,
        mask_ms=1200,
        quiet_ms=60_000,
        ended="quiet",
        errors=("TypeError: x is undefined at «url»",),
        shortcuts=("ctrl+s",),
    )


def test_an_effect_is_capped() -> None:
    kept = effect_kept({"appeared": [{"role": "row", "text": f"row {n}"} for n in range(500)]})
    assert kept is not None and len(kept["appeared"]) == K_SEEN_ITEMS


def test_a_choice_keeps_option_labels_and_the_chosen_index() -> None:
    assert choice_from({"chosen": "Retail", "index": 2, "options": ["Bulk", "Pallet", "Retail"]}) == Choice(
        "Retail", 2, ("Bulk", "Pallet", "Retail")
    )
    assert choice_from({"index": "two"}) is None


def test_a_cookie_is_its_name_and_expiry_never_a_value() -> None:
    assert cookies_from(
        [
            {"name": "JSESSIONID", "expires_at": 1_790_000_000.5, "domain": "wms.example", "session": False, "value": "abc"},
            {"name": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig", "expires_at": None},
            {"name": "x" * 200},
        ]
    ) == (CookieSeen("JSESSIONID", 1_790_000_000.5, "wms.example", False),)


def test_a_mail_thread_reference_is_an_id_or_nothing() -> None:
    assert mail_thread_kept("FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk") == "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"
    assert mail_thread_kept("Re: your order 42") is None
    assert mail_thread_kept("a" * 300) is None


def test_target_extras_pass_the_said_rule() -> None:
    assert extras_kept(
        {"labelText": "Customer code *", "fullName": "Bearer abcdefghijklmnopqrstuvwxyz0123456789", "siblingIndex": 3, "siblingCount": "x"}
    ) == {"labelText": "Customer code *", "fullName": None, "siblingIndex": 3, "siblingCount": None}
```

```python
# backend/tests/unit/infrastructure/test_an_old_gesture_row_loads.py
from pydantic import TypeAdapter

from sro.domain.observation.gesture import Action, PageMark

OLD_ROW = {
    "kind": "click",
    "at": 1_790_000_000.0,
    "value": None,
    "secret": False,
    "url": "https://wms.example/a",
    "target": {"tag": "button", "role": "button", "name": "Save", "secret": False, "text": "Save",
               "test_id": None, "css_path": "button", "xpath": "/html/body/button[1]", "required": None,
               "component": None, "bounds": {}, "attributes": {}, "landmarks": []},
    "modifiers": [], "frame_path": None, "detail": 1, "trusted": True, "after": None, "outlines": [],
}


def test_a_row_stored_before_the_new_fields_loads_with_their_defaults() -> None:
    action = TypeAdapter(Action).validate_python(OLD_ROW)
    assert (action.place, action.effect, action.choice) == (None, None, None)
    assert action.target is not None
    assert (action.target.label_text, action.target.sibling_index, action.target.full_name) == (None, None, None)


def test_an_old_page_mark_loads_with_no_cookies_and_no_mail_thread() -> None:
    mark = TypeAdapter(PageMark).validate_python({"at": 1.0, "page_kind": "navigated"})
    assert (mark.cookies, mark.mail_thread) == ((), None)
```

Append to `backend/tests/unit/domain/rig/test_identity.py` (use the module's existing gesture builder — read the top of the file and reuse its helper; the names below are the domain's):

```python
def test_the_new_capture_never_moves_an_identity() -> None:
    from dataclasses import replace

    from sro.domain.observation.gesture import Choice, Effect, Place, Seen

    plain = _a_gesture()  # the file's existing builder for a click on a named control
    rich = replace(
        plain,
        action=replace(
            plain.action,
            place=Place(route="/a", title="T", headings=("H",)),
            effect=Effect(appeared=(Seen("status", "Saved"),)),
            choice=Choice("Retail", 2, ("Bulk", "Retail")),
            target=replace(plain.action.target, label_text="Code", sibling_index=1, sibling_count=2, full_name="Code"),
        ),
    )
    assert target_identity(rich) == target_identity(plain)
    assert screen_of(rich) == screen_of(plain)
```

If the file's builder or identity function is named differently, use the names it already imports — the assertion (identity and screen equal with and without the new fields) is what matters.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/domain/rig/test_seen.py tests/unit/infrastructure/test_an_old_gesture_row_loads.py tests/unit/domain/rig/test_identity.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sro.domain.observation.seen'` and `ImportError` for `Place`.

- [ ] **Step 3: Implement the domain shapes**

In `backend/src/sro/domain/observation/gesture.py`, add after `Outline`:

```python
@dataclass(frozen=True, slots=True)
class Place:
    route: str | None = None
    title: str | None = None
    headings: tuple[str, ...] = ()
    tabs: tuple[str, ...] = ()
    grid: str | None = None
    landmarks: tuple[str, ...] = ()
    version: str | None = None


@dataclass(frozen=True, slots=True)
class Seen:
    role: str
    text: str | None = None
    title: str | None = None
    buttons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FieldChange:
    label: str
    change: str


@dataclass(frozen=True, slots=True)
class Effect:
    appeared: tuple[Seen, ...] = ()
    vanished: tuple[Seen, ...] = ()
    route_before: str | None = None
    route_after: str | None = None
    fields: tuple[FieldChange, ...] = ()
    requests_ms: int | None = None
    mask_ms: int | None = None
    quiet_ms: int | None = None
    ended: str | None = None
    errors: tuple[str, ...] = ()
    shortcuts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Choice:
    chosen: str | None = None
    index: int | None = None
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CookieSeen:
    name: str
    expires_at: float | None = None
    domain: str | None = None
    session: bool = False
```

`Place`, `Seen`, `FieldChange`, `Effect`, `Choice` must be defined **before** `Action`; `CookieSeen` before `PageMark`. Append (at the end of each class, after every existing field):

```python
# Target
    label_text: str | None = None
    sibling_index: int | None = None
    sibling_count: int | None = None
    full_name: str | None = None

# Action
    place: Place | None = None
    effect: Effect | None = None
    choice: Choice | None = None

# PageMark
    cookies: tuple[CookieSeen, ...] = ()
    mail_thread: str | None = None
```

In `backend/src/sro/domain/observation/outline.py`, after `_said`:

```python
def said_text(raw: object) -> str | None:
    return _said(raw)
```

- [ ] **Step 4: Implement `seen.py`**

```python
# backend/src/sro/domain/observation/seen.py
from __future__ import annotations

import re
from collections.abc import Mapping

from sro.domain.observation.gesture import Choice, CookieSeen, Effect, FieldChange, Place, Seen
from sro.domain.observation.outline import said_text
from sro.domain.observation.trim import path_shape
from sro.domain.recording.sensitivity import redact_shapes

SEEN_ROLES = frozenset(
    {"dialog", "alertdialog", "alert", "status", "toast", "row", "mask", "invalid", "progressbar"}
)
FIELD_CHANGES = frozenset({"enabled", "disabled", "shown", "hidden", "invalid", "valid"})
ENDINGS = frozenset({"quiet", "max", "next"})

K_SEEN_ITEMS = 20
K_FIELD_CHANGES = 40
K_ERRORS = 10
K_SHORTCUTS = 10
K_CHOICE_OPTIONS = 50
K_PLACE_HEADINGS = 3
K_PLACE_ITEMS = 10
K_BUTTONS = 8
K_MS = 60_000
K_COOKIES = 40
K_COOKIE_NAME = 64
K_MAIL_REF = 200

_URL = re.compile(r"\S+://\S+")
_SHORTCUT = re.compile(r"(?:(?:ctrl|alt|meta|shift)\+)+(?:[a-z0-9]|f[0-9]{1,2}|enter|escape|delete|backspace)")
_MAIL_REF = re.compile(r"[A-Za-z0-9_\-=+/.]+")
_COOKIE_NAME = re.compile(r"[A-Za-z0-9_\-.]+")


def _items(raw: object, cap: int) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)][:cap] if isinstance(raw, list) else []


def _texts(raw: object, cap: int) -> list[str]:
    items = raw if isinstance(raw, list) else []
    return [said for one in items if (said := said_text(one)) is not None][:cap]


def _route(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path, _, hashed = raw.partition("#")
    shaped = path_shape(path) if path else ""
    if hashed:
        shaped += "#" + path_shape(hashed)
    return shaped or None


def _ms(raw: object) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float) or raw < 0:
        return None
    return min(int(raw), K_MS)


def _seen(one: Mapping[str, object]) -> dict[str, object] | None:
    role = one.get("role")
    if not isinstance(role, str) or role not in SEEN_ROLES:
        return None
    text, title = one.get("text"), one.get("title")
    if (isinstance(text, str) and text and said_text(text) is None) or (
        isinstance(title, str) and title and said_text(title) is None
    ):
        return None
    return {
        "role": role,
        "text": said_text(text),
        "title": said_text(title),
        "buttons": _texts(one.get("buttons"), K_BUTTONS),
    }


def place_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    kept: dict[str, object] = {
        "route": _route(raw.get("route")),
        "title": said_text(raw.get("title")),
        "headings": _texts(raw.get("headings"), K_PLACE_HEADINGS),
        "tabs": _texts(raw.get("tabs"), K_PLACE_ITEMS),
        "grid": said_text(raw.get("grid")),
        "landmarks": _texts(raw.get("landmarks"), K_PLACE_ITEMS),
        "version": said_text(raw.get("version")),
    }
    return kept if any(kept.values()) else None


def effect_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    fields = [
        {"label": label, "change": change}
        for one in _items(raw.get("fields"), K_FIELD_CHANGES * 2)
        if (label := said_text(one.get("label"))) is not None
        and isinstance(change := one.get("change"), str)
        and change in FIELD_CHANGES
    ][:K_FIELD_CHANGES]
    errors = [
        said
        for one in (raw.get("errors") if isinstance(raw.get("errors"), list) else [])
        if isinstance(one, str)
        and (said := said_text(redact_shapes(_URL.sub("«url»", one)))) is not None
    ][:K_ERRORS]
    shortcuts = [
        one
        for one in (raw.get("shortcuts") if isinstance(raw.get("shortcuts"), list) else [])
        if isinstance(one, str) and _SHORTCUT.fullmatch(one)
    ][:K_SHORTCUTS]
    ended = raw.get("ended")
    kept: dict[str, object] = {
        "appeared": [s for one in _items(raw.get("appeared"), K_SEEN_ITEMS * 5) if (s := _seen(one))][:K_SEEN_ITEMS],
        "vanished": [s for one in _items(raw.get("vanished"), K_SEEN_ITEMS * 5) if (s := _seen(one))][:K_SEEN_ITEMS],
        "route_before": _route(raw.get("route_before")),
        "route_after": _route(raw.get("route_after")),
        "fields": fields,
        "requests_ms": _ms(raw.get("requests_ms")),
        "mask_ms": _ms(raw.get("mask_ms")),
        "quiet_ms": _ms(raw.get("quiet_ms")),
        "ended": ended if isinstance(ended, str) and ended in ENDINGS else None,
        "errors": errors,
        "shortcuts": shortcuts,
    }
    return kept if any(value not in (None, []) for value in kept.values()) else None


def choice_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    index = raw.get("index")
    if index is not None and (isinstance(index, bool) or not isinstance(index, int) or index < 0):
        return None
    kept: dict[str, object] = {
        "chosen": said_text(raw.get("chosen")),
        "index": index,
        "options": _texts(raw.get("options"), K_CHOICE_OPTIONS),
    }
    return kept if kept["chosen"] is not None or kept["options"] else None


def cookies_kept(raw: object) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for one in _items(raw, K_COOKIES):
        name = one.get("name")
        if (
            not isinstance(name, str)
            or len(name) > K_COOKIE_NAME
            or not _COOKIE_NAME.fullmatch(name)
            or redact_shapes(name) != name
        ):
            continue
        expires = one.get("expires_at")
        domain = one.get("domain")
        kept.append(
            {
                "name": name,
                "expires_at": float(expires) if isinstance(expires, int | float) and not isinstance(expires, bool) else None,
                "domain": domain if isinstance(domain, str) and len(domain) <= 253 else None,
                "session": one.get("session") is True,
            }
        )
    return kept


def mail_thread_kept(raw: object) -> str | None:
    if not isinstance(raw, str) or len(raw) > K_MAIL_REF or not _MAIL_REF.fullmatch(raw):
        return None
    return raw


def extras_kept(target: Mapping[str, object]) -> dict[str, object]:
    def _count(raw: object) -> int | None:
        return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else None

    return {
        "labelText": said_text(target.get("labelText")),
        "fullName": said_text(target.get("fullName")),
        "siblingIndex": _count(target.get("siblingIndex")),
        "siblingCount": _count(target.get("siblingCount")),
    }


def _seen_of(one: Mapping[str, object]) -> Seen:
    buttons = one.get("buttons")
    return Seen(
        str(one["role"]),
        one.get("text") if isinstance(one.get("text"), str) else None,
        one.get("title") if isinstance(one.get("title"), str) else None,
        tuple(str(b) for b in buttons) if isinstance(buttons, list) else (),
    )


def place_from(raw: object) -> Place | None:
    kept = place_kept(raw)
    if kept is None:
        return None
    return Place(
        route=kept["route"],  # type: ignore[arg-type]
        title=kept["title"],  # type: ignore[arg-type]
        headings=tuple(kept["headings"]),  # type: ignore[arg-type]
        tabs=tuple(kept["tabs"]),  # type: ignore[arg-type]
        grid=kept["grid"],  # type: ignore[arg-type]
        landmarks=tuple(kept["landmarks"]),  # type: ignore[arg-type]
        version=kept["version"],  # type: ignore[arg-type]
    )


def effect_from(raw: object) -> Effect | None:
    kept = effect_kept(raw)
    if kept is None:
        return None
    return Effect(
        appeared=tuple(_seen_of(one) for one in kept["appeared"]),  # type: ignore[attr-defined]
        vanished=tuple(_seen_of(one) for one in kept["vanished"]),  # type: ignore[attr-defined]
        route_before=kept["route_before"],  # type: ignore[arg-type]
        route_after=kept["route_after"],  # type: ignore[arg-type]
        fields=tuple(FieldChange(str(one["label"]), str(one["change"])) for one in kept["fields"]),  # type: ignore[attr-defined]
        requests_ms=kept["requests_ms"],  # type: ignore[arg-type]
        mask_ms=kept["mask_ms"],  # type: ignore[arg-type]
        quiet_ms=kept["quiet_ms"],  # type: ignore[arg-type]
        ended=kept["ended"],  # type: ignore[arg-type]
        errors=tuple(kept["errors"]),  # type: ignore[arg-type]
        shortcuts=tuple(kept["shortcuts"]),  # type: ignore[arg-type]
    )


def choice_from(raw: object) -> Choice | None:
    kept = choice_kept(raw)
    if kept is None:
        return None
    return Choice(kept["chosen"], kept["index"], tuple(kept["options"]))  # type: ignore[arg-type]


def cookies_from(raw: object) -> tuple[CookieSeen, ...]:
    return tuple(
        CookieSeen(str(one["name"]), one["expires_at"], one["domain"], bool(one["session"]))  # type: ignore[arg-type]
        for one in cookies_kept(raw)
    )
```

The `# type: ignore` lines are there because `kept` is a `dict[str, object]`; if `mypy --strict` prefers it, replace them with small typed locals (`route = kept["route"]; assert isinstance(route, str | None)`) — either is acceptable, comments are not. Check the `path_shape` placeholder: the test above assumes it renders numeric segments as `{id}`; run `uv run python -c "from sro.domain.observation.trim import path_shape; print(path_shape('/wms/customers/12345'))"` and update the expected strings in the test to what `path_shape` really prints (the rule under test is "the route is shaped by `path_shape`", not the placeholder spelling).

- [ ] **Step 5: Update the enumerated Action dump**

In `backend/tests/unit/interface/test_workflows_route.py` (the dict ending at `"outlines": []` near line 661), add to the `target` dict `"label_text": None, "sibling_index": None, "sibling_count": None, "full_name": None,` and to the action dict `"place": None, "effect": None, "choice": None,`. Then search for other exact dumps of a gesture/`PageMark`: `grep -rn '"outlines": \[\]' backend/tests` and `grep -rn '"opener_tab_id"' backend/tests` and add the new keys (`"cookies": [], "mail_thread": None` for page marks) wherever a full dump is asserted.

- [ ] **Step 6: Write the ADR**

Create `docs/07-adr/016-richer-capture-is-additions-only.md`:

```markdown
# 016 — Richer capture is additions only

**Status:** accepted, 2026-10-02
**Relates to:** [008 — passive observation](008-passive-observation.md); spec `docs/superpowers/specs/2026-10-02-richer-capture-for-steel-design.md`

## The problem

Steel runs fail or stall in four measured classes — a write sent with nothing confirming it, sign-in,
a control or page not found, duplicates — and resume on the wrong step. Baseline (QA, last 30 days,
`scripts/measure.py` section 3b, 2026-10-02): <paste the class counts from Task 1 here, including `other`>.
The recording holds what the person did, not what the page did back.

## Decision

1. The recorder captures more (effect after each action, place, element extras, combo choice, cookie
   names/expiry, app version, opt-in mail thread reference) as **optional fields with defaults** on
   the wire, the domain and the JSONB gesture row. No migration touches `gestures`; old rows load.
2. "What changed after the action" travels as its own `effect` event, joined to its gesture by `ref`
   in a batch and by (stream, tab, frame path, time) across batches — it is only known after the
   gesture was emitted.
3. New data never feeds identity: `targetIdentity`, `screenOf` and shape keys read only today's fields;
   the golden fixtures prove it byte for byte.
4. Every consumer in Steel is a lane-level note first (`shadow:<check>:<verdict>` in
   `workflow_run_steps.notes`), per tenant, empty by default. Promotion is per check and per tenant,
   after the gate (≥20 shadowed steps on QA, ≥95% agreement, zero false confirmations, no run that
   passes today failing) and the owner's yes. A promoted check may only turn unknown into confirmed,
   add a wait, add a locator after today's, or add an ask. Stopping a run (wrong screen, duplicate) is
   a separate yes.
5. Nothing is removed (owner ruling): gesture rows outlive "delete the last hour" and retention, so
   every new field is safe to keep forever — no field values, no cookie values, no mail text, text
   through `outline._said`.

## Consequences

- Recognition and offers are untouched; only jobs recorded after the extension update carry the new
  data, so the owner's main QA jobs are recorded again once.
- Two new effect paths at ingest (in-batch join, cross-batch update of the stored row's JSONB); an
  effect that matches no or several stored gestures is dropped and logged, never guessed.
- The `cookies` permission is optional and requested at runtime, so updating the extension shows no
  new warning.
```

- [ ] **Step 7: Code notes**

Create `docs/code-notes/backend/src/sro/domain/observation/seen.py.md` in the format of the sibling notes files (title, the "Comments and docstrings moved out of…" line, then one heading per function with its line). Say: why each `*_kept` drops rather than truncates text that fails `said_text` (a token cut in half is still a token); why routes go through `path_shape` (ids in routes are record ids); why cookies are matched by name shape and never by value; why `mail_thread_kept` only accepts id characters (anything else is mail text); why `*_from` builds from `*_kept` (one sanitising path for the wire, the store and live page reads). Add to `gesture.py.md` a heading for `Place`/`Effect`/`Choice`/`CookieSeen` stating they are optional and defaulted so old rows load, and that nothing in identity reads them. Add to `outline.py.md` a heading for `said_text`: the public name for `_said`, so new capture text obeys the same rule as outlines.

- [ ] **Step 8: Run tests and lint**

Run: `cd backend && uv run pytest tests/unit/domain/rig tests/unit/infrastructure/test_an_old_gesture_row_loads.py tests/unit/interface/test_workflows_route.py -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run lint-imports`
Expected: PASS; no lint, type or import-contract errors (`seen.py` imports domain only).

- [ ] **Step 9: Commit**

```bash
git add backend/src/sro/domain/observation/gesture.py backend/src/sro/domain/observation/outline.py backend/src/sro/domain/observation/seen.py backend/tests/unit/domain/rig/test_seen.py backend/tests/unit/domain/rig/test_identity.py backend/tests/unit/infrastructure/test_an_old_gesture_row_loads.py backend/tests/unit/interface/test_workflows_route.py docs/07-adr/016-richer-capture-is-additions-only.md docs/code-notes/backend/src/sro/domain/observation/seen.py.md docs/code-notes/backend/src/sro/domain/observation/gesture.py.md docs/code-notes/backend/src/sro/domain/observation/outline.py.md
git commit -m "feat(capture): optional place, effect, choice and cookie shapes, sanitised once, ADR 016

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RNYbCzVj7p76GmLhf2MBKL"
```

---

### Task 3: Declare every new key on the wire; admit and redact it

**Files:**
- Modify: `backend/src/sro/application/capture/rig_wire.py`
- Modify: `backend/src/sro/application/observation/admit.py`
- Modify: `backend/src/sro/application/observation/redact.py`
- Test: `backend/tests/unit/application/test_the_new_capture_survives_redaction.py` (new)
- Test: `backend/tests/unit/application/test_rig_wire.py` (add cases)
- Modify: `docs/code-notes/backend/src/sro/application/observation/redact.py.md`, `docs/code-notes/backend/src/sro/application/capture/rig_wire.py.md`, `docs/code-notes/backend/src/sro/application/observation/admit.py.md` (create if absent)

**Interfaces:**
- Consumes: `seen.place_kept`, `seen.effect_kept`, `seen.choice_kept`, `seen.cookies_kept`, `seen.mail_thread_kept`, `seen.extras_kept`, `outline.said_text` (Task 2).
- Produces: wire models `rig_wire.Place`, `rig_wire.Seen`, `rig_wire.FieldChange`, `rig_wire.Effect`, `rig_wire.Choice`, `rig_wire.CookieSeen`, `rig_wire.EffectEvent(kind="effect", of: str, of_at: float, url: str|None, frame_path: list[FrameHop]|None, effect: Effect, tab_id: int|None, frame_url: str|None)`; `rig_wire.Target.labelText/fullName/siblingIndex/siblingCount`; `rig_wire.Gesture.place/choice`; `rig_wire.PageEvent.cookies/mail_thread`; `Event` union includes `EffectEvent`; `admit.KINDS` includes `"effect"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/test_the_new_capture_survives_redaction.py
from sro.application.capture.rig_wire import Batch, EffectEvent, Gesture, PageEvent, Target
from sro.application.observation.admit import admit
from sro.application.observation.redact import redact_events
from sro.domain.observation.policy import ObservationPolicy

ON = ObservationPolicy(capture_enabled=True)


def _gesture(**extra: object) -> dict[str, object]:
    return {
        "kind": "gesture",
        "tab_id": 7,
        "gesture": {
            "kind": "click",
            "at": 1_790_000_000.25,
            "url": "https://wms.example/a",
            "ref": "r.1",
            "target": {"role": "button", "name": "Save", "labelText": "Save", "fullName": "Save",
                       "siblingIndex": 2, "siblingCount": 3},
            "place": {"route": "/a", "title": "Customers", "headings": ["Customers"]},
            "choice": {"chosen": "Retail", "index": 1, "options": ["Bulk", "Retail"]},
            **extra,
        },
    }


def _effect() -> dict[str, object]:
    return {
        "kind": "effect",
        "of": "r.1",
        "of_at": 1_790_000_000.25,
        "url": "https://wms.example/a",
        "tab_id": 7,
        "effect": {"appeared": [{"role": "status", "text": "Saved"}], "quiet_ms": 640, "ended": "quiet"},
    }


def test_every_key_the_recorder_now_sends_is_declared_on_the_wire() -> None:
    assert {"place", "choice"} <= set(Gesture.model_fields)
    assert {"labelText", "fullName", "siblingIndex", "siblingCount"} <= set(Target.model_fields)
    assert {"cookies", "mail_thread"} <= set(PageEvent.model_fields)
    assert {"of", "of_at", "effect", "url", "tab_id", "frame_path"} <= set(EffectEvent.model_fields)


def test_the_new_gesture_keys_reach_storage() -> None:
    (out,) = redact_events([_gesture()])
    gesture = out["gesture"]
    assert gesture["place"]["title"] == "Customers"
    assert gesture["choice"]["chosen"] == "Retail"
    assert gesture["target"]["labelText"] == "Save" and gesture["target"]["siblingIndex"] == 2


def test_an_undeclared_gesture_key_is_still_dropped() -> None:
    (out,) = redact_events([_gesture(somethingNew="x")])
    assert "somethingNew" not in out["gesture"]


def test_an_effect_event_is_admitted_kept_and_parsed() -> None:
    admitted = admit([_gesture(), _effect()], ON)
    assert admitted.rejected == ()
    _, effect = redact_events(admitted.accepted)
    assert effect["effect"]["appeared"][0]["text"] == "Saved"
    batch = Batch.model_validate(
        {"batch_id": "b", "device_id": "d", "started_at": "2026-10-02T00:00:00+00:00",
         "ended_at": "2026-10-02T00:01:00+00:00", "events": [effect]}
    )
    assert isinstance(batch.events[0], EffectEvent)


def test_an_effect_on_an_excluded_host_is_refused() -> None:
    event = _effect() | {"url": "https://accounts.google.com/x"}
    assert admit([event], ON).accepted == ()


def test_an_effect_without_its_gesture_reference_is_refused() -> None:
    event = {key: value for key, value in _effect().items() if key != "of_at"}
    assert admit([event], ON).accepted == ()


def test_an_effect_s_unlisted_keys_never_reach_storage() -> None:
    (out,) = redact_events([_effect() | {"body": "everything typed"}])
    assert "body" not in out


def test_cookie_names_and_a_mail_thread_reach_storage_and_values_never_do() -> None:
    page = {
        "kind": "page", "at": "2026-10-02T00:00:00+00:00", "page_kind": "cookies_set",
        "url": "https://wms.example/a", "tab_id": 7,
        "cookies": [{"name": "JSESSIONID", "expires_at": 1_790_003_600.0, "value": "secret"}],
        "mail_thread": "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk",
    }
    (out,) = redact_events([page])
    assert out["cookies"] == [{"name": "JSESSIONID", "expires_at": 1_790_003_600.0, "domain": None, "session": False}]
    assert out["mail_thread"] == "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"
```

Check `ObservationPolicy(capture_enabled=True).allows("https://wms.example/a")` is true with default exclusions (it is: no include list), and that `admit` with no `granted`/`ours` arguments is how other unit tests call it (`grep -n "admit(" backend/tests/unit/application/test_what_a_browser_may_upload.py`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/application/test_the_new_capture_survives_redaction.py -q`
Expected: FAIL with `ImportError: cannot import name 'EffectEvent'`.

- [ ] **Step 3: Declare the wire**

In `rig_wire.py`, add after `Outline` (import `said_text` from `sro.domain.observation.outline` and `cookies_kept`, `mail_thread_kept` from `sro.domain.observation.seen`):

```python
class Place(BaseModel):
    route: str | None = None
    title: str | None = None
    headings: list[str] = Field(default_factory=list)
    tabs: list[str] = Field(default_factory=list)
    grid: str | None = None
    landmarks: list[str] = Field(default_factory=list)
    version: str | None = None


class Seen(BaseModel):
    role: str
    text: str | None = None
    title: str | None = None
    buttons: list[str] = Field(default_factory=list)


class FieldChange(BaseModel):
    label: str
    change: str


class Effect(BaseModel):
    appeared: list[Seen] = Field(default_factory=list)
    vanished: list[Seen] = Field(default_factory=list)
    route_before: str | None = None
    route_after: str | None = None
    fields: list[FieldChange] = Field(default_factory=list)
    requests_ms: int | None = None
    mask_ms: int | None = None
    quiet_ms: int | None = None
    ended: str | None = None
    errors: list[str] = Field(default_factory=list)
    shortcuts: list[str] = Field(default_factory=list)


class Choice(BaseModel):
    chosen: str | None = None
    index: int | None = None
    options: list[str] = Field(default_factory=list)


class CookieSeen(BaseModel):
    name: str
    expires_at: float | None = None
    domain: str | None = None
    session: bool = False
```

On `Target`, after `landmarks`:

```python
    labelText: str | None = None
    fullName: str | None = None
    siblingIndex: int | None = None
    siblingCount: int | None = None

    @model_validator(mode="after")
    def the_new_prose_is_said_or_dropped_here(self) -> "Target":
        if self.secret:
            self.labelText = None
            self.fullName = None
        self.labelText = said_text(self.labelText)
        self.fullName = said_text(self.fullName)
        return self
```

On `Gesture`, after `outlines`:

```python
    place: Place | None = None
    choice: Choice | None = None
```

On `PageEvent`, after `opener_tab_id`:

```python
    cookies: list[CookieSeen] = Field(default_factory=list)
    mail_thread: str | None = None

    @model_validator(mode="after")
    def only_names_and_ids_reach_a_page_event(self) -> "PageEvent":
        self.cookies = [CookieSeen.model_validate(one) for one in cookies_kept([c.model_dump() for c in self.cookies])]
        self.mail_thread = mail_thread_kept(self.mail_thread)
        return self
```

New event (after `PageEvent`):

```python
class EffectEvent(BaseModel):
    kind: Literal["effect"]
    of: str
    of_at: float
    url: str | None = None
    frame_path: list[FrameHop] | None = None
    effect: Effect
    tab_id: int | None = None
    frame_url: str | None = None

    @model_validator(mode="after")
    def a_credential_in_a_url_is_dropped_here(self) -> "EffectEvent":
        if self.url:
            self.url = redact_url(self.url)
        if self.frame_url:
            self.frame_url = redact_url(self.frame_url)
        return self
```

and `Event = Annotated[GestureEvent | RequestEvent | PageEvent | SnapshotEvent | EffectEvent, Field(discriminator="kind")]`.

- [ ] **Step 4: Admit the kind**

In `admit.py`: `KINDS = ("gesture", "request", "snapshot", "page", "effect")`, and in `_why_not`, before the final page branch:

```python
    if kind == "effect":
        if not isinstance(event.get("of"), str) or not event.get("of"):
            return "an effect that does not say which gesture it followed"
        of_at = event.get("of_at")
        if isinstance(of_at, bool) or not isinstance(of_at, int | float):
            return "an effect with no gesture time cannot be joined to its gesture"
        if _mapping(event.get("effect")) is None:
            return "an effect event with no effect in it"
        return _url_refusal(event.get("url"), policy, granted, ours)
```

- [ ] **Step 5: Redact it**

In `redact.py`: import `EffectEvent` and add `("effect", EffectEvent)` to `_EVENT_KEYS`; import `choice_kept, cookies_kept, effect_kept, extras_kept, mail_thread_kept, place_kept` from `sro.domain.observation.seen`. In `_event`, after the request branch:

```python
    if out.get("kind") == "effect":
        out["effect"] = effect_kept(out.get("effect")) or {}
        frame_path = out.get("frame_path")
        if isinstance(frame_path, list):
            out["frame_path"] = [_hop(hop) if isinstance(hop, Mapping) else hop for hop in frame_path]
    if "cookies" in out:
        out["cookies"] = cookies_kept(out["cookies"])
    if "mail_thread" in out:
        out["mail_thread"] = mail_thread_kept(out["mail_thread"])
```

In `_gesture`, after the `outlines` block:

```python
    if "place" in out:
        out["place"] = place_kept(out["place"])
    if "choice" in out:
        out["choice"] = choice_kept(out["choice"])
```

In `_element`, at the end before `return out` (applies to the target; the component recursion has none of these keys, so `extras_kept` is applied only when one is present):

```python
    if any(key in out for key in ("labelText", "fullName", "siblingIndex", "siblingCount")):
        out |= extras_kept(out)
        if out.get("secret"):
            out["labelText"] = out["fullName"] = None
```

- [ ] **Step 6: Code notes**

Add to `redact.py.md` a heading for the `effect` branch of `_event` and the `place`/`choice` branch of `_gesture`: the whitelist trap (`_GESTURE_KEYS` comes from `rig_wire.Gesture.model_fields`; an undeclared key is dropped) and why the new keys are sanitised through `seen.py` here and again by the wire validators (the blob is written from the redacted dicts, the rows from the parsed models). Add to `rig_wire.py.md` a heading for `EffectEvent` (why a separate event: the effect is known only after the gesture left the page) and for `Target.the_new_prose_is_said_or_dropped_here`. Add to `admit.py.md` the `effect` rule.

- [ ] **Step 7: Run tests, lint, types**

Run: `cd backend && uv run pytest tests/unit/application -q && uv run ruff check src tests && uv run mypy src && make -C .. types && git -C .. status --short frontend`
Expected: PASS. If `make types` changed `frontend/openapi.json` / `generated.ts` (it does only if a route schema exposes `rig_wire` models), stage them in the commit below.

- [ ] **Step 8: Commit**

```bash
git add backend/src/sro/application/capture/rig_wire.py backend/src/sro/application/observation/admit.py backend/src/sro/application/observation/redact.py backend/tests/unit/application/test_the_new_capture_survives_redaction.py backend/tests/unit/application/test_rig_wire.py docs/code-notes/backend/src/sro/application/observation/redact.py.md docs/code-notes/backend/src/sro/application/capture/rig_wire.py.md docs/code-notes/backend/src/sro/application/observation/admit.py.md
git commit -m "feat(capture): declare place, choice, target extras, cookies, mail ref and the effect event on the wire

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RNYbCzVj7p76GmLhf2MBKL"
```

(Add `frontend/openapi.json frontend/src/lib/api/generated.ts` to `git add` only if Step 7 changed them.)

---

### Task 4: Map to the domain, join effects to their gestures, store across batches

**Files:**
- Modify: `backend/src/sro/application/observation/correlate.py` (`as_action`, `as_mark`, new `correlate_with_effects`; `correlate` delegates)
- Modify: `backend/src/sro/application/observation/ingest.py` (use `correlate_with_effects`; attach leftovers)
- Modify: `backend/src/sro/application/ports/repositories.py` (`GestureRepository.attach_effect`)
- Modify: `backend/src/sro/infrastructure/db/evidence.py` (`SqlGestureRepository.attach_effect`)
- Modify: `backend/tests/unit/fakes.py` (`FakeGestureRepository.attach_effect`)
- Test: `backend/tests/unit/application/test_correlate.py` (add cases), `backend/tests/unit/application/test_an_effect_reaches_its_gesture.py` (new), `backend/tests/integration/test_an_effect_lands_on_a_stored_gesture.py` (new)
- Modify: `docs/code-notes/backend/src/sro/application/observation/correlate.py.md`, `docs/code-notes/backend/src/sro/infrastructure/db/evidence.py.md`, `docs/code-notes/backend/src/sro/application/observation/ingest.py.md` (create if absent)

**Interfaces:**
- Consumes: `rig_wire.EffectEvent`, `seen.place_from/effect_from/choice_from/cookies_from` (Tasks 2–3).
- Produces: `correlate_with_effects(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Call], list[PageMark], int, list[EffectEvent]]` (the last item: effects whose gesture is not in this batch); `GestureRepository.attach_effect(self, tenant_id: TenantId, *, stream_id: str, tab_id: int | None, frame_path: tuple[FrameHop, ...] | None, at: float, effect: Effect) -> bool` (True only when exactly one stored gesture matched and it had no effect).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/test_an_effect_reaches_its_gesture.py
from sro.application.capture.rig_wire import Batch
from sro.application.observation.correlate import correlate, correlate_with_effects
from sro.domain.observation.gesture import Effect, Seen

AT = 1_790_000_000.25


def _batch(*events: dict[str, object]) -> Batch:
    return Batch.model_validate(
        {"batch_id": "b1", "device_id": "dev", "started_at": "2026-10-02T00:00:00+00:00",
         "ended_at": "2026-10-02T00:01:00+00:00", "events": list(events)}
    )


def _gesture(ref: str, at: float, name: str = "Save") -> dict[str, object]:
    return {"kind": "gesture", "tab_id": 1, "gesture": {
        "kind": "click", "at": at, "ref": ref, "url": "https://wms.example/a",
        "target": {"role": "button", "name": name, "labelText": "Save", "siblingIndex": 0, "siblingCount": 2},
        "place": {"route": "/a", "title": "Customers"},
        "choice": {"chosen": "Retail", "index": 1, "options": ["Bulk", "Retail"]}}}


def _effect(of: str, at: float, text: str = "Saved") -> dict[str, object]:
    return {"kind": "effect", "of": of, "of_at": at, "url": "https://wms.example/a", "tab_id": 1,
            "effect": {"appeared": [{"role": "status", "text": text}], "ended": "quiet"}}


def test_an_effect_lands_on_the_gesture_it_names_in_the_same_batch() -> None:
    gestures, _, _, _, left = correlate_with_effects(
        _batch(_gesture("r.1", AT), _gesture("r.2", AT + 1, "Cancel"), _effect("r.1", AT)), "acme"
    )
    saved = next(g for g in gestures if g.action.target and g.action.target.name == "Save")
    other = next(g for g in gestures if g.action.target and g.action.target.name == "Cancel")
    assert saved.action.effect == Effect(appeared=(Seen("status", "Saved"),), ended="quiet")
    assert other.action.effect is None
    assert left == []


def test_an_effect_whose_gesture_is_not_in_the_batch_is_handed_back() -> None:
    _, _, _, _, left = correlate_with_effects(_batch(_effect("r.9", AT)), "acme")
    assert [one.of for one in left] == ["r.9"]


def test_the_new_gesture_fields_reach_the_action() -> None:
    (gesture,), *_ = correlate(_batch(_gesture("r.1", AT)), "acme")
    assert gesture.action.place is not None and gesture.action.place.title == "Customers"
    assert gesture.action.choice is not None and gesture.action.choice.index == 1
    assert gesture.action.target is not None
    assert (gesture.action.target.label_text, gesture.action.target.sibling_index, gesture.action.target.sibling_count) == ("Save", 0, 2)


def test_correlate_still_answers_its_four_things() -> None:
    assert len(correlate(_batch(_gesture("r.1", AT)), "acme")) == 4
```

Append to `backend/tests/unit/application/test_correlate.py` a case that a page event with `cookies` and `mail_thread` becomes a `PageMark` with `cookies=(CookieSeen("JSESSIONID", 1_790_003_600.0),)` and `mail_thread="FMfcg..."` (build the batch the way that file's other page-event cases do).

Ingest-level tests (Review Focus 1) in the same new file, using the fakes the way `test_the_backend_stores_what_the_browser_sent.py` does (register a device, set the policy on, call `IngestObservation.execute` twice):

```python
async def test_an_effect_in_the_next_batch_lands_on_the_stored_gesture() -> None:
    uow, ingest, device = await _ready()  # helper: FakeUnitOfWork, IngestObservation, a registered device with capture on
    await _send(ingest, device, "b1", [_gesture("r.1", AT)])
    await _send(ingest, device, "b2", [_effect("r.1", AT)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is not None and stored.action.effect.appeared[0].text == "Saved"


async def test_an_effect_never_overwrites_one_already_there() -> None:
    uow, ingest, device = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT), _effect("r.1", AT, "Saved")])
    await _send(ingest, device, "b2", [_effect("r.1", AT, "Saved again")])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is not None and stored.action.effect.appeared[0].text == "Saved"


async def test_an_effect_matching_two_stored_gestures_lands_on_neither() -> None:
    uow, ingest, device = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT), _gesture("r.2", AT, "Also save")])
    await _send(ingest, device, "b2", [_effect("r.1", AT)])
    assert all(one.action.effect is None for one in uow.gestures.rows.values())
```

Write `_ready` and `_send` in the new file by copying the setup lines from `test_the_backend_stores_what_the_browser_sent.py` (RegisterDevice → SetObservationPolicy(enabled) → IngestObservation with `FakeBlobStore`, `FakeClock`); `_send` calls `ingest.execute(ctx, device_id=..., secret=..., batch_id=BatchId(name), started_at=..., ended_at=..., mode=CaptureMode.PASSIVE, events=events)`.

```python
# backend/tests/integration/test_an_effect_lands_on_a_stored_gesture.py
```
Model it on `backend/tests/integration/test_a_target_keeps_its_attributes.py` (same fixtures, same session factory): store one gesture with `SqlGestureRepository.add_gestures`, call `attach_effect(...)` with its stream, tab, frame path and `at`, read it back with `gestures_for`, and assert the effect is there; then call again and assert it returns `False` and the first effect stands; then store two gestures with the same `at` and assert `attach_effect` returns `False` and neither has an effect.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/application/test_an_effect_reaches_its_gesture.py tests/unit/application/test_correlate.py -q`
Expected: FAIL with `ImportError: cannot import name 'correlate_with_effects'`.

- [ ] **Step 3: Implement the mapping and the join**

In `correlate.py`: import `EffectEvent` from `rig_wire`; import `place_from, effect_from, choice_from, cookies_from` from `sro.domain.observation.seen`; add `"correlate_with_effects"` to `__all__`. Rename the body of `correlate` into `correlate_with_effects`, extended:

```python
def correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Call], list[PageMark], int]:
    gestures, orphans, marks, snapshots, _ = correlate_with_effects(batch, tenant)
    return gestures, orphans, marks, snapshots


def correlate_with_effects(
    batch: Batch, tenant: str
) -> tuple[list[Gesture], list[Call], list[PageMark], int, list[EffectEvent]]:
    # ... the existing body unchanged, plus:
    effects: list[EffectEvent] = []
    # in the event loop, a new branch:
    #     elif isinstance(event, EffectEvent):
    #         effects.append(event)
    # after the priors loop:
    left: list[EffectEvent] = []
    for one in effects:
        key = (one.tab_id, _hops(one.frame_path), one.of)
        owner = made.get(key)
        effect = effect_from(one.effect.model_dump())
        if owner is None:
            left.append(one)
        elif owner.action.effect is None and effect is not None:
            owner.action = replace(owner.action, effect=effect)
    # ... and return gestures, orphan_requests, orphan_pages, snapshots_ignored, left
```

with

```python
def _hops(frame_path: list[WireFrameHop] | None) -> tuple[FrameHop, ...] | None:
    return None if frame_path is None else tuple(FrameHop(index=hop.index, url=hop.url) for hop in frame_path)
```

(`made` is keyed `(tab_id, frame_path_tuple, ref)` already; import `FrameHop as WireFrameHop` from `rig_wire`.)

In `as_action`, add to the `Target(...)` call `label_text=target.labelText, sibling_index=target.siblingIndex, sibling_count=target.siblingCount, full_name=target.fullName,` and to the `Action(...)` call:

```python
        place=None if wire.place is None else place_from(wire.place.model_dump()),
        choice=None if wire.choice is None else choice_from(wire.choice.model_dump()),
```

In `as_mark`, add `cookies=cookies_from([one.model_dump() for one in event.cookies]), mail_thread=event.mail_thread,`.

- [ ] **Step 4: The repository method**

Port (`repositories.py`, in `GestureRepository`):

```python
    async def attach_effect(
        self,
        tenant_id: TenantId,
        *,
        stream_id: str,
        tab_id: int | None,
        frame_path: tuple[FrameHop, ...] | None,
        at: float,
        effect: Effect,
    ) -> bool: ...
```

SQL (`evidence.py`, in `SqlGestureRepository`):

```python
    async def attach_effect(
        self,
        tenant_id: TenantId,
        *,
        stream_id: str,
        tab_id: int | None,
        frame_path: tuple[FrameHop, ...] | None,
        at: float,
        effect: Effect,
    ) -> bool:
        rows = (
            await self._session.scalars(
                select(GestureRow).where(
                    GestureRow.tenant_id == tenant_id.value,
                    GestureRow.stream_id == stream_id,
                    GestureRow.tab_id.is_not_distinct_from(tab_id),
                    GestureRow.at == at,
                )
            )
        ).all()
        same = [row for row in rows if _ACTION.validate_python(row.gesture).frame_path == frame_path]
        if len(same) != 1:
            return False
        action = _ACTION.validate_python(same[0].gesture)
        if action.effect is not None:
            return False
        same[0].gesture = dump(_ACTION, replace(action, effect=effect))
        await self._session.flush()
        return True
```

(import `replace` from `dataclasses`, `Effect`, `FrameHop` from the gesture module.)

Fake (`fakes.py`, in `FakeGestureRepository`), same rule:

```python
    async def attach_effect(
        self,
        tenant_id: TenantId,
        *,
        stream_id: str,
        tab_id: int | None,
        frame_path: tuple[FrameHop, ...] | None,
        at: float,
        effect: Effect,
    ) -> bool:
        same = [
            one
            for one in self.rows.values()
            if one.tenant == tenant_id.value
            and one.stream_id == stream_id
            and one.tab_id == tab_id
            and one.at == at
            and one.action.frame_path == frame_path
        ]
        if len(same) != 1 or same[0].action.effect is not None:
            return False
        same[0].action = replace(same[0].action, effect=effect)
        return True
```

- [ ] **Step 5: Ingest uses it**

In `ingest.py`, replace `correlate` with `correlate_with_effects` in the import and the call:

```python
            gestures, orphans, marks, snapshots, left = correlate_with_effects(wire, ctx.tenant_id.value)
```

and after `if gestures: await uow.gestures.add_gestures(tuple(gestures))`:

```python
            for one in left:
                effect = effect_from(one.effect.model_dump())
                if effect is None:
                    continue
                attached = await uow.gestures.attach_effect(
                    ctx.tenant_id,
                    stream_id=device_id.value,
                    tab_id=one.tab_id,
                    frame_path=None if one.frame_path is None else tuple(FrameHop(hop.index, hop.url) for hop in one.frame_path),
                    at=one.of_at,
                    effect=effect,
                )
                if not attached:
                    logger.info("%s: an effect of %s matched no single stored gesture", batch_id.value, one.of)
```

(add `logger = logging.getLogger(__name__)` and the imports.)

- [ ] **Step 6: Code notes**

In `correlate.py.md`: a heading for `correlate_with_effects` saying the effect joins exactly as `prior` does (by `ref`, same tab and frame path, never by position), and that `correlate` keeps its four-tuple for its existing callers. In `evidence.py.md`: `attach_effect` matches on stream, tab, frame path and the gesture's own `at` (the recorder sends `of_at` as the exact float it stamped on the gesture), refuses when zero or several rows match (two gestures in one millisecond — a checkbox's click and change), and never overwrites — nothing stored is replaced. In `ingest.py.md`: the ceiling — an effect arriving before its gesture's batch (an upload retried out of order) is dropped and logged.

- [ ] **Step 7: Run tests**

Run: `cd backend && uv run pytest tests/unit -q -x && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_an_effect_lands_on_a_stored_gesture.py -q && uv run mypy src && uv run lint-imports`
Expected: PASS (the integration test skips itself if Postgres is not up; run `make up` first).

- [ ] **Step 8: Commit**

```bash
git add backend/src/sro/application/observation/correlate.py backend/src/sro/application/observation/ingest.py backend/src/sro/application/ports/repositories.py backend/src/sro/infrastructure/db/evidence.py backend/tests/unit/fakes.py backend/tests/unit/application/test_an_effect_reaches_its_gesture.py backend/tests/unit/application/test_correlate.py backend/tests/integration/test_an_effect_lands_on_a_stored_gesture.py docs/code-notes/backend/src/sro/application/observation/correlate.py.md docs/code-notes/backend/src/sro/infrastructure/db/evidence.py.md docs/code-notes/backend/src/sro/application/observation/ingest.py.md
git commit -m "feat(capture): an effect joins its gesture in a batch or on the stored row, never overwriting

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RNYbCzVj7p76GmLhf2MBKL"
```

- [ ] **Step 9: Deploy gate (backend first)**

Open the PR for Tasks 1–4 and stop for the owner's "merge"; after it is merged and the API **and worker** are restarted on QA, an old extension's batch must still be accepted with no new rejections: run `make measure tenant=<qa-tenant>` and confirm section 1's rejected-event count did not rise. Only then start packaging Tasks 5–7.

---

## Phase 3 — Extension captures (after the backend is live)

### Task 5: Where the person was, richer element identity, the combo choice

**Files:**
- Modify: `new-chrome-extension/src/page/page-code.js` (readers block: `fullNameOf`, `siblingOf`, `choiceOf`, `versionOf`, `placeOf`; add them to the readers' `return {…}` and to the destructuring right after it)
- Modify: `backend/src/sro/infrastructure/steel/recorder.js` (destructure the new readers; `describe` adds `labelText`, `fullName`, `siblingIndex`, `siblingCount`; `emit` adds `place`; the click listener adds `choice`)
- Regenerate (never hand-edit): `new-chrome-extension/src/content/recorder.generated.js` via `make gen-recorder`; fixtures via `make fixtures`
- Test: `backend/tests/browser/test_what_a_gesture_saw.py` (new), `new-chrome-extension/src/content/evidence.test.mjs` (add a `siblingOf` case)
- Modify: `docs/code-notes/new-chrome-extension/src/page/page-code.js.md`, `docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md`

**Interfaces:**
- Consumes: wire keys declared in Task 3 (`place`, `choice`, `target.labelText/fullName/siblingIndex/siblingCount`).
- Produces: readers `fullNameOf(el) -> string|null`, `siblingOf(el) -> {index, count}`, `choiceOf(el) -> {chosen, index, options}|null`, `versionOf(doc) -> string|null`, `placeOf(doc) -> {route, title, headings, tabs, grid, landmarks, version}`. Task 8's `sroPage.look({ask: "place"})` returns `placeOf(document)`; Task 11's locators use `siblingOf` and `labelOf`.

- [ ] **Step 1: Write the failing browser test**

```python
# backend/tests/browser/test_what_a_gesture_saw.py
"""What a gesture records about where the person was, in a real Chrome."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><head><title>Customer Types</title>
<meta name="version" content="7.4.2"></head><body>
<h1>Customer Types</h1>
<div role="tablist"><span role="tab" aria-selected="true">General</span><span role="tab">Other</span></div>
<form aria-label="New Customer Type">
  <label for="code">Customer code *</label><input id="code" name="code">
  <input id="pw" type="password" aria-label="Password">
  <button type="button" id="a">Add</button><button type="button" id="b">Save</button>
</form>
<ul role="listbox"><li role="option">Bulk</li><li role="option">Pallet</li><li role="option" id="retail">Retail</li></ul>
</body></html>"""


@pytest.fixture
def page() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            context = browser.new_context()
            context.add_init_script("window.__sroRecord = (j) => (window.__got = window.__got || []).push(j);")
            context.add_init_script(_recorder_script())
            context.add_init_script(path=get_settings().page_code_path)
            context.route("http://sro.test/**", lambda route: route.fulfill(body=PAGE, content_type="text/html"))
            one = context.new_page()
            one.goto("http://sro.test/customers#!/types")
            yield one
        finally:
            browser.close()


def _all(page: Any) -> list[dict[str, Any]]:
    return [json.loads(raw) for raw in page.evaluate("window.__got || []")]


def test_a_click_says_where_the_person_was(page: Any) -> None:
    page.click("#b")
    place = _all(page)[-1]["place"]
    assert place["route"] == "/customers#!/types"
    assert place["title"] == "Customer Types"
    assert place["headings"] == ["Customer Types"]
    assert place["tabs"] == ["General"]
    assert "New Customer Type" in place["landmarks"]
    assert place["version"] == "7.4.2"


def test_a_field_records_its_label_its_full_name_and_its_position(page: Any) -> None:
    page.fill("#code", "C-1")
    page.click("#a")
    typed = next(one for one in _all(page) if one["kind"] == "type")
    assert typed["target"]["labelText"] == "Customer code *"
    assert typed["target"]["fullName"] == "Customer code *"
    clicked = _all(page)[-1]
    assert (clicked["target"]["siblingIndex"], clicked["target"]["siblingCount"]) == (0, 2)


def test_a_secret_field_records_no_label_and_no_name(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#a")
    typed = next(one for one in _all(page) if one["kind"] == "type" and one["target"]["secret"])
    assert typed["target"]["labelText"] is None and typed["target"]["fullName"] is None
    assert "hunter2" not in json.dumps(_all(page))


def test_a_click_on_an_option_records_the_list_and_the_choice(page: Any) -> None:
    page.click("#retail")
    assert _all(page)[-1]["choice"] == {"chosen": "Retail", "index": 2, "options": ["Bulk", "Pallet", "Retail"]}


def test_a_click_that_is_not_an_option_records_no_choice(page: Any) -> None:
    page.click("#b")
    assert _all(page)[-1]["choice"] is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/browser/test_what_a_gesture_saw.py -q -m browser`
Expected: FAIL with `KeyError: 'place'`.

- [ ] **Step 3: Add the readers to `page-code.js`**

Inside the `readers` IIFE, after `outlineOf` and before `return {`:

```js
    const fullNameOf = (el) => {
      if (isSecretField(el)) return null;
      const doc = el.ownerDocument || document;
      const by = el.getAttribute("aria-labelledby");
      const named = by
        ? by.split(/\s+/).map((id) => doc.getElementById(id)).filter(Boolean)
            .map((one) => plainOf(one.getAttribute("aria-label") || one.innerText)).join(" ").trim()
        : "";
      const labels = el.labels && el.labels.length ? [...el.labels].map((one) => plainOf(one.innerText)).join(" ").trim() : "";
      const fromContent = ["button", "link", "tab", "menuitem", "option", "cell", "row", "heading"].includes(roleOf(el) || "");
      const said =
        named ||
        plainOf(el.getAttribute("aria-label")) ||
        labels ||
        plainOf(el.getAttribute("title") || el.getAttribute("placeholder") || el.getAttribute("alt")) ||
        (fromContent ? plainOf(el.innerText) : "");
      return said ? said.slice(0, MAX_TEXT) : null;
    };
    const siblingOf = (el) => {
      const parent = el.parentElement;
      if (!parent) return { index: 0, count: 1 };
      const role = roleOf(el);
      const same = [...parent.children].filter((one) => one.tagName === el.tagName && roleOf(one) === role);
      return { index: same.indexOf(el), count: same.length };
    };
    const OPTION_ROWS = "[role=option], .x-boundlist-item";
    const choiceOf = (el) => {
      const row = el && el.closest ? el.closest(OPTION_ROWS) : null;
      if (!row) return null;
      const list = row.closest("[role=listbox], .x-boundlist") || row.parentElement;
      const rows = list ? [...list.querySelectorAll(OPTION_ROWS)] : [row];
      return {
        chosen: plainOf(row.innerText).slice(0, MAX_TEXT) || null,
        index: rows.indexOf(row),
        options: rows.slice(0, 50).map((one) => plainOf(one.innerText).slice(0, MAX_TEXT)),
      };
    };
    const versionOf = (doc) => {
      const win = doc.defaultView || window;
      const said = win.Ext && win.Ext.getVersion ? win.Ext.getVersion() : null;
      const ext = (said && said.version) || (win.Ext && win.Ext.version);
      if (ext) return `Ext ${ext}`;
      const meta = doc.querySelector("meta[name=version], meta[name=app-version], meta[name=build]");
      if (meta && meta.content) return plainOf(meta.content).slice(0, 60);
      const main = [...doc.scripts].map((one) => one.src).filter(Boolean).pop();
      return main ? main.split("/").pop().split("?")[0].slice(0, 60) : null;
    };
    const placeOf = (doc) => {
      const win = doc.defaultView || window;
      const visible = (selector) => [...doc.querySelectorAll(selector)].filter((one) => one.getClientRects().length > 0);
      const texts = (items, cap) => [...new Set(items.map(plainOf).filter(Boolean))].slice(0, cap);
      const grid = visible("[role=grid], [role=treegrid], .x-grid")[0];
      const panel = grid && grid.closest(".x-panel");
      const panelTitle = panel && panel.querySelector(".x-title-text");
      const gridTitle = grid ? plainOf(grid.getAttribute("aria-label")) || plainOf(panelTitle ? panelTitle.innerText : "") : "";
      return {
        route: `${win.location.pathname}${win.location.hash}`,
        title: plainOf(doc.title).slice(0, MAX_TEXT) || null,
        headings: texts(visible("h1, h2, h3, [role=heading], .x-title-text").map((one) => one.innerText), 3),
        tabs: texts(visible("[role=tab][aria-selected=true], .x-tab-active").map((one) => one.innerText || one.getAttribute("aria-label")), 10),
        grid: gridTitle || null,
        landmarks: texts(visible("form, dialog, [role=dialog], [role=alertdialog], [role=form], [role=region]").map(ownName), 10),
        version: versionOf(doc),
      };
    };
```

Add `fullNameOf, siblingOf, choiceOf, versionOf, placeOf` to the readers' `return { … }` and to the destructuring `const { … } = readers;` that follows it.

- [ ] **Step 4: Use them in `recorder.js`**

Add `labelOf, fullNameOf, siblingOf, choiceOf, placeOf` to the `__PAGE_READERS__` destructuring at the top. In `describe`, before `return {`, add `const sibling = siblingOf(el);` and inside the returned object, after `landmarks: landmarksOf(el),`:

```js
      labelText: secret ? null : labelOf(el) || null,
      fullName: secret ? null : fullNameOf(el),
      siblingIndex: sibling.index,
      siblingCount: sibling.count,
```

Add two readers that never throw (after `label`):

```js
  const placeNow = () => {
    try {
      return placeOf(document);
    } catch {
      return null;
    }
  };
  const choiceNow = (el) => {
    try {
      return choiceOf(el);
    } catch {
      return null;
    }
  };
```

In `emit`, inside the `JSON.stringify({...})` object, after `outlines: sent,` add `place: placeNow(),`. In the `click` listener's record, after `trusted: e.isTrusted,` add `choice: choiceNow(e.target),`. Every existing key and listener stays exactly as it is.

- [ ] **Step 5: Regenerate and prove identity did not move**

Run:
```bash
make gen-recorder
cd backend && uv run pytest tests/browser/test_what_a_gesture_saw.py tests/browser/test_the_state_a_gesture_left.py tests/browser/test_the_screen_outline.py tests/browser/test_page_code_parity.py -q -m browser
```
then, from the repo root:
```bash
make fixtures
git diff --exit-code new-chrome-extension/fixtures/shape-identity.json new-chrome-extension/fixtures/screen-of.json
git diff --stat new-chrome-extension/fixtures
```
Expected: browser tests PASS; the `--exit-code` diff prints nothing and exits 0 (identity fixtures byte-identical); `--stat` shows only `gesture-*.json` / `batch*.json` gaining the new keys. If either identity fixture changed, stop: a new field is feeding identity — find the cause; never regenerate the fixture to make it pass.

- [ ] **Step 6: Node and unit checks**

Append to `new-chrome-extension/src/content/evidence.test.mjs`:

```js
test("a control's position counts only siblings of its own kind", () => {
  const parent = { children: [] };
  const button = () => ({ nodeType: 1, tagName: "BUTTON", parentElement: parent, getAttribute: () => null });
  const input = { nodeType: 1, tagName: "INPUT", parentElement: parent, getAttribute: () => null };
  const [a, b] = [button(), button()];
  parent.children.push(a, input, b);
  const { siblingOf } = lift(["siblingOf"], { roleOf: (el) => (el.tagName === "BUTTON" ? "button" : "textbox") });
  assert.deepEqual(siblingOf(b), { index: 1, count: 2 });
});
```

Run: `make test-extension` and `cd backend && uv run pytest tests/unit/infrastructure/test_generated_scripts_are_current.py tests/unit/infrastructure/test_what_the_recorder_hides.py tests/contract -q`
Expected: PASS.

- [ ] **Step 7: Code notes**

In `page-code.js.md` add headings for `fullNameOf` (the accessible-name order used: labelledby, aria-label, labels, title/placeholder/alt, content for roles named from content — the full AX computation needs the debugger permission the extension does not ask for), `siblingOf` (same tag **and** role, so a field's position does not move when a label is added), `choiceOf` (Ext renders the list floating, so it is read from the clicked row, never from the field), `versionOf`, `placeOf`. In `recorder.js.md` add a heading for the new keys in `describe`/`emit`: none of them is read by `targetIdentity` or `screenOf`.

- [ ] **Step 8: Commit**

Check `git status --short new-chrome-extension/fixtures` and add fixture files by name.

```bash
git add new-chrome-extension/src/page/page-code.js backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js new-chrome-extension/src/content/evidence.test.mjs backend/tests/browser/test_what_a_gesture_saw.py docs/code-notes/new-chrome-extension/src/page/page-code.js.md docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md
git add new-chrome-extension/fixtures/gesture-click.json new-chrome-extension/fixtures/gesture-type.json
git commit -m "feat(recorder): each gesture says where the person was, its label, position and combo choice"
```

(The second `git add` lists whichever fixture files `--stat` showed; every commit message ends with the two attribution lines from Global Constraints.)

---

### Task 6: What changed after the action (items 1, 4, 6, 8; 11's errors and shortcuts)

**Files:**
- Modify: `new-chrome-extension/src/page/page-code.js` (readers: `watchEffect` and its helpers)
- Modify: `backend/src/sro/infrastructure/steel/recorder.js` (start a watcher at each `emit`, finish the previous one with `"next"`, send each effect through `window.__sroEffect`; shortcuts into the open watcher)
- Modify: `new-chrome-extension/src/content/recorder-bridge.main.js` (`window.__sroEffect` → `sro:effect`)
- Modify: `new-chrome-extension/src/content/observe.js` (relay `sro:effect` as `{kind: "effect", effect, frameUrl}`)
- Modify: `new-chrome-extension/src/background/service-worker.js` (`case "effect"` under the same gate as gestures; enqueue)
- Regenerate: `make gen-recorder`, `make fixtures`
- Test: `backend/tests/browser/test_what_an_action_did.py` (new), `new-chrome-extension/src/content/observe.test.mjs` (add cases)
- Modify: `docs/code-notes/new-chrome-extension/src/page/page-code.js.md`, `docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md`

**Interfaces:**
- Consumes: `rig_wire.EffectEvent` keys (`of`, `of_at`, `effect`, `frame_path`, `url`, `tab_id`, `frame_url`) from Task 3; readers from Task 5.
- Produces: reader `watchEffect(win, onDone) -> {finish(ended) -> effect|null, shortcut(keys)}` where `effect` has exactly the keys of `rig_wire.Effect`; constants `EFFECT_QUIET_MS = 500`, `EFFECT_MAX_MS = 3000`. Task 9's `sroPage.look({ask: "watch"|"effect"})` wraps the same `watchEffect`.

- [ ] **Step 1: Write the failing browser test**

```python
# backend/tests/browser/test_what_an_action_did.py
"""The effect the recorder sends after each gesture, in a real Chrome."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<form aria-label="New Customer Type">
  <label for="code">Code</label><input id="code" aria-required="true">
  <label for="desc">Description</label><input id="desc" disabled>
  <input id="pw" type="password" aria-label="Password">
  <button type="button" id="save">Save</button>
  <button type="button" id="incomplete">Submit empty</button>
  <button type="button" id="ask">Delete</button>
  <button type="button" id="go">Go</button>
  <button type="button" id="boom">Boom</button>
</form>
<script>
  const say = (role, text) => { const d = document.createElement('div'); d.setAttribute('role', role); d.innerText = text; document.body.appendChild(d); };
  save.onclick = () => setTimeout(() => say('status', 'Customer type ' + code.value + ' saved'), 200);
  incomplete.onclick = () => { code.setAttribute('aria-invalid', 'true'); desc.disabled = false; say('alert', 'Code is required'); };
  ask.onclick = () => { const d = document.createElement('div'); d.setAttribute('role', 'dialog'); d.innerHTML = '<h2>Delete?</h2><p>Delete this row?</p><button>Yes</button><button>No</button>'; document.body.appendChild(d); };
  go.onclick = () => { history.pushState({}, '', '/customers/42'); };
  boom.onclick = () => setTimeout(() => { throw new Error('x is undefined at https://wms.example/app.js:1:2'); }, 10);
</script>
</body></html>"""


@pytest.fixture
def page() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            context = browser.new_context()
            context.add_init_script(
                "window.__sroRecord = (j) => (window.__got = window.__got || []).push(j);"
                "window.__sroEffect = (j) => (window.__did = window.__did || []).push(j);"
            )
            context.add_init_script(_recorder_script())
            context.add_init_script(path=get_settings().page_code_path)
            context.route("http://sro.test/**", lambda route: route.fulfill(body=PAGE, content_type="text/html"))
            one = context.new_page()
            one.goto("http://sro.test/customers")
            yield one
        finally:
            browser.close()


def _last(page: Any) -> dict[str, Any]:
    return json.loads(page.evaluate("window.__got[window.__got.length - 1]"))


def _effect_of(page: Any, ref: str) -> dict[str, Any]:
    page.wait_for_function(f"(window.__did || []).some((j) => JSON.parse(j).of === {json.dumps(ref)})", timeout=5000)
    return next(json.loads(raw) for raw in page.evaluate("window.__did") if json.loads(raw)["of"] == ref)


def test_a_save_that_shows_a_toast_yields_the_toast(page: Any) -> None:
    page.fill("#code", "ABC")
    page.click("#save")
    last = _last(page)
    sent = _effect_of(page, last["ref"])
    assert sent["of_at"] == last["at"]
    assert any(one["role"] == "status" and one["text"] == "Customer type ABC saved" for one in sent["effect"]["appeared"])
    assert sent["effect"]["ended"] in ("quiet", "max")


def test_a_click_that_opens_a_dialog_yields_its_title_and_buttons(page: Any) -> None:
    page.click("#ask")
    sent = _effect_of(page, _last(page)["ref"])
    dialog = next(one for one in sent["effect"]["appeared"] if one["role"] == "dialog")
    assert (dialog["title"], dialog["buttons"]) == ("Delete?", ["Yes", "No"])


def test_an_incomplete_submit_yields_the_invalid_field_and_the_one_it_enabled(page: Any) -> None:
    page.click("#incomplete")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert {"label": "Code", "change": "invalid"} in effect["fields"]
    assert {"label": "Description", "change": "enabled"} in effect["fields"]
    assert any(one["role"] == "alert" and one["text"] == "Code is required" for one in effect["appeared"])


def test_a_route_change_yields_before_and_after(page: Any) -> None:
    page.click("#go")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert (effect["route_before"], effect["route_after"]) == ("/customers", "/customers/42")


def test_an_uncaught_error_is_recorded_as_text(page: Any) -> None:
    page.click("#boom")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert any("x is undefined" in one for one in effect["errors"])


def test_the_next_gesture_ends_the_previous_effect(page: Any) -> None:
    page.click("#ask")
    first = _last(page)["ref"]
    page.click("#go")
    assert _effect_of(page, first)["effect"]["ended"] == "next"


def test_a_shortcut_is_recorded_on_the_open_effect(page: Any) -> None:
    page.click("#code")
    page.keyboard.press("Control+s")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert "ctrl+s" in effect["shortcuts"]


def test_no_effect_ever_carries_what_was_typed_in_a_secret(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#save")
    _effect_of(page, _last(page)["ref"])
    assert "hunter2" not in json.dumps(page.evaluate("window.__did"))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/browser/test_what_an_action_did.py -q -m browser`
Expected: FAIL (timeout waiting for `window.__did`).

- [ ] **Step 3: Add `watchEffect` to the readers**

Inside the `readers` IIFE, before `return {`:

```js
    const EFFECT_QUIET_MS = 500;
    const EFFECT_MAX_MS = 3000;
    const EFFECT_ITEMS = 20;
    const NOTICED = "dialog, [role=dialog], [role=alertdialog], [role=alert], [role=status], [role=row], .x-mask, .x-toast, .x-window, [role=progressbar], .x-form-error-msg";
    const BUSY = ".x-mask, [role=progressbar], [aria-busy=true]";
    const roleSeen = (el) => {
      if (el.matches(".x-mask, [role=progressbar]")) return "mask";
      if (el.matches(".x-toast")) return "toast";
      if (el.matches(".x-form-error-msg")) return "invalid";
      if (el.matches(".x-window") || el.tagName === "DIALOG") return "dialog";
      return el.getAttribute("role");
    };
    const seenOf = (el) => {
      const role = roleSeen(el);
      const dialog = role === "dialog" || role === "alertdialog";
      const heading = dialog ? el.querySelector(".x-title-text, [role=heading], h1, h2, h3") : null;
      return {
        role,
        text: plainOf(el.innerText).slice(0, MAX_TEXT) || null,
        title: heading ? plainOf(heading.innerText).slice(0, MAX_TEXT) || null : dialog ? ownName(el) : null,
        buttons: dialog
          ? [...el.querySelectorAll("button, [role=button], .x-btn")].map((one) => plainOf(one.innerText)).filter(Boolean).slice(0, 8)
          : [],
      };
    };
    const fieldStates = (doc) =>
      new Map(
        [...doc.querySelectorAll("input, select, textarea, [role=combobox], [role=textbox]")]
          .slice(0, 400)
          .filter((el) => !isSecretField(el))
          .map((el) => [
            el,
            {
              enabled: !(el.disabled === true || el.getAttribute("aria-disabled") === "true"),
              shown: el.getClientRects().length > 0,
              invalid: el.getAttribute("aria-invalid") === "true" || Boolean(el.closest(".x-form-invalid, .x-field-invalid")),
            },
          ]),
      );
    const routeOf = (win) => `${win.location.pathname}${win.location.hash}`;
    const watchEffect = (win, onDone) => {
      const doc = win.document;
      const clock = win.performance;
      const started = clock.now();
      const before = fieldStates(doc);
      const routeBefore = routeOf(win);
      const appeared = [];
      const vanished = [];
      const errors = [];
      const shortcuts = [];
      let lastChange = started;
      let busySince = doc.querySelector(BUSY) ? started : null;
      let busyMs = 0;
      let done = false;
      let timer = null;
      const noticedIn = (node) =>
        node.nodeType === 1 ? [node.matches(NOTICED) ? node : null, ...node.querySelectorAll(NOTICED)].filter(Boolean) : [];
      const observer = new win.MutationObserver((changes) => {
        lastChange = clock.now();
        for (const change of changes) {
          for (const node of change.addedNodes) for (const el of noticedIn(node)) if (appeared.length < EFFECT_ITEMS) appeared.push(seenOf(el));
          for (const node of change.removedNodes) for (const el of noticedIn(node)) if (vanished.length < EFFECT_ITEMS) vanished.push(seenOf(el));
        }
        const busy = [...doc.querySelectorAll(BUSY)].some((el) => el.getClientRects().length > 0);
        if (busy && busySince === null) busySince = clock.now();
        if (!busy && busySince !== null) {
          busyMs += clock.now() - busySince;
          busySince = null;
        }
      });
      observer.observe(doc, { childList: true, subtree: true, attributes: true, attributeFilter: ["aria-invalid", "disabled", "aria-disabled", "class", "style"] });
      const heard = (said) => {
        if (errors.length < 10) errors.push(String(said || "").slice(0, MAX_TEXT));
      };
      const onError = (e) => heard(e.message || (e.reason && e.reason.message) || e.reason);
      const quietly = win.console.error;
      const loudly = function (...args) {
        heard(args.map(String).join(" "));
        return quietly.apply(this, args);
      };
      win.console.error = loudly;
      win.addEventListener("error", onError, true);
      win.addEventListener("unhandledrejection", onError, true);
      const finish = (ended) => {
        if (done) return null;
        done = true;
        observer.disconnect();
        if (timer !== null) clearInterval(timer);
        win.removeEventListener("error", onError, true);
        win.removeEventListener("unhandledrejection", onError, true);
        if (win.console.error === loudly) win.console.error = quietly;
        const now = clock.now();
        if (busySince !== null) busyMs += now - busySince;
        const after = fieldStates(doc);
        const fields = [];
        for (const [el, was] of before) {
          const is = after.get(el);
          const label = is ? labelOf(el) : "";
          if (!label) continue;
          if (was.enabled !== is.enabled) fields.push({ label, change: is.enabled ? "enabled" : "disabled" });
          if (was.shown !== is.shown) fields.push({ label, change: is.shown ? "shown" : "hidden" });
          if (was.invalid !== is.invalid) fields.push({ label, change: is.invalid ? "invalid" : "valid" });
        }
        const loads = clock
          .getEntriesByType("resource")
          .filter((one) => one.startTime >= started && (one.initiatorType === "fetch" || one.initiatorType === "xmlhttprequest"));
        const effect = {
          appeared,
          vanished,
          route_before: routeBefore,
          route_after: routeOf(win),
          fields: fields.slice(0, 40),
          requests_ms: loads.length ? Math.round(Math.max(...loads.map((one) => one.responseEnd)) - started) : null,
          mask_ms: busyMs ? Math.round(busyMs) : null,
          quiet_ms: Math.round(lastChange - started),
          ended,
          errors,
          shortcuts,
        };
        if (onDone) onDone(effect);
        return effect;
      };
      timer = setInterval(() => {
        const now = clock.now();
        if (now - started >= EFFECT_MAX_MS) finish("max");
        else if (now - lastChange >= EFFECT_QUIET_MS && now - started >= EFFECT_QUIET_MS) finish("quiet");
      }, 100);
      return {
        finish,
        shortcut: (keys) => {
          if (!done && shortcuts.length < 10) shortcuts.push(keys);
        },
      };
    };
```

Add `watchEffect` to the readers' `return {…}` and to the destructuring after it.

- [ ] **Step 4: The recorder sends one effect per gesture**

In `recorder.js`, add `watchEffect` to the readers destructuring. After `let lastRef = null;` add:

```js
  let watching = null;
  const sendEffect = (of, of_at) => (effect) => {
    try {
      window.__sroEffect(
        JSON.stringify({ of, of_at, effect, frame_path: framePathOf(window), url: location.href }),
      );
    } catch {}
  };
```

In `emit`: first line `if (watching) watching.finish('next');`; then compute the timestamp once (`const at = Date.now() / 1000;` before the `try`) and use `at` in the `JSON.stringify` object in place of the inline `Date.now() / 1000` (same value, now shared with the effect's `of_at`). After the `try { window.__sroRecord(...) } catch {...}` block:

```js
    try {
      watching = watchEffect(window, sendEffect(ref, at));
    } catch {
      watching = null;
    }
```

In the `keydown` listener, before the existing `if (!['Enter', 'Escape', 'Tab'].includes(e.key)) return;`:

```js
    if ((e.ctrlKey || e.metaKey || e.altKey) && e.key.length === 1 && watching) {
      watching.shortcut([...modifiers(e), e.key.toLowerCase()].join('+'));
    }
```

The existing `press` gesture for Enter/Escape/Tab is unchanged, and a shortcut never becomes a gesture (a new gesture would change shape keys).

- [ ] **Step 5: Relay it to the worker**

`recorder-bridge.main.js`, inside the IIFE after `__sroRecord`:

```js
  window.__sroEffect = (json) => {
    window.dispatchEvent(new CustomEvent("sro:effect", { detail: json }));
  };
```

`observe.js`, after the `sro:gesture` listener:

```js
  window.addEventListener("sro:effect", (event) => {
    const json = event.detail;
    if (typeof json !== "string" || json.length > MAX_GESTURE_CHARS) return;
    let effect;
    try {
      effect = JSON.parse(json);
    } catch {
      return;
    }
    if (!effect || typeof effect.of !== "string" || typeof effect.of_at !== "number" || typeof effect.effect !== "object") return;
    tell({ kind: "effect", effect, frameUrl: location.href });
  });
```

`service-worker.js`: make the gate `case "gesture":` / `case "request":` also take `case "effect":`, and right after `const page_url = redactUrl(sender?.tab?.url);` (before `if (message.kind === "gesture") {`):

```js
      if (message.kind === "effect") {
        await queue.enqueue({
          ...message.effect,
          kind: "effect",
          url: redactUrl(message.effect?.url),
          tab_id,
          frame_url: redactUrl(frameUrl),
        });
        return { ok: true };
      }
```

`considerOffer` and `didItThemselves` are already guarded by `message.kind` and never fire for an effect.

- [ ] **Step 6: Relay test**

Append to `observe.test.mjs`, using its `aWorld` harness (read the harness's return value first and use its names for running the script and dispatching an event):

```js
test("an effect is relayed once, as an effect", () => {
  const world = aWorld();
  world.load();
  world.sandbox.window.dispatchEvent(new world.sandbox.CustomEvent("sro:effect", { detail: JSON.stringify({ of: "r.1", of_at: 1.5, effect: { appeared: [] } }) }));
  assert.deepEqual(world.sent.filter((one) => one.kind === "effect").length, 1);
});

test("an effect that names no gesture is not relayed", () => {
  const world = aWorld();
  world.load();
  world.sandbox.window.dispatchEvent(new world.sandbox.CustomEvent("sro:effect", { detail: JSON.stringify({ effect: {} }) }));
  assert.equal(world.sent.filter((one) => one.kind === "effect").length, 0);
});
```

- [ ] **Step 7: Regenerate, prove identity, run everything**

```bash
make gen-recorder
make fixtures
git diff --exit-code new-chrome-extension/fixtures/shape-identity.json new-chrome-extension/fixtures/screen-of.json
make test-extension
```
and
```bash
cd backend && uv run pytest tests/browser/test_what_an_action_did.py tests/browser/test_what_a_gesture_saw.py tests/browser/test_the_state_a_gesture_left.py tests/browser/test_page_code_parity.py -q -m browser
cd backend && uv run pytest tests/unit/infrastructure/test_generated_scripts_are_current.py tests/unit/infrastructure/test_what_the_recorder_hides.py tests/contract -q
```
Expected: PASS; identity fixtures unchanged.

- [ ] **Step 8: Code notes and commit**

`page-code.js.md`: a heading for `watchEffect` — ends on 500 ms of quiet, 3 s at most, or the next gesture; reads request timing from Resource Timing (no patching of the app's network); `console.error` is restored only if nobody wrapped it after us; never reads a field's value (states only). `recorder.js.md`: a heading for `sendEffect` and the `"next"` cut, and why a shortcut rides on the open effect instead of becoming a gesture.

```bash
git add new-chrome-extension/src/page/page-code.js backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js new-chrome-extension/src/content/recorder-bridge.main.js new-chrome-extension/src/content/observe.js new-chrome-extension/src/content/observe.test.mjs new-chrome-extension/src/background/service-worker.js backend/tests/browser/test_what_an_action_did.py docs/code-notes/new-chrome-extension/src/page/page-code.js.md docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md
git commit -m "feat(recorder): what changed after each action travels as an effect event"
```

(Add any fixture files `make fixtures` changed, by name.)

---

### Task 7: Page events — sign-in cookie names (optional permission) and tab focus

**Files:**
- Create: `new-chrome-extension/src/background/page-marks.js`, `new-chrome-extension/src/background/page-marks.test.mjs`
- Modify: `new-chrome-extension/src/background/service-worker.js` (`pageEvent` gains an `extra` argument spread last into the event; cookie and focus listeners)
- Modify: `new-chrome-extension/manifest.json` (`"optional_permissions": ["cookies"]`, version `0.3.0`)
- Modify: `new-chrome-extension/src/options/options.html`, `new-chrome-extension/src/options/options.js` (a button that requests the permission at runtime and shows whether it is held)
- Test: `backend/tests/unit/scripts/test_package_extension.py` (cookies optional, never required)

**Interfaces:**
- Consumes: `rig_wire.PageEvent.cookies` (Task 3).
- Produces: `page-marks.js` exports `MAIL_HOSTS`, `hostMatches(cookieDomain, url) -> boolean`, `cookieSeen(cookie) -> {name, expires_at, domain, session}`, `startCookieMarks(chromeApi, onCookie) -> Promise<boolean>`, `focusMarks(from, to) -> Array<[page_kind, tabId]>`, `threadInUrl(url) -> string|null` (used by Task 15); `pageEvent(page_kind, tab_id, url, timeStamp, opener_tab_id = null, extra = {})`.

- [ ] **Step 1: Write the failing node test**

```js
// new-chrome-extension/src/background/page-marks.test.mjs
// Run with `node --test src/background/page-marks.test.mjs`.
import assert from "node:assert/strict";
import { test } from "node:test";

import { cookieSeen, focusMarks, hostMatches, startCookieMarks, threadInUrl } from "./page-marks.js";

test("a cookie is its name and expiry, never its value", () => {
  assert.deepEqual(
    cookieSeen({ name: "JSESSIONID", value: "secret", domain: ".wms.example", expirationDate: 1790003600.5, session: false }),
    { name: "JSESSIONID", expires_at: 1790003600.5, domain: ".wms.example", session: false },
  );
  assert.deepEqual(cookieSeen({ name: "s", value: "v", domain: "wms.example", session: true }), {
    name: "s", expires_at: null, domain: "wms.example", session: true,
  });
});

test("a cookie belongs to the watched tab whose host it is set for", () => {
  assert.equal(hostMatches(".wms.example", "https://app.wms.example/a"), true);
  assert.equal(hostMatches("wms.example", "https://wms.example/a"), true);
  assert.equal(hostMatches("other.example", "https://wms.example/a"), false);
});

test("cookie marks need the permission", async () => {
  const added = [];
  const chromeApi = (granted) => ({
    permissions: { contains: async () => granted },
    cookies: { onChanged: { addListener: (fn) => added.push(fn) } },
  });
  assert.equal(await startCookieMarks(chromeApi(false), () => {}), false);
  assert.equal(added.length, 0);
  assert.equal(await startCookieMarks(chromeApi(true), () => {}), true);
  assert.equal(added.length, 1);
});

test("a removed cookie makes no mark", async () => {
  let listener = null;
  const seen = [];
  await startCookieMarks(
    { permissions: { contains: async () => true }, cookies: { onChanged: { addListener: (fn) => (listener = fn) } } },
    (cookie) => seen.push(cookie),
  );
  listener({ removed: true, cookie: { name: "a", domain: "x" } });
  listener({ removed: false, cookie: { name: "b", domain: "x", value: "v" } });
  assert.deepEqual(seen.map((one) => one.name), ["b"]);
});

test("leaving a watched tab and landing on one each make a mark", () => {
  assert.deepEqual(focusMarks({ id: 1, watched: true }, { id: 2, watched: false }), [["tab_left", 1]]);
  assert.deepEqual(focusMarks({ id: 1, watched: false }, { id: 2, watched: true }), [["tab_focused", 2]]);
  assert.deepEqual(focusMarks(null, { id: 2, watched: true }), [["tab_focused", 2]]);
});

test("a mail thread id is read from a mail tab's address and nothing else", () => {
  assert.equal(threadInUrl("https://mail.google.com/mail/u/0/#inbox/FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"), "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk");
  assert.equal(threadInUrl("https://mail.google.com/mail/u/0/#inbox"), null);
  assert.equal(threadInUrl("https://wms.example/#inbox/FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"), null);
  assert.equal(threadInUrl("https://outlook.office.com/mail/inbox/id/AAQkADAwATM3ZmYAZS1hNzQ4LTk5"), "AAQkADAwATM3ZmYAZS1hNzQ4LTk5");
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd new-chrome-extension && node --test src/background/page-marks.test.mjs`
Expected: FAIL with `Cannot find module './page-marks.js'`.

- [ ] **Step 3: Implement `page-marks.js`**

```js
// new-chrome-extension/src/background/page-marks.js
export const MAIL_HOSTS = ["mail.google.com", "outlook.office.com", "outlook.office365.com", "outlook.live.com"];

export function hostMatches(cookieDomain, url) {
  let host;
  try {
    host = new URL(url).hostname;
  } catch {
    return false;
  }
  const domain = String(cookieDomain || "").replace(/^\./, "");
  return Boolean(domain) && (host === domain || host.endsWith(`.${domain}`));
}

export function cookieSeen(cookie) {
  return {
    name: String(cookie.name),
    expires_at: typeof cookie.expirationDate === "number" ? cookie.expirationDate : null,
    domain: cookie.domain || null,
    session: Boolean(cookie.session),
  };
}

export async function startCookieMarks(chromeApi, onCookie) {
  let held = false;
  try {
    held = await chromeApi.permissions.contains({ permissions: ["cookies"] });
  } catch {
    held = false;
  }
  if (!held || !chromeApi.cookies) return false;
  chromeApi.cookies.onChanged.addListener((change) => {
    if (change.removed || !change.cookie) return;
    onCookie(cookieSeen(change.cookie));
  });
  return true;
}

export function focusMarks(from, to) {
  const marks = [];
  if (from && from.watched && (!to || from.id !== to.id)) marks.push(["tab_left", from.id]);
  if (to && to.watched && (!from || from.id !== to.id)) marks.push(["tab_focused", to.id]);
  return marks;
}

export function threadInUrl(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (!MAIL_HOSTS.includes(parsed.hostname)) return null;
  if (parsed.hostname === "mail.google.com") {
    const last = parsed.hash.split("/").pop() || "";
    return /^[A-Za-z0-9_-]{16,200}$/.test(last) ? last : null;
  }
  const match = parsed.pathname.match(/\/id\/([^/?#]{16,200})/);
  const id = match ? decodeURIComponent(match[1]).replace(/[^A-Za-z0-9_\-=+/.]/g, "") : "";
  return id || null;
}
```

- [ ] **Step 4: Wire it into the worker**

In `service-worker.js`: import `{ hostMatches, startCookieMarks, focusMarks }` from `./page-marks.js`. Change `pageEvent`'s signature to `async function pageEvent(page_kind, tab_id, url, timeStamp, opener_tab_id = null, extra = {})` and spread `...extra` as the **last** property of the enqueued object (every existing caller passes no `extra`, so enqueues exactly what it did). Add at module level:

```js
async function cookieMark(cookie) {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.id == null || !tab.url || !hostMatches(cookie.domain, tab.url)) continue;
    if (!(await isWatched(tab.id))) continue;
    await pageEvent("cookies_set", tab.id, tab.url, Date.now(), null, { cookies: [cookie] });
  }
}

void startCookieMarks(chrome, (cookie) => void cookieMark(cookie));
chrome.permissions.onAdded.addListener((added) => {
  if ((added.permissions || []).includes("cookies")) void startCookieMarks(chrome, (cookie) => void cookieMark(cookie));
});

const activeIn = new Map();
chrome.tabs.onActivated.addListener(async ({ tabId, windowId }) => {
  const before = activeIn.get(windowId) ?? null;
  activeIn.set(windowId, tabId);
  const from = before == null ? null : { id: before, watched: await isWatched(before) };
  const to = { id: tabId, watched: await isWatched(tabId) };
  for (const [kind, id] of focusMarks(from, to)) {
    const tab = await chrome.tabs.get(id).catch(() => null);
    if (tab?.url) await pageEvent(kind, id, tab.url, Date.now());
  }
});
```

`pageEvent` already refuses unwatched tabs, paused capture and excluded hosts. If `worker.test.mjs` loads the whole worker with a stubbed `chrome`, add `permissions: { contains: async () => false, onAdded: { addListener() {} } }`, `cookies: { onChanged: { addListener() {} } }` and `tabs.onActivated` to its stub so it still loads.

- [ ] **Step 5: Manifest and options**

`manifest.json`: `"version": "0.3.0"`, and after the `"permissions"` array add `"optional_permissions": ["cookies"],`.

`options.html` — inside the settings page body:

```html
<section id="cookie-names">
  <h2>Sign-in cookie names</h2>
  <p>Lets AI-SRO note the names and expiry times of cookies a sign-in sets — never their values — so a run can sign in again before a session runs out.</p>
  <button type="button" id="allow-cookie-names">Allow</button>
  <span id="cookie-names-state"></span>
</section>
```

`options.js`:

```js
const cookieState = document.getElementById("cookie-names-state");
const showCookieState = async () => {
  const held = await chrome.permissions.contains({ permissions: ["cookies"] });
  cookieState.textContent = held ? "Allowed" : "Not allowed";
  document.getElementById("allow-cookie-names").hidden = held;
};
document.getElementById("allow-cookie-names").addEventListener("click", async () => {
  await chrome.permissions.request({ permissions: ["cookies"] });
  await showCookieState();
});
void showCookieState();
```

- [ ] **Step 6: Package test**

Append to `backend/tests/unit/scripts/test_package_extension.py`:

```python
def test_cookie_names_are_an_optional_permission_never_a_required_one() -> None:
    import json

    manifest = json.loads((EXTENSION / "manifest.json").read_text())
    assert "cookies" in manifest.get("optional_permissions", [])
    assert "cookies" not in manifest["permissions"]
```

- [ ] **Step 7: Run**

Run: `make test-extension` and `cd backend && uv run pytest tests/unit/scripts/test_package_extension.py -q && uv run pytest tests/browser/test_the_extension_in_a_real_chrome.py -q -m browser`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add new-chrome-extension/src/background/page-marks.js new-chrome-extension/src/background/page-marks.test.mjs new-chrome-extension/src/background/service-worker.js new-chrome-extension/manifest.json new-chrome-extension/src/options/options.html new-chrome-extension/src/options/options.js backend/tests/unit/scripts/test_package_extension.py
git commit -m "feat(extension): sign-in cookie names behind an optional permission, and tab focus marks"
```

- [ ] **Step 9: Ship and re-record (owner)**

After the owner's "merge": `make package-extension`, install on QA, grant the cookie permission from the options page, and ask the owner to record the main QA jobs once more (customer type, warehouse equipment type, bin adjust, the mail jobs). Confirm on QA that new gestures carry `place` and `effect` (read one through the workflow evidence route that `test_workflows_route.py` exercises) before starting Phase 4's QA shadow runs.

---

## Phase 4 — Steel consumers, in shadow

Every consumer below follows one pattern, set up in Task 8:

- It runs only when `ctx.checks.watching("<check>")` (the tenant is in `steel_shadow_checks[<check>]` or `steel_promoted_checks[<check>]`); otherwise it makes **no** extra page call.
- It writes `note("<check>", "yes"|"no"|"n/a", detail)` onto the step's `StepResult.notes` (→ `workflow_run_steps.notes`). `yes` always means "this check predicts the step holds / would confirm"; `no` the opposite; `n/a` that the recording has nothing for it (an old recording). Details carry numbers, strategy names and `said_text` labels only — never a value.
- It changes the verdict only when `ctx.checks.promoted("<check>")`, and only in the directions the Global Constraints allow.
- A failure while reading the page for a check is swallowed into `n/a` (never into the verdict); `Stopped`, `Superseded` and cancellation still propagate.

### Task 8: Shadow plumbing — flags, notes, and `PageDriver.look`

**Files:**
- Create: `backend/src/sro/domain/execution/checks.py`
- Modify: `backend/src/sro/domain/execution/lanes.py` (`StepResult.notes: tuple[str, ...] = ()`, last field)
- Modify: `backend/src/sro/application/runtime/step.py` (`LaneContext.checks: Checks = field(default_factory=Checks)`, last field)
- Modify: `backend/src/sro/application/runtime/run_steps.py` (`RunSteps(..., checks: CheckFlags = CheckFlags())`; `_lane_context` passes `checks`; `_advance` and `_ask` copy notes onto `RunStep`; `_ask` gains `noted: Sequence[str] = ()`)
- Modify: `backend/src/sro/config.py` (`steel_shadow_checks`, `steel_promoted_checks`), `backend/src/sro/container.py` (pass `CheckFlags` to `RunSteps`)
- Modify: `backend/src/sro/application/ports/page.py` (`PageDriver.look`), `backend/src/sro/infrastructure/steel/driver.py` (`SteelPageDriver.look` — use the class's real name), `backend/tests/unit/fakes.py` (`FakePageDriver.look`, `looks`, `looked`)
- Modify: `new-chrome-extension/src/page/page-code.js` (`sroPage.look` with `ask: "place"`)
- Modify: `backend/tests/unit/runtime_support.py` (`steel_run(..., checks=CheckFlags())`, `lane_context(..., checks=Checks())`)
- Test: `backend/tests/unit/domain/execution/test_checks.py` (new), `backend/tests/unit/application/runtime/test_run_steps.py` (add), `backend/tests/unit/test_container_wiring.py` (add)
- Create: `docs/code-notes/backend/src/sro/domain/execution/checks.py.md`; Modify the code-notes of `lanes.py`, `step.py`, `run_steps.py`, `driver.py`, `page-code.js`

**Interfaces:**
- Consumes: `outline.said_text` (Task 2), `placeOf` reader (Task 5).
- Produces:
  - `checks.CHECKS = ("C1", "C2", "C2-stop", "C3", "C4", "C5", "C6", "C8", "C9", "C9-stop", "C10", "C11")`
  - `checks.Checks(shadow: frozenset[str] = frozenset(), on: frozenset[str] = frozenset())` with `.watching(check) -> bool`, `.promoted(check) -> bool`
  - `checks.CheckFlags(shadow: Mapping[str, Collection[str]] = {}, on: Mapping[str, Collection[str]] = {})` with `.for_tenant(tenant: str) -> Checks`
  - `checks.note(check: str, verdict: str, detail: str = "") -> str`; `checks.read_note(text: str) -> tuple[str, str, str] | None`
  - `checks.K_GATE_STEPS = 20`, `checks.K_GATE_AGREEMENT = 0.95`, `checks.ready_to_promote(*, shadowed: int, agreed: int, false_confirmations: int, regressions: int) -> bool` (used by Task 17)
  - `PageDriver.look(self, session: SessionRef, target_id: str, payload: Mapping[str, object]) -> Mapping[str, object]`; `payload["ask"]` ∈ `"place"` (this task), `"watch"`, `"effect"` (Task 9), `"locate"` (Task 11); `payload["frame_path"]` optional list
  - `FakePageDriver.looks: dict[str, Mapping[str, object]]` (answer per ask) and `FakePageDriver.looked: list[Mapping[str, object]]` (every payload asked)
  - `StepResult.notes`, `LaneContext.checks`, `RunSteps._ask(..., noted=...)`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/execution/test_checks.py
from sro.domain.execution.checks import (
    CheckFlags,
    Checks,
    note,
    read_note,
    ready_to_promote,
)


def test_a_tenant_gets_only_the_checks_named_for_it() -> None:
    flags = CheckFlags(shadow={"C1": ("qa",), "C2": ("other",), "C99": ("qa",)}, on={"C4": ("qa",)})
    checks = flags.for_tenant("qa")
    assert checks == Checks(shadow=frozenset({"C1"}), on=frozenset({"C4"}))
    assert checks.watching("C4") and checks.promoted("C4")
    assert checks.watching("C1") and not checks.promoted("C1")
    assert not checks.watching("C2")


def test_nothing_is_watched_by_default() -> None:
    assert CheckFlags().for_tenant("qa") == Checks()


def test_a_note_reads_back_as_check_verdict_and_detail() -> None:
    assert read_note(note("C1", "yes", "status Saved")) == ("C1", "yes", "status Saved")
    assert read_note(note("C2-stop", "no")) == ("C2-stop", "no", "")
    assert read_note("the operator says it was done") is None


def test_a_note_never_carries_text_shaped_like_a_value_or_token() -> None:
    assert note("C9", "yes", "key=ABC123") == "shadow:C9:yes"
    assert note("C1", "no", "a3f9b8c7d6e5f4a3b2c1d0e9f8a7b6c5") == "shadow:C1:no"


def test_the_promotion_gate() -> None:
    assert ready_to_promote(shadowed=20, agreed=19, false_confirmations=0, regressions=0)
    assert not ready_to_promote(shadowed=19, agreed=19, false_confirmations=0, regressions=0)
    assert not ready_to_promote(shadowed=40, agreed=37, false_confirmations=0, regressions=0)
    assert not ready_to_promote(shadowed=40, agreed=40, false_confirmations=1, regressions=0)
    assert not ready_to_promote(shadowed=40, agreed=40, false_confirmations=0, regressions=1)
```

Append to `test_run_steps.py`:

```python
async def test_a_lane_s_notes_reach_the_run_step() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("done", Lane.UI, notes=("shadow:C1:yes",)))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert run.steps[-1].notes == ["shadow:C1:yes"]


async def test_a_lane_s_notes_reach_the_step_it_asks_about() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, "control_not_found", notes=("shadow:C3:no",)))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert run.steps[-1].notes == ["shadow:C3:no"]
```

Append to `test_container_wiring.py`:

```python
def test_no_check_is_watched_unless_a_deployment_names_a_tenant() -> None:
    from sro.config import Settings

    settings = Settings()
    assert settings.steel_shadow_checks == {} and settings.steel_promoted_checks == {}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/unit/domain/execution/test_checks.py tests/unit/application/runtime/test_run_steps.py tests/unit/test_container_wiring.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sro.domain.execution.checks'` (create `tests/unit/domain/execution/__init__.py` if the directory is new).

- [ ] **Step 3: Implement `checks.py`**

```python
# backend/src/sro/domain/execution/checks.py
from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from sro.domain.observation.outline import said_text

CHECKS = ("C1", "C2", "C2-stop", "C3", "C4", "C5", "C6", "C8", "C9", "C9-stop", "C10", "C11")
VERDICTS = ("yes", "no", "n/a")
K_GATE_STEPS = 20
K_GATE_AGREEMENT = 0.95

_NOTE = re.compile(r"shadow:(C\d+(?:-stop)?):(yes|no|n/a)(?: (.*))?")


@dataclass(frozen=True, slots=True)
class Checks:
    shadow: frozenset[str] = frozenset()
    on: frozenset[str] = frozenset()

    def watching(self, check: str) -> bool:
        return check in self.shadow or check in self.on

    def promoted(self, check: str) -> bool:
        return check in self.on


@dataclass(frozen=True, slots=True)
class CheckFlags:
    shadow: Mapping[str, Collection[str]] = field(default_factory=dict)
    on: Mapping[str, Collection[str]] = field(default_factory=dict)

    def for_tenant(self, tenant: str) -> Checks:
        return Checks(
            frozenset(name for name, who in self.shadow.items() if name in CHECKS and tenant in who),
            frozenset(name for name, who in self.on.items() if name in CHECKS and tenant in who),
        )


def note(check: str, verdict: str, detail: str = "") -> str:
    said = said_text(detail) if detail else None
    return f"shadow:{check}:{verdict}" + (f" {said}" if said else "")


def read_note(text: str) -> tuple[str, str, str] | None:
    found = _NOTE.fullmatch(text)
    return None if found is None else (found[1], found[2], found[3] or "")


def ready_to_promote(
    *, shadowed: int, agreed: int, false_confirmations: int, regressions: int
) -> bool:
    return (
        shadowed >= K_GATE_STEPS
        and agreed >= K_GATE_AGREEMENT * shadowed
        and false_confirmations == 0
        and regressions == 0
    )
```

- [ ] **Step 4: Thread it through**

- `lanes.py`, `StepResult`: add `notes: tuple[str, ...] = ()` as the last field.
- `step.py`, `LaneContext`: add `checks: Checks = field(default_factory=Checks)` as the last field (import `Checks`).
- `config.py`, beside `steel_tenants`: `steel_shadow_checks: dict[str, tuple[str, ...]] = Field(default_factory=dict)` and `steel_promoted_checks: dict[str, tuple[str, ...]] = Field(default_factory=dict)` (set per deployment as JSON, e.g. `SRO_STEEL_SHADOW_CHECKS='{"C1": ["qa"]}'` — confirm the env prefix with `grep -n env_prefix backend/src/sro/config.py`).
- `container.py`, in the `RunSteps(...)` call: `checks=CheckFlags(self.settings.steel_shadow_checks, self.settings.steel_promoted_checks),`.
- `run_steps.py`: `__init__` takes `checks: CheckFlags = CheckFlags()` (keyword) and stores `self._checks`; `_lane_context` passes `checks=self._checks.for_tenant(ctx.tenant_id.value)` into `LaneContext(...)`; in `_advance`'s `RunStep(...)` add `notes=list(result.notes),`; `_ask` gains keyword `noted: Sequence[str] = ()` and its `RunStep(...)` gets `notes=[*(last.notes if last is not None else ()), *noted],`.
- `runtime_support.py`: `steel_run(..., checks: CheckFlags = CheckFlags())` passes it to `_worker`, which passes `checks=checks` to `RunSteps`; `lane_context(..., checks: Checks = Checks())` passes it to `LaneContext`.

- [ ] **Step 5: `PageDriver.look`**

Port (`ports/page.py`, in `PageDriver`):

```python
    async def look(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> Mapping[str, object]: ...
```

Steel driver (beside `outline`):

```python
    async def look(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        page = await self._page(session, target_id)
        hops = payload.get("frame_path")
        frame, _ = await self._frame(page, {"frame_path": hops if isinstance(hops, list) else []})
        if frame is None:
            return {}
        got = await self._call(
            session, target_id, page, lambda: frame.evaluate("p => globalThis.sroPage.look(p)", dict(payload))
        )
        return got if isinstance(got, dict) else {}
```

Fake (`FakePageDriver`): in `__init__` add `self.looks: dict[str, Mapping[str, object]] = {}` and `self.looked: list[Mapping[str, object]] = []`; method:

```python
    async def look(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        self.looked.append(dict(payload))
        return self.looks.get(str(payload.get("ask")), {})
```

`page-code.js`, in `sroPage` after `outline()`:

```js
    async look(payload) {
      const ask = payload && payload.ask;
      if (ask === "place") return { place: placeOf(document) };
      return {};
    },
```

Add a shared reader for lanes in `backend/src/sro/application/runtime/step.py`:

```python
async def looked(driver: PageDriver, held: Held, payload: Mapping[str, object]) -> Mapping[str, object]:
    try:
        return await driver.look(held.session, held.target_id, payload)
    except (Stopped, Superseded):
        raise
    except Exception:
        logger.info("a shadow check could not read the page", exc_info=True)
        return {}
```

(`step.py` may not import `PageDriver` if that creates an import cycle — then put `looked` in a new `backend/src/sro/application/runtime/shadow.py` and import it from there in Tasks 9–16. Use the same name, `looked`, either way.)

- [ ] **Step 6: Code notes**

`checks.py.md`: what `yes`/`no`/`n/a` mean for every check (copy the table from the top of Phase 4), why details pass `said_text` (notes are kept forever), and the gate numbers come from the spec. `run_steps.py.md`: notes ride on `StepResult` so every exit (`_advance`, `_ask`) keeps them. `driver.py.md` and `page-code.js.md`: `look` is read-only, one ask per call.

- [ ] **Step 7: Run**

Run: `cd backend && uv run pytest tests/unit -q -x && uv run mypy src && uv run lint-imports && uv run ruff check src tests`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/sro/domain/execution/checks.py backend/src/sro/domain/execution/lanes.py backend/src/sro/application/runtime/step.py backend/src/sro/application/runtime/run_steps.py backend/src/sro/config.py backend/src/sro/container.py backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/tests/unit/fakes.py backend/tests/unit/runtime_support.py new-chrome-extension/src/page/page-code.js backend/tests/unit/domain/execution/test_checks.py backend/tests/unit/domain/execution/__init__.py backend/tests/unit/application/runtime/test_run_steps.py backend/tests/unit/test_container_wiring.py docs/code-notes
git commit -m "feat(steel): per-tenant shadow checks write notes onto run steps; the page can be looked at"
```

(`git add docs/code-notes` stages only the notes files this task touched; check `git status --short docs/code-notes` first and add them by name if anything else appears.)

---

### Task 9: C1 + C4 + C6 — confirm a write by what the page did; wait as long as the step needs; dialogs as a chain

**Files:**
- Create: `backend/src/sro/domain/execution/effects.py`
- Modify: `backend/src/sro/application/runtime/ui_lane.py` (`_perform`: arm the watcher after `mark`, use the C4 deadline, read the live effect, note C1/C4/C6, promote C1)
- Modify: `new-chrome-extension/src/page/page-code.js` (`look` asks `"watch"` and `"effect"`)
- Test: `backend/tests/unit/domain/execution/test_effects.py` (new), `backend/tests/unit/application/runtime/test_the_ui_lane.py` (add), `backend/tests/integration/test_runs_on_local_steel.py` (append one test)
- Create/Modify code-notes for `effects.py`, `ui_lane.py`, `page-code.js`

**Interfaces:**
- Consumes: `gesture.Effect/Seen` (Task 2), `seen.effect_from` (Task 2), `checks.note` and `looked` (Task 8), `watchEffect` reader (Task 6).
- Produces:
  - `effects.CONFIRMING = frozenset({"dialog", "alertdialog", "alert", "status", "toast", "row"})`, `effects.K_SLOW = 2.0`
  - `effects.typed_values(by_id: Mapping[str, Gesture]) -> tuple[str, ...]` (values the recording typed or selected, never secret ones)
  - `effects.templated(text: str, values: Iterable[str]) -> str`
  - `effects.signs(effect: Effect, values: Iterable[str]) -> frozenset[str]`
  - `effects.confirms(recorded: Effect, live: Effect, recorded_values: Iterable[str], values: Iterable[str]) -> bool`
  - `effects.settle_ms(effect: Effect | None) -> int | None`, `effects.waited_s(base_s: float, recorded: Effect | None) -> float`
  - `effects.dialog_opened(effect: Effect | None) -> Seen | None`, `effects.chain_matches(recorded: Effect, live: Effect, recorded_values, values) -> bool | None`
  - page-code asks: `look({ask: "watch"})` → `{watching: true}`; `look({ask: "effect"})` → `{effect: <Effect wire dict>|null}` (awaits quiet/max)

- [ ] **Step 1: Write the failing domain tests**

```python
# backend/tests/unit/domain/execution/test_effects.py
from sro.domain.execution.effects import (
    chain_matches,
    confirms,
    settle_ms,
    signs,
    templated,
    waited_s,
)
from sro.domain.observation.gesture import Effect, FieldChange, Seen

SAVED = Effect(appeared=(Seen("status", "Customer type ABC saved"),), quiet_ms=800)


def test_a_value_in_page_text_becomes_a_slot() -> None:
    assert templated("Customer type ABC saved", ["ABC"]) == "Customer type {} saved"
    assert templated("Customer type ABC saved", ["A"]) == "Customer type ABC saved"


def test_a_toast_naming_the_run_s_own_value_confirms() -> None:
    live = Effect(appeared=(Seen("status", "Customer type XYZ saved"),))
    assert confirms(SAVED, live, ["ABC"], ["XYZ"])


def test_a_different_toast_does_not_confirm() -> None:
    live = Effect(appeared=(Seen("status", "Customer type XYZ could not be saved"),))
    assert not confirms(SAVED, live, ["ABC"], ["XYZ"])


def test_a_recording_that_showed_nothing_confirms_nothing() -> None:
    assert not confirms(Effect(), Effect(appeared=(Seen("status", "Saved"),)), [], [])


def test_a_field_that_turned_invalid_live_never_confirms() -> None:
    live = Effect(appeared=SAVED.appeared, fields=(FieldChange("Code", "invalid"),))
    assert not confirms(SAVED, live, ["ABC"], ["ABC"])


def test_a_route_change_is_a_sign() -> None:
    moved = Effect(route_before="/a", route_after="/a/{id}")
    assert "route /a/{id}" in signs(moved, [])


def test_a_wait_is_never_shorter_than_today_s() -> None:
    assert waited_s(15.0, Effect(requests_ms=2_000)) == 15.0
    assert waited_s(15.0, Effect(mask_ms=12_000)) == 24.0
    assert waited_s(15.0, None) == 15.0
    assert settle_ms(Effect(requests_ms=100, mask_ms=900, quiet_ms=400)) == 900


def test_a_dialog_chain_matches_by_title_and_buttons() -> None:
    asked = Effect(appeared=(Seen("dialog", "Delete ABC?", "Delete?", ("Yes", "No")),))
    assert chain_matches(asked, Effect(appeared=(Seen("dialog", "Delete XYZ?", "Delete?", ("Yes", "No")),)), ["ABC"], ["XYZ"])
    assert chain_matches(asked, Effect(), ["ABC"], ["XYZ"]) is False
    assert chain_matches(Effect(), Effect(), [], []) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/unit/domain/execution/test_effects.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `effects.py`**

```python
# backend/src/sro/domain/execution/effects.py
from __future__ import annotations

from collections.abc import Iterable, Mapping

from sro.domain.observation.gesture import Effect, Gesture, Seen

CONFIRMING = frozenset({"dialog", "alertdialog", "alert", "status", "toast", "row"})
K_SLOW = 2.0
K_SHORTEST_VALUE = 2


def typed_values(by_id: Mapping[str, Gesture]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            one.action.value
            for one in by_id.values()
            if one.action.kind in ("type", "select")
            and one.action.value
            and not one.action.secret
            and not (one.action.target and one.action.target.secret)
        )
    )


def templated(text: str, values: Iterable[str]) -> str:
    out = text
    for value in sorted((v for v in values if len(v) >= K_SHORTEST_VALUE), key=len, reverse=True):
        out = out.replace(value, "{}")
    return out


def _said(one: Seen, values: Iterable[str]) -> str:
    return templated(one.title or one.text or "", values)


def signs(effect: Effect, values: Iterable[str]) -> frozenset[str]:
    kept = list(values)
    found = {f"{one.role} {_said(one, kept)}" for one in effect.appeared if one.role in CONFIRMING}
    if effect.route_after and effect.route_after != effect.route_before:
        found.add(f"route {effect.route_after}")
    return frozenset(found)


def confirms(
    recorded: Effect, live: Effect, recorded_values: Iterable[str], values: Iterable[str]
) -> bool:
    wanted = signs(recorded, recorded_values)
    if not wanted or any(one.change == "invalid" for one in live.fields):
        return False
    return wanted <= signs(live, values)


def settle_ms(effect: Effect | None) -> int | None:
    if effect is None:
        return None
    seen = [ms for ms in (effect.requests_ms, effect.mask_ms, effect.quiet_ms) if ms is not None]
    return max(seen) if seen else None


def waited_s(base_s: float, recorded: Effect | None) -> float:
    took = settle_ms(recorded)
    return base_s if took is None else max(base_s, took / 1000 * K_SLOW)


def dialog_opened(effect: Effect | None) -> Seen | None:
    if effect is None:
        return None
    return next((one for one in effect.appeared if one.role in ("dialog", "alertdialog")), None)


def chain_matches(
    recorded: Effect, live: Effect, recorded_values: Iterable[str], values: Iterable[str]
) -> bool | None:
    asked = dialog_opened(recorded)
    if asked is None:
        return None
    seen = dialog_opened(live)
    return (
        seen is not None
        and _said(seen, values) == _said(asked, recorded_values)
        and seen.buttons == asked.buttons
    )
```

- [ ] **Step 4: page-code asks**

In `sroPage.look`, before `return {};`:

```js
      if (ask === "watch") {
        if (globalThis.__sroWatch) globalThis.__sroWatch.finish("next");
        globalThis.__sroWatch = watchEffect(window, null);
        return { watching: true };
      }
      if (ask === "effect") {
        const open = globalThis.__sroWatch;
        if (!open) return { effect: null };
        const quiet = await new Promise((resolve) => {
          const until = Date.now() + 3500;
          const tick = setInterval(() => {
            if (Date.now() - until >= 0) {
              clearInterval(tick);
              resolve(open.finish("max"));
            }
          }, 100);
          const ended = open.finish.bind(open);
          setTimeout(() => {
            clearInterval(tick);
            resolve(ended("quiet"));
          }, 600);
        });
        globalThis.__sroWatch = null;
        return { effect: quiet };
      }
```

Simpler and equivalent is acceptable: `watchEffect(window, onDone)` with an `onDone` that resolves a stored promise; then `ask === "effect"` returns `await` that promise (it resolves at quiet/max by the watcher's own timer) with a 3.5 s guard that calls `finish("max")`. Prefer that form:

```js
      if (ask === "watch") {
        if (globalThis.__sroWatch) globalThis.__sroWatch.handle.finish("next");
        let settle;
        const done = new Promise((resolve) => (settle = resolve));
        globalThis.__sroWatch = { done, handle: watchEffect(window, (effect) => settle(effect)) };
        return { watching: true };
      }
      if (ask === "effect") {
        const open = globalThis.__sroWatch;
        if (!open) return { effect: null };
        const guard = setTimeout(() => open.handle.finish("max"), 3500);
        const effect = await open.done;
        clearTimeout(guard);
        globalThis.__sroWatch = null;
        return { effect };
      }
```

Use this second form only (delete the first block); it is the one the integration test exercises.

- [ ] **Step 5: Write the failing ui_lane tests**

Append to `test_the_ui_lane.py` (add imports: `from sro.domain.execution.checks import Checks`, `from sro.domain.observation.gesture import Effect, Seen`):

```python
def _saved_step_with(effect: Effect | None):  # type: ignore[no-untyped-def]
    step, by_id = save_step(status=201)
    (gid,) = by_id
    by_id[gid] = replace(by_id[gid], action=replace(by_id[gid].action, effect=effect))
    return step, by_id


TOAST = {"effect": {"appeared": [{"role": "status", "text": "Customer type saved"}], "ended": "quiet"}}


async def test_c1_in_shadow_notes_a_confirmation_and_leaves_unknown_alone() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="css_path"), calls=[])
    driver.looks["effect"] = TOAST
    step, by_id = _saved_step_with(Effect(appeared=(Seen("status", "Customer type saved"),)))

    result = await UiLane(driver).execute(step, {}, lane_context(by_id, checks=Checks(shadow=frozenset({"C1"}))))

    assert result.verdict == "unknown"
    assert "shadow:C1:yes" in [one.split(" ")[0] for one in result.notes]


async def test_a_promoted_c1_turns_unknown_into_done_when_the_page_confirms() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="css_path"), calls=[])
    driver.looks["effect"] = TOAST
    step, by_id = _saved_step_with(Effect(appeared=(Seen("status", "Customer type saved"),)))

    result = await UiLane(driver).execute(step, {}, lane_context(by_id, checks=Checks(on=frozenset({"C1"}))))

    assert result.verdict == "done"
    assert result.reason == "the page showed what the recording showed"


async def test_a_promoted_c1_never_turns_a_failed_or_done_write_around() -> None:
    rejected = scripted_driver(answer=PageAnswer(ok=True), calls=[SeenCall("POST", SAVE_URL, 500, "")])
    rejected.looks["effect"] = TOAST
    step, by_id = _saved_step_with(Effect(appeared=(Seen("status", "Customer type saved"),)))
    on = Checks(on=frozenset({"C1"}))
    assert (await UiLane(rejected).execute(step, {}, lane_context(by_id, checks=on))).verdict == "failed"

    confirmed = scripted_driver(answer=PageAnswer(ok=True), calls=[SAVED])
    confirmed.looks["effect"] = {"effect": None}
    assert (await UiLane(confirmed).execute(step, {}, lane_context(by_id, checks=on))).verdict == "done"


async def test_a_repaired_match_stays_unknown_even_when_promoted() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="repair", repaired=True), calls=[])
    driver.looks["effect"] = TOAST
    step, by_id = _saved_step_with(Effect(appeared=(Seen("status", "Customer type saved"),)))

    result = await UiLane(driver).execute(step, {}, lane_context(by_id, checks=Checks(on=frozenset({"C1"}))))

    assert result.verdict == "unknown"


async def test_no_check_watched_means_no_page_look() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True), calls=[SAVED])
    step, by_id = _saved_step_with(Effect(appeared=(Seen("status", "Saved"),)))

    await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert driver.looked == []


async def test_c4_promoted_waits_longer_for_a_slow_recorded_step_never_shorter() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True), calls=[SAVED])
    step, by_id = _saved_step_with(Effect(mask_ms=12_000))

    await UiLane(driver, wait_s=15.0).execute(step, {}, lane_context(by_id, checks=Checks(on=frozenset({"C4"}))))

    assert driver.waited_for_call_deadlines[-1] == 24.0


async def test_an_old_recording_with_c1_c4_c6_shadowed_says_n_a_and_acts_as_today() -> None:
    today = await UiLane(scripted_driver(answer=PageAnswer(ok=True), calls=[])).execute(*_old(), lane_context(_old()[2]))
    driver = scripted_driver(answer=PageAnswer(ok=True), calls=[])
    shadowed = await UiLane(driver).execute(*_old(), lane_context(_old()[2], checks=Checks(shadow=frozenset({"C1", "C4", "C6"}))))
    assert (shadowed.verdict, shadowed.reason) == (today.verdict, today.reason)
    assert {one.split(" ")[0] for one in shadowed.notes} == {"shadow:C1:n/a", "shadow:C4:n/a", "shadow:C6:n/a"}
```

with the helper

```python
def _old():  # type: ignore[no-untyped-def]
    step, by_id = save_step(status=201)
    return step, {}, by_id
```

(adjust `_old` so `execute(step, values, ctx)` is called with `values={}`; the point is: no `effect` on the recorded gesture.) `FakePageDriver` needs `waited_for_call_deadlines: list[float]` appended in `wait_for_call` — add it in this task's `fakes.py` change. `SAVE_URL` is importable from `tests.unit.runtime_support`.

- [ ] **Step 6: Run to verify failure**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_ui_lane.py -q`
Expected: the new tests FAIL (no notes; `looked` empty; deadline 15.0).

- [ ] **Step 7: Implement in `ui_lane.py`**

Imports: `from sro.domain.execution.checks import note`, `from sro.domain.execution.effects import chain_matches, confirms, settle_ms, typed_values, waited_s`, `from sro.domain.observation.seen import effect_from`, and `looked` (Task 8).

In `_perform`, right after `mark = await self._driver.mark(...)`:

```python
        recorded_effect = primary.action.effect
        watching = any(ctx.checks.watching(one) for one in ("C1", "C4", "C6", "C11"))
        if watching:
            await looked(self._driver, held, {"ask": "watch", "frame_path": payload.get("frame_path")})
        deadline = (
            waited_s(self._wait_s, recorded_effect) if ctx.checks.promoted("C4") else self._wait_s
        )
```

Use `deadline` in place of `self._wait_s` in the `wait_for_call(...)` call and pass it into `_holds` (add a `deadline_s: float` parameter to `_holds`, defaulting to `self._wait_s` at its other call site via `deadline`).

Add a method:

```python
    async def _effect_notes(
        self, held: Held, primary: Gesture, values: Mapping[str, str], ctx: LaneContext, started: float
    ) -> tuple[tuple[str, ...], bool]:
        live = effect_from((await looked(self._driver, held, {"ask": "effect"})).get("effect"))
        recorded = primary.action.effect
        then, now = typed_values(ctx.by_id), tuple(values.values())
        notes: list[str] = []
        confirmed = False
        if ctx.checks.watching("C1"):
            if recorded is None or live is None:
                notes.append(note("C1", "n/a"))
            else:
                confirmed = confirms(recorded, live, then, now)
                notes.append(note("C1", "yes" if confirmed else "no"))
        if ctx.checks.watching("C4"):
            took, live_took = settle_ms(recorded), settle_ms(live)
            notes.append(
                note("C4", "n/a")
                if took is None
                else note("C4", "yes" if live_took is None or live_took <= took * 2 else "no", f"recorded {took} ms live {live_took} ms")
            )
        if ctx.checks.watching("C6"):
            chained = None if recorded is None or live is None else chain_matches(recorded, live, then, now)
            notes.append(note("C6", "n/a" if chained is None else "yes" if chained else "no"))
        return tuple(notes), confirmed
```

In the write branch, replace the final `return StepResult(verdict or "unknown", ...)` with:

```python
            notes, confirmed = (
                await self._effect_notes(held, primary, values_of(ctx), ctx, 0.0) if watching else ((), False)
            )
            if (
                verdict is None
                and not answer.repaired
                and confirmed
                and ctx.checks.promoted("C1")
            ):
                return StepResult(
                    "done",
                    Lane.UI,
                    "the page showed what the recording showed",
                    read=made,
                    calls=calls,
                    notes=notes,
                )
            return StepResult(
                verdict or "unknown",
                Lane.UI,
                read=made,
                calls=calls,
                keyed=confirming(found, wanted) if verdict == "done" else {},
                notes=notes,
            )
```

`values` is not in `_perform`'s signature today — add a `values: Mapping[str, str]` parameter to `_perform` and pass `values` from both call sites in `execute` (replace `values_of(ctx)` above with that parameter; the `started` argument is unused — drop it). The early `failed` return ("the system rejected the write") and the non-write branches also return the notes when `watching` (call `_effect_notes` before returning and pass `notes=`), never changing their verdicts. Note: `verdict is None` is exactly the "nothing confirms it" case; `verdict == "unknown"` after a repaired match or an after-state that did not hold is never promoted.

- [ ] **Step 8: Integration test (real Steel)**

Append to `backend/tests/integration/test_runs_on_local_steel.py`, modelled on `test_a_field_nobody_demonstrated_is_filled_confirmed_by_the_save_and_learned` (same `world`/`_a_run`/`_run_to_its_end` helpers): the rig's save endpoint answers 202 with no body the lane recognises (so today's verdict is `unknown`) and the page shows a status "Saved"; the recorded save gesture carries `Effect(appeared=(Seen("status", "Saved"),))`. Run once with `CheckFlags(shadow={"C1": (tenant,)})` and assert the step is `unclear` with note `shadow:C1:yes`; run again with `CheckFlags(on={"C1": (tenant,)})` and assert the step is `held` with reason `the page showed what the recording showed`. Name it `test_a_save_the_page_confirms_is_noted_in_shadow_and_held_when_promoted`.

- [ ] **Step 9: Run**

Run: `cd backend && uv run pytest tests/unit -q -x && uv run mypy src && uv run pytest tests/integration/test_runs_on_local_steel.py -q -k "page_confirms"` (the last skips without local Steel; run `make up` first).
Expected: PASS.

- [ ] **Step 10: Code notes and commit**

`effects.py.md`: values ≥ 2 characters are slotted (a one-letter value would slot every "a"); an invalid field live vetoes; waits only grow (`K_SLOW` = 2× the recorded settle). `ui_lane.py.md`: promotion only on `verdict is None and not repaired`.

```bash
git add backend/src/sro/domain/execution/effects.py backend/src/sro/application/runtime/ui_lane.py new-chrome-extension/src/page/page-code.js backend/tests/unit/domain/execution/test_effects.py backend/tests/unit/application/runtime/test_the_ui_lane.py backend/tests/unit/fakes.py backend/tests/integration/test_runs_on_local_steel.py docs/code-notes/backend/src/sro/domain/execution/effects.py.md docs/code-notes/backend/src/sro/application/runtime/ui_lane.py.md docs/code-notes/new-chrome-extension/src/page/page-code.js.md
git commit -m "feat(steel): C1, C4 and C6 in shadow - confirm by what the page did, wait as long as the step needs"
```

---

### Task 10: C2 — know the screen (and C2-stop, shadow only)

**Files:**
- Create: `backend/src/sro/domain/execution/place.py`
- Modify: `backend/src/sro/application/runtime/run_steps.py` (`_shadow_place` before `executor.run`; resume note on the first step an attempt runs after `progress.step > 0`)
- Test: `backend/tests/unit/domain/execution/test_place.py` (new), `backend/tests/unit/application/runtime/test_run_steps.py` (add), integration test appended
- Code-notes for `place.py`, `run_steps.py`

**Interfaces:**
- Consumes: `gesture.Place`, `seen.place_from`, `checks.note`, `looked`, `PageDriver.look({ask: "place"})` (Task 8). `RunSteps` reaches the page through `self._broker` — add `SessionBroker.look(self, ctx, held, payload) -> Mapping[str, object]` delegating to `self._driver.look(held.session, held.target_id, payload)` (one line, beside `screenshot`).
- Produces: `place.place_match(recorded: Place, live: Place) -> float` (0..1), `place.K_SAME_SCREEN = 0.6`, `place.K_WRONG_SCREEN = 0.2`, `place.best_step(places: Sequence[tuple[int, Place]], live: Place) -> int | None`.

- [ ] **Step 1: Failing domain tests**

```python
# backend/tests/unit/domain/execution/test_place.py
from sro.domain.execution.place import K_SAME_SCREEN, K_WRONG_SCREEN, best_step, place_match
from sro.domain.observation.gesture import Place

LIST = Place(route="/customers", title="Customer Types", headings=("Customer Types",), grid="Customer Types")
FORM = Place(route="/customers#!/new", title="Customer Types", headings=("New Customer Type",), landmarks=("New Customer Type",))


def test_the_same_screen_matches() -> None:
    assert place_match(LIST, LIST) == 1.0


def test_another_screen_of_the_app_does_not() -> None:
    assert place_match(LIST, FORM) < K_SAME_SCREEN


def test_a_wholly_different_screen_is_clearly_wrong() -> None:
    assert place_match(LIST, Place(route="/bins", title="Bins", headings=("Bins",))) <= K_WRONG_SCREEN


def test_an_empty_place_matches_nothing() -> None:
    assert place_match(Place(), LIST) == 0.0


def test_resume_picks_the_step_whose_place_matches_best() -> None:
    assert best_step([(1, LIST), (2, FORM)], FORM) == 2
    assert best_step([(1, LIST)], Place(route="/bins")) is None
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/unit/domain/execution/test_place.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `place.py`**

```python
# backend/src/sro/domain/execution/place.py
from __future__ import annotations

from collections.abc import Sequence

from sro.domain.observation.gesture import Place

K_SAME_SCREEN = 0.6
K_WRONG_SCREEN = 0.2


def _words(place: Place) -> frozenset[str]:
    parts = [
        ("route", place.route),
        ("title", place.title),
        ("grid", place.grid),
        *(("heading", one) for one in place.headings),
        *(("tab", one) for one in place.tabs),
        *(("landmark", one) for one in place.landmarks),
    ]
    return frozenset(f"{kind}:{said}" for kind, said in parts if said)


def place_match(recorded: Place, live: Place) -> float:
    want, have = _words(recorded), _words(live)
    if not want or not have:
        return 0.0
    return len(want & have) / len(want | have)


def best_step(places: Sequence[tuple[int, Place]], live: Place) -> int | None:
    scored = [(place_match(one, live), order) for order, one in places]
    best = max(scored, default=(0.0, -1))
    return best[1] if best[0] >= K_SAME_SCREEN else None
```

- [ ] **Step 4: Failing run-steps tests**

Append to `test_run_steps.py` (imports: `CheckFlags`, `Place`, `TENANT`):

```python
def _placed(step_and_by_id, place):  # type: ignore[no-untyped-def]
    step, by_id = step_and_by_id
    (gid,) = by_id
    return step, {gid: replace(by_id[gid], action=replace(by_id[gid].action, place=place))}


async def test_c2_notes_how_well_the_live_screen_matches_and_changes_nothing() -> None:
    form = Place(route="/app", title="Customer Types", headings=("New",))
    world = await steel_run(steps=[_placed(save_step(status=201), form)], checks=CheckFlags(shadow={"C2": (TENANT,)}))
    world.driver.looks["place"] = {"place": {"route": "/app", "title": "Customer Types", "headings": ["New"]}}
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert run.steps[-1].verdict == "held"
    assert run.steps[-1].notes[0].startswith("shadow:C2:yes")


async def test_c2_stop_in_shadow_says_it_would_ask_and_the_write_still_goes() -> None:
    form = Place(route="/app", title="Customer Types", headings=("New",))
    world = await steel_run(steps=[_placed(save_step(status=201), form)], checks=CheckFlags(shadow={"C2-stop": (TENANT,)}))
    world.driver.looks["place"] = {"place": {"route": "/bins", "title": "Bins", "headings": ["Bins"]}}
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert run.steps[-1].verdict == "held"
    assert "shadow:C2-stop:no" in [one.split(" ")[0] for one in run.steps[-1].notes]


async def test_c2_stop_promoted_asks_before_a_write_on_a_clearly_wrong_screen() -> None:
    form = Place(route="/app", title="Customer Types", headings=("New",))
    world = await steel_run(steps=[_placed(save_step(status=201), form)], checks=CheckFlags(on={"C2-stop": (TENANT,)}))
    world.driver.looks["place"] = {"place": {"route": "/bins", "title": "Bins", "headings": ["Bins"]}}

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert world.lanes.ui.ran == []
```

(`world.driver` is the `FakePageDriver` in `SteelRun`; if `RecordingLane` names its call log differently than `ran`, use its name. `steel_run` gained `checks` in Task 8.)

- [ ] **Step 5: Implement in `run_steps.py`**

```python
    async def _shadow_place(
        self, ctx: RequestContext, lane: LaneContext, step: Step, writes_now: bool, notes: list[str]
    ) -> NeedsAPerson | None:
        watching = [one for one in ("C2", "C2-stop") if lane.checks.watching(one)]
        primary = primary_gesture(step, lane.by_id)
        if not watching or lane.held is None or primary is None:
            return None
        recorded = primary.action.place
        live = place_from((await self._broker.look(ctx, lane.held, {"ask": "place"})).get("place"))
        if recorded is None or live is None:
            notes.extend(note(one, "n/a") for one in watching)
            return None
        score = place_match(recorded, live)
        if "C2" in watching:
            notes.append(note("C2", "yes" if score >= K_SAME_SCREEN else "no", f"match {score:.2f}"))
        if "C2-stop" in watching and writes_now:
            wrong = score <= K_WRONG_SCREEN
            notes.append(note("C2-stop", "no" if wrong else "yes", f"match {score:.2f}"))
            if wrong and lane.checks.promoted("C2-stop"):
                return NeedsAPerson(
                    f"'{step.says}' is about to write, and the page does not look like the screen it was recorded on; check it and answer",
                    kind="step",
                )
        return None
```

`self._broker.look` must swallow page errors the way `looked` does (implement `SessionBroker.look` with the same try/except, re-raising `Stopped`/`Superseded`). In `step()`, declare `pre: list[str] = []` before the `try:`; after `lane = await self._lane_context(...)` and the `field_key`/`in_doubt` early returns, before `broken = ...`:

```python
            asked_here = await self._shadow_place(ctx, lane, step, writes(step, by_id), pre)
            if asked_here is not None:
                return StepOutcome(more=True, asking=await self._ask(ctx, run, step, asked_here, index=index, noted=pre))
```

After `last = tried[-1] if tried else ...`: `last = replace(last, notes=(*pre, *last.notes))` — and make every following branch use this `last` (they already do). Also pass `noted=pre` in the `except (NeedsAPerson, ...)` branch's `_ask` call.

Resume (C2 note only — see Spec gaps: promotion asks, never jumps): when `progress.step > 0` and no `run.steps` row exists for any step at or after `ordered[index].order` in this run, add, inside `_shadow_place` when `"C2"` is watched, `note("C2", "yes" if best == step.order else "no", f"resume picks {best}")` where `best = best_step([(one.order, p) for one in ordered if (g := primary_gesture(one, lane.by_id)) and (p := g.action.place)], live)`. Promoted C2 at resume: if `best is not None and best != step.order`, return `NeedsAPerson("the page looks like the screen of step {best}, not step {step.order}; check where the job stands and answer", kind="step")` — an ask, never a jump.

- [ ] **Step 6: Integration test, run, notes, commit**

Append `test_c2_notes_the_screen_match_on_real_steel` to `test_runs_on_local_steel.py` (shadow only; assert the note exists and the run's verdicts equal a run with no checks). Run: `uv run pytest tests/unit -q -x && uv run mypy src`. Code notes: why Jaccard over labelled words (a route alone is shared by every Ext screen), the two thresholds, and why a promoted C2 asks rather than jumps (additions only).

```bash
git add backend/src/sro/domain/execution/place.py backend/src/sro/application/runtime/run_steps.py backend/src/sro/application/runtime/broker.py backend/tests/unit/domain/execution/test_place.py backend/tests/unit/application/runtime/test_run_steps.py backend/tests/integration/test_runs_on_local_steel.py docs/code-notes/backend/src/sro/domain/execution/place.py.md docs/code-notes/backend/src/sro/application/runtime/run_steps.py.md
git commit -m "feat(steel): C2 in shadow - the live screen against the recorded one, per step and at resume"
```

---

### Task 11: C3 + C10 — more ways to find a control, and a dropdown option by its label

**Files:**
- Modify: `new-chrome-extension/src/page/page-code.js` (`MORE` strategies used by `find` only when `payload.more === true`, after `STRATEGIES` and before `repair`; `look({ask: "locate"})`)
- Modify: `backend/src/sro/application/runtime/ui_lane.py` (`_locator_notes`; `payload["more"] = True` when promoted)
- Test: `backend/tests/browser/test_more_locators.py` (new), `backend/tests/unit/application/runtime/test_the_ui_lane.py` (add), integration test appended
- Code notes for `page-code.js`, `ui_lane.py`

**Interfaces:**
- Consumes: `Target.label_text/sibling_index/sibling_count` (Task 2; they reach page-code through `asdict(target)` in `ui_payload` as `label_text`, `sibling_index`, `sibling_count`), `Action.choice`, readers `labelOf`, `siblingOf` (Task 5), `looked` (Task 8).
- Produces: page-code `MORE = [["label_text", …], ["sibling", …], ["option_label", …]]`; `look({ask: "locate", payload})` → `{today: strategy|null, more: {label_text: n, sibling: n, option_label: n}, same: {label_text: bool|null, sibling: bool|null, option_label: bool|null}}`.

- [ ] **Step 1: Failing browser test**

```python
# backend/tests/browser/test_more_locators.py
"""The locators tried after today's, in a real Chrome, through page-code itself."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<label for="c">Customer code</label><input id="c">
<div><button>Go</button><button>Go</button></div>
<ul role="listbox"><li role="option">Retail</li><li role="option">Bulk</li></ul>
</body></html>"""


@pytest.fixture
def page() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            context = browser.new_context()
            context.add_init_script(path=get_settings().page_code_path)
            context.route("http://sro.test/**", lambda route: route.fulfill(body=PAGE, content_type="text/html"))
            one = context.new_page()
            one.goto("http://sro.test/")
            yield one
        finally:
            browser.close()


def _resolve(page: Any, payload: dict[str, Any]) -> Any:
    return page.evaluate("p => globalThis.sroPage.resolve(p)", payload)


def test_more_locators_are_tried_only_after_today_s_fail(page: Any) -> None:
    gone = {"action": "type", "target": {"css_path": "#nope", "label_text": "Customer code"}}
    assert not _resolve(page, gone)["found"]
    assert _resolve(page, {**gone, "more": True})["strategy"] == "label_text"


def test_today_s_locator_still_wins_when_it_finds_the_control(page: Any) -> None:
    both = {"action": "type", "more": True, "target": {"css_path": "#c", "label_text": "Customer code"}}
    assert _resolve(page, both)["strategy"] == "css_path"


def test_a_sibling_position_finds_the_second_of_two_same_buttons(page: Any) -> None:
    second = {"action": "click", "more": True, "target": {"role": "button", "text": "Nope", "tag": "button", "sibling_index": 1, "sibling_count": 2, "name": "Go"}}
    assert _resolve(page, second)["strategy"] == "sibling"


def test_an_option_is_picked_by_the_run_s_label_when_the_order_changed(page: Any) -> None:
    pick = {"action": "click", "more": True, "value": "Bulk", "target": {"role": "option", "css_path": "#nope"}}
    assert _resolve(page, pick)["strategy"] == "option_label"


def test_locate_reports_which_new_locator_agrees_with_today(page: Any) -> None:
    said = page.evaluate("p => globalThis.sroPage.look(p)", {"ask": "locate", "payload": {"action": "type", "target": {"css_path": "#c", "label_text": "Customer code"}}})
    assert said["today"] == "css_path"
    assert said["same"]["label_text"] is True
```

(If `sroPage.resolve` returns a different shape, read `resolve(payload)` in `page-code.js` — it returns `{found, strategy, candidates, ...}` — and assert on its actual keys.)

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/browser/test_more_locators.py -q -m browser` → FAIL.

- [ ] **Step 3: Implement in `page-code.js`**

After `STRATEGIES`:

```js
  const OPTIONS = "[role=option], .x-boundlist-item";
  const MORE = [
    ["label_text", (t) => (t.label_text ? qsa("input, select, textarea, [role=combobox], [role=textbox]").filter((el) => labelOf(el) === t.label_text) : [])],
    ["sibling", (t) => {
      if (typeof t.sibling_index !== "number" || !t.role) return [];
      const groups = new Map();
      for (const el of qsa(CANDIDATES).filter((one) => roleOf(one) === t.role && (!t.name || nameOf(one) === t.name))) {
        const key = el.parentElement;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(el);
      }
      return [...groups.values()]
        .filter((same) => same.length === t.sibling_count)
        .map((same) => same[t.sibling_index])
        .filter(Boolean);
    }],
    ["option_label", (t, p) => {
      const wanted = p.value || t.choice_chosen;
      return wanted ? qsa(OPTIONS).filter((el) => plainOf(el.innerText) === wanted) : [];
    }],
  ];
```

In `find`, after the `for (const [strategy, run] of STRATEGIES)` loop and before `const repairable = ...`:

```js
    if (payload.more === true) {
      for (const [strategy, run] of MORE) {
        const found = run(t, payload).filter(shown);
        if (found.length === 1) return { el: found[0], strategy, candidates: 1, score: null };
      }
    }
```

(Only a single match counts: a new locator never guesses between two.) In `look`:

```js
      if (ask === "locate") {
        const asked = payload.payload || {};
        const t = asked.target || {};
        const today = find({ ...asked, more: false });
        const more = {};
        const same = {};
        for (const [strategy, run] of MORE) {
          const found = run(t, asked).filter(shown);
          more[strategy] = found.length;
          same[strategy] = today.el && found.length === 1 ? found[0] === today.el : null;
        }
        return { today: today.strategy, more, same };
      }
```

- [ ] **Step 4: Failing ui_lane tests**

```python
async def test_c3_in_shadow_says_which_new_locator_would_have_found_a_missing_control() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    driver.looks["locate"] = {"today": None, "more": {"label_text": 1, "sibling": 0, "option_label": 0}, "same": {}}
    step, by_id = type_step()

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, checks=Checks(shadow=frozenset({"C3"}))))

    assert result.verdict == "failed"
    assert any(one.startswith("shadow:C3:yes") for one in result.notes)
    assert all(not one.get("more") for one in driver.acted)


async def test_c3_promoted_asks_page_code_for_more_locators() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="label_text"), holds=True)
    step, by_id = type_step(after=AfterState(value="GT1", visible=True, enabled=True))

    await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, checks=Checks(on=frozenset({"C3"}))))

    assert driver.acted[-1]["more"] is True
```

(`FakePageDriver` must keep `acted: list[Mapping]` of `act` payloads — add it if absent.)

- [ ] **Step 5: Implement in `ui_lane.py`**

In `execute`, after `payload = ui_payload(...)`: if `ctx.checks.promoted("C3") or ctx.checks.promoted("C10")`, `payload = {**payload, "more": True}`; when `primary.action.choice` is set and C10 is watched, add `"choice_chosen": primary.action.choice.chosen` to `payload["target"]` (a copy). Add:

```python
    async def _locator_notes(self, held: Held, payload: Mapping[str, object], answer: PageAnswer, ctx: LaneContext) -> tuple[str, ...]:
        watching = [one for one in ("C3", "C10") if ctx.checks.watching(one)]
        if not watching:
            return ()
        said = await looked(self._driver, held, {"ask": "locate", "payload": {**payload, "more": False}, "frame_path": payload.get("frame_path")})
        more, same = said.get("more") or {}, said.get("same") or {}
        names = {"C3": ("label_text", "sibling"), "C10": ("option_label",)}
        notes = []
        for check in watching:
            mine = names[check]
            if answer.ok:
                agreed = [same.get(one) for one in mine if same.get(one) is not None]
                notes.append(note(check, "n/a" if not agreed else "yes" if all(agreed) else "no"))
            else:
                hit = next((one for one in mine if more.get(one) == 1), None)
                notes.append(note(check, "yes" if hit else "no", hit or ""))
        return tuple(notes)
```

Call it in `_perform` right after the final `answer` is known (both the failed branch and the success paths), and add its notes to every `StepResult` returned (concatenate with Task 9's notes). `C10` is a separate check name with its own flags; it shares the code path.

- [ ] **Step 6: Run, integration test, notes, commit**

Append `test_a_moved_control_is_found_by_its_label_only_when_promoted` to the Steel integration file (rig page renames the control's id between recording and run). Run unit, browser and mypy. Notes: why only a single match counts, and why `more` never reaches `repair`'s path (it returns before it).

```bash
git add new-chrome-extension/src/page/page-code.js backend/src/sro/application/runtime/ui_lane.py backend/tests/browser/test_more_locators.py backend/tests/unit/application/runtime/test_the_ui_lane.py backend/tests/unit/fakes.py backend/tests/integration/test_runs_on_local_steel.py docs/code-notes/new-chrome-extension/src/page/page-code.js.md docs/code-notes/backend/src/sro/application/runtime/ui_lane.py.md
git commit -m "feat(steel): C3 and C10 in shadow - label, position and option label as locators after today's"
```

---

### Task 12: C5 — stay signed in

**Files:**
- Create: `backend/src/sro/domain/execution/staying_in.py`
- Modify: `backend/src/sro/application/ports/page.py` + `infrastructure/steel/driver.py` + `tests/unit/fakes.py` (`PageDriver.clear_cookies(session) -> None` via CDP `Storage.clearCookies {browserContextId}`)
- Modify: `backend/src/sro/application/runtime/broker.py` (`reauth(..., fresh: bool = False)`: when `fresh`, `await self._driver.clear_cookies(held.session)` before `goto`)
- Modify: `backend/src/sro/application/runtime/executor.py` (pre-step C5 note/promotion at a screen boundary)
- Modify: `backend/src/sro/application/runtime/ui_lane.py` (on a failed step, the recorded session-expired dialog → note; promoted → `expired=True`)
- Test: `backend/tests/unit/domain/execution/test_staying_in.py` (new), `tests/unit/application/runtime/test_executor.py` or the existing executor test file (add), `test_the_ui_lane.py` (add), integration test appended

**Interfaces:**
- Consumes: `PageMark.cookies`, `Effect`, `gesture.passed_through`, `PageDriver.storage_state` (returns JSON whose `cookies` carry `name` and `expires`), `looked`.
- Produces: `staying_in.K_REAUTH_MARGIN_S = 120.0`; `staying_in.recorded_cookie_names(by_id: Mapping[str, Gesture]) -> frozenset[str]`; `staying_in.expiring(live_cookies: Sequence[Mapping[str, object]], names: Collection[str], now: float, margin_s: float = K_REAUTH_MARGIN_S) -> bool | None` (`None` = nothing to judge); `staying_in.expiry_dialog(gestures: Sequence[Gesture]) -> str | None` (title of a dialog that appeared on the gesture right before one whose page events passed through a sign-in origin); `staying_in.screen_boundary(step, previous, by_id) -> bool`.

- [ ] **Step 1: Failing domain tests**

```python
# backend/tests/unit/domain/execution/test_staying_in.py
from sro.domain.execution.staying_in import expiring, recorded_cookie_names


def test_only_cookies_the_recording_saw_set_are_judged() -> None:
    live = [{"name": "JSESSIONID", "expires": 1_000.0}, {"name": "_ga", "expires": 10.0}]
    assert expiring(live, {"JSESSIONID"}, now=900.0) is True
    assert expiring(live, {"JSESSIONID"}, now=800.0) is False


def test_session_cookies_and_unknown_names_judge_nothing() -> None:
    assert expiring([{"name": "JSESSIONID", "expires": -1}], {"JSESSIONID"}, now=0.0) is None
    assert expiring([], {"JSESSIONID"}, now=0.0) is None
    assert expiring([{"name": "a", "expires": 5.0}], set(), now=0.0) is None
```

plus a `recorded_cookie_names` test building two `Gesture`s whose `page_events` carry `PageMark(at=1.0, page_kind="cookies_set", cookies=(CookieSeen("JSESSIONID"),))` (use `save_step`'s gesture with `replace`) and asserting `{"JSESSIONID"}`, and an `expiry_dialog` test (a gesture whose effect opened `Seen("dialog", None, "Session expired", ("OK",))`, followed by a gesture whose `page_events` include a `navigated` mark on another origin → `"Session expired"`).

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement `staying_in.py`**

```python
# backend/src/sro/domain/execution/staying_in.py
from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from sro.domain.execution.effects import dialog_opened
from sro.domain.observation.gesture import Gesture, passed_through
from sro.domain.skill.workflow import Step

K_REAUTH_MARGIN_S = 120.0


def recorded_cookie_names(by_id: Mapping[str, Gesture]) -> frozenset[str]:
    return frozenset(
        cookie.name for one in by_id.values() for mark in one.page_events for cookie in mark.cookies
    )


def expiring(
    live_cookies: Sequence[Mapping[str, object]],
    names: Collection[str],
    now: float,
    margin_s: float = K_REAUTH_MARGIN_S,
) -> bool | None:
    ends = [
        float(expires)
        for one in live_cookies
        if one.get("name") in names
        and isinstance(expires := one.get("expires"), int | float)
        and not isinstance(expires, bool)
        and expires > 0
    ]
    return None if not ends else min(ends) - now <= margin_s


def expiry_dialog(gestures: Sequence[Gesture]) -> str | None:
    ordered = sorted(gestures, key=lambda one: one.at)
    for before, after in zip(ordered, ordered[1:], strict=False):
        asked = dialog_opened(before.action.effect)
        if asked is not None and asked.title and passed_through(after):
            return asked.title
    return None


def screen_boundary(step: Step, previous: Step | None, by_id: Mapping[str, Gesture]) -> bool:
    from sro.domain.execution.evidence import primary_gesture

    here = primary_gesture(step, by_id)
    there = None if previous is None else primary_gesture(previous, by_id)
    if here is None:
        return False
    return there is None or (here.page_url or here.url) != (there.page_url or there.url)
```

(Move the `primary_gesture` import to the top if `lint-imports`/cycles allow; it is a domain import.)

- [ ] **Step 4: Driver, broker, executor, ui_lane**

- `PageDriver.clear_cookies(self, session: SessionRef) -> None`; Steel: `link = await self._context(session); await self._send(link, "Storage.clearCookies", {"browserContextId": session.context_id})`; fake: records `("clear_cookies", session.context_id)` in `calls`.
- `SessionBroker.reauth(..., fresh: bool = False)`: inside the lock, before `goto`, `if fresh: await self._driver.clear_cookies(held.session)`. Every existing caller passes nothing → unchanged.
- `StepExecutor.run`: before the lane loop, when `ctx.held is not None and ctx.checks.watching("C5")`:

```python
        names = recorded_cookie_names(ctx.by_id)
        state = json.loads(await self._broker.storage_state(ctx.ctx, ctx.held) or "{}")
        soon = expiring(state.get("cookies") or [], names, now=time.time())
        pre_note = note("C5", "n/a" if soon is None else "no" if soon else "yes")
        if soon and ctx.checks.promoted("C5") and screen_boundary(step, previous_step, ctx.by_id):
            await self._broker.reauth(ctx.ctx, ctx.held, start_url, back_to=page, fresh=True)
```

`yes` = "the session will last the step". Add `SessionBroker.storage_state(ctx, held) -> str` delegating to `self._driver.storage_state(held.session)` if no such broker method exists. `previous_step` is the step before `step` in `ctx.workflow.steps` order. Attach `pre_note` to the returned results' last item (`replace(tried[-1], notes=(pre_note, *tried[-1].notes))`). Use the injected `Clock` if `StepExecutor` has one; otherwise add `clock: Clock` to its constructor with the container's clock (time must come from the port in unit tests: `FakeClock`).
- `ui_lane`, failed branch (`if not answer.ok:`): when `ctx.checks.watching("C5")`, `title = expiry_dialog(list(ctx.by_id.values()))`; read `look({ask: "place"})` and the live outline; the dialog is "seen" when `title` is among the live `place.headings` or `place.landmarks`. Note `note("C5", "no", "expiry dialog")` when seen; when promoted, return the failed result with `expired=True` (today's executor path then re-signs in and retries).

- [ ] **Step 5: Tests, run, notes, commit**

Unit: executor test with a `FakePageDriver` whose `storage_state` returns cookies expiring in 60 s → shadow note `shadow:C5:no`, `driver.calls` has no `clear_cookies`; promoted at a screen boundary → `clear_cookies` called once and the broker re-signed; promoted mid-screen → nothing cleared. ui_lane test: failed step + recorded expiry dialog + live heading "Session expired" → `expired` only when promoted. Integration: `test_an_expiring_session_is_noted_and_renewed_only_when_promoted` (rig sets a 3-minute cookie at sign-in). Notes: why only at a screen boundary (navigating back loses form state otherwise), names only, never values.

```bash
git add backend/src/sro/domain/execution/staying_in.py backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/src/sro/application/runtime/broker.py backend/src/sro/application/runtime/executor.py backend/src/sro/application/runtime/ui_lane.py backend/src/sro/container.py backend/tests/unit/fakes.py backend/tests/unit/domain/execution/test_staying_in.py backend/tests/unit/application/runtime backend/tests/integration/test_runs_on_local_steel.py docs/code-notes
git commit -m "feat(steel): C5 in shadow - recorded sign-in cookies and the expiry dialog say when to sign in again"
```

(Stage `backend/tests/unit/application/runtime` and `docs/code-notes` files by name after checking `git status --short`.)

---

### Task 13: C8 — ask for what the job really needs

**Files:**
- Create: `backend/src/sro/domain/skill/proven.py`
- Modify: `backend/src/sro/application/runtime/run_steps.py` (at the `required` check in `step()`)
- Test: `backend/tests/unit/domain/skill/test_proven.py` (new), `test_run_steps.py` (add)

**Interfaces:**
- Consumes: `Effect.fields` (Task 2), `learned.control_names`, `learned.called`, `skill.workflow.Step.parameters`.
- Produces: `proven.proven_required(workflow: Workflow, by_id: Mapping[str, Gesture]) -> frozenset[str]` — names of parameters whose control the recording showed turning `invalid` after a submit.

- [ ] **Step 1: Failing tests**

```python
# backend/tests/unit/domain/skill/test_proven.py
from dataclasses import replace

from sro.domain.observation.gesture import Effect, FieldChange
from sro.domain.skill.proven import proven_required
from tests.unit.runtime_support import WORKFLOW, save_step, type_step


def test_a_field_the_page_called_invalid_after_a_submit_is_proven_required() -> None:
    typed_step, typed = type_step()
    save, saved = save_step(status=201)
    (gid,) = saved
    label = next(iter(typed.values())).action.target.name  # the typed control's label
    saved[gid] = replace(saved[gid], action=replace(saved[gid].action, effect=Effect(fields=(FieldChange(label, "invalid"),))))
    job = replace(WORKFLOW, steps=[replace(typed_step, order=0), replace(save, order=1)])
    assert proven_required(job, {**typed, **saved}) == frozenset(typed_step.parameters)


def test_no_effect_proves_nothing() -> None:
    typed_step, typed = type_step()
    job = replace(WORKFLOW, steps=[typed_step])
    assert proven_required(job, typed) == frozenset()
```

and in `test_run_steps.py`: an optional parameter with no value whose control is proven required → shadow `C8` note `shadow:C8:no` (the job "would ask") while the step is skipped exactly as today; promoted → the run asks (`outcome.asking`), the step is not skipped.

- [ ] **Step 2: Implement**

```python
# backend/src/sro/domain/skill/proven.py
from __future__ import annotations

from collections.abc import Mapping

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.learned import control_names
from sro.domain.skill.workflow import Workflow


def proven_required(workflow: Workflow, by_id: Mapping[str, Gesture]) -> frozenset[str]:
    invalid = {
        change.label
        for one in by_id.values()
        if one.action.effect is not None
        for change in one.action.effect.fields
        if change.change == "invalid"
    }
    if not invalid:
        return frozenset()
    found: set[str] = set()
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is not None and invalid & set(control_names(gesture)):
                found.update(step.parameters)
    return frozenset(found)
```

In `run_steps.step()`, right after `required = [...]`:

```python
        if self._checks_for(ctx).watching("C8"):
            proven = proven_required(workflow, by_id)
            more = [name for name in absent if name in proven and name not in required]
            pre.append(note("C8", "n/a" if not proven else "no" if more else "yes", ", ".join(more)))
            if more and self._checks_for(ctx).promoted("C8"):
                required = [*required, *more]
```

(`_checks_for(ctx)` = `self._checks.for_tenant(ctx.tenant_id.value)`; move `pre: list[str] = []` to the top of `step()` so this branch can use it; the existing `if required:` ask then passes `noted=pre`. The detail names parameters (names, not values) and passes `said_text`.)

- [ ] **Step 3: Run, notes, commit**

```bash
git add backend/src/sro/domain/skill/proven.py backend/src/sro/application/runtime/run_steps.py backend/tests/unit/domain/skill/test_proven.py backend/tests/unit/application/runtime/test_run_steps.py docs/code-notes/backend/src/sro/domain/skill/proven.py.md docs/code-notes/backend/src/sro/application/runtime/run_steps.py.md
git commit -m "feat(steel): C8 in shadow - a field the recording proved required is asked for"
```

---

### Task 14: C11 — explain failures

**Files:**
- Modify: `backend/src/sro/application/runtime/ui_lane.py` (on a `failed` result: errors from the live effect, failed calls, version drift)
- Test: `test_the_ui_lane.py` (add), and the Review Focus 3 test for every `ui_lane` check

**Interfaces:**
- Consumes: Task 9's watcher (`C11` arms it), `Place.version`, `StepResult.calls`.
- Produces: notes `shadow:C11:no errors=<n> failed_calls=<n> version=<same|changed|unknown>` on failed UI steps only; never a verdict change (informational even when "promoted").

- [ ] **Step 1: Failing tests**

```python
async def test_c11_explains_a_failed_step_and_changes_nothing() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    driver.looks["effect"] = {"effect": {"errors": ["TypeError: x is undefined"]}}
    driver.looks["place"] = {"place": {"version": "Ext 7.7.0"}}
    step, by_id = type_step()
    (gid,) = by_id
    by_id[gid] = replace(by_id[gid], action=replace(by_id[gid].action, place=Place(version="Ext 7.6.0")))

    shadow = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, checks=Checks(on=frozenset({"C11"}))))

    assert shadow.verdict == "failed"
    (said,) = [one for one in shadow.notes if one.startswith("shadow:C11")]
    assert "errors 1" in said and "version changed" in said


async def test_a_recording_without_new_data_runs_as_today_with_every_check_shadowed() -> None:
    every = Checks(shadow=frozenset({"C1", "C3", "C4", "C5", "C6", "C10", "C11"}))
    for answer, calls in ((PageAnswer(ok=True), [SAVED]), (PageAnswer(ok=True), []), (PageAnswer(ok=False, error_kind="control_not_found"), [])):
        step, by_id = save_step(status=201)
        today = await UiLane(scripted_driver(answer=answer, calls=calls)).execute(step, {}, lane_context(by_id))
        shadowed = await UiLane(scripted_driver(answer=answer, calls=calls)).execute(step, {}, lane_context(by_id, checks=every))
        assert (shadowed.verdict, shadowed.reason, shadowed.expired, shadowed.never_left) == (
            today.verdict, today.reason, today.expired, today.never_left,
        )
        assert all(one.split(" ")[0].endswith(("n/a", "yes", "no")) for one in shadowed.notes)
```

- [ ] **Step 2: Implement**

On every `failed` return in `_perform` (including the `not answer.ok` branch), when `ctx.checks.watching("C11")`: `live = effect_from((await looked(..., {"ask": "effect"})).get("effect"))` (the watcher was armed by Task 9's code because `C11` is in its tuple); `place = place_from((await looked(..., {"ask": "place"})).get("place"))`; `bad = sum(1 for one in calls if one.status is not None and one.status >= 400)`; version `same`/`changed`/`unknown` from `primary.action.place.version` vs `place.version`. Append `note("C11", "no", f"errors {len(live.errors) if live else 0} failed calls {bad} version {drift}")`. Never touch the verdict. The detail uses words, not `=`, so it passes `said_text`.

- [ ] **Step 3: Run, notes, commit**

```bash
git add backend/src/sro/application/runtime/ui_lane.py backend/tests/unit/application/runtime/test_the_ui_lane.py docs/code-notes/backend/src/sro/application/runtime/ui_lane.py.md
git commit -m "feat(steel): C11 - a failed step notes the page's errors, failed calls and version drift"
```

---

## Phase 5 — The mail reference (Owner decision 2)

### Task 15: Item 7 + C7 — the thread id a job came from, by reference, opt-in; mining notes

**Files:**
- Modify: `backend/src/sro/domain/observation/policy.py` (`note_mail_thread: bool = False`; `noting_mail_threads(on: bool) -> ObservationPolicy` bumps the version)
- Modify: `backend/src/sro/interface/http/schemas.py` (`ObservationPolicyModel.note_mail_thread: bool = False`, filled in `of`)
- Modify: `backend/src/sro/cli/observe.py` (`--mail-thread on|off`)
- Modify: the policy's SQL decode if it lists fields (find it with `grep -rn "ObservationPolicyRow" backend/src/sro/infrastructure`)
- Modify: `new-chrome-extension/src/background/service-worker.js` (on `tabs.onActivated`, a mail tab left for a watched tab → `pageEvent("mail_ref", ..., {mail_thread})` when the policy says so)
- Create: `backend/src/sro/domain/execution/mail_pairing.py`, `backend/src/sro/application/observation/pair_mail.py`
- Create: migration `backend/migrations/versions/<date>_<next>_mail_pairings_are_mining_notes.py` (table `mail_pairings`)
- Modify: `backend/src/sro/infrastructure/db/models.py` (`MailPairingRow`), a repository (`MailPairingRepository` port in `ports/repositories.py`, SQL in `infrastructure/db/mail_pairings.py`, fake in `fakes.py`, `UnitOfWork.mail_pairings`)
- Modify: `backend/src/sro/application/observation/mine_lately.py` (`pair: PairMail | None = None`; after a pass, for a tenant with `note_mail_thread`, `await self._pair.execute(ctx)`), `container.py`
- Test: `backend/tests/unit/domain/execution/test_mail_pairing.py`, `backend/tests/unit/application/test_pair_mail.py`, `backend/tests/unit/domain/test_observation_policy.py` (or the file that tests `ObservationPolicy`), `new-chrome-extension/src/background/page-marks.test.mjs` (Task 7 already covers `threadInUrl`), `make types`

**Interfaces:**
- Consumes: `PageMark.mail_thread` (Tasks 2–4), `threadInUrl`, `MAIL_HOSTS`, `pageEvent(..., extra)` (Task 7), `mail_job._conversation` (rename nothing; import it, or add a public `conversation(ctx, tools, thread)` wrapper beside it).
- Produces: `mail_pairing.labels_for(text: str, values: Mapping[str, str]) -> dict[str, str]` (parameter name → the ≤40-character label right before its value in the mail, through `said_text`; never the value); `PairMail(uow, tools).execute(ctx) -> int`; table `mail_pairings(tenant_id, workflow_id, mail_ref, field, label, seen_at)` PK `(tenant_id, workflow_id, mail_ref, field)`.

- [ ] **Step 1: Failing tests**

```python
# backend/tests/unit/domain/execution/test_mail_pairing.py
from sro.domain.execution.mail_pairing import labels_for


def test_the_words_before_a_value_name_its_field_and_the_value_is_never_kept() -> None:
    text = "Hi,\nplease add a customer type.\nCustomer type: GT7\nDescription: Garden tools\nThanks"
    assert labels_for(text, {"Customer Type": "GT7", "Description": "Garden tools"}) == {
        "Customer Type": "Customer type:",
        "Description": "Description:",
    }


def test_a_value_the_mail_never_says_pairs_nothing() -> None:
    assert labels_for("nothing here", {"Customer Type": "GT7"}) == {}


def test_a_short_or_ambiguous_value_pairs_nothing() -> None:
    assert labels_for("a a a", {"x": "a"}) == {}
    assert labels_for("Code: 12 and Qty: 12", {"Code": "12"}) == {}
```

```python
def test_noting_mail_threads_is_off_until_a_tenant_says_yes() -> None:
    policy = ObservationPolicy()
    assert policy.note_mail_thread is False
    on = policy.noting_mail_threads(True)
    assert on.note_mail_thread is True and on.version == policy.version + 1
```

`test_pair_mail.py`: with `FakeUnitOfWork`, a kept job whose cited gesture has `page_events=[PageMark(at=1.0, page_kind="mail_ref", mail_thread="FMfcg...")]` and typed value `GT7`; a fake `ToolCaller` answering `get_thread` with `{"messages": [{"body": "Customer type: GT7"}]}`; assert one `mail_pairings` row `("Customer Type", "Customer type:")` and that `"GT7"` appears nowhere in the stored rows; a thread the connector cannot read → no row and the count of unreadable refs is returned in the log line (test with `caplog`). A tenant without `note_mail_thread` → `execute` returns 0 and calls no tool.

Extension (append to `page-marks.test.mjs`):

```js
test("no mail ref without the tenant's yes", () => {
  assert.equal(mailRefFor({ note_mail_thread: false }, "https://mail.google.com/mail/u/0/#inbox/FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"), null);
  assert.equal(mailRefFor({ note_mail_thread: true }, "https://mail.google.com/mail/u/0/#inbox/FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"), "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk");
  assert.equal(mailRefFor({ note_mail_thread: true }, "https://wms.example/a"), null);
});
```

with `export function mailRefFor(policy, url) { return policy && policy.note_mail_thread === true ? threadInUrl(url) : null; }` added to `page-marks.js`.

- [ ] **Step 2: Implement**

`mail_pairing.py`:

```python
from __future__ import annotations

import re
from collections.abc import Mapping

from sro.domain.observation.outline import said_text

K_LABEL_CHARS = 40
K_SHORTEST_VALUE = 3


def labels_for(text: str, values: Mapping[str, str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, value in values.items():
        value = value.strip()
        if len(value) < K_SHORTEST_VALUE or text.count(value) != 1:
            continue
        line = next((one for one in text.splitlines() if value in one), "")
        before = line.split(value, 1)[0].strip()[-K_LABEL_CHARS:]
        label = said_text(re.sub(r"\s+", " ", before))
        if label and value not in label:
            found[name] = label
    return found
```

(`K_SHORTEST_VALUE = 3` and "exactly once" are what make `"a a a"` and `"12 … 12"` pair nothing.)

`pair_mail.py`: for each workflow of the tenant (`uow.workflows.list_for(...)` — use the repository's existing "all jobs" method), load cited gestures, collect `mail_thread` refs from their `page_events` and the typed values per parameter (`step.parameters` ↔ the step's typed gesture value), read the thread via the mail connector (`get_thread`), join message bodies, `labels_for`, and `uow.mail_pairings.add(...)` each pair (insert-or-ignore on the PK). Nothing of the mail is stored but the label. Mining notes only: nothing reads these rows to decide anything until the owner promotes C7 (see Spec gaps).

Migration (docstring header like `0092`, new table only, no existing table touched):

```python
def upgrade() -> None:
    op.create_table(
        "mail_pairings",
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(64), nullable=False),
        sa.Column("mail_ref", sa.String(200), nullable=False),
        sa.Column("field", sa.Text, nullable=False),
        sa.Column("label", sa.String(40), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "workflow_id", "mail_ref", "field"),
    )


def downgrade() -> None:
    op.drop_table("mail_pairings")
```

Service worker, in Task 7's `tabs.onActivated` listener, before the focus marks: `const left = before == null ? null : await chrome.tabs.get(before).catch(() => null); const ref = left?.url ? mailRefFor(await state.policy(), left.url) : null; if (ref && to.watched) { const tab = await chrome.tabs.get(tabId).catch(() => null); if (tab?.url) await pageEvent("mail_ref", tabId, tab.url, Date.now(), null, { mail_thread: ref }); }` — the event's URL is the **watched** tab's, so admission's host policy is unchanged; nothing is read from the mail page itself. `ObservationPolicyModel` carries `note_mail_thread` so the extension's stored policy has it after the version bump.

- [ ] **Step 3: Run, types, notes, commit**

Run: `cd backend && uv run pytest tests/unit -q -x && uv run mypy src && make -C .. types && make -C .. test-extension && make -C .. migrate` (local DB), then `SRO_INTEGRATION_DATABASE_URL=... uv run pytest tests/integration -q -k mail_pairing` if you add an integration test for the SQL repository (model it on an existing repository integration test).

Code notes: `policy.py.md` (`note_mail_thread`: Owner decision 2, off by default, bumps the version so browsers refetch), `mail_pairing.py.md` (a label, never a value; once-only values), `pair_mail.py.md` (reads at mining time through the tenant's own connector; nothing of the mail kept but labels), `service-worker` comment-free (JS notes live in the notes file for `page-code.js` only; add a short section to `docs/code-notes/new-chrome-extension/src/background/service-worker.js.md`, creating it if absent).

```bash
git add backend/src/sro/domain/observation/policy.py backend/src/sro/interface/http/schemas.py backend/src/sro/cli/observe.py backend/src/sro/domain/execution/mail_pairing.py backend/src/sro/application/observation/pair_mail.py backend/src/sro/application/observation/mine_lately.py backend/src/sro/application/ports/repositories.py backend/src/sro/infrastructure/db/models.py backend/src/sro/infrastructure/db/mail_pairings.py backend/src/sro/container.py backend/migrations/versions backend/tests/unit new-chrome-extension/src/background/page-marks.js new-chrome-extension/src/background/page-marks.test.mjs new-chrome-extension/src/background/service-worker.js frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "feat(capture): the mail thread a job came from, by reference and opt-in; C7 mining notes"
```

(Stage directories only after `git status --short` shows nothing unexpected in them; otherwise add files by name.)

---

## Phase 6 — C9 in shadow

### Task 16: C9 — check before writing, confirm after (and C9-stop, shadow only)

**Files:**
- Create: `backend/src/sro/domain/execution/existence.py`
- Modify: `backend/src/sro/application/lookup/answer.py` (add `exists_verdict`)
- Create: `backend/src/sro/application/runtime/existence_check.py`
- Modify: `backend/src/sro/application/runtime/run_steps.py` (before a create write; after it)
- Modify: `container.py` (`RunSteps(..., existence=ExistenceCheck(self.session_broker()))`)
- Test: `backend/tests/unit/domain/execution/test_existence.py`, `backend/tests/unit/application/test_exists_verdict.py`, `test_run_steps.py` (add), integration test appended

**Interfaces:**
- Consumes: `domain.lookup.plan.Lookup`, `domain.lookup.address.address_for`, `application.execution.answer.read_answer`, `application.runtime.api_lane.session_headers/needs_of`, `answer._hits/_whole` rules, `SessionBroker.send`.
- Produces: `existence.existence_lookup(workflow: Workflow, by_id: Mapping[str, Gesture], step: Step, values: Mapping[str, str]) -> Lookup | None` (the last 2xx GET the recording made before this create whose query carries the value of one of the step's parameters; `Lookup(how="call", target=<path>, params={<query key>: <run value>}, find=<run value>)`); `answer.exists_verdict(find: str, reads: Sequence[Answer | None]) -> Literal["exists", "absent", "unsure"]` ("absent" only off whole lists, exactly `existence_across`'s rule); `ExistenceCheck(broker).check(ctx, held, lookup, gestures) -> str`.

- [ ] **Step 1: Failing tests**

```python
# backend/tests/unit/application/test_exists_verdict.py
from sro.application.execution.answer import Answer
from sro.application.lookup.answer import exists_verdict

WHOLE = Answer(rows=2, records=({"code": "GT1"}, {"code": "GT2"}), counted=2)


def test_a_hit_is_exists() -> None:
    assert exists_verdict("gt2", [WHOLE]) == "exists"


def test_absent_only_off_a_whole_list() -> None:
    assert exists_verdict("GT9", [WHOLE]) == "absent"
    assert exists_verdict("GT9", [Answer(rows=2, records=WHOLE.records, counted=2, partial=True)]) == "unsure"
    assert exists_verdict("GT9", [Answer(rows=2, records=WHOLE.records, counted=2, narrowed_by=("page",))]) == "unsure"
    assert exists_verdict("GT9", [None]) == "unsure"
```

(Read `Answer`'s constructor — `counted` and the other names come from `application/execution/answer.py` — and build the fixtures with its real fields.)

`test_existence.py`: a recording whose search gesture made `GET /api/customer-types?code=GT1` (200) before the save that typed `GT1` → `existence_lookup(job, by_id, save, {"Customer Type": "GT7"})` returns `Lookup(how="call", target="/api/customer-types", params={"code": "GT7"}, find="GT7", system=...)`; no GET before the save → `None`; a GET whose query carries no parameter value → `None`.

`test_run_steps.py`: shadow `C9` with the broker answering a whole list that contains `GT1` → note `shadow:C9:no` ("would have found it already exists" — `no` = predicts the create should not go), the write still runs; `C9-stop` promoted → the run asks and the UI lane never ran; after a done create, `C9` shadow notes `readback found|missing|unsure` in the detail.

- [ ] **Step 2: Implement**

```python
# in application/lookup/answer.py
def exists_verdict(find: str, reads: Sequence[Answer | None]) -> str:
    if any(read is not None and _hits(find, read) for read in reads):
        return "exists"
    if all(read is not None and _whole(read) for read in reads) and reads:
        return "absent"
    return "unsure"
```

`existence.py`: walk `workflow.steps` before `step` (by order), collect cited gestures' `requests` that are `GET`, 2xx, not failed; keep those whose query (`parse_qsl(urlsplit(call.url).query)`) has a value equal to a value the recording typed for one of `step.parameters`; take the last; build the `Lookup` with the run's value for that parameter.

`existence_check.py`:

```python
class ExistenceCheck:
    def __init__(self, broker: SessionBroker) -> None:
        self._broker = broker

    async def check(self, ctx: RequestContext, held: Held, lookup: Lookup, gestures: Sequence[Gesture]) -> str:
        address = address_for(lookup, gestures)
        if address is None:
            return "unsure"
        needs = needs_of(dict.fromkeys((*address.live_headers, *address.struck), REDACTED))
        headers = await session_headers(self._broker, ctx, held, address.url, address.headers, fresh=False, needs=needs, wait_s=K_CHECK_S)
        got = await self._broker.send(ctx, held, "GET", address.url, headers=headers)
        if not got.succeeded:
            return "unsure"
        read = read_answer(got.text, url=address.url)
        return exists_verdict(lookup.find, [replace(read, narrowed_by=address.narrowed) if read else None])
```

(`K_CHECK_S = 10.0`; any exception other than `Stopped`/`Superseded` → `"unsure"`.)

`run_steps.step()`, before `tried = await self._executor.run(...)`, when `writes(step, by_id)` and the recorded write call is a `POST` and `lane.checks.watching("C9") or lane.checks.watching("C9-stop")`: compute the lookup; `n/a` when `None`; else `seen = await self._existence.check(...)`; note `C9` (`yes` when absent, `no` when exists, `n/a` when unsure) and `C9-stop` (`no` when exists); when `seen == "exists" and lane.checks.promoted("C9-stop")` ask `NeedsAPerson(f"'{step.says}' would create a record the job's own search already finds; check it and answer", kind="step")` with `noted=pre`. After the executor, when the last verdict is `done` or `unknown`, run the same check again and add `note("C9", "yes" if found else "no", f"readback {seen}")` — notes only (C9 has no promotion that confirms; C1 does that).

- [ ] **Step 3: Run, integration test, notes, commit**

Integration: `test_a_create_whose_record_exists_is_noted_and_refused_only_when_promoted` (rig's list endpoint returns a whole list containing the value). Notes: "absent" needs a whole list (the lookup's strict rule), the stop is its own yes.

```bash
git add backend/src/sro/domain/execution/existence.py backend/src/sro/application/lookup/answer.py backend/src/sro/application/runtime/existence_check.py backend/src/sro/application/runtime/run_steps.py backend/src/sro/container.py backend/tests/unit/domain/execution/test_existence.py backend/tests/unit/application/test_exists_verdict.py backend/tests/unit/application/runtime/test_run_steps.py backend/tests/unit/runtime_support.py backend/tests/integration/test_runs_on_local_steel.py docs/code-notes
git commit -m "feat(steel): C9 in shadow - the recorded search checks before a create and reads back after"
```

---

## Phase 7 — Measure and promote

### Task 17: Shadow agreement, the promotion gate, and the QA runs

**Files:**
- Modify: `backend/scripts/measure.py` (section `shadow_agreement`; per-check counts; the gate)
- Test: `backend/tests/unit/scripts/test_shadow_agreement.py` (new)
- Modify: `docs/code-notes/backend/scripts/measure.py.md`
- Create: `docs/measurements/<date>-capture-shadow.json` (QA output)

**Interfaces:**
- Consumes: `checks.read_note`, `checks.ready_to_promote` (Task 8), `class_of` (Task 1).
- Produces: `agreement(rows: Sequence[tuple[str, list[str], str]]) -> dict[str, Tally]` where each row is `(of_step_final_verdict, notes, verdict_by)` and `Tally(shadowed, agreed, false_confirmations)`; `async def shadow_agreement(db, tenant) -> Section`.

- [ ] **Step 1: Failing test**

```python
# backend/tests/unit/scripts/test_shadow_agreement.py
from scripts.measure import Tally, agreement


def test_a_yes_agrees_with_a_held_step_and_a_no_with_one_that_did_not_hold() -> None:
    rows = [
        ("held", ["shadow:C1:yes"], "ui"),
        ("failed", ["shadow:C1:no"], "ui"),
        ("held", ["shadow:C2:no match 0.10"], "ui"),
        ("held", ["shadow:C3:n/a"], "ui"),
    ]
    tallies = agreement(rows)
    assert tallies["C1"] == Tally(shadowed=2, agreed=2, false_confirmations=0)
    assert tallies["C2"] == Tally(shadowed=1, agreed=0, false_confirmations=0)
    assert "C3" not in tallies


def test_a_c1_yes_on_a_step_a_person_said_was_not_done_is_a_false_confirmation() -> None:
    tallies = agreement([("failed", ["shadow:C1:yes"], "operator")])
    assert tallies["C1"] == Tally(shadowed=1, agreed=0, false_confirmations=1)
```

- [ ] **Step 2: Implement**

```python
@dataclass(frozen=True)
class Tally:
    shadowed: int = 0
    agreed: int = 0
    false_confirmations: int = 0


def agreement(rows: Sequence[tuple[str, list[str], str]]) -> dict[str, Tally]:
    found: dict[str, Tally] = {}
    for final, notes, _by in rows:
        held = final in ("held", "skipped", "not_needed")
        for text in notes:
            read = read_note(text)
            if read is None or read[1] == "n/a":
                continue
            check, verdict, _ = read
            was = found.get(check, Tally())
            agrees = (verdict == "yes") == held
            found[check] = Tally(
                was.shadowed + 1,
                was.agreed + int(agrees),
                was.false_confirmations + int(check == "C1" and verdict == "yes" and not held),
            )
    return found
```

`shadow_agreement(db, tenant)`: select, per run and `of_step`, the **last** row's verdict and `verdict_by` (the outcome a person confirmed when `verdict_by = 'operator'`, otherwise the settled verdict) together with every note on that `of_step`'s rows; feed `agreement`; for each check print shadowed/agreed/false confirmations and `ready_to_promote(..., regressions=<runs that held before this check was promoted and fail since>)` — regressions are 0 for a check never promoted, and for a promoted one are counted by comparing Task 1's class counts before and after the promotion date the owner records (pass it with `--promoted C1=2026-10-20`; add that argument).

- [ ] **Step 3: Run on QA and decide nothing alone**

After Tasks 9–16 are deployed (API + worker restarted) with `SRO_STEEL_SHADOW_CHECKS` naming the QA tenant for every check, and the owner's main jobs have run on Steel enough times:

```bash
cd backend && uv run python scripts/measure.py --tenant <qa-tenant> --json ../docs/measurements/<date>-capture-shadow.json
```

For each check the report marks ready (≥20 shadowed, ≥95% agreed, 0 false confirmations, 0 regressions), ask the owner — one check at a time — whether to add the QA tenant to `steel_promoted_checks[<check>]`. `C2-stop` and `C9-stop` are asked about separately and explicitly as behaviour changes. After each promotion, re-run section 3b and compare the class counts per tenant against the Task 1 baseline.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/measure.py backend/tests/unit/scripts/test_shadow_agreement.py docs/code-notes/backend/scripts/measure.py.md docs/measurements
git commit -m "feat(measure): shadow agreement per check and the promotion gate"
```

---

## Self-review (done against the spec)

**Spec coverage.** Items 1, 4, 6, 8 → Tasks 2–4, 6; item 2 → Tasks 2–5; item 3 → Tasks 2–5; item 5 → Tasks 2–4, 6 (dialogs), 7 (cookies); item 7 → Task 15; item 9 → Task 16 (nothing new captured); item 10 → Tasks 2–5; item 11 → Tasks 5 (version), 6 (errors, shortcuts), 7 (focus). Storage order (sensitivity → rig_wire → domain → correlate → recorder → trim) → Tasks 2–6; `trim()` is deliberately not extended (no miner or reader needs the new fields yet; add when one does). Consumers C1/C4/C6 → 9, C2 → 10, C3/C10 → 11, C5 → 12, C8 → 13, C11 → 14, C7 → 15, C9 → 16. Measuring → Tasks 1, 17. Privacy → Tasks 2–3 (`seen.py`, wire validators), 7, 15. Order of work → phases 1–7. Tests section → browser (5, 6, 11), unit (every task), Steel integration (9–14, 16), redaction (3, plus `test_what_the_recorder_hides.py` and `test_generated_scripts_are_current.py` run in 5–6). Owner decisions → Global Constraints and Tasks 10, 15, 16.

**Type consistency.** `Effect`/`Seen`/`Place`/`Choice`/`CookieSeen` (domain) and their wire twins keep the same field names except the target extras (`labelText` on the wire, `label_text` in the domain — mapped in `as_action`). `look` asks: `place` (8), `watch`/`effect` (9), `locate` (11). Notes: `note(check, verdict, detail)` everywhere; verdicts `yes`/`no`/`n/a`.

## Spec gaps and conflicts found while planning (for the owner)

1. **C2 promotion vs. the binding rule.** The consumers table says a promoted C2 "resume picks the step whose recorded place matches"; that changes which step runs, which rule 5 does not allow outside "Promotions that change behaviour". This plan makes a promoted C2 **ask** when the matching step differs from today's resume (an added ask), never jump. A real jump needs its own yes.
2. **C7 has no defined promoted mechanism.** "Better mail readings; feeds the mail eval corpus" names no consumer. This plan stores labels-before-values in `mail_pairings` (mining notes only); turning them into reader aliases or eval cases is a later decision.
3. **Gmail's URL token is not the API thread id.** The id visible in a Gmail tab's address (`FMfcg…`) is not what the Gmail API's `get_thread` takes; Outlook's URL id needs conversion for Graph. Task 15 stores the URL token as-is and counts unreadable refs; expect C7 to read little on Gmail until a mapping exists.
4. **"The accessible name computed the full way" needs the AX tree**, which needs the `debugger` permission the extension deliberately lacks. `fullNameOf` follows the accname order with DOM signals only.
5. **Item 11's keyboard shortcuts** cannot become gestures (a new gesture moves shape keys, breaking rule 3); they ride on the open effect, so a shortcut pressed with no gesture before it is not recorded.
6. **Cross-batch effects** are matched on (stream, tab, frame path, the gesture's exact `at`); two gestures in one millisecond (a checkbox's click and change) make that ambiguous, so such an effect is dropped and logged rather than guessed.
7. **Early re-sign-in (C5)** cannot happen through today's broker path alone (a still-valid session never shows a sign-in page); Task 12 adds `fresh` (clear cookies first) and limits it to screen boundaries so no half-filled form is lost.
8. **Notes are kept forever** (no data removed), so every shadow note detail passes `said_text` and carries names, numbers and strategy words only — the spec does not say this about notes explicitly.
