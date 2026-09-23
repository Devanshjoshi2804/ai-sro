# Notes for `backend/src/sro/application/intent/spend.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/spend.py`](../../../../../../../backend/src/sro/application/intent/spend.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/spend.py#L1): Docstring

> What a tenant's day of model calls may cost before the rig stops asking.
>
> The rule is the rig's ``over_cap`` in ``new_agent_arch/src/rig/api.py``, and
> the number it judges comes from ``SpendRepository.today`` -- the ledger the
> metered client writes one row per model call into, summed since midnight UTC,
> with the blind rows counted beside the sum. This file judges; it queries
> nothing itself.
>
> Three things about the rule, each of them a decision rather than an accident:
>
> * **A cap that stops the ASKING is honest in a way a cap that stopped capture
>   would not be.** Evidence still arrives and is still stored, so raising the
>   cap tomorrow reads what today declined. Over the cap, the mining pass, the
>   chat door and a new run answer 429 with the sentence returned here, and the
>   reading loop simply does not ask.
> * **A negative cap means no cap**, which is what a deliberate one-off
>   measurement wants -- and it is answered before the repository is touched, so
>   the measurement does not pay for a query it has already opted out of. **Zero
>   disables the asking entirely**: nothing has been spent, and zero is still
>   reached.
> * **A day whose cost cannot be trusted is not a cheap day.** ``blind`` stops
>   the day just as hard as the dollars do, because a model name the price table
>   never knew about records $0.0000 with ``unpriced`` set: an unattended week on
>   a new preview name spends without limit while a guard reading ``cost_usd``
>   alone reads zero. This deployment lived that once -- the run that proved the
>   architecture billed $1.12 and every row said free.
>
> What bills is answered once, by the metered client every Gemini adapter is
> handed in ``container.py``; this file never names a table.

## `spent_today`, [line 11](../../../../../../../backend/src/sro/application/intent/spend.py#L11): Docstring

> The dollars and the blind calls this tenant has run up since midnight.
>
> A delegation, kept because the rule below and every caller that reports the
> day's bill want one name for it, and because ``now`` travelling this far is
> what lets a caller's clock -- not the server's -- decide which day is being
> asked about.

## `over_cap`, [line 15](../../../../../../../backend/src/sro/application/intent/spend.py#L15): Docstring

> Why the rig will not make another model call today, or ``None``.
>
> The sentence is the one a 429 carries and the log keeps: how much of what,
> so whoever reads it knows whether to raise the cap or to go and find the
> unpriced call.

## `over_cap`, [line 18](../../../../../../../backend/src/sro/application/intent/spend.py#L18): Comment

Code: `attribute(tenant=tenant_id.value)`

> Asking the cap is where model work for a tenant starts, so it is where the
> work is attributed: the metered client bills, and checks the cap of,
> whichever tenant `sro.whose` names. A loop over tenants -- the miner's --
> re-attributes on every tenant's first check rather than billing the next
> tenant's reading to the last one. Before the negative-cap return, so an
> uncapped deployment is attributed too.

## `over_cap`, [line 22](../../../../../../../backend/src/sro/application/intent/spend.py#L22): Comment

Code: `if day.cost_usd >= cap_usd or day.blind:`

> `>=`, not `>`: a cap is the amount that may be spent, so the day that
> spent exactly it has spent it. And `or day.blind`, because cost_usd
> alone cannot tell an honestly-cheap day from one whose bills were never
> priced -- the reason says both numbers so a reader can tell which stopped
> the day.
