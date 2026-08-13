# Capture completeness

**Principle: nothing observable is discarded.**

A demonstration happens once. Whatever was not captured is gone, and the only
recovery is asking an operator to do it again. Storage is cheap; a second
demonstration is not, and a third is a credibility problem.

So the capture harness records everything the browser can tell us, and
normalisation is **additive** — the raw stream is kept verbatim alongside the
derived view, so improved parsing can be re-run against old recordings without
re-recording.

## What is captured

### Network — complete

| | |
|---|---|
| Request | method, full URL, all headers, cookies sent, body (any size, any encoding), POST data entries for multipart |
| Response | status, status text, all headers, cookies set, body, MIME type, `fromDiskCache` / `fromServiceWorker` |
| Transport | protocol (`h2`, `http/1.1`), remote address, security details, resource type |
| Timing | full `ResourceTiming` — DNS, connect, TLS, send, wait, receive |
| Causality | **initiator**: parser, script (with the JS stack), preload, or another request |
| Chain | every redirect hop, not just the final URL |
| Failure | `Network.loadingFailed` with the error text, blocked reason, CORS status |

Bodies over the inline threshold go to object storage and the row keeps the URI.
They are never truncated away.

### Accessibility — a graph, not a list

The full AX tree with node identity and parent/child edges preserved, at every
action. Roles, computed accessible names, descriptions, values, states
(`disabled`, `checked`, `expanded`, `selected`, `focused`), bounds, and the
backing DOM attributes.

A flat list answers "was this label present". A graph answers "what is this
control *inside*", which is what disambiguates the third **Save** button on a
page and what a heal step needs to score candidates.

### Browser state

Cookies (all attributes: domain, path, `Secure`, `HttpOnly`, `SameSite`,
expiry), `localStorage`, `sessionStorage`, and the origin they belong to —
snapshotted at each action so state changes are attributable to the action that
caused them.

### Page and console

Navigations, loads, dialogs, downloads, frame attach/detach, plus every console
message with its stack. A WMS that logs a validation failure to the console is
telling us why a branch was taken; that is exactly the "what happened and why"
signal.

### Human channel

Input events with full element fingerprints, the screencast, and optional
narration audio with transcript.

### Raw

The unabridged CDP event stream, stored as an artifact. This is the guarantee
behind "nothing is scrapped": if the normaliser has a bug or gets smarter, frames
are re-derived from the raw stream rather than re-recorded.

## What is *derived* from it

Capture is total; derivation is where judgement enters. Each derived artifact is
recomputable from the raw stream.

| Derived | From |
|---|---|
| Action frames | input + network + AX + state, grouped by causality |
| Action flow graph | frames + navigations + branch conditions |
| Skill (two plans per step) | two aligned recordings, diffed |
| **API catalogue** | every distinct endpoint observed, with header sets, auth scheme, inferred request/response schema, observed latency and status distribution |

The API catalogue is the point worth stating plainly: **the demo pipeline is an
API discovery pipeline**. Every recording documents a system whose API was never
documented. Built explicitly for that, not as a side effect.

## The three planes

Total capture is safe only because propagation is deliberate.

| Plane | Contents | Rule |
|---|---|---|
| **Evidence** — capture store | Everything above, verbatim | Encrypted at rest, tenant-scoped, access-audited, retention policy per tenant |
| **Skill** — workflow repository | The full header *set* and its shape. Secret **values** by reference into the credential vault. | Skills are versioned, shared across facilities and exportable. A bearer token embedded here becomes a durable, replicated credential. |
| **Telemetry** — logs, traces, metrics | Never a body, never a secret value. Names, shapes, sizes, hashes only. | Telemetry fans out to third-party backends with different retention and access control. Non-negotiable regardless of customer agreement. |

Credentials are captured, stored and **used**. `NetworkPlan` records that a
request carried `Authorization: Bearer <…>` and points at the vault entry; the
executor resolves it at run time and sends the real value. Nothing is lost, and
nothing sensitive is copied into an artifact designed to travel.

Classification is in `domain/recording/sensitivity.py` — it labels, it never
deletes.

## Why this is not "log everything"

Storing a payload in a tenant-scoped, encrypted, access-audited store is a
product feature. Printing the same payload to stdout puts it in a log aggregator,
a third-party APM, a support ticket screenshot and a laptop scrollback.

Same bytes, entirely different blast radius.
