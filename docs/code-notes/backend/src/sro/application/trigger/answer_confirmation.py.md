# Notes for `backend/src/sro/application/trigger/answer_confirmation.py`

Comments and docstrings moved out of [`backend/src/sro/application/trigger/answer_confirmation.py`](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L1): Docstring

> Somebody answering a fire that was waiting for them.
>
> The run starts here rather than when the trigger went off, and it starts with
> the name of whoever pressed the button. That is the whole point of the queue:
> an unattended write happens because a person said so, minutes or hours later,
> and the record says which person.
>
> Nothing in this file starts anything on its own. `Sweep` marks the ones nobody
> answered as expired, and expiring runs nothing -- a write that happened because
> everybody was on holiday is the failure the ladder exists to prevent.

## `ReadConfirmations`, [line 115](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L115): Docstring

> What is waiting, oldest first.

## `ExpireConfirmations`, [line 124](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L124): Docstring

> Mark the ones nobody answered, so a screen can say so.
>
> `Confirmation.waiting_at` already refuses a late answer on read, so this
> changes nothing about what may run -- it is what turns "not answered yet"
> into "nobody looked", which is a different thing to read a month later and
> the only one worth changing how a team works over.

## `_refuse_unless_still_askable`, [line 143](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L143): Docstring

> The domain object holds both rules; this is where they are asked.
>
> Kept as a call rather than inlined twice, because approve and decline have
> to refuse for the same reasons -- a decline recorded against something that
> already ran would read as somebody having stopped it.

## `AnswerConfirmation.approve`, [line 46](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L46): Docstring

> Yes: run it, with this person's name on the run.
>
> The values are the ones frozen when it was asked. Re-reading the
> trigger here would let a change made in between turn a yes to one thing
> into a yes to another, and the person who pressed the button would
> carry the name on it.

## `AnswerConfirmation.decline`, [line 102](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L102): Docstring

> No. Kept rather than deleted: a card somebody turned down is the
> clearest evidence there is about a trigger that should not exist.

## `AnswerConfirmation.__init__`, [line 43](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L43): Comment

Code: `self._start_run = start_run`

> The job half, the same shape `dispatcher` has for the skill half:
> `None` in a process that cannot drive a browser.

## `AnswerConfirmation.approve`, [line 54](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L54): Comment

Code: `raise InvariantViolation(`

> Switched off between the fire and the answer. Approving it
> now would run a task somebody has since decided to stop.

## `AnswerConfirmation.approve`, [line 60](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L60): Comment

Code: `if self._start_run is None and self._dispatcher is None:`

> A mined job. Started the same way a fire starts one, for the
> reason the comment below gives about the skill path: a second
> start beside the first is how the first one's device_id got
> dropped. `authorized_by` is the person who answered.

## `AnswerConfirmation.approve`, [line 84](../../../../../../../backend/src/sro/application/trigger/answer_confirmation.py#L84): Comment

Code: `run_id = await start_for(`

> The same start a fire uses, rather than a second one beside it.
> This called `execute_skill` directly and quietly dropped the
> trigger's `device_id`, so a card for a task bound to the
> operator's own browser drove a browser this deployment owns --
> and failed to attach to a CDP endpoint nobody was listening on,
> with the card already marked approved. Found by pressing the
> button.
>
> `authorized_by` is the person who answered, not the person who
> made the trigger: an unattended write happens because somebody
> said so, and this is the somebody.
