# 016 — Richer capture is additions only

**Status:** accepted, 2026-10-02
**Relates to:** [008 — passive observation](008-passive-observation.md); spec `docs/superpowers/specs/2026-10-02-richer-capture-for-steel-design.md`

## The problem

Steel runs fail or stall in a few measured classes: a write sent with nothing confirming it, sign-in,
a control or page not found, duplicates, and resuming on the wrong step. Baseline (QA, last 30 days,
`backend/scripts/measure.py` section 3b, `docs/measurements/2026-10-02-capture-baseline.json`):
151 failing or unclear steps of 1,207 — no_browser 49, sign_in 21, unconfirmed_write 19,
no_approval 15, duplicate 13, missing_value 11, screen_disagrees 8, not_found 7, no_model 5,
wrong_page 2, timing 0, other 1. Several of these (no_browser, no_approval, no_model) are not
something richer capture can touch; the rest are what the recording does not say: the recording
holds what the person did, not what the page did back.

## Decision

1. The recorder captures more (effect after each action, place, element extras, combo choice, cookie
   names and expiry, app version, opt-in mail thread reference) as **optional fields with defaults** on
   the wire, the domain and the JSONB gesture row. No migration touches `gestures`; old rows load.
2. "What changed after the action" travels as its own `effect` event, joined to its gesture by `ref`
   in a batch and by (stream, tab, frame path, time) across batches — it is only known after the
   gesture was emitted.
3. New data never feeds identity: `targetIdentity`, `screenOf` and shape keys read only today's fields;
   the golden fixtures prove it byte for byte.
4. Every consumer in Steel is a lane-level note first (`shadow:<check>:<verdict>` in
   `workflow_run_steps.notes`), per tenant, empty by default. Promotion is per check and per tenant,
   after the gate (at least 20 shadowed steps on QA, at least 95% agreement, zero false
   confirmations, no run that passes today failing) and the owner's yes. A promoted check may only
   turn unknown into confirmed, add a wait, add a locator after today's, or add an ask. Stopping a
   run (wrong screen, duplicate) is a separate yes.
5. Nothing is removed (owner ruling): gesture rows outlive "delete the last hour" and retention, so
   every new field is safe to keep forever — no field values, no cookie values, no mail text, and
   every new text passes `outline.said_text` (the one rule outlines already use) in
   `domain/observation/seen.py`, the single sanitiser for wire, store and live reads.

## Consequences

- Recognition and offers are untouched; only jobs recorded after the extension update carry the new
  data, so the owner's main QA jobs are recorded again once.
- Two new effect paths at ingest (in-batch join, cross-batch update of the stored row's JSONB); an
  effect that matches no or several stored gestures is dropped and logged, never guessed.
- The `cookies` permission is optional and requested at runtime, so updating the extension shows no
  new warning.

## Accepted ceilings of the new-text sanitiser

Data is kept forever, so `said_text` drops on doubt, but two shapes cannot be told from ordinary words and are accepted: a mail thread reference is kept when it is 16 or more id characters that `redact_shapes` leaves alone (a real Gmail id looks exactly like a short secret), and a route path token under 20 characters that is not digit-heavy (`/reset/Zm9vYmFy`) is kept. A credential written with no separator ("password hunter2") is also kept for the same reason.
