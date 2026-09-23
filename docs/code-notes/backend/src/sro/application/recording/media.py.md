# Notes for `backend/src/sro/application/recording/media.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/media.py`](../../../../../../../backend/src/sro/application/recording/media.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/media.py#L1): Docstring

> Playback links for a recording's media.
>
> URLs are minted per request and expire. A recording holds live customer traffic,
> so a link that outlives the page it was rendered on is a copy of the evidence
> nobody is tracking.
