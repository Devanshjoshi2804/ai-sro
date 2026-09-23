# Notes for `backend/scripts/dry_run.py`

Comments and docstrings moved out of [`backend/scripts/dry_run.py`](../../../../backend/scripts/dry_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/dry_run.py#L1): Docstring

> The offer, replayed against the backend's own stored evidence.
>
> `make offer-replay-backend`. Writes the file
> `new-chrome-extension/scripts/offer-replay.mjs` reads: every shape this
> backend serves, beside the gestures each proven job was mined from, in the
> order the operator made them. The `.mjs` feeds those gestures one at a time
> through the same `tailWith` and `match` the service worker runs, and reports
> at which gesture each job would have been offered and whether the offer named
> the job the operator was actually doing.
>
> The port of `new_agent_arch/scripts/dry_run.py`'s `--replay` half, and only
> that half. The rig's script also starts every workflow over `POST /v1/runs`
> against a fake browser and a model that is not a model; the runner is not in
> the backend yet, and a dry run of a runner that does not exist is not a thing
> to write. The replay is what the spec makes phase 4's acceptance test, and the
> replay is what this emits.
>
> Reads only. Nothing here writes, and no model is asked: the shapes come from
> `ServeShapes` and the gestures from the evidence repository, both under a unit
> of work that never commits.
>
> `ServeShapes` is called directly, where the rig's script went over
> `GET /v1/shapes`. So the acceptance test proves the use case and the matcher
> and does NOT exercise the HTTP door: the router, its auth dependency and its
> response model are covered by `tests/integration/test_the_read_only_doors.py`
> and by nothing here. A shape that serialises differently through the route
> than through the use case would pass this replay.
>
>     uv run python scripts/dry_run.py --replay /tmp/backend-replay.json

## module, [line 20](../../../../backend/scripts/dry_run.py#L20): Note on the line above

Code: `TYPED = "•"`

> What a gesture carrying a declared parameter's value exports as.
>
> The matcher lifts on "a value was typed here", never on the text, so the text
> does not leave the store: the replay file is written to /tmp and read by a
> node script, and a customer's part number has no business in either.

## `_gestures_of`, [line 23](../../../../backend/scripts/dry_run.py#L23): Docstring

> One job's cited gestures as the extension would have seen them.
>
> Scrolls stay in. `recognise.js`'s `tailWith` is what drops them, and this
> is a test of `recognise.js` -- handing it a tail with the scrolls already
> removed would be marking its own homework.

## `replay`, [line 43](../../../../backend/scripts/dry_run.py#L43): Docstring

> `{"shapes": [...], "jobs": [...]}` -- what `offer-replay.mjs` reads.
>
> Every workflow is a job here, not only the served ones. A shape that is
> withheld and a job whose gestures are still replayed is exactly the case
> the matcher must answer "never offered" to, and dropping those jobs would
> hide it by never asking.
>
> No `device_id`: the shapes are served as they are to a browser that has
> refused nothing, which is what the rig's dry run asked for too. A device's
> own refusals rest a job on that device alone, and a corpus measurement
> taken through one browser's sulk is a measurement of the sulk.

## `_gestures_of`, [line 24](../../../../backend/scripts/dry_run.py#L24): Comment

Code: `cited = in_time_order(workflow, by_id)`

> In the order they HAPPENED, not the order the model narrated them.
> A browser appends to its tail as gestures arrive; it has never heard of a
> step. Replaying in step order -- the same order the served shape is built
> from -- handed the matcher its own answer, and the difference is not
> small: acme read 5 of 7 offered that way and 3 of 7 honestly.

## `_gestures_of`, [line 25](../../../../backend/scripts/dry_run.py#L25): Comment

Code: `seen: set[str] = set()`

> The values a declared parameter has been seen holding, which the store
> already records on the workflow: a typed gesture carrying one is exported
> as a presence mark and nothing else.

## `_gestures_of`, [line 30](../../../../backend/scripts/dry_run.py#L30): Comment

Code: `return [`

> `shape_key` over the whole list rather than a triple built by hand here:
> it is the function `shape_of` builds the served shape from, and a second
> spelling of the triple is a replay that fails to match for a reason that
> is in this file rather than in the matcher.

## `_gestures_of`, [line 33](../../../../backend/scripts/dry_run.py#L33): Comment

Code: `"value": TYPED if seen & put_by(gesture) else None,`

> `put_by` and not `action.value`: a dropdown pick is a click on a
> row of a floating list and carries its answer in that row's text,
> which is what the service worker now writes into the tail. Asking
> the narrower question here would replay a browser that never
> existed and report every dropdown parameter unanswered.

## `replay`, [line 45](../../../../backend/scripts/dry_run.py#L45): Comment

Code: `async with uow as opened:`

> A `UnitOfWork` has no repositories until its session opens.
