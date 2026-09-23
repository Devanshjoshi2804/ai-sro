# Notes for `backend/src/sro/application/observation/record_attempt.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/record_attempt.py`](../../../../../../../backend/src/sro/application/observation/record_attempt.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/record_attempt.py#L1): Docstring

> Writing down what somebody asked for, from the door that answered them.
>
> The domain says what an attempt is. This is the one way to make one, and it
> exists so that a door can record one in a single line while it is busy doing
> something else -- because the doors that most need to are the ones in the
> middle of refusing somebody, and a recorder that takes five lines and a
> transaction is a recorder that does not get called.
>
> **It cannot fail the thing it records.** The repository swallows and logs its
> own errors, and this adds the other half: a caller passing something the
> domain refuses gets it written down as a fault here rather than raised into a
> door that was already answering. Nothing this returns is ever checked, and
> nothing in this system's behaviour reads the table.

## module, [line 13](../../../../../../../backend/src/sro/application/observation/record_attempt.py#L13): Note on the line above

Code: `ABOUT = ("run", "workflow", "thread", "device", "offer", "trigger", "command")`

> What an attempt may name. The telemetry plane's list, for its reason: this
> row leaves the tenant's deployment whenever somebody exports an audit, and a
> bag that can hold anything ends up holding what a customer is called.

## `RecordAttempt.execute`, [line 22](../../../../../../../backend/src/sro/application/observation/record_attempt.py#L22): Docstring

> One attempt, written where a person can read it back.
>
> `ctx` supplies who: the tenant it belongs to and the principal who
> asked. A door with no person behind it -- a trigger firing on its own
> schedule -- passes the tenant's own context and the principal comes out
> whatever that context carries, which is the honest answer rather than a
> name invented here.

## `RecordAttempt.execute`, [line 47](../../../../../../../backend/src/sro/application/observation/record_attempt.py#L47): Comment

Code: `logger.exception("an attempt could not be made: %s came to %s", asked_for, came_of)`

> A door asking for an outcome this system does not recognise is a
> bug in that door, and it is not one the person in front of it
> should be told about by a 500.

## `RecordAttempt.execute`, [line 51](../../../../../../../backend/src/sro/application/observation/record_attempt.py#L51): Comment

Code: `await uow.commit()`

> `__aexit__` closes the session and does not commit -- one request
> is one transaction and the caller says when it ends. Without
> this the insert was flushed and thrown away, silently, and the
> table stayed empty while every door reported having written to
> it.
