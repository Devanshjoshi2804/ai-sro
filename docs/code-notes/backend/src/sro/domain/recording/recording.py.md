# Notes for `backend/src/sro/domain/recording/recording.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/recording.py`](../../../../../../../backend/src/sro/domain/recording/recording.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/recording.py#L1): Docstring

> Recording aggregate. See docs/06-glossary.md#recording.

## `Recording`, [line 29](../../../../../../../backend/src/sro/domain/recording/recording.py#L29): Docstring

> One demonstration. Mutable while capturing, immutable once sealed.
>
> Skill provenance cites recordings, so a sealed recording must never change --
> every state transition goes through a method, never a direct assignment.

## `Recording`, [line 35](../../../../../../../backend/src/sro/domain/recording/recording.py#L35): Note on the line above

Code: `objective_key: ObjectiveKey | None = None`

> What the demonstration was about. Unknown until it is over: the operator
> starts one by naming a URL, and the evidence names the task at seal.

## `Recording`, [line 38](../../../../../../../backend/src/sro/domain/recording/recording.py#L38): Note on the line above

Code: `device_id: DeviceId | None = None`

> Set when the demonstration happened in the operator's own browser rather
> than one this deployment opened.
>
> The two are exclusive in practice and the difference decides everything
> about how the recording is filled: a server-side one is driven through CDP
> while it happens, and this one arrives afterwards as teaching-mode
> observation batches. It is also the answer to why a recording has no
> browser session, which otherwise reads as a bug.

## `Recording.artifact`, [line 72](../../../../../../../backend/src/sro/domain/recording/recording.py#L72): Docstring

> Most recent artifact of a kind. Re-uploads supersede rather than fail.

## `Recording.append_frame`, [line 82](../../../../../../../backend/src/sro/domain/recording/recording.py#L82): Docstring

> Append with an aggregate-assigned index.
>
> The caller's index is overwritten: the two-run diff aligns positionally,
> so a gap from a retrying capture adapter would mis-pair steps silently.

## `Recording.absorb_late_evidence`, [line 100](../../../../../../../backend/src/sro/domain/recording/recording.py#L100): Docstring

> Attach evidence belonging to the most recent action.
>
> Returns whether there was a frame to attach it to. Nothing to attach to
> means the traffic really is page-load noise from before the first
> action, which the caller counts rather than keeps.

## `Recording.attach_narration`, [line 111](../../../../../../../backend/src/sro/domain/recording/recording.py#L111): Docstring

> Replace what was heard. A re-transcription supersedes, never appends.
>
> Kept in time order because everything downstream lines it up against
> frames, and a transcriber is free to return segments out of order.

## `Recording.name_objective`, [line 115](../../../../../../../backend/src/sro/domain/recording/recording.py#L115): Docstring

> Say what this was. Once only -- provenance cites the key as taught.
