# Notes for `backend/src/sro/domain/knowledge/supersede.py`

Comments and docstrings moved out of [`backend/src/sro/domain/knowledge/supersede.py`](../../../../../../../backend/src/sro/domain/knowledge/supersede.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/knowledge/supersede.py#L1): Docstring

> What happens when the same thing is claimed twice.
>
> The learning loop lives here. A scraped catalogue says an endpoint exists; a run
> later proves what it answers. Both are claims about one key, and deciding
> between them by timestamp would let a re-scrape undo everything execution has
> learned. Evidence decides, and time only breaks ties.

## `Verdict`, [line 9](../../../../../../../backend/src/sro/domain/knowledge/supersede.py#L9): Note on the line above

Code: `UNCHANGED = "unchanged"`

> The same claim, from the same source, saying the same thing. Ingest is
> re-runnable precisely because this exists.

## `Verdict`, [line 11](../../../../../../../backend/src/sro/domain/knowledge/supersede.py#L11): Note on the line above

Code: `SUPERSEDES = "supersedes"`

> The new claim replaces the old one, which stays, pointing forward.

## `Verdict`, [line 13](../../../../../../../backend/src/sro/domain/knowledge/supersede.py#L13): Note on the line above

Code: `RECORDED_NOT_BELIEVED = "recorded_not_believed"`

> Weaker evidence contradicting stronger. Kept -- a scrape disagreeing
> with a verified run is a fact about the scrape worth having -- but it does
> not become what the system believes.

## `judge`, [line 16](../../../../../../../backend/src/sro/domain/knowledge/supersede.py#L16): Docstring

> What to do with a claim, given what is already believed about its key.
>
> Takes the incoming claim's three deciding fields rather than a whole entry:
> the caller has not minted one yet, and building a throwaway entity to ask a
> question is how identity fields end up carrying placeholder values.
