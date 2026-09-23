# Notes for `backend/src/sro/domain/skill/reversals.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/reversals.py`](../../../../../../../backend/src/sro/domain/skill/reversals.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/reversals.py#L1): Docstring

> Taking back what a run made, where the evidence shows how.
>
> A rig run creates records in a warehouse and nothing could take one back. The
> guards in front of it -- a door that says when it is unsure, a list that proves
> the first thing before doing the rest -- stop wrong records being MADE; none of
> them helps with one that was.
>
> **An undo is a job somebody has done, not a call this system invents.** The rig
> knows what an operator was seen doing and nothing else. Where a tenant's
> evidence shows somebody deleting the kind of record a job creates, that deleting
> is itself a mined job and can be run; where it does not, there is no undo and
> the honest thing is to say so and name what was made, so a person can go and do
> it themselves.
>
> Measured on this tenant's whole store the day this was written: three PUTs to
> one address endpoint and **not one DELETE anywhere**. So this finds nothing
> today, on purpose -- it is the mechanism, and it lights up the first time
> somebody deletes a warehouse equipment type in front of the recorder.

## module, [line 11](../../../../../../../backend/src/sro/domain/skill/reversals.py#L11): Note on the line above

Code: `K_CREATED = 201`

> What a record being made looks like, and `repeats` says why it is 201 and
> not "any mutation".

## module, [line 13](../../../../../../../backend/src/sro/domain/skill/reversals.py#L13): Note on the line above

Code: `REMOVES = frozenset({"DELETE"})`

> What taking a record back looks like on the wire.
>
> `DELETE` alone. A PUT that sets a flag to inactive is how several warehouses
> retire a record, and it is also how every other edit is made -- reading one as
> an undo would offer to "take back" a job by overwriting the record it made.
> The day a tenant's evidence shows a disable being demonstrated as its own job,
> that job is the undo and this is where it is recognised.

## `identifies`, [line 16](../../../../../../../backend/src/sro/domain/skill/reversals.py#L16): Docstring

> Which fields of a record the undo's own delete addresses it by.
>
> **Read off the delete, never guessed from a name.** A DELETE addresses one
> member of a collection -- `DELETE /wm/customerTypes/GDD` -- and on this
> platform it carries the record it is removing as its BODY. So the fields
> that could identify are the ones whose value is the segment in the path,
> and no part of that is `customerType` being the singular of
> `customerTypes`, which is the correspondence `write_plan` refuses at
> length.
>
> A SET, because the real answer is not one field. Measured on the
> deployment 2026-09-19, the delete of `GDD` carries it twice -- as
> `customerType` and as `resourceId` -- and either would address the record.
> What settles it is the other side: `addresses` keeps whichever of these the
> CREATE recorded making, and a run's `made` holds `customerType` and no
> `resourceId`.
>
> Empty where the delete carried nothing, which is every platform that
> answers a delete with an empty request, and then nothing has changed: one
> record named one way, or no button.

## `asks_for`, [line 34](../../../../../../../backend/src/sro/domain/skill/reversals.py#L34): Docstring

> What the undo calls the value it needs, in its own vocabulary.
>
> The press has to speak the JOB's language, not the warehouse's. `Delete a
> Customer Type` declares one parameter and it is called `Customer Type` --
> the screen's label, which is how every mined job names what varies -- while
> the record it deletes is keyed `customerType` in the body. A press that
> sent the body key would name a parameter this job does not have, and the
> run would refuse it as a value nobody supplied.
>
> One parameter or nothing. A delete that varies two things is a delete this
> cannot fill from one created record, and guessing which of them wants the
> id is the wrong kind of guess to make with a DELETE.

## `_record`, [line 43](../../../../../../../backend/src/sro/domain/skill/reversals.py#L43): Docstring

> A body's top-level string values, keyed. The envelope first, as
> everything that reads a Blue Yonder body does.

## `addresses`, [line 61](../../../../../../../backend/src/sro/domain/skill/reversals.py#L61): Docstring

> Which record an undo would address, out of what a run read back.
>
> The mapping `undo` has said it lacked since it was written: *what a press
> would have to do -- address each created record by whatever the warehouse
> called it -- is a mapping nothing here has evidence for, and a wrong
> mapping deletes the wrong record.* It has evidence for it now. A step that
> created something records what the warehouse called it, and `made_by` keeps
> the identifying fields and nothing else.
>
> **Exactly one record, named by exactly one field.** Everything else is a
> refusal, and each is the same refusal wearing a different hat:
>
> - A run that made two records would need two deletes, and an undo that
>   takes back half of what a run did is worse than none -- somebody presses
>   it, sees the card go quiet, and believes the warehouse is back where it
>   started.
> - A record named two ways is a record this cannot name at all. `made_by`
>   keeps `id`, `code`, `name`, `number` and `key`, and a warehouse that
>   answered with two of them has not said which one addresses it.
>
> A wrong guess here removes somebody else's record, which is the one thing
> an undo must never do.

## `undoes`, [line 79](../../../../../../../backend/src/sro/domain/skill/reversals.py#L79): Docstring

> Which job of this tenant's undoes what `made` creates, if any holds one.
>
> Matched on the endpoint and nothing else: a job that deletes the records
> another job creates is that job's undo, whatever either is called. Names
> are a model's, and an undo chosen by name is an undo chosen by a sentence
> somebody wrote about a job.
>
> The two endpoints are not the same string and must not be compared as one.
> A create addresses the collection -- `POST /wm/equipmentTypes` -- and a
> delete addresses one record in it -- `DELETE /wm/equipmentTypes/4471`,
> whose path is the collection's plus the id. A DELETE to the collection
> ITSELF is not an undo of one record: it is whatever that warehouse means by
> emptying it, and this would be a poor place to find that out.
>
> **One more segment, and never `path_shape`'s `*`.** That function blanks a
> segment carrying a DIGIT, which is right for `/equipmentTypes/4471` and
> silent for `/customerTypes/GDD` -- so the id survived the blanking, the
> delete's shape carried the record it happened to be demonstrated on, and it
> could never equal `collection/*`. Measured on this deployment 2026-09-19:
> the tenant has held `Create a Customer Type` and `Delete a Customer Type`
> for weeks, and this answered None every time.
>
> Comparing the SEGMENTS needs no rule about what an id looks like, which is
> the right amount to know: that a delete addresses one member of the
> collection a create posts to is structural, and what that member is called
> is the warehouse's business.

## `_pieces`, [line 98](../../../../../../../backend/src/sro/domain/skill/reversals.py#L98): Docstring

> A path shape in segments, with the empties dropped.

## `_endpoint`, [line 102](../../../../../../../backend/src/sro/domain/skill/reversals.py#L102): Docstring

> The path shape this job's own write goes to, or None.
>
> `recorded_call` rather than every call the evidence holds, for the reason
> it was narrowed in the first place: a page's own background traffic is not
> what the operator did, and a job identified by a telemetry beacon's
> endpoint would be every job on that host.

## `addresses`, [line 69](../../../../../../../backend/src/sro/domain/skill/reversals.py#L69): Comment

Code: `shared = [key for key in by if only.get(key, "").strip()]`

> The delete's own evidence named the fields it addresses a record by,
> so a record carrying more than one thing is no longer a record named
> two ways -- it is a record named once and described alongside.
>
> The intersection, and it has to be exactly one. On the deployment the
> delete addresses `GDD` as both `customerType` and `resourceId` and
> the create records only the first, so one side narrows the other.
> Two survivors would be two names for one record again, and this
> refuses that for the reason it always has.
