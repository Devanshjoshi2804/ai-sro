# Notes for `backend/src/sro/domain/chat/request.py`

R1's request reading, checked in code (spec §4.1; GC 10). The model says which job and which values; nothing it says is taken until it passes here.

## `Candidate`, [line 18](../../../../../../../backend/src/sro/domain/chat/request.py#L18): Design

> One job as the reader is shown it: its field classes (C2), the operator's
> aliases, the values seen, the mails that asked for it, and the tenant's
> sign-in names. `parameters` are the fields the job fills (kind not
> `never`); `required` only the page-demanded ones, so an optional field is
> never missing and never asked for (amendment 2, item 3; thr_c563).

## `field_of`, [line 49](../../../../../../../backend/src/sro/domain/chat/request.py#L49): Design

> Which field a wording means: an alias wins (the operator's own word, R2),
> then a parameter's name or label, then an on-screen label the job never
> filled. The bool says whether the job fills it.

## `_names`, [line 79](../../../../../../../backend/src/sro/domain/chat/request.py#L79): Design

> The fields a quote names, as whole words. A value binds only to a field its
> quote supports (amendment 2, item 2): a quote that names another field and
> not this one ("customer type :- RRF" offered as the description) is a
> misfiled value, refused and asked for. A quote that names no field (the
> answer "use GT7") supports any.

## `_placed`, [line 110](../../../../../../../backend/src/sro/domain/chat/request.py#L110): Design

> Each value on its own (invariant 14). The quote must be in the thread and
> the value in the quote; one that is not makes the whole reading unsure --
> a model that invents one value may have invented the job -- and is dropped.
> The value must be in its quote whole and in the same case (`_rest`; R1
> review, I2): "RR" out of "RRF", or "rrf" where the mail said "RRF", is a
> truncation or a rewrite, never the value (amendment 1, GC 10). What the
> quote names is looked for with the value's own span removed (I6), so a
> description "returns customer type" is not refused for naming Customer
> Type. A login (`_signing`) is refused on a parameter and not carried aside
> into the run either. A value that breaks its field's limits (C2's
> `FieldLimits.refuses`, knowledge-base limits included) is refused, never
> cut. A refused required field is missing, so it is asked; a refused
> optional one is reported in `refused` and dropped, never asked for (I4;
> thr_c563's Manufacturer). A value for a field the
> job never fills goes aside under its label, and one the reader could not
> place under the request's own wording, where X10's compose and R2 take it.

## `read_of`, [line 143](../../../../../../../backend/src/sro/domain/chat/request.py#L143): Design

> Only a candidate is a job. `missing` is the required fields some thing
> lacks, nothing else. `also` and `items` stay because callers read
> them (converse's which-job question, several things per request). Items
> with no valid value are dropped from `items` but still count for missing,
> so one thing that lacks a value is asked for. The `also` settling rule is
> the one `understand` had: when the chosen job is the only one the checked
> values fill, the reading is sure after all -- the real "customer type :-
> RRF and description :- ..." mail that was asked "which job?" against Reply
> to Email.

## `_rest`, [line 65](../../../../../../../backend/src/sro/domain/chat/request.py#L65): Design

> The quote with the value's own span taken out, or None when the value is
> not in it whole: bounded by non-word characters, case kept, whitespace
> runs read as one space.

## `_signing`, [line 83](../../../../../../../backend/src/sro/domain/chat/request.py#L83): Design

> A login is the tenant's recorded sign-in name (thr_163b's RKUCHIYAGM), or
> a value the thread states right after the name of a box a sign-in was
> typed in ("username QATEST01", "user: X") -- only a box of a sign-in that
> lands on one of the job's own systems (`Candidate.systems`). The label
> merely appearing near the value is no signal (R1 re-review 1, item 3): a
> generic box name such as "User" refused "12 Main St" out of "user asked
> for address 12 Main St". A job's own field of that name wins (`own`): a
> Create-a-User job's Username is the new user's.

## `refusal`, [line 95](../../../../../../../backend/src/sro/domain/chat/request.py#L95): Design

> The one check every binder calls (R1 review, I5): the value must be in
> what was said, must not be a recorded login, and must pass the field's
> limits. The box-name signal needs the thread and the job's systems, so
> `_placed` applies it itself; a chat answer is the bare value, which states
> no box name.
> `_placed` calls it for the reader, and `asking.answered` for a chat answer
> to a pending question, where the value is the whole reply.

## `_fills`, [line 139](../../../../../../../backend/src/sro/domain/chat/request.py#L139): Design

> Whether the stated values settle a job: at least one value is named, the
> job takes every named field, and they hold all its required ones (R1
> review, I3). A job with no fields is filled by nothing, so a 0-parameter
> Navigate or Log Out in `also` never competes with the job the values
> settle, and a reading with no value settles nothing.
