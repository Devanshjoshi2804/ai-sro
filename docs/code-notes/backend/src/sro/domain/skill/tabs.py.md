# Notes for `backend/src/sro/domain/skill/tabs.py`

Notes for [`backend/src/sro/domain/skill/tabs.py`](../../../../../../../backend/src/sro/domain/skill/tabs.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 8](../../../../../../../backend/src/sro/domain/skill/tabs.py#L8): Note on the line above

Code: `from sro.domain.skill.workflow import MAIN, Step, Workflow`

> Tab roles (spec §5 "Learning"; A3, L4). `MAIN` is defined once, in
> `domain/skill/workflow.py`, and this module is its public home: `Step.tab`
> defaults to it, and `workflow.py` cannot import this module back, because
> `tabs.py` reads `primary_gesture` and `from_a_mailbox`, and both of their
> modules import `workflow.py`. Everything else imports `MAIN` from here.

## `_in_one_doing`, [line 15](../../../../../../../backend/src/sro/domain/skill/tabs.py#L15): Docstring

> A step's gesture for its role is its first cite in the doing's stream. One
> doing, because a stream's tab ids are one browser's: two doings' tab ids
> mean nothing together, and a step citing both would otherwise read a tab of
> the second doing as a new tab of the first.
>
> A mailbox gesture never names a tab. A mailbox step is run by the tool lane,
> not in the run's browser, so it has no tab of its own and keeps the role
> before it.

## `tab_roles`, [line 23](../../../../../../../backend/src/sro/domain/skill/tabs.py#L23): Docstring

> Code, not a model, names each step's tab role (L4). The doing is the stream
> of the first browser step's primary gesture. The first tab seen is `main`;
> a tab a `popup_opened` mark says was opened from a tab already named R is
> `opened_from:R`; any other new tab is `tab_2`, `tab_3`, ... in the order
> they first appear. A step with no gesture in the doing keeps the role before
> it.
>
> The openers are read from every gesture in `by_id` in that stream, not only
> the cited ones: mining passes its whole pool, so a popup mark on a gesture
> nobody cited still counts. `compile_job` passes what it has; with only the
> cited evidence a popup whose mark is uncited reads as `tab_2` rather than
> `opened_from:main`, which is still not all `main`, so its
> `tab_roles_unlearned` check still fires.
>
> Ceiling: two popups opened from the same role share one role name, so the
> later replaces the earlier in the run's role-to-tab map. Upgrade path: number
> them (`opened_from:main#2`) when a job needs both open at once.

## `unresolved`, [line 63](../../../../../../../backend/src/sro/domain/skill/tabs.py#L63): Docstring

> The orders whose role the runtime could not open: `opened_from:R` with no
> earlier step in role R (there is no opener to click in), or a `tab_N` out of
> sequence (a `tab_3` before any `tab_2`). `compile_job` turns each into
> `tab_role_unresolved`.
