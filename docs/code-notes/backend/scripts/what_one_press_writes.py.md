# Notes for `backend/scripts/what_one_press_writes.py`

Comments and docstrings moved out of [`backend/scripts/what_one_press_writes.py`](../../../../backend/scripts/what_one_press_writes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/what_one_press_writes.py#L1): Docstring

> What one press of each mined job would write, and what depends on what.
>
>     uv run python scripts/what_one_press_writes.py            # acme and new
>     uv run python scripts/what_one_press_writes.py acme
>     uv run python scripts/what_one_press_writes.py --all      # every tenant in the store
>
> Reads only. Nothing here starts a run, touches a warehouse or writes a row.
>
> Written because three defects in one day came out of running the real code over
> the real store rather than over its own fixtures, and every one of them was
> invisible to a green suite:
>
> * the only `uses` edge in three tenants was a step depending on itself -- a
>   confirming read-back counted as a value the warehouse minted, and two steps
>   citing one click read the same call from both sides;
> * four steps stood on a doing that wrote TWICE, and the deterministic replay
>   sends one call, so a run made half a supplier and reported `held`;
> * the offer card, built on the single call a replay would send, named the
>   address a supplier create edits and never the supplier.
>
> So this is the shape of question that has to be asked of the store and not of a
> fixture. Four sections, each one a rule the product depends on:
>
>     1. what one press writes   what the card now says, per job
>     2. a Save that writes twice  the cascade the replay must refuse
>     3. which step uses which     `Step.uses`, as the producer reads it today
>     4. one job into another      the chain composition (7) has no instance of
>     5. what can be taken back    which job undoes which, and what the runs made
>     6. one call into the next    a cascade: a write carrying an id the write
>                                  before it returned, both behind one press
>
> Run it against a deployment by running it ON the deployment -- the settings
> already name that database, and a report about a store is worth what the store
> is.

## module, [line 22](../../../../backend/scripts/what_one_press_writes.py#L22): Note on the line above

Code: `K_RUNS = 500`

> How many runs back to read. Every run this system has ever done, on every
> deployment there is: the number is a bound, not a window.

## module, [line 24](../../../../backend/scripts/what_one_press_writes.py#L24): Note on the line above

Code: `_LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)`

> Every tenant that has ever uploaded. `tenants_since` is the one tenant-blind
> read this system has, and it is what "every tenant" can honestly mean here.

## `_what_a_press_writes`, [line 48](../../../../backend/scripts/what_one_press_writes.py#L48): Docstring

> Section 1. Exactly what the offer card will say before the press.

## `_a_save_that_writes_twice`, [line 64](../../../../backend/scripts/what_one_press_writes.py#L64): Docstring

> Section 2. One logical create is often several physical resources.
>
> Counted per DOING and only over writes the ledger recognises -- a step
> cites one gesture per demonstration, and the same click fires keepalives
> and telemetry. `plan_step` refuses the deterministic replay for exactly
> this shape; anything printed here is a step that now clicks Save instead.

## `_which_step_uses_which`, [line 90](../../../../backend/scripts/what_one_press_writes.py#L90): Docstring

> Section 3. `Step.uses`, read off the evidence rather than off the row.
>
> Printed beside what the STORE holds, because the two disagreeing is the
> interesting case: a job mined before the producer was fixed carries edges
> nothing would draw today.

## `_one_job_into_another`, [line 104](../../../../backend/scripts/what_one_press_writes.py#L104): Docstring

> Section 4. The chain item 7 needs and has never seen.
>
> A value one job's answer MINTED, taken by another job later in the same
> browsing stream. Minted means: in a mutation's response, not in its own
> request, and not typed or sent by anybody earlier in that stream -- which
> is the subtraction the first version of this measurement lacked, and it
> reported 329 chains on a tenant that has none.

## `_what_can_be_taken_back`, [line 128](../../../../backend/scripts/what_one_press_writes.py#L128): Docstring

> Section 5. The compensation story, as the store actually holds it.
>
> Three questions in one: which job undoes which (`reversals.undoes`, matched
> on the endpoint and never on a name), which runs made a record this system
> could address, and how many runs say which run they take back.
>
> The last is what `7aa7645d` added and is `0` until somebody presses an
> undo. It is here so that the day it is not zero, the pair is readable.

## `_one_call_into_the_next`, [line 161](../../../../backend/scripts/what_one_press_writes.py#L161): Docstring

> Section 6. The chain that is really there, one level below section 4.
>
> `KNOWLEDGE-BASE.md` 3b, watched on the live host: creating one client fires
> four POSTs behind a single Save -- addresses, clients, clientWarehouse,
> packingConfigurations -- **each carrying an id the one before it
> returned**. That is a value flowing out of one write's answer and into the
> next write's body, which is what composition IS; it happens inside one
> doing rather than between two jobs.
>
> `domain/execution/cascade.flows_in` is the rule, so this and `plan_step`
> read the evidence the same way.

## `_first_typed`, [line 181](../../../../backend/scripts/what_one_press_writes.py#L181): Docstring

> When each value was first typed or sent by anybody, across every stream.
>
> A value the operator typed at 10:01 and the server echoed at 10:05 is not a
> value the server made, and without this every read-back reads as a mint.
>
> Across streams and not within one, which the first version got wrong and
> tenant `new` said so: a stream is a BROWSER's lifetime, so an operator who
> signed in during an earlier one and then created a work area has a create
> whose answer carries `RKUCHIYAGM` -- their own username, stamped by the
> warehouse -- with no typing of it in that stream to subtract. Read per
> stream, that is a work-area job "producing" a value the login job "takes",
> which is two jobs sharing a person rather than a chain.

## `_put_in`, [line 216](../../../../backend/scripts/what_one_press_writes.py#L216): Docstring

> Everything this doing put in: typed into a control, or sent in a body.

## `_values`, [line 226](../../../../backend/scripts/what_one_press_writes.py#L226): Docstring

> A body's leaf strings, long enough to carry an identity.

## `_what_can_be_taken_back`, [line 134](../../../../backend/scripts/what_one_press_writes.py#L134): Comment

Code: `takes_back: dict[str, tuple[str, frozenset[str]]] = {}`

> Which job takes back which, and which field that job's delete addresses a
> record by -- the two halves the card needs before it can offer a press.

## `_what_can_be_taken_back`, [line 155](../../../../backend/scripts/what_one_press_writes.py#L155): Comment

Code: `asks = asks_for(by_job[other]) if other in by_job else None`

> What the press would actually send: the value, under the name the
> UNDO asks for. A press in the warehouse's vocabulary names a
> parameter the job does not have.
