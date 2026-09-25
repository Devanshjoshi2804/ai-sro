# Notes for `backend/src/sro/application/runtime/api_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/api_lane.py`](../../../../../../../backend/src/sro/application/runtime/api_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_AUTH_REFUSED`, [line 32](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L32): Comment

> The answers that mean the session, not the step (spec §3, §5.5): 401 and
> 403 are a missing or refused session, 419 is the refused CSRF token some
> frameworks (Laravel) answer with. The lane marks the result `expired`; the
> executor has the broker sign in again and retries the step once. Every
> other rejection belongs to the step and drops it to the UI lane for this run.

## `ApiLane`, [line 35](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L35): Docstring

> Replays a write the ledger has watched succeed (`replay_without_asking`)
> through httpx, with the recorded headers under the broker's live cookie and
> CSRF headers for this exact request URL (scheme included: the broker's
> cookie rule is per request, host-only, Secure and Path). A header the
> session names replaces the recorded one of the same name in any case, so a
> name is never sent twice. No header value is logged or put in a reason.

## `ApiLane.execute`, [line 42](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L42): Comment

> A request httpx could not frame never left this worker, so the step is a
> plain failure the UI lane may take up. Anything else raised once
> `about_to_write` has run may have reached the system: the write is in
> doubt and is `unknown`, never failed, so no lane repeats it blindly (§6.2).

## `ApiLane.execute`, [line 42](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L42): Comment

> The lane sends one call, so the answer is the write's own call; the ruling
> that a write is done only by its own call holds by construction.
> `write_confirmed` reads its status the one way every lane does: a status
> the recording saw (or any 2xx when it saw none) passes, a 5xx is in doubt
> (`unknown`: the system may have written before it failed), and a 4xx is a
> rejection. The recorded call is compared at the URL actually sent, because
> a path-addressed write names this run's record, not the recorded one.

## `ApiLane.execute`, [line 42](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L42): Comment

> A 2xx is not proof (§6.2; parent spec §4.3 "Unconfirmed write"): the step is
> `done` only when the recorded confirming read, sent after the write, shows
> the values written. Without one, or when it does not show them, the write
> is `unknown` and the run settles it later with `read_back` or asks.

## `ApiLane._confirmed`, [line 126](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L126): Comment

> A value the read's own URL carries proves nothing when the body echoes it,
> so only the values the URL does not name are looked for; a read with none
> left confirms nothing. A read URL still holding a redacted marker cannot be
> sent.

## `ApiLane._confirmed`, [line 126](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L126): Comment

> When the replay filled named body slots, one record must carry every slot
> with its value (`record_carrying`): a list where the value sits in another
> field or another row is not the record this run wrote. Without slots (a
> path-addressed write, or settling an unknown write by parameter name) the
> values must each appear in the body.
