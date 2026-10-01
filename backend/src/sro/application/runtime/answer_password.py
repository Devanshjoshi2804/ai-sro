from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.execution.account import Account
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import answers_for
from sro.domain.shared.errors import Conflict, NotFound


class AnswerPassword:
    """Store the password a run asked for and tell the run, in one door.

    The key is the one the broker reads, for the account the QUESTION names:
    the person never says which key, and the body never says whose. Checked
    before anything is stored, so a stranger, another question or a question
    that is not a password one stores nothing. Stored before the run is told,
    so a failed vault leaves the question standing for a second press; a
    press after a crash between the two stores the same value again.

    A different password than the vault's stays usable because a refusal
    names the password it refused (`RefusedCredentials.standing`); the same
    one stays refused, which is the lockout protection."""

    def __init__(
        self, uow: UnitOfWork, vault: CredentialVault, once: OneTimeSecrets, answer: AnswerRun
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._once = once
        self._answer = answer

    async def execute(
        self, ctx: RequestContext, *, run_id: str, question_id: str, value: str, keep: bool
    ) -> None:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise NotFound("no such run")
        if not answers_for(run, ctx.principal_id.value):
            raise Conflict("only the operator who started this run answers its questions")
        asking = Progress.of(run.progress).asking
        if (
            run.outcome != "running"
            or asking.get("id") != question_id
            or asking.get("kind") != "password"
            or asking.get("answered")
        ):
            raise Conflict("this run is not waiting on that password question")
        origin, username = asking.get("origin", ""), asking.get("username", "")
        if not origin or not username:
            raise Conflict(
                "this question does not say whose password it wants; "
                "store it with PUT /v1/secrets and answer with an empty value"
            )
        if not value:
            raise Conflict("a password is not empty")
        key = Account.of(ctx.tenant_id.value, origin, username).vault_key("password")
        if keep:
            await self._vault.store(key, value)
        else:
            self._once.hold(key, value, run_id=run_id)
        await self._answer.execute(ctx, run_id=run_id, question_id=question_id, value="")
