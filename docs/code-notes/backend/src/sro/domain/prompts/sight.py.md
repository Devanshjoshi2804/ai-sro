# Notes for `backend/src/sro/domain/prompts/sight.py`

Notes on [`backend/src/sro/domain/prompts/sight.py`](../../../../../../../backend/src/sro/domain/prompts/sight.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 22](../../../../../../../backend/src/sro/domain/prompts/sight.py#L22): Note on the line above

Code: `SIGHT = Prompt(`

> One gesture from the computer-use tool, for the sight lane. It was
> `_INSTRUCTIONS` in `sro.infrastructure.gemini.computer_use`, one paragraph,
> so its first sentence is the role. The line the adapter added after the
> evidence -- coordinates are 0-1000 -- is prompt text too, and is the task's
> last paragraph now.
>
> `output_schema` is empty: computer use answers with a function call, not JSON,
> and a JSON schema beside the tool is refused with a 400.
>
> `3.8-flash`, the `gemini_vision_model` default and what runtime GC 14 and
> `test_the_sight_lane_escalates_from_flash_to_pro_and_both_are_metered` pin.
> `.env.example` pinned `gemini-2.5-computer-use-preview-10-2025`, which a
> deployment copying it would have run; that model is not in `prices.py`, so its
> calls were billed at zero, the failure the note below records for `3.7-flash`.
> A deployment that still sets `SRO_GEMINI_VISION_MODEL` is refused at load and
> told the model lives here, so it cannot move silently either way.
>
> Computer use is native here rather than a separate specialised model.
> Checked against the account rather than assumed: the standalone
> `gemini-2.5-computer-use-preview` still answers, and this one accepts the
> same tool while being the model everything else already uses.

## module, [line 64](../../../../../../../backend/src/sro/domain/prompts/sight.py#L64): Note on the line above

Code: `SIGHT_ESCALATED = replace(SIGHT, name="sight_escalated", model="gemini-3.1-pro-preview")`

> The one escalation to pro (runtime GC 14). A second record, not a model
> argument: see `GeminiVisionDriver` in `computer_use.py.md`.
