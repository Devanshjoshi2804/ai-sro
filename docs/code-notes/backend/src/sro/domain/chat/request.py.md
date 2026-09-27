# Notes for `backend/src/sro/domain/chat/request.py`

R1's request reading, checked in code (spec §4.1; GC 10). The model says which job and which values; nothing it says is taken until it passes here.

## `Candidate`, [line 17](../../../../../../../backend/src/sro/domain/chat/request.py#L17): Design

> One job as the reader is shown it: its field classes (C2), the operator's
> aliases, the values seen, the mails that asked for it, and the tenant's
> sign-in names. `parameters` are the fields the job fills (kind not
> `never`); `required` only the page-demanded ones, so an optional field is
> never missing and never asked for (amendment 2, item 3; thr_c563).

## `field_of`, [line 47](../../../../../../../backend/src/sro/domain/chat/request.py#L47): Design

> Which field a wording means: an alias wins (the operator's own word, R2),
> then a parameter's name or label, then an on-screen label the job never
> filled. The bool says whether the job fills it.

## `_names`, [line 58](../../../../../../../backend/src/sro/domain/chat/request.py#L58): Design

> The fields a quote names, as whole words. A value binds only to a field its
> quote supports (amendment 2, item 2): a quote that names another field and
> not this one ("customer type :- RRF" offered as the description) is a
> misfiled value, refused and asked for. A quote that names no field (the
> answer "use GT7") supports any.

## `_placed`, [line 75](../../../../../../../backend/src/sro/domain/chat/request.py#L75): Design

> Each value on its own (invariant 14). The quote must be in the thread and
> the value in the quote; one that is not makes the whole reading unsure --
> a model that invents one value may have invented the job -- and is dropped.
> A value equal to a sign-in name (`Candidate.logins`, thr_163b's
> RKUCHIYAGM) is never a job value: refused on a parameter, and not carried
> aside into the run either. A value that breaks its field's limits (C2's
> `FieldLimits.refuses`, knowledge-base limits included) is refused, never
> cut. Refused names are missing, so they are asked. A value for a field the
> job never fills goes aside under its label, and one the reader could not
> place under the request's own wording, where X10's compose and R2 take it.

## `read_of`, [line 110](../../../../../../../backend/src/sro/domain/chat/request.py#L110): Design

> Only a candidate is a job. `also` and `items` stay because callers read
> them (converse's which-job question, several things per request). Items
> with no valid value are dropped from `items` but still count for missing,
> so one thing that lacks a value is asked for. The `also` settling rule is
> the one `understand` had: when the chosen job is the only one the checked
> values fill, the reading is sure after all -- the real "customer type :-
> RRF and description :- ..." mail that was asked "which job?" against Reply
> to Email.
