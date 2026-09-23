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
from sro.domain.shared.errors import NotFound
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    NewSecretOnceRequest,
    NewSecretRequest,
    SecretHeldModel,
    SecretStoredModel,
)

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
        raise unusable
    return SecretStoredModel(key=key)


@router.post("/secrets/once", status_code=status.HTTP_202_ACCEPTED)
async def hold_secret_for_one_run(
    body: NewSecretOnceRequest, container: ContainerDep, ctx: ContextDep
) -> SecretHeldModel:
    """Keep one password for the next run that types it, and nowhere else.

    The other answer to the question `PUT /v1/secrets` asks. An operator
    signing into a system whose credential does not belong in this
    deployment's vault gives it for the run in front of them: it is held in
    memory, handed to that run and nothing else, and forgotten -- there is
    nothing to rotate and nothing to delete afterwards.

    `POST` and not `PUT`: this stores nothing. It is a value handed to the
    next step that asks, which is an action rather than a resource.

    No vault, so a deployment with none configured can still sign in by hand.
    What comes back is the key and when the value is forgotten -- never the
    value, for the reason the door above has no GET.
    """
    async with container.unit_of_work() as uow:
        run = await uow.workflow_runs.get(ctx.tenant_id, body.run_id)
    if run is None:
        raise NotFound(f"no such run: {body.run_id}")
    key = secret_key_of(ctx.tenant_id.value, body.system, body.field)
    until = container.one_time_secrets.hold(key, body.value, run_id=body.run_id)
    return SecretHeldModel(key=key, until=until)
