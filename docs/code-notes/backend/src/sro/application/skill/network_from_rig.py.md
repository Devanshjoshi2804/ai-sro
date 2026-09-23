# Notes for `backend/src/sro/application/skill/network_from_rig.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/network_from_rig.py`](../../../../../../../backend/src/sro/application/skill/network_from_rig.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L1): Docstring

> The call a mined gesture caused, as a plan a run can replay.
>
> `from_rig` builds the gesture half of a step and `version_from_rig` assembles
> those into a version. Both stop at the screen. This is the other recipe -- see
> ADR 005 -- and it is the difference between a skill that can climb the ladder
> and one that cannot: `SkillVersion.needs_a_person` is true of any version with
> a step carrying no network plan, `judge` makes every run of one DEGRADED, and
> DEGRADED resets the clean streak. Measured before this existed: all eight
> workflows mined from the real corpus needed a person on all 165 steps, so not
> one of them could ever have reached the top of the ladder, however many times
> it ran perfectly.
>
> The rig stores the requests each gesture caused, so the evidence was already
> there. What was missing was the reading.
>
> **Which call a gesture is about** is `network.primary_of`, called rather than
> restated -- the induction path's rule, with its reasoning about analytics
> noise, keep-alives and the path-before-time ordering that stopped two runs of
> one task looking like they diverged. The rig captures no `initiator`, so a rig
> request degrades from the rule's first rung to its second: a successful
> mutation, just not one known to have come from a click handler.
>
> **What this cannot supply, on this corpus.** Measured over all 291 stored
> requests: the only `authorization` header anywhere is on twelve `localhost`
> calls, which are the rig talking to its own ingest. Every business call to the
> real WMS authenticates by cookie, and the rig captures no cookies -- so no
> plan built from this evidence carries a credential reference, because no
> credential was observed. A replay therefore depends on the executor's own
> session. That is a fact about the capture rather than a decision here, and
> inventing a SESSION header to hang a vault key on would be worse than the gap:
> it would make an unauthenticated plan look authenticated.
>
> The CSRF header IS handled, and it is the one that matters for a write: Blue
> Yonder's `CSRF-ENCRYPT-TOKEN`, classified by `sro.domain.recording.sensitivity`
> -- stale by construction, minted live, and the plan records that the call
> requires one. A count of those headers used to stand here in place of the name;
> it was taken over a capture store that is gone, nothing in this repository
> reproduces it, and the handling does not rest on it.

## `_when`, [line 37](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L37): Docstring

> A stored ISO timestamp, or None when it is not one.
>
> `CapturedRequest` refuses a naive datetime, and the rig writes `Z`, which
> `fromisoformat` reads only from 3.11 on. Nothing here guesses a timezone:
> a request with no readable time keeps its place by list order instead,
> which is what `primary_of`'s path-before-time ordering already prefers.

## `_sequence`, [line 48](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L48): Docstring

> A stored list, or nothing. A JSON null where a list belongs is not a list.

## `_epoch`, [line 52](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L52): Docstring

> A stored epoch-seconds clock, which is how the rig writes a gesture's.

## `_headers`, [line 61](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L61): Docstring

> Every observed header, empty values included.
>
> `build_header_plans` promises "one HeaderPlan per observed header. Nothing
> is dropped", and a header sent with an empty value was still sent -- some
> APIs distinguish absent from blank. Only a nameless one is dropped, because
> `HeaderPlan` refuses it.

## `_body`, [line 74](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L74): Docstring

> A stored body, which the rig keeps as a dict beside its own metadata.
>
> A body the rig replaced wholesale with `UNINSPECTABLE` is not a body: it is
> a sentence saying the redactor gave up. Sending it as a payload would post
> that sentence to the warehouse. It comes back as a blob-less, text-less
> Body so the caller can see something was captured and that none of it is
> replayable, rather than as None, which reads as "this call had no body".

## `request_from_rig`, [line 94](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L94): Docstring

> One stored exchange as the domain's, or None where it is not one.
>
> `at` is the fallback timestamp -- the gesture's own -- for a request whose
> stored `started_at` cannot be read. A CapturedRequest must have an aware
> one, and the alternative to a fallback is dropping real evidence over a
> clock format.

## `network_plan_for_gesture`, [line 126](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L126): Docstring

> The call this gesture caused, as a plan, or None where it caused none.
>
> `requests` is `Sequence[object]` rather than a sequence of mappings because
> that is what it is: rows off `json.loads`, out of a column, shaped by
> whatever wrote them. Promising a narrower type here would make the guard
> below unreachable to a type checker and reachable to a real payload.
>
> None is the ordinary answer and not a failure: most gestures are a click
> that moved focus. Measured on the real corpus, 78 of 387 gestures carry any
> request at all.

## `_unreplayable`, [line 169](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L169): Docstring

> Why this call cannot be replayed, or None when it can.
>
> `NetworkPlan` refuses `replayable=False` with no reason -- "an unexplained
> dead end is indistinguishable from a capture bug" -- so the previous
> version's bare `replayable=` flag could never once fire without raising and
> taking the whole workflow build with it. A guard that crashes instead of
> guarding is worse than no guard, because it looks like one.

## `_bind`, [line 179](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L179): Docstring

> Values the job is known to vary, as the names it varies under.
>
> A JSON body is where the rig's parameters actually land -- the two the rig
> derived from the SCREEN, `workArea` and `workAreaDescription`, are two keys
> of the POST that creates a work area -- so this substitutes by KEY and never
> by scanning the text. A blind string replacement would rewrite the same
> characters wherever else they appeared, and a work area named `SG` would
> have rewritten the site id sitting beside it in the same body.
>
> Everything not bound is escaped, because `Template` is `string.Template`:
> a literal `$` in a captured body would otherwise report itself as a
> parameter the plan needs and either raise on render or substitute something
> nobody typed. The placeholders are written through a sentinel so the escape
> pass cannot eat the very `$` this is trying to produce.

## module, [line 69](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L69): Comment

Code: `UNINSPECTABLE = "«whole body: could not be parsed to redact»"`

> What the rig writes in place of a body it could not parse well enough to
> redact. Declared here rather than imported, because `new_agent_arch` is a
> separate package this one may not reach into -- the same deliberate twinning
> as the OAuth companion list.

## `network_plan_for_gesture`, [line 134](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L134): Comment

Code: `at = _when(gesture.get("at")) or _epoch(gesture.get("at"))`

> The gesture's own clock, where it has a readable one. It is only ever a
> FALLBACK for a request that stored no usable time of its own, so a
> gesture with no clock costs nothing as long as its requests have theirs.
> Refusing the whole gesture on a missing `at` threw away every call it
> caused over a field none of them needed.

## `network_plan_for_gesture`, [line 139](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L139): Comment

Code: `continue`

> Neither clock is readable. `CapturedRequest` refuses a naive
> datetime and inventing one would order this call against the
> others by a time nobody observed.

## `network_plan_for_gesture`, [line 157](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L157): Comment

Code: `target_system=target_system or urlsplit(primary.url).hostname or "",`

> The host this call actually went to, not the workflow's. A
> credential reference is a vault key scoped per system, and the
> jobs this project exists to capture cross systems -- so one
> target_system for a whole workflow files half its calls under the
> wrong login. `target_system` remains as the caller's override for
> a host it wants named differently.

## `network_plan_for_gesture`, [line 160](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L160): Comment

Code: `body=Template(raw=_bind(body.text, bindings)) if body and body.text else None,`

> A body the rig kept out of line is not an absent body. `_body` returns
> None when there is no inline text, and passing that through made a
> large POST into an empty POST that still called itself replayable;
> `body_blob_uri` is the field that exists for this. All 39 real request
> bodies carry the key, so the shape is live even where the value is not.

## `network_plan_for_gesture`, [line 162](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L162): Comment

Code: `expected_status=primary.status if primary.succeeded else None,`

> Only a status the call actually succeeded with. `primary_of`'s last
> rung is "the first call at all", so a gesture whose every call FAILED
> still yields a plan -- and recording its 4xx as the expected status
> makes a run correct when the warehouse rejects the write and failed
> when it lands. There is one in the real store: a PUT to
> /data/WM/wm/addresses that came back 422. No expectation is a plan
> that proves nothing; a wrong one is a plan that proves the opposite.

## `_bind`, [line 189](../../../../../../../backend/src/sro/application/skill/network_from_rig.py#L189): Comment

Code: `sentinel = "@@SRO-PARAM-{}@@"`

> A printable token, because `json.dumps` escapes a control character --
> `\x00` came back as the six characters `\u0000` and the swap below found
> nothing, leaving the sentinel in the body. Checked against the text
> first: a body that already contains it is left alone rather than
> corrupted, which costs a binding and never a payload.
