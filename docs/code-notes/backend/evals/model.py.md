# Notes for `backend/evals/model.py`

What a case, a scored case and a suite's report are, and the gate a prompt change must pass.

## `K_COVERS`, [line 10](../../../../backend/evals/model.py#L10): Constant

> Spec §2.2, mining: "One proposed job covering at least 80% of the cites".

## `K_OWN`, [line 11](../../../../backend/evals/model.py#L11): Constant

> The precision floor: at least half of what the covering job cites must be
> the case's own cites. Recall alone passes one lumped job that cites the
> whole window, so a prompt that over-merges would score better.

## `K_COST_TOLERANCE`, [line 12](../../../../backend/evals/model.py#L12): Constant

> Cost per case may rise by up to 10% before the gate calls it a rise. The
> output length of one prompt jitters between runs, so an exact comparison
> fails the same prompt against itself about half the time. Accuracy and
> sure-but-wrong stay exact: they are compared on the same frozen cases.

## `Report.load`, [line 62](../../../../backend/evals/model.py#L62): Design

> A baseline records the sorted ids of the cases it was scored on, so a run
> is gated only against the same case set.

## `report`, [line 71](../../../../backend/evals/model.py#L71): Design

> Sure-but-wrong is counted over all cases, not over the sure ones: a prompt
> that grows less sure and no more right lowers it, and the gate wants that.
> p50 and p95 are nearest-rank on the sorted latencies. An errored case (a
> timeout, a closed client, a call refused for no tenant) is counted in
> `errors`, not passed off as an unsure miss.

## `gate`, [line 90](../../../../backend/evals/model.py#L90): Design

> Spec §2.2: "A prompt change merges only if accuracy holds or improves,
> sure-but-wrong does not rise, and cost does not rise."
>
> A run with any error fails, with or without a baseline (`before` is
> None), so a failing run is never written as the baseline. A run on a
> different case set from the baseline's fails without comparing numbers.
> Returns every broken rule, so one report names all of them.
