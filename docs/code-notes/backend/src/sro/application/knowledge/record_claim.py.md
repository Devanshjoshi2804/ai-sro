# Notes for `backend/src/sro/application/knowledge/record_claim.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/record_claim.py`](../../../../../../../backend/src/sro/application/knowledge/record_claim.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/record_claim.py#L1): Docstring

> Believe something about a system, or record that something was claimed.
>
> One way in for every source -- the scraped catalogue, a verified run, an
> operator's correction -- so the supersession rule cannot be bypassed by whoever
> writes next.

## `_vectors`, [line 98](../../../../../../../backend/src/sro/application/knowledge/record_claim.py#L98): Docstring

> No vectors is a worse ordering, never a failed ingest.

## `Claim.as_text`, [line 24](../../../../../../../backend/src/sro/application/knowledge/record_claim.py#L24): Docstring

> What a request is matched against. Title and key carry the system's
> own vocabulary, which is the vocabulary an operator will use.

## `RecordClaims.execute`, [line 67](../../../../../../../backend/src/sro/application/knowledge/record_claim.py#L67): Comment

Code: `vectors = await _vectors(self._embedder, tuple(claim for claim, _, _ in decided))`

> One embedding call for the batch: ingesting a catalogue is
> thousands of claims, and a request each would be the slowest part
> of the job by two orders of magnitude.

## `RecordClaims.execute`, [line 84](../../../../../../../backend/src/sro/application/knowledge/record_claim.py#L84): Comment

Code: `not_believed += 1`

> Kept, and pointed straight at what outranks it: a scrape
> disagreeing with a verified run is a fact worth having and
> is not what the system believes.
