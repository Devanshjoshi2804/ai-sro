# Notes for `backend/src/sro/infrastructure/db/mappers.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/mappers.py`](../../../../../../../backend/src/sro/infrastructure/db/mappers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L1): Docstring

> Rows to aggregates and back.
>
> Kept apart from the repositories so the shape of persistence is readable in one
> place, and apart from the domain so the domain never learns it is stored.

## `row_to_recording`, [line 167](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L167): Comment

Code: `recording._frames.extend(load_frames(row.frames))`

> Frames and artifacts are replayed through the private lists rather than
> ``append_frame``: a sealed recording rejects appends, and rehydration is
> not a state transition.

## `update_skill_row`, [line 186](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L186): Comment

Code: `row.latest_version = skill.versions[-1].version if skill.versions else 0`

> Denormalised so listing skills does not mean parsing every version.

## `row_to_run`, [line 290](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L290): Comment

Code: `may_change_the_system=False,`

> A stored run was validated when it was created; rehydration must not
> re-litigate that. A read-only assisted run has no authoriser by
> design, and re-checking would make it unreadable ever afterwards.

## `update_device_row`, [line 486](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L486): Comment

Code: `row.grants = dump_grants(device.grants)`

> Deliberately not written back from the record: revocation is a column the
> repository sets under its own condition, and a device loaded before it was
> revoked and saved after would otherwise undo the revocation with a
> heartbeat. `revoked_at` leaves the store on read and never returns.

## `update_trigger_row`, [line 570](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L570): Comment

Code: `row.from_message = [] if trigger.watch else list(trigger.from_message)`

> A watch derives its `from_message` from the places it reads, so storing
> that list too would be the same names written down twice -- and two
> lists of the same names are two lists that can disagree.

## `update_candidate_row`, [line 640](../../../../../../../backend/src/sro/infrastructure/db/mappers.py#L640): Comment

Code: `row.times_seen = candidate.times_seen`

> Lifted out of the document so "offer me what happened most often" is an
> index rather than a scan of every candidate's episodes.
