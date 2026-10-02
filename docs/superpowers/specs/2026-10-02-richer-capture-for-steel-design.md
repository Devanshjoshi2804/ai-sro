# Richer demonstration capture for Steel runs

Date: 2026-10-02. Status: approved by the owner 2026-10-02 ("approved everything").
Grounded in: the read-only map of the recorder, gesture storage, mining and Steel lanes (2026-10-02).

## Goal

Fewer failed or stuck Steel runs in the four measured classes: a write sent with nothing confirming it,
sign-in, a control or page not found, and duplicates — and runs that resume on the right step. The
extension records more of what a person saw while doing the job once; Steel uses it when it runs the
job.

## The binding rule: additions only

The owner's rule (2026-10-02): nothing is removed and nothing that works today behaves differently.

1. Every gesture field captured today stays, with the same meaning and the same values.
2. A recording without the new data — every job learned before this ships — runs exactly as today.
3. New data never feeds a job's identity (shape keys, `targetIdentity`, `screenOf`), so every existing
   job is still recognised and offered.
4. Every new check in Steel starts in **shadow**: it runs beside today's verdict, is written down, and
   changes nothing. Each check is switched on per tenant only after QA shows it agrees, and only with
   the owner's yes (flag per item, empty by default).
5. A promoted check may only:
   - turn today's "unknown" into "confirmed", or
   - add a wait, a locator tried after all of today's have failed, or an ask that would otherwise not
     happen,
   and never turns today's pass into a failure. The two checks that would stop a run (wrong screen,
   record already exists) are listed separately under "Promotions that change behaviour" and need
   their own yes.

## What is captured (the eleven items)

All of it goes through the existing redaction: values of secret fields never leave the page
(`isSecretField`), names are matched by `domain/recording/sensitivity.py` and regenerated with
`make gen-recorder`, and the server redacts again (`redact.py`, `rig_wire` validators). Text read from
the page is capped (200 characters) and never includes a field's value; the outline rules for what may
be said (`outline._said`) apply to every new text field.

| # | Capture | Where it lives | Notes |
|---|---|---|---|
| 1 | **What changed after the action**: elements with a role that appeared or vanished (dialog, alert, status, toast, grid row, load mask), their role and short text; URL/route before and after; fields that became enabled, disabled, shown, hidden or invalid | new optional `effect` on the gesture | Watched from the action until the page is quiet for 500 ms, at most 3 s, or until the next gesture. Sent as a separate `effect` event referencing the gesture (`of: ref`), the way `prior` already reaches the previous gesture, because it is only known after the gesture was emitted. |
| 2 | **Where am I**: route/hash, title, up to 3 headings, selected tab labels, the main grid's title, the set of landmark labels | new optional `place` on the gesture | Taken at every gesture (outlines today are at most 3 per gesture and not on every one). |
| 3 | **Richer element identity**: the label text next to an input, the position among siblings of the same kind, the accessible name computed the full way | new optional fields on `target` | Most of the list in the proposal is already there (`attributes` carries all aria-* and the form-field name; `component` carries the Ext type, itemId and chain; `landmarks` the container path). Only the three missing signals are added. |
| 4 | **Readiness timing**: ms until the action's own requests finished, ms the load mask was visible, ms until the page was quiet | inside `effect` | |
| 5 | **Sign-in and session expiry**: the page sequence through a sign-in (already in `page_events`), consent or MFA prompts and the session-expired dialog with the button pressed (these come from item 1/6), and the **names and expiry times** of cookies set during sign-in — never values | `effect` + a new `cookies_set` page event | Cookie names need the `cookies` permission. It is added as an **optional** permission requested at runtime, so updating the extension never disables it or shows a new warning. A tenant that declines gets everything else. |
| 6 | **Dialogs as a chain**: opened (title, text, buttons), which button was pressed, closed, and the response that followed | from item 1's `effect` on consecutive gestures | No separate capture: the chain is assembled on the server from the open, press and close effects. |
| 7 | **The mail the work came from** — by reference only | a `mail_ref` on the recording window | Mail hosts stay excluded: nothing on a mail page is captured, screenshotted or uploaded. Only the thread id visible in the mail tab's URL is noted, and only for a tenant that opts in. The text is read at mining time through the tenant's own mail connector and never stored with the gestures. **Owner decision** (it touches the "mail hosts are excluded" rule). |
| 8 | **Required, optional and dependent fields**: validation messages shown after an incomplete submit, `aria-invalid` changes, other fields enabled/shown after one is set | inside `effect` (field changes) | The label star, `aria-required` and Ext `allowBlank` are already captured. |
| 9 | **What the person checked before and after writing** | nothing new to capture | The searches are already recorded as GETs on the gestures. What is new is reading them (consumer C9) with the lookup's strict "whole list" rules. |
| 10 | **Combobox options and the chosen value**: the floating list's option labels (up to 50) and the chosen label and index | new optional `choice` on the gesture | Ext combos render a floating list, so this is read when an option row is clicked. |
| 11 | **Extras**: tab focus and visibility changes; console errors and uncaught exceptions (text capped, URLs redacted); keyboard shortcuts with modifiers; the app's build or version string (Ext version, a version meta tag, the main script's name) | `effect`, new page events, and `place.version` | Hover and per-container scroll are not captured: the map shows no failure they explain. |

### How the new data reaches storage

Per the map, a gesture key that is not declared on the server is silently dropped before storage
(`redact.py` whitelists `rig_wire` fields). So each new field is added in this order, in one change per
item:

1. `domain/recording/sensitivity.py` and the server redaction for any new text,
2. `rig_wire.Gesture` / `Target` / a new `EffectEvent` (so the server keeps it),
3. `domain/observation/gesture.py` (`Action` / `Target` with a default, so old rows load unchanged),
4. `correlate.as_action` (attach `effect` events to their gesture),
5. `recorder.js` / `page-code.js`, then `make gen-recorder` and `make fixtures`,
6. `trim()` only where the miner or reader should see it.

The **backend ships first**, so an extension that sends the new fields never meets a server that drops
them. An old extension keeps working against the new server (all new fields are optional).

## How Steel uses it (consumers)

Each consumer stays a lane `StepResult` (no model call in `domain/` or in a Temporal workflow body), and
each writes its shadow verdict into the step's notes in `workflow_run_steps` so it can be counted.

| | Consumer | Uses | Shadow records | When promoted |
|---|---|---|---|---|
| C1 | **Confirm a write by what the page did**: the same dialog, toast, status text (values replaced by the job's parameters), route change or grid row the demonstration showed | 1, 4, 6, 8 | "would confirm / would not" next to today's `unknown` | an `unknown` write the page confirms counts as done instead of parking "sent and nothing confirms it" |
| C2 | **Know the screen**: compare the live `place` with the recorded one before each step and when resuming | 2 | match score per step and at resume | resume picks the step whose recorded place matches; see "Promotions that change behaviour" for stopping on a wrong screen |
| C3 | **More ways to find a control**: label text and sibling position as locators | 3 | which locator would have found it | the new locators are tried only **after** every locator used today has failed, before `repair` |
| C4 | **Wait as long as this step needs**: the recorded settle time | 4 | recorded vs live settle time | waits get longer where the recording shows a slow step, never shorter than today's |
| C5 | **Stay signed in**: re-sign-in before the recorded cookie/token expiry; recognise the recorded session-expired dialog | 5 | "would re-sign-in now" | an early re-sign-in through today's broker path |
| C6 | **Dialogs**: expect the recorded open → press → close → response chain | 6 | chain matched or not | part of C1's confirmation |
| C7 | **Learn from the mail**: pair mail to job and learn which words became which field | 7 | mining notes only | better mail readings; feeds the mail eval corpus |
| C8 | **Ask for what the job really needs**: fields the recording proved required | 8 | "would ask for X" | the job asks for that value, where today it would run without it and fail on the page |
| C9 | **Check before writing, confirm after**: the recorded search becomes the job's existence check before a create and its read-back after | 9 | "would have found it already exists" | see "Promotions that change behaviour" |
| C10 | **Pick a dropdown option by its label** when the order differs | 10 | which option would be picked | a label locator tried after today's |
| C11 | **Explain failures**: console errors and failed requests shown on the failed step; a changed app version flagged as possible drift | 11 | shown only | stays informational |

### Promotions that change behaviour (each needs its own yes)

- **C2 stop on the wrong screen**: before a write, a place that clearly does not match makes the run ask
  instead of acting.
- **C9 refuse a duplicate**: a create whose own recorded check finds the record already there asks
  instead of creating. Only a whole-list read under the lookup's strict rules may say "not there".

Both prevent harm (a write on the wrong screen, a duplicate record), but they stop runs that today would
go ahead, so they are not covered by the additions-only rule.

## Measuring it

- **Baseline first**, before anything ships: count the last 30 days of QA steps per class from
  `workflow_run_steps` (verdict, verdict_by, reason, matched_by) and `known_broken` fingerprints. The
  classes are: unconfirmed write, sign-in, control/page not found, duplicate, timing, wrong resume. The
  counts in the proposal (6 of 15, 3, 3, 2) are re-derived from this, not assumed. The query goes in
  `scripts/measure.py`.
- **Re-record**: new captures only exist for jobs recorded after the extension update. On QA the
  owner's main jobs (customer type, warehouse equipment type, bin adjust, the mail jobs) are recorded
  again once.
- **Shadow agreement per consumer**: how often the shadow verdict agrees with the outcome a person
  confirmed. A false confirmation from C1 (it said done, the record was not there) is the critical
  error and is checked on every shadowed write by a read-back where one exists.
- **Promotion gate per consumer**: at least 20 shadowed steps on QA, agreement of at least 95%, zero
  false confirmations, and no run that passes today failing. Then the owner's yes.
- **After**: the same class counts per tenant after each promotion.

## Privacy and data

- Values of secret fields and cookie values are never captured. Cookie names and expiry only, behind
  an optional permission.
- Mail stays unobserved; at most a thread id by reference, opt-in.
- Every new text field is capped and passes `outline._said` (no ids, URLs, hex or long tokens).
- **Found while mapping:** "delete the last hour" and retention remove the batches and blobs but not
  the `gestures` rows. **Owner ruling (2026-10-02): no data is removed** — deletion and retention stay
  exactly as they are. Consequence for this design: because gesture rows are kept, every new field
  must be safe to keep indefinitely: no field values, no cookie values, no mail text, nothing a
  redaction rule would hide, text capped and passed through `outline._said`.

## Order of work

1. Baseline measurement on QA.
2. Server: accept and store `effect`, `place`, the target extras, `choice`, page events and
   `place.version` (old extension unaffected).
3. Extension: capture items 1-6, 8, 10 and 11; `make gen-recorder`, `make fixtures`; the optional
   cookies permission.
4. Consumers C1-C6, C8, C10 and C11 in shadow; re-record the main QA jobs.
5. Item 7 and C7, if the owner says yes to the mail reference.
6. C9 in shadow.
7. Measure; promote one consumer at a time with the owner's yes.

## Tests

- Unit: each new field round-trips wire → storage → `Action`; an old row loads with defaults; an
  unlisted key is not silently lost (the `redact.py` trap gets a test); identity and shape keys are
  byte-identical with and without the new fields (golden fixtures `shape-identity.json`,
  `screen-of.json`).
- Browser (`tests/browser`, the template `test_the_state_a_gesture_left.py`): a click that opens a
  dialog, a Save that shows a toast, a validation message after an incomplete submit, a combo choice, a
  route change — each yields the expected `effect`; secrets never appear.
- Steel (`tests/integration/test_runs_on_local_steel.py`): each consumer in shadow leaves verdicts
  unchanged and writes its note; each promoted consumer only turns `unknown` into done, adds waits, or
  adds locators after today's.
- Redaction: `test_what_the_recorder_hides.py` and `test_generated_scripts_are_current.py` extended to
  every new text field.

## Owner decisions (2026-10-02)

1. No data is removed: deletion and retention stay exactly as they are.
2. Item 7: yes — the extension may note the mail thread id from the mail tab's URL, for tenants that
   opt in; nothing else from a mail page is captured.
3. C2 (stop on a wrong screen) and C9 (refuse a duplicate) are built now, in shadow; switching either
   on is a separate yes.
