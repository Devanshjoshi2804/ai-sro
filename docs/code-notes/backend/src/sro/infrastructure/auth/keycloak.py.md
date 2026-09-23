# Notes for `backend/src/sro/infrastructure/auth/keycloak.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/auth/keycloak.py`](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L1): Docstring

> Offline tokens from Keycloak, so a run does not depend on a browser session.
>
> The realm advertises what it will do -- `password`, `refresh_token` and the
> `offline_access` scope -- and the WMS behind it distinguishes a bad token from
> no credential at all: it answers a bearer it dislikes with 401 and a request
> with nothing at all with a redirect to the identity provider. That difference
> is what makes this worth building; an API that only understood cookies could
> not be given a token however good the token was.
>
> Two things are stored and they are not the same. The offline token is the thing
> worth protecting: it acts as the operator until somebody revokes it, so it
> lives in the vault and is never returned by anything. The access token it
> produces is short-lived and kept in memory only, refreshed when it is close
> enough to expiry that a slow call would outlive it.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L14): Note on the line above

Code: `_EARLY = 60.0`

> Seconds before expiry to refresh anyway. A token that dies mid-call fails a
> run for a reason that has nothing to do with the task.

## `KeycloakTokens._key`, [line 40](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L40): Docstring

> Tenant-scoped, like every other credential: one tenant's token must
> never authenticate another tenant's run.

## `KeycloakTokens.establish`, [line 43](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L43): Docstring

> One login, exchanged for something that outlives it.

## `KeycloakTokens.establish`, [line 50](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L50): Comment

Code: `"scope": "openid offline_access",`

> Without this the refresh token dies with the SSO session,
> which is the whole problem being solved.

## `KeycloakTokens.access_token`, [line 79](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L79): Comment

Code: `if rotated := answer.get("refresh_token"):`

> Rotation is on in some realms: the refresh that comes back replaces
> the one that produced it, and keeping the old one means the next
> refresh fails for a reason nobody would guess at.

## `KeycloakTokens._grant`, [line 102](../../../../../../../backend/src/sro/infrastructure/auth/keycloak.py#L102): Comment

Code: `detail = response.json().get("error_description") if _json(response) else response.text`

> The provider's own words, which name the actual problem --
> invalid_grant for a revoked token, unauthorized_client for a
> client that may not do this.
