# Notes for `backend/src/sro/application/runtime/api_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/api_lane.py`](../../../../../../../backend/src/sro/application/runtime/api_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_AUTH_REFUSED`, [line 33](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L33): Comment

> The answers that mean the session, not the step (spec §3, §5.5): 401 and
> 403 are a missing or refused session, 419 is the refused CSRF token some
> frameworks (Laravel) answer with. The lane marks the result `expired`; the
> executor has the broker sign in again and retries the step once, with
> `LaneContext.reauthed` so the retry asks for fresh headers. Every other
> rejection belongs to the step and drops it to the UI lane for this run.

## `K_REPRESENTATION`, [line 35](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L35): Comment

> The only headers taken from the recording: they describe the body, not who
> sends it. Anything that names an account (an `x-user-id`, a tenant header,
> a token) comes from this account's own context through the broker, never
> from the account that was recorded.

## `ApiLane`, [line 43](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L43): Docstring

> Replays a write the ledger has watched succeed (`replay_without_asking`)
> through httpx, with the broker's live cookie and token headers for this
> exact request URL (scheme included: the broker's cookie rule is per request,
> host-only, Secure and Path). No header value is logged or put in a reason,
> and an exception is reported by its class alone: an httpx or h11 message can
> quote the header value it refused.

## `ApiLane.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L49): Comment

> The broker is asked to wait (within its bound) for every token the
> recorded write carried; a token the live session still does not have is
> refused before anything is sent (`never_left`): the call would only be
> refused, and nothing has left, so another lane may take the step.

## `ApiLane.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L49): Comment

> `never_left` is decided by phase, not by the kind of exception. The request
> is checked whole before `about_to_write`: an absolute http(s) URL, and
> header names and values a request line can carry. From the send on, any
> exception (a reset, a timeout, an answer httpx could not decode) may follow
> a request the system received and applied, so the write is `unknown`, never
> failed, and no lane repeats it blindly (§6.2).

## `ApiLane.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L49): Comment

> A redirect off the system's host (or a sign-in form in place of an answer),
> by the same structural test `CheckSession` uses, means the session is gone.
> A write answered that way is not provably unapplied (post-redirect-get after
> a success is common), so it is `unknown` and `expired`: the executor signs
> in again and settles it by `read_back`, never by sending it again.

## `ApiLane.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L49): Comment

> The lane sends one call, so the answer is the write's own call; the ruling
> that a write is done only by its own call holds by construction.
> `write_confirmed` reads its status the one way every lane does: a status
> the recording saw (or any 2xx when it saw none) passes, a 5xx is in doubt
> (`unknown`: the system may have written before it failed), and a 4xx is a
> rejection. The recorded call is compared at the URL actually sent, because
> a path-addressed write names this run's record, not the recorded one.

## `ApiLane.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L49): Comment

> A 2xx is not proof (§6.2; parent spec §4.3 "Unconfirmed write"): the step is
> `done` only when the recorded confirming read, sent after the write, shows
> the record written. Without one, or when it does not show it, the write is
> `unknown` and the run settles it later with `read_back` or asks.

## `ApiLane.execute`, [line 69](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L69): Note

Code: `if missing:`

> A token the write needs that the session never sent is a session
> problem, not a broken lane: the result is `expired` (nothing left, so
> `never_left`) and carries no fingerprint, so nothing marks the API lane
> broken for it. The executor signs back in -- a sign-in waiting for a
> person answers `AccountBusy` and the run queues -- and retries with
> fresh headers.

## `ApiLane._confirmed`, [line 270](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L270): Comment

> One check for `execute` and `read_back`. The confirming read goes only to
> the write's own origin (a GET recorded after the write may be analytics or
> the identity provider). It confirms only when the replay filled named body
> slots and one record carries every slot with this run's value
> (`carries_in_slot`): the value in another field, another row or a longer
> string is not the record this run wrote. A write with no filled slots is
> never confirmed by a read-back.

## `_aimed`, [line 389](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L389): Comment

> The recorded read names the recorded record. A path segment equal to a value
> the recording saw for a filled parameter is replaced by this run's value. A
> recorded value found anywhere else in the URL (inside a segment, in the
> query) cannot be re-aimed safely, so no read is sent and the write stays
> `unknown`.

## `ApiLane.execute`, [line 98](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L98): Note

Code: `if status in K_AUTH_REFUSED and ctx.reauthed:`

> A refusal the first time is the session's problem: the executor signs
> back in and retries. A refusal on that retry, after a fresh sign-in, is an
> authorization refusal -- this account may not make this call -- so it is
> the lane's own failure, with a fingerprint, and the step joins the
> known-broken list instead of signing in again on every run.

## `ApiLane.execute`, [line 179](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L179): Note

Code: `refused = verdict == "unknown" and found is not None and found[0] != "ours"`

> A write that is not confirmed is read back once more, at its own record's
> address (`_by_key`), before anybody is asked. PJ26 (greyorange,
> 2026-09-30) was a 409 whose record never existed, and the run asked the
> operator to go and look in Blue Yonder -- something the system could check.
>
> Only a write the system did NOT accept (409, 5xx: `unknown`) can be
> proven refused. Its record absent means the save was refused, in the
> system's own words; present with other values means the key already
> exists. Either is `failed` and `refused`, and never handed to another lane.
> A write the system DID accept (2xx) whose record is absent stays
> `unknown`: the address may not be where this system keeps it, and a
> write that went in is never called refused. A read-back that cannot be
> made stays `unknown` too, and the operator is asked.
>
> The key is the first parameter of the job this write carries (`_key_of`).
> ponytail: a naive pick; a system whose record address is a composite id
> (Blue Yonder's `AITE6*!trlr_typ`) answers 404 there, which is why the
> resourceId read and the recording's own confirming read go first.

## `session_headers`, [line 306](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L306): Note on the line above

Code: `async def session_headers(`

> The one rule for which headers ride on a replayed call, shared by the API
> lane and lookups: the account's own cookie and token headers from the broker,
> plus only the recording's representation headers (`K_REPRESENTATION`) that the
> session did not answer itself. `wait_s` is how long the broker may wait for
> the headers `needs` names; a caller with a budget passes what is left of it.

## `needs_of`, [line 296](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L296): Note on the line above

Code: `def needs_of(recorded: Mapping[str, str]) -> list[str]:`

> The one rule for which headers a replayed call must get from the live
> session before it goes: the recorded call's redacted headers whose role the
> driver keeps (`K_TOKENS`). A redacted header of any other role -- a
> shape-redacted `X-Acme-Ticket` -- is never in any request log, so waiting
> for it would only burn the caller's deadline. Used by the lane's write, its
> read-back (so a read-back after `fresh=True` waits for its CSRF token rather
> than answering from an empty since-mark log), and lookups.

## `confirmed_keys`, [line 342](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L342): Function

> The learned fields this write's read-back confirmed, as `StepResult.keyed`
> reads (`{parameter: body_key}`), so `_settle_fields` holds them and a run
> that wrote them through the API lane is not left "failed" at `finish`.
> Only a learned slot whose key is in the plan's `confirm`, and only on a
> result a read-back made `done`: `carries_in_slot` checked every `confirm`
> entry, so each key here is one the record was seen holding (invariant 1).
> `_undemonstrated` puts every learned slot it fills into `confirm`
> unconditionally, so a learned slot the plan carries is always checked.
