# Notes for `backend/src/sro/infrastructure/knowledge/catalogue.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/knowledge/catalogue.py`](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L1): Docstring

> The recorded knowledge base on disk, read as claims.
>
> `knowledge-base/blue-yonder-sce/` was produced by driving the real application
> and storing every exchange. This turns it into entries the system can retrieve,
> carrying each record's own evidence level rather than flattening everything to
> "we know this" -- the flattening is exactly what its own audit caught.
>
> Reading only. Nothing here writes to the knowledge base directory: it is
> evidence, and evidence that a program edits is no longer evidence.

## `read_catalogue`, [line 23](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L23): Docstring

> Every claim the recorded base makes, in one pass.

## `_screens`, [line 43](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L43): Docstring

> A screen: its route, what it reads, and what it lets an operator do.

## `_fields`, [line 104](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L104): Docstring

> A payload key and what the vendor's help says it means.
>
> Always `asserted`: this is documentation joined to a key, not a request
> anybody watched. It is the vocabulary layer -- what `abcCountFlag` is called
> on screen -- which is what makes an operator's sentence resolvable.

## `_forms`, [line 131](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L131): Docstring

> The fields a create form actually posts, captured from the real form.

## `_flows`, [line 156](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L156): Docstring

> A recorded call cascade: what a create or update actually sends, in order.
>
> Deliberately compact. The full exchange -- headers, real payloads, real
> responses -- is what `seed_skills` reads to induce a runnable skill from;
> a claim only needs enough to answer "what does this send and in what
> order", with a pointer at the file for whoever needs the rest.
>
> Only the full-cascade shape (``calls`` of real request/response pairs) is
> read here. Two other shapes also live under this directory -- ``phases``
> of one-line ``METHOD path -> status`` strings, and a flat read-only-
> dashboard shape with a top-level method/url and no nested request or
> response at all -- and neither has anything this claim could replay or
> cite precisely. Both are skipped rather than half-represented: a call
> missing the nested shape used to leave method/status silently null
> instead of raising anything, so a flow with real writes was cited here
> as having none.

## `_statuses`, [line 195](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L195): Docstring

> What a resource answered for each case of the probe battery.
>
> This is the verifier's raw material, and the reason the base distinguishes
> two 404s: `ROUTE-MISSING` means the endpoint never existed, `RECORD-MISSING`
> means it exists and the record is gone. Only the second proves a delete.

## `_quirks`, [line 223](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L223): Docstring

> Claims the base makes about behaviour, including the falsified ones.
>
> A falsified claim is kept with its verdict. "We believed this and it was
> wrong" is the single most useful thing in the base, and deleting it is how
> the same wrong belief gets rediscovered next quarter.

## `_screens`, [line 69](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L69): Comment

Code: `evidence=(`

> A screen nobody could open is a claim, not an observation.

## `_endpoints`, [line 96](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L96): Comment

Code: `evidence=(`

> `hits` counts times the endpoint was actually seen on the wire.
> Zero means it was catalogued from a screen's configuration and
> nobody has watched it answer.

## `_flows`, [line 162](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L162): Comment

Code: `spec = document.get("spec") or path.stem`

> `resource` alone collides -- a duplicate-name rejection flow and the
> ordinary create both name `clients`. `spec` is the file's own scenario
> name and is unique by construction: it is where the filename came from.

## `_statuses`, [line 215](../../../../../../../backend/src/sro/infrastructure/knowledge/catalogue.py#L215): Comment

Code: `evidence=(`

> The battery was re-run: a case seen more than once matched
> what was stored the first time, which is what reproduced means.
