# Notes for `backend/scripts/backfill_gestures.py`

Comments and docstrings moved out of [`backend/scripts/backfill_gestures.py`](../../../../backend/scripts/backfill_gestures.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/backfill_gestures.py#L1): Docstring

> Replay stored batches through correlate into the evidence plane.
>
> Written as a one-off: the 397 batches predate the ingest wiring, so their events
> are in the blob store and nothing read them out. Reads the payload that was
> actually stored (already redacted), so a gesture cites what the blob holds.
>
> **Skips a batch already in `gesture_batches`, and that is not an optimisation.**
> `correlate` mints a fresh `new_gesture_id()` every time it reads an event, so a
> batch replayed twice lands twice with different ids, and nothing refuses it --
> `add_gestures` only catches an id it has already seen. The evidence doubles and
> every doubled gesture is mined as a second doing of the same job. Without this
> the script could be run exactly once per store, and there was nothing in it
> saying so.
>
> That mattered on 2026-09-14: four days were observed and never reached the
> evidence plane -- `new` 2026-09-02 alone was 127 batches and 0 gestures, which
> is where `Create a supplier` was done. The model path was never shown it, and
> the deletion argument in `docs/new-agent-doc-arc/two-miners-one-day.md` rests
> on that gap being closed rather than explained away.

## `_database_url`, [line 14](../../../../backend/scripts/backfill_gestures.py#L14): Docstring

> The address the app reads, taken the same way the app takes it.
