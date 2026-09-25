# Notes for `backend/src/sro/application/runtime/api_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/api_lane.py`](../../../../../../../backend/src/sro/application/runtime/api_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_AUTH_REFUSED`, [line 31](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L31): Comment

> The answers that mean the session, not the step (spec §3, §5.5): 401 and
> 403 are a missing or refused session, 419 is the refused CSRF token some
> frameworks (Laravel) answer with. The lane marks the result `expired`; the
> executor has the broker sign in again and retries the step once, with
> `LaneContext.reauthed` so the retry asks for fresh headers. Every other
> rejection belongs to the step and drops it to the UI lane for this run.

## `K_REPRESENTATION`, [line 33](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L33): Comment

> The only headers taken from the recording: they describe the body, not who
> sends it. Anything that names an account (an `x-user-id`, a tenant header,
> a token) comes from this account's own context through the broker, never
> from the account that was recorded.

## `K_TOKEN_ROLES`, [line 35](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L35): Comment

> The header roles the page's request log keeps (the same roles the Steel
> driver logs). A recorded header of one of these roles whose value was
> redacted is one the write needs from the live session.

## `ApiLane`, [line 38](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L38): Docstring

> Replays a write the ledger has watched succeed (`replay_without_asking`)
> through httpx, with the broker's live cookie and token headers for this
> exact request URL (scheme included: the broker's cookie rule is per request,
> host-only, Secure and Path). No header value is logged or put in a reason,
> and an exception is reported by its class alone: an httpx or h11 message can
> quote the header value it refused.

## `ApiLane.execute`, [line 45](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L45): Comment

> A token the recorded write carried and the live session does not have is
> refused before anything is sent (`never_left`): the call would only be
> refused, and nothing has left, so another lane may take the step.

## `ApiLane.execute`, [line 45](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L45): Comment

> `never_left` is decided by phase, not by the kind of exception. The request
> is checked whole before `about_to_write`: an absolute http(s) URL, and
> header names and values a request line can carry. From the send on, any
> exception (a reset, a timeout, an answer httpx could not decode) may follow
> a request the system received and applied, so the write is `unknown`, never
> failed, and no lane repeats it blindly (§6.2).

## `ApiLane.execute`, [line 45](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L45): Comment

> A redirect off the system's host (or a sign-in form in place of an answer),
> by the same structural test `CheckSession` uses, means the session is gone.
> A write answered that way is not provably unapplied (post-redirect-get after
> a success is common), so it is `unknown` and `expired`: the executor signs
> in again and settles it by `read_back`, never by sending it again.

## `ApiLane.execute`, [line 45](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L45): Comment

> The lane sends one call, so the answer is the write's own call; the ruling
> that a write is done only by its own call holds by construction.
> `write_confirmed` reads its status the one way every lane does: a status
> the recording saw (or any 2xx when it saw none) passes, a 5xx is in doubt
> (`unknown`: the system may have written before it failed), and a 4xx is a
> rejection. The recorded call is compared at the URL actually sent, because
> a path-addressed write names this run's record, not the recorded one.

## `ApiLane.execute`, [line 45](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L45): Comment

> A 2xx is not proof (§6.2; parent spec §4.3 "Unconfirmed write"): the step is
> `done` only when the recorded confirming read, sent after the write, shows
> the record written. Without one, or when it does not show it, the write is
> `unknown` and the run settles it later with `read_back` or asks.

## `ApiLane._confirmed`, [line 129](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L129): Comment

> One check for `execute` and `read_back`. The confirming read goes only to
> the write's own origin (a GET recorded after the write may be analytics or
> the identity provider). It confirms only when the replay filled named body
> slots and one record carries every slot with this run's value
> (`carries_in_slot`): the value in another field, another row or a longer
> string is not the record this run wrote. A write with no filled slots is
> never confirmed by a read-back.

## `_aimed`, [line 197](../../../../../../../backend/src/sro/application/runtime/api_lane.py#L197): Comment

> The recorded read names the recorded record. A path segment equal to a value
> the recording saw for a filled parameter is replaced by this run's value. A
> recorded value found anywhere else in the URL (inside a segment, in the
> query) cannot be re-aimed safely, so no read is sent and the write stays
> `unknown`.
