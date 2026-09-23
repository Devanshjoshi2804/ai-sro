# Notes for `backend/src/sro/application/connection/cookies.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/cookies.py`](../../../../../../../backend/src/sro/application/connection/cookies.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/cookies.py#L1): Docstring

> Whether a stored cookie belongs to the host we are about to send it to.
>
> Both places that asked this asked it as ``host.endswith(domain)``, with a bare
> substring test as a second chance. ``"evil-wms.acme.com".endswith("wms.acme.com")``
> is true, and so is ``"wms.acme.com" in "wms.acme.com.attacker.test"`` -- so a
> lookalike host was read as carrying the customer's session, and could be handed
> one. Browsers have never matched this way: a cookie for ``acme.com`` goes to
> ``acme.com`` and to its subdomains, and to nothing that merely ends with it.
>
> The rule itself moved to ``domain/shared/hosts.py`` when observation policy
> needed the same one to decide whether a page is excluded from capture.

## `belongs_to`, [line 10](../../../../../../../backend/src/sro/application/connection/cookies.py#L10): Docstring

> Whether ``cookie`` would be sent to ``url``, by domain alone.
