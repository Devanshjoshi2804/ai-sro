# Notes for `backend/src/sro/domain/trigger/confirmation.py`

Comments and docstrings moved out of [`backend/src/sro/domain/trigger/confirmation.py`](../../../../../../../backend/src/sro/domain/trigger/confirmation.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L1): Docstring

> A fire that is waiting for somebody to say yes.
>
> A manual trigger needs none of this: the click that fires it is the
> confirmation. A schedule and an inbound message both go off with nobody there
> to ask, and until now the only honest options were auto-approve -- chosen by a
> named person, for one trigger -- or refusing to create the trigger at all.
> `CreateTrigger` said so in as many words: *a write has nowhere to ask for
> confirmation yet*.
>
> This is the nowhere. The fire becomes an item, somebody answers it, and the run
> starts then and with their name on it.
>
> What it is not is a queue that drains itself. Nothing here starts a run because
> time passed; an item nobody answered expires, and expiring is a decision to do
> nothing rather than a decision deferred. The alternative -- a write that happens
> because everybody was on holiday -- is the failure this whole ladder exists to
> prevent.

## module, [line 19](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L19): Note on the line above

Code: `ANSWER_WITHIN = timedelta(hours=24)`

> How long an unanswered fire stays answerable.
>
> Long enough to survive a night and a weekend morning; short enough that
> approving one is still approving *this* mail rather than something that
> arrived on Tuesday. A warehouse instruction nobody looked at for a week is not
> an instruction any more, and asking somebody to judge one is asking them to
> guess at what was true then.

## `Answer`, [line 27](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L27): Note on the line above

Code: `EXPIRED = "expired"`

> Nobody answered in time. Its own answer rather than an absence: "we chose
> not to" and "we never looked" are different things to read a month later,
> and only one of them is worth changing how the team works.

## `Confirmation`, [line 31](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L31): Docstring

> One fire, and what somebody decided about it.

## `Confirmation`, [line 39](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L39): Note on the line above

Code: `workflow_id: str | None = None`

> What the fire would run. Exactly one, the same rule `Trigger` keeps and
> for the same reason: a card is a person being asked to authorise one
> particular thing, and one that named two would be asking about which?

## `Confirmation`, [line 41](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L41): Note on the line above

Code: `values: Mapping[str, str] = field(default_factory=dict)`

> What the run would go with, frozen at the moment it was asked.
>
> Not re-read from the trigger when somebody answers: what they are approving
> is what is written on the card in front of them. A trigger edited in
> between would otherwise turn a yes to one thing into a yes to another.

## `Confirmation`, [line 43](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L43): Note on the line above

Code: `because: str = ""`

> What made this fire -- the mail's subject, the schedule's name. The one
> sentence somebody reads before deciding.

## `Confirmation.runs`, [line 66](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L66): Docstring

> What this card would run, as an id, whichever kind it is.

## `Confirmation.waiting_at`, [line 69](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L69): Docstring

> Whether somebody can still answer this.
>
> Expiry is read rather than swept, for the same reason a grant's is: an
> item that has run out must stop being answerable the moment it does,
> and a job that has not run yet is not a thing to base that on.

## `Confirmation.expire`, [line 86](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L86): Docstring

> Nobody answered. Recorded rather than deleted: a fire that was asked
> about and left is evidence about how a team is working, and a row that
> disappeared would be evidence of nothing.

## `Confirmation._require_waiting`, [line 96](../../../../../../../backend/src/sro/domain/trigger/confirmation.py#L96): Comment

Code: `raise InvariantViolation(`

> Answering one that has run out is not a late yes, it is a yes to
> something nobody has looked at since. The trigger fires again if
> it is still true.
