# Notes for `backend/src/sro/domain/prompts/check_step.py`

Notes on [`backend/src/sro/domain/prompts/check_step.py`](../../../../../../../backend/src/sro/domain/prompts/check_step.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 7](../../../../../../../backend/src/sro/domain/prompts/check_step.py#L7): Comment

Code: `"properties": {`

> held first, why last: decide, then explain.
>
> `why` is nullable: the verdict is the answer and `why` its commentary, so a
> verdict that came without one keeps its verdict with an empty reason
> (`Prompt.kept`), where a required string made the whole verdict unsure.

## module, [line 41](../../../../../../../backend/src/sro/domain/prompts/check_step.py#L41): Note on the line above

Code: `CHECK_SCREEN = Prompt(`

> What a picture can settle about a step that DID something.
>
> The last two sentences were added 2026-09-22, measured on the deployment that
> night. `Create a Customer Type` reached *"Select Create Shipment By value"*,
> the dropdown stayed empty, and the step was held on the reason *"The Save
> button is clearly visible and accessible at the bottom of the screen."* True,
> about a different control, and no answer to the question asked. The run went
> on to Save with the field unset and the record was never created -- the
> read-back looked for it and it was not there.
>
> The rule this rung already carried -- do not assume success from the absence
> of an error -- did not cover it, because the model was not assuming anything
> from an absence. It was reporting a presence, of something else.
>
> It was `SCREEN_INSTRUCTIONS` in `sro.domain.execution.belts`; the text is
> verbatim, split at its first blank line into role and task.

## module, [line 99](../../../../../../../backend/src/sro/domain/prompts/check_step.py#L99): Note on the line above

Code: `CHECK_WAY_THROUGH = Prompt(`

> The proposition a step that changes nothing can actually settle.
>
> Measured on the deployment 2026-09-19. `Delete a Customer Type` stopped six
> times running on its first step, *"Opens the filter dropdown."* -- a sentence a
> mining model wrote about a click on a combobox field that sent no request and
> typed nothing. The click landed every time (`matched_by = component`), the
> field was focused, and the screen belt was asked whether a dropdown had opened.
> It had not, and the job stopped, and it could never have done anything else:
> five of that job's six steps send no traffic at all, so five of six were being
> judged against a guess.
>
> A picture cannot settle what a click was FOR. It can settle whether the screen
> is now somewhere the job can continue from, which is the only thing the step
> after this one needs to be true.
>
> And it has to be TOLD what that step is. Until 2026-09-22 this rung claimed
> that proposition and never tested it: the model was shown one screen and asked
> whether anything looked broken, which is a different question and a weaker one.
> Measured on the deployment that night, on this same job. *"Presses Enter to
> apply the filter"* was held with the reason *"the screen remains functional and
> unchanged, with no blocking errors"* -- true, and the filter had not applied.
> Enter had opened the field's suggestion list, four rows of `KKYT in Customer
> Type`, `KKYT in Description`, sitting over an unfiltered grid. The next step,
> *"Selects the matching customer type from the grid"*, then spent nine attempts
> and a trip to the vision rung hunting a row that was not there, and refused.
>
> A suggestion list over the grid is not something "looking broken". It is
> exactly and only a problem for the step that comes next, so the step that comes
> next is what the question has to name.
>
> It was `WAY_THROUGH_INSTRUCTIONS` in `sro.domain.execution.belts`; the text
> is verbatim, split at its first blank line into role and task. Both checks
> share one schema and one input contract, since `verify` builds one evidence
> for either and chooses the record by whether the step changes anything.
