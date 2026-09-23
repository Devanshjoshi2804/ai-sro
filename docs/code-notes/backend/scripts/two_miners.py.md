# Notes for `backend/scripts/two_miners.py`

Comments and docstrings moved out of [`backend/scripts/two_miners.py`](../../../../backend/scripts/two_miners.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/two_miners.py#L1): Docstring

> Both miners over one tenant's day, side by side.
>
> The precondition on deleting anything, and the one number the spec asks for
> that nobody has produced. `MineObservations` reads `observations` and writes
> `task_candidates`; `mining_pass.mine` reads `gestures` and the pool and writes
> `workflows`. **Neither reads the other's tables**, so "the model path works"
> and "the rule-based path is safe to delete" are two claims and only the first
> has ever been tested.
>
>     uv run python scripts/two_miners.py acme
>     uv run python scripts/two_miners.py acme --window-hours 720
>
> Reads only, by default. The rule-based miner WRITES candidates as it goes --
> that is how it records what it found -- so `--rule-based` has to be asked for,
> and the model pass costs a 150K-token call, so `--model` does too. With
> neither, this reports what the two paths have already produced over the same
> window, which is the comparison as far as it can be made for free.
>
> What it cannot answer is the half the spec puts last: how many of each a person
> agrees with. That is a reading, not a count, and it is why this prints both
> lists in full rather than only their sizes.

## `_report`, [line 41](../../../../backend/scripts/two_miners.py#L41): Comment

Code: `print(f"   {len(candidate.episodes):3}x  {candidate.title or candidate.signature}")`

> How many times it was seen, because that is what the rule-based path
> is FOR: a task done once is not a task worth automating, and the
> count is the whole of its argument.
