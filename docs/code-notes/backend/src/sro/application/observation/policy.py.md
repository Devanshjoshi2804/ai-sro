# Notes for `backend/src/sro/application/observation/policy.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/policy.py`](../../../../../../../backend/src/sro/application/observation/policy.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/policy.py#L1): Docstring

> Reading and changing what a tenant agreed to have observed.
>
> Changing it is not an endpoint. There is no role model here -- every credential
> for a tenant can do everything that tenant can do -- so an HTTP route to switch
> observation on would let any operator consent on their colleagues' behalf. It is
> a shell command for the same reason minting a credential is one.

## `current_policy`, [line 8](../../../../../../../backend/src/sro/application/observation/policy.py#L8): Docstring

> This tenant's policy, or the refusing default.
>
> Absence is not consent: a tenant nobody has configured captures nothing.

## `SetObservationPolicy`, [line 21](../../../../../../../backend/src/sro/application/observation/policy.py#L21): Docstring

> The shell's way in. Every change moves the version, so every extension
> picks it up on its next heartbeat.
