# Notes for `backend/src/sro/domain/knowledge/entry.py`

Comments and docstrings moved out of [`backend/src/sro/domain/knowledge/entry.py`](../../../../../../../backend/src/sro/domain/knowledge/entry.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L1): Docstring

> What is known about a system, and how well it is known.
>
> Every entry is a claim with the evidence behind it named. That is the rule the
> knowledge base was rebuilt under after an audit found endpoints marked
> "verified" whose only proof was a 404 on a route that never existed -- see
> knowledge-base/SCHEMA.md.
>
> Nothing here is ever overwritten. A verified run that contradicts a scraped
> claim supersedes it and both rows stay, because "we used to believe this" is the
> only way to explain an incident afterwards.

## module, [line 35](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L35): Note on the line above

Code: `SUPPORTS_AUTOMATION = EvidenceLevel.REPRODUCED`

> Below this, a claim may inform a human and may not drive a call.

## `EvidenceLevel`, [line 12](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L12): Note on the line above

Code: `ASSERTED = "asserted"`

> Written down by a human or a model. Not evidence.

## `EvidenceLevel`, [line 14](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L14): Note on the line above

Code: `OBSERVED = "observed"`

> Seen once, and the exchange was stored.

## `EvidenceLevel`, [line 16](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L16): Note on the line above

Code: `REPRODUCED = "reproduced"`

> Re-run deliberately and matched what was stored before.

## `EvidenceLevel`, [line 18](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L18): Note on the line above

Code: `ROUND_TRIP = "round_trip"`

> Created, read back, changed and removed, all recorded.

## `EntryKind`, [line 46](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L46): Note on the line above

Code: `QUESTION = "question"`

> Something the system could not decide and will not guess at.
>
> Kept with what is known about the system on purpose: an open question is a
> fact about this deployment -- the place where the next confident answer
> would be a guess -- and it is answered once, by somebody who works here.

## `KnowledgeEntry`, [line 54](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L54): Docstring

> One claim about one system.
>
> ``key`` is the claim's identity within its kind -- an endpoint's method and
> path, a screen's route, a field's payload name. Two entries with the same
> key are the same claim believed twice, which is what supersession is for.

## `KnowledgeEntry`, [line 62](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L62): Note on the line above

Code: `source: str`

> Where this came from: a knowledge-base file, or the run that proved it.

## `KnowledgeEntry.superseded`, [line 79](../../../../../../../backend/src/sro/domain/knowledge/entry.py#L79): Docstring

> Point forward at what replaced this. The old row stays.
