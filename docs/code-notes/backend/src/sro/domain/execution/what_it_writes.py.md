# Notes for `backend/src/sro/domain/execution/what_it_writes.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/what_it_writes.py`](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L1): Docstring

> What a job would write, said before anybody presses it.
>
> Item 6 closed the half that was silent about VALUES -- a request naming a field
> the job has no parameter for is now said out loud on the card. What the card
> still could not say is the write itself: *this will create a Customer Type
> record on the SG site*. It names the values it holds; it does not name the act.
>
> The difference does not bite on a deployment whose one job has one write. It
> bites on the second job, and on any job with two writes in it, where "yes" is a
> press against something nobody described -- and the moment to fix that is
> before the second job arrives rather than after.
>
> **Read off the evidence, like everything else here.** Every write the step's
> own doing made, said in words. Nothing is guessed: a step with no recorded
> mutation contributes nothing, and a job whose evidence has aged out says
> nothing at all rather than something reassuring.
>
> **Every write of the doing and not only the one a replay would send.** One
> logical create is often several physical resources -- `new`'s `Create a
> Supplier` PUTs an address and then POSTs the supplier from one Save -- and a
> card built on `recorded_call` named the address and never the supplier. The
> same measurement that found `plan_step` replaying one call of a cascade found
> this describing one call of it.
>
> **Which of a page's calls is a write anybody cares about.** A create, or a
> call whose answer NAMES the record it touched. Measured over both real
> tenants' evidence, 2026-09-19: that rule keeps every warehouse write in the
> store -- `customerTypes`, `equipmentTypes`, `workAreas`, `activityCodes`,
> `carrierCrossReferences`, `workOperations` (201 with an answer that names
> nothing), the supplier's address PUT -- and drops all 100-odd of Gmail's own
> POSTs, the `sessionKeepAlive`s and the `webPerformanceEntries/batch`es, none
> of which is either. Before it the card offered to "create a bv record on
> mail.google.com".
>
> **What a method means is a convention, and the only one taken.** POST creates,
> PUT and PATCH change, DELETE removes. That is the whole of the interpretation,
> and it is the same convention `reversals.REMOVES` already rests on.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L13): Note on the line above

Code: `DOES = {"POST": "create", "PUT": "change", "PATCH": "change", "DELETE": "remove"}`

> What each method does, in the word a person would use.
>
> A method this does not know is left as itself -- upper case, as the wire had
> it. Inventing a verb for one is how `PROPFIND` becomes "create".

## `what_it_writes`, [line 16](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L16): Docstring

> Every write this job would make, in step order. Empty where it makes none.
>
> One entry per writing CALL and not per step: a job that posts twice behind
> one Save makes two records, and a card that said it once would be
> describing half of what the press does.
>
> Per DOING, never across the step's cites: a step cites one gesture per
> demonstration, so reading every cited call would say a job demonstrated
> three times writes three records.

## `_made_something`, [line 40](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L40): Docstring

> Whether this call is a write a person would want warned about.
>
> A DELETE always; else `201`; else an answer that names the record. The
> last two are signals this codebase already keeps -- `reversals.K_CREATED`
> and `records.names_in` -- and between them they separate the warehouse's
> writes from the page's own chatter exactly, on both tenants' whole
> evidence.
>
> A DELETE is not asked to prove anything, and it is the one method where
> that matters: removing a record is the most consequential thing a job can
> do and the answer to one is empty by nature -- 200 or 204, no body, nothing
> to name. A rule that made a delete earn its place would be silent about
> precisely the press a person most needs warning about, which is the undo.

## `_what_it_addresses`, [line 47](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L47): Docstring

> What the record is called, out of the path the call went to.
>
> A create addresses the COLLECTION -- `POST /wm/customerTypes` -- and a
> delete addresses one member of it -- `DELETE /wm/customerTypes/GDD`. Same
> structural rule `reversals.undoes` compares on, and the reason it cannot be
> "the last segment": on a delete that is the record's own id, so a card
> would offer to remove a `GDD` rather than a customer type.
>
> `path_shape` blanks a segment carrying a digit, and `*` names nothing --
> so a segment it blanked is dropped here for the same reason the id is.

## `_what_it_addresses`, [line 49](../../../../../../../backend/src/sro/domain/execution/what_it_writes.py#L49): Comment

Code: `if method == "DELETE" and len(pieces) > 1:`

> The member first, then the blanks. `path_shape` already blanked
> `/customerTypes/4471` and left `/customerTypes/GDD` alone, so dropping
> `*` first would take `customerTypes` off the numbered one and leave `wm`
> -- a card offering to remove a `wm`.
