# Notes for `backend/src/sro/application/chat/brain.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/brain.py`](../../../../../../../backend/src/sro/application/chat/brain.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `Brain._turn`, [line 197](../../../../../../../backend/src/sro/application/chat/brain.py#L197): Comment

Code: `budget = budget or Budget(self._max_calls, self._max_turn_usd)`

> One message has one budget. A tool that reads on the model too (`check_mail` reads each
> mail with a dry brain turn of its own) is handed this object through `Turn` and spends from it,
> so a "check my mail" cannot make up to eight full turns outside the cap the outer turn keeps. A
> nested read that finds the budget gone leaves its mail unread (`ModelUnavailable`, never counted
> against the mail) for the next look.
