# Notes for `backend/src/sro/domain/execution/cascade.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/cascade.py`](../../../../../../../backend/src/sro/domain/execution/cascade.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/cascade.py#L1): Docstring

> One press, several writes, and the value that flows between them.
>
> **One logical create is often several physical resources.** Creating a client
> on the real platform fires four POSTs behind a single Save -- addresses,
> clients, clientWarehouse, packingConfigurations -- and the second carries an id
> the first returned. `knowledge-base/KNOWLEDGE-BASE.md` 3b records it, and the
> research capture holds the exchange: `POST /wm/clients` carries
> `addressId: A000365896`, which no operator typed and `POST /wm/addresses`
> answered with.
>
> That is composition. Item 7 has been waiting for a chain between two mined jobs
> and there is none -- 306 ordered pairs on the deployment, 0 -- but the same
> shape, a value moving out of one write's answer and into the next write's body,
> is what this platform does behind every cascade create. It is one press rather
> than two jobs, and everything about the binding is the same.
>
> **Nothing here is guessed.** A dependency is a value the SERVER made: in a
> mutation's answer, not in its own request, and not typed by anybody earlier --
> the same subtraction `uses_edges` makes between steps, made here between calls.
> A form posting back what the operator typed is their value coming round again,
> and an edit that PUTs a record it has just read carries the whole record back,
> which is exactly what this must not read as a dependency.
>
> **No instance in mined evidence yet, and that is the honest state.** Measured
> 2026-09-19 over three tenants' stores: four steps stand on a doing that wrote
> twice, and not one of those second writes carries anything the first answered
> with -- `Create a Supplier` PUTs an address that already existed. So this finds
> nothing today, on purpose, and lights up the first time somebody creates a
> client (or anything else with a cascade behind it) in front of the recorder.
>
> `plan_step` reads it to refuse a replay it cannot send whole; the report reads
> it to say what a press would really do.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/cascade.py#L12): Note on the line above

Code: `K_SHORTEST = 3`

> How long a value must be before it can carry a dependency. `0`, `-1` and
> `SG` are all over a warehouse body, and a flow drawn from one is a flow drawn
> from a coincidence.

## `Flow`, [line 16](../../../../../../../backend/src/sro/domain/execution/cascade.py#L16): Docstring

> One value, out of a write's answer and into the next write's body.

## `Flow`, [line 17](../../../../../../../backend/src/sro/domain/execution/cascade.py#L17): Note on the line above

Code: `key: str`

> What the answer called it -- `addressId`.

## `Flow`, [line 19](../../../../../../../backend/src/sro/domain/execution/cascade.py#L19): Note on the line above

Code: `into: str`

> What the later request calls it. Usually the same word, and never
> assumed to be: the flow is found by VALUE, and the two names are read off
> the two bodies.

## `Flow`, [line 21](../../../../../../../backend/src/sro/domain/execution/cascade.py#L21): Note on the line above

Code: `made_at: str`

> The write that answered with it, as `METHOD path`.

## `Flow`, [line 23](../../../../../../../backend/src/sro/domain/execution/cascade.py#L23): Note on the line above

Code: `used_at: str`

> The write that sent it on.

## `writes_of`, [line 26](../../../../../../../backend/src/sro/domain/execution/cascade.py#L26): Docstring

> The calls of this doing that really write, in the order they went out.
>
> Only what the LEDGER recognises where one is given. A page fires
> keepalives, telemetry and performance beacons from the very click that
> creates a record -- `sessionKeepAlive` and `webPerformanceEntries/batch`
> are both in this store's evidence -- and counting those makes every real
> write look like a cascade.

## `flows_in`, [line 35](../../../../../../../backend/src/sro/domain/execution/cascade.py#L35): Docstring

> Every value this doing's own writes minted and its own later writes sent.
>
> `typed` is when each value was first typed or sent anywhere, which is what
> keeps an operator's own value from reading as the warehouse's. Optional,
> because a caller with one gesture in hand has nothing to compare against;
> then the subtraction is only against the minting call's own request, which
> is the narrower half of the same rule.

## `_values`, [line 56](../../../../../../../backend/src/sro/domain/execution/cascade.py#L56): Docstring

> A body's leaf strings, keyed, with the envelope read through.
>
> Blue Yonder answers a create with `{"@type": "ResponseBodyWrapper", "data":
> {…}}` -- 112 of the 114 successful writes in the research capture -- so a
> reader that stopped at the top level would find `@type` and nothing else.
