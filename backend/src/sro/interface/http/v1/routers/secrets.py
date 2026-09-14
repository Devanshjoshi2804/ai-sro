"""Storing a password a run will type, and never reading one back.

The operator's question was why their browser fills the username, presses Sign
In, and leaves the password blank. Because the recorder strikes a secret field
out at the boundary and always will: a recorded password is a password in the
evidence plane, in a mining prompt, and in whatever a model does with one.

So a password is not recorded. It is STORED, once, deliberately, through this
door, and fetched by the run at the moment the step types it --
`domain/execution/secrets` builds the key from the system and the field, and
`workflow_runs` reads it from the vault and puts it in that one command.

**There is no GET here, and there will not be one.** The vault's own `get` is
reached by the runner and by nothing a browser can call. A route that answered
with a stored password would make every credential in the deployment one
leaked tenant token away from being read out, which is the whole thing a vault
is for.

**Tenant-only.** A browser proving itself with its own secret may not write one
either: this is the tenant's credential store, and the same argument
`tenant_only` makes for the model budget applies harder here.

The key is built here from `system` and `field` rather than accepted whole, so
a caller cannot write over another tenant's key by naming it: the tenant comes
from the credential and never from the body.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.application.ports.vault import VaultUnavailable
from sro.domain.execution.secrets import secret_key_of
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import NewSecretRequest, SecretStoredModel

router = APIRouter(tags=["secrets"], dependencies=[TenantOnly])


@router.put("/secrets", status_code=status.HTTP_200_OK)
async def store_secret(
    body: NewSecretRequest, container: ContainerDep, ctx: ContextDep
) -> SecretStoredModel:
    """Keep one password, so a run can type it without anybody recording it.

    `PUT` and not `POST`: storing the same key twice is a rotation, not a
    second credential, and the vault overwrites for exactly that reason.

    What comes back is the KEY and never the value -- so an operator can see
    what they stored under, check it against what a refused step said it
    wanted, and still have nothing readable in a browser history or a proxy
    log.
    """
    key = secret_key_of(ctx.tenant_id.value, body.system, body.field)
    try:
        await container.vault.store(key, body.value)
    except VaultUnavailable as unusable:
        # Deliberately not a 500. A deployment with no key configured is a
        # deployment that cannot keep a secret, and the honest answer is that
        # it refused rather than that something broke.
        raise unusable
    return SecretStoredModel(key=key)
