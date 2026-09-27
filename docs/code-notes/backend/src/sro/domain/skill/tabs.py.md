# Notes for `backend/src/sro/domain/skill/tabs.py`

Notes for [`backend/src/sro/domain/skill/tabs.py`](../../../../../../../backend/src/sro/domain/skill/tabs.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 9](../../../../../../../backend/src/sro/domain/skill/tabs.py#L9): Note on the line above

Code: `from sro.domain.skill.workflow import MAIN, Step, Workflow`

> Tab roles (spec §5 "Learning"; A3, L4). `MAIN` is defined once, in
> `domain/skill/workflow.py`, and this module is its public home: `Step.tab`
> defaults to it, and `workflow.py` cannot import this module back, because
> `tabs.py` reads `primary_gesture` and `from_a_mailbox`, and both of their
> modules import `workflow.py`. Everything else imports `MAIN` from here.
>
> The popup kind is `PageEventKind.POPUP_OPENED`, the one the capture decoder
> writes; there is no second constant for it.

## `_acts_in`, [line 15](../../../../../../../backend/src/sro/domain/skill/tabs.py#L15): Docstring

> The gesture a step acts through is its `primary_gesture` -- the one the
> runtime acts on -- not its first cite: a step citing a scroll in another tab
> before its click acts in the click's tab.
>
> Only in the doing's stream, because a stream's tab ids are one browser's:
> two doings' tab ids mean nothing together. A mailbox gesture never names a
> tab: a mailbox step is run by the tool lane, not in the run's browser, so it
> keeps the role before it -- as does any step with no gesture (a learned
> field step, `with_field`, `keeping_fields`). That rule holds everywhere a
> step is made, not only here.

## `_openers`, [line 22](../../../../../../../backend/src/sro/domain/skill/tabs.py#L22): Docstring

> Every popup mark in the doing's stream, including marks on gestures the job
> does not cite (mining passes its whole pool, the sweep `evidence_of`'s
> surroundings) -- but only within the doing's own time span, from its first
> acting gesture to its last. Tab ids repeat across browser sessions, so a
> mark from an earlier sitting would otherwise name this doing's tab 9 after
> another doing's opener.

## `tab_roles`, [line 35](../../../../../../../backend/src/sro/domain/skill/tabs.py#L35): Docstring

> Code, not a model, names each step's tab role (L4). The doing is the stream
> of the first browser step's primary gesture. Tabs are named in the order of
> their first acting gesture's time, not in cite order, so a popup a model
> cited before its opener is never `main`: it becomes `opened_from:main`, and
> `unresolved` then says no earlier step opened it.
>
> - The first tab is `main`.
> - A tab a popup mark says was opened from a named tab R is `opened_from:R`.
> - A new tab with no known opener on a system an earlier tab is already on is
>   `tab_2`, `tab_3`, ...: a second tab of the same system (spec §5).
> - Any other new tab -- another system reached in a tab of its own, with no
>   opener seen -- takes no role: its steps act where the step before them
>   acted, and the run navigates there.
>
> Ceiling: two popups opened from the same role share one role name, so the
> later replaces the earlier in the run's role-to-tab map. Upgrade path: number
> them (`opened_from:main#2`) when a job needs both open at once.

## `undecided`, [line 80](../../../../../../../backend/src/sro/domain/skill/tabs.py#L80): Docstring

> A step stored before 0086 was never judged: its tab is NULL. Such a job is
> undecided until the mining sweep (`decide_tabs`) decides each such step from
> its evidence; meanwhile every reader takes the NULL as `main` (`Step.role`).

## `unresolved`, [line 84](../../../../../../../backend/src/sro/domain/skill/tabs.py#L84): Docstring

> The orders whose role the runtime could not open: `opened_from:R` with no
> earlier step in role R (there is no opener to click in), or a `tab_N` out of
> sequence (a `tab_3` before any `tab_2`). Read through `Step.role`, so an
> undecided step is `main` and never raises. `compile_job` turns each into
> `tab_role_unresolved`, but only for a decided job.
