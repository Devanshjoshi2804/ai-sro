# Notes for `backend/src/sro/application/observation/admit.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/admit.py`](../../../../../../../backend/src/sro/application/observation/admit.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/admit.py#L1): Docstring

> Which of an upload's events may be kept, and why the rest were not.
>
> Screening, not parsing. The evidence plane keeps what arrived verbatim, so this
> answers one question per event -- is this a thing we agreed to record, in a
> shape the domain can read later -- and says why when the answer is no. Turning
> an event into an ``InputAction`` happens when something needs one.
>
> A rejection is a bug in the extension, reported back on the same response so it
> is found on the day it is introduced rather than in a mining run three weeks
> later that quietly saw fewer tasks than happened.

## module, [line 15](../../../../../../../backend/src/sro/application/observation/admit.py#L15): Note on the line above

Code: `_SIGNALS = ("role", "name", "text", "testId", "cssPath", "xpath")`

> What an element fingerprint may be found by. ``ElementFingerprint`` refuses
> one carrying none of these, so an event with such a target is evidence that
> cannot be replayed, aligned or matched. Kept out here rather than discovered by
> a miner months later.

## `admit`, [line 28](../../../../../../../backend/src/sro/application/observation/admit.py#L28): Docstring

> What may be kept out of one upload, and why the rest was not.
>
> ``ours`` is this deployment itself -- its API and its console -- as
> ``(host:port, path prefix)`` pairs from ``Settings.our_own_origins``. They
> are refused ahead of everything else and no grant widens them, which is the
> difference between this and ``exclude_hosts``.
>
> That distinction is not theoretical. The operator had the console open in a
> tab while demonstrating, so the extension captured both halves: the console
> page itself (7 gestures in the real store) and the console talking to the
> API -- twelve requests, of which one is the POST to
> `/v1/recordings/<id>/finish` that a mined workflow then reported as the
> write its job performs.
> Configuration could have excluded it and did not, because a default nobody
> sets is a default nobody has -- and worse, ``exclude_hosts`` is exactly what
> an operator's grant is allowed to widen, so pressing "observe this page" on
> the console would switch it back on. Watching the apparatus record is never
> what anybody meant by watching the work.

## `_is_ours`, [line 117](../../../../../../../backend/src/sro/application/observation/admit.py#L117): Docstring

> Whether this url is this system talking to itself.
>
> Host and port, unlike every other rule here: a deployment whose API and
> console are one machine on two ports is the ordinary shape, and matching
> the hostname alone would refuse the warehouse test server beside them.
> Built from ``hostname`` rather than ``netloc`` because netloc carries
> userinfo and keeps a trailing dot, and both slipped past a netloc compare.
>
> The path prefix is the other half: a deployment path-routing this system
> and the WMS on one hostname is ordinary too, and refusing the whole host
> would make every warehouse page on it unrecordable with no grant able to
> restore it.

## `_url_refusal`, [line 113](../../../../../../../backend/src/sro/application/observation/admit.py#L113): Comment

Code: `return "this page is outside what the tenant agreed to observe"`

> Never the URL itself: this refusal is logged and read, and the point
> of an exclusion is that the excluded page leaves no trace here.

## `_why_not`, [line 45](../../../../../../../backend/src/sro/application/observation/admit.py#L45): Note on the effect rule

> An `effect` needs `of` and a numeric `of_at` (without them it cannot be
> joined to its gesture), an `effect` object, and a URL the policy allows.
