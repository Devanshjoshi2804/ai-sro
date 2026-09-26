# Notes for `backend/evals/model.py`

What a case, a scored case and a suite's report are, and the gate a prompt change must pass.

## `K_COVERS`, [line 10](../../../../backend/evals/model.py#L10): Constant

> Spec §2.2, mining: "One proposed job covering at least 80% of the cites".

## `report`, [line 61](../../../../backend/evals/model.py#L61): Design

> Sure-but-wrong is counted over all cases, not over the sure ones: a prompt
> that grows less sure and no more right lowers it, and the gate wants that.
> p50 and p95 are nearest-rank on the sorted latencies.

## `gate`, [line 78](../../../../backend/evals/model.py#L78): Design

> Spec §2.2: "A prompt change merges only if accuracy holds or improves,
> sure-but-wrong does not rise, and cost does not rise."
>
> Each rule is compared exactly. The spec gives no tolerance, and a cost that
> wobbles between two runs of one prompt means its output length is unstable,
> which is itself worth seeing. Returns every broken rule, so one report names
> all of them.
